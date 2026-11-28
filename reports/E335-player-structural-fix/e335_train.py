"""E-335（gpu5090-3）：球員 OVR 結構性修正重訓：
  1. 軟化高齡二次項：age_eff = min(age, 34.0) 算二次項，避免 38 歲高產球星（如 Curry）被 a_std^2=9.76 斷崖懲罰。
  2. 多季 EPM 先驗衰減改為 decay=0.35（更重視近一季，解決 Cade/LaMelo 被前兩年重建/傷病季拖低），保留正成長斜率。
  3. 同時執行兩階段：
     - blind25：訓練 2015-24、驗證 2024-25、嚴格盲測 2025-26（確認 GameBrier / EPM_Rho 不退反進）
     - prod26：訓練 2015-25、驗證 2025-26、產出 15 個正式 .pt 權重（DecayResNet / DecaySwiGLU / DecayTCNMix × 5 seeds）直推 2026-27！
"""
import argparse, csv, json, math, os, time
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.stats import spearmanr

SEASONS_LIST = [
    '2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20',
    '2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27'
]


def load_epm_all(epm_dir):
    by_s = {}
    for s_idx, sname in enumerate(SEASONS_LIST):
        fp = os.path.join(epm_dir, f'epm_{sname}.csv')
        if not os.path.exists(fp): continue
        mp = {}
        for r in csv.DictReader(open(fp, encoding='utf-8-sig')):
            poss = float(r.get('stintPoss') or 0)
            if poss >= 400:
                mp[int(r['playerId'])] = (float(r['O']), float(r['D']), float(r['net']), poss, min(1.5, (poss / 3000.0) ** 0.5))
        by_s[s_idx] = mp
    return by_s


def soften_age_in_stat(stat_raw):
    """把 stat_raw 裡 col -3 (a_std) 與 col -2 (a_std^2) 軟化：超過 34 歲（a_std > 2.125）不再二次方暴衝！"""
    st = stat_raw.copy()
    a_std = st[:, -3]
    a_soft = np.minimum(a_std, 2.125) + 0.35 * np.maximum(0.0, a_std - 2.125)
    st[:, -3] = a_soft
    st[:, -2] = np.minimum(a_soft * a_soft, 4.5)
    return st


def build_multiepm_features(by_s, meta, stat_soft, decay=0.35):
    n = len(meta)
    eo = np.zeros(n, np.float32); ed = np.zeros(n, np.float32)
    en = np.zeros(n, np.float32); ew = np.zeros(n, np.float32)
    nen = np.zeros(n, np.float32); new = np.zeros(n, np.float32)
    pf = np.zeros((n, 10), np.float32)
    age_z = stat_soft[:, -3]

    for i in range(n):
        s_idx = int(meta[i, 0]); pid = int(meta[i, 1])
        cur = by_s.get(s_idx, {}).get(pid)
        if cur is not None and cur[3] >= 600:
            eo[i], ed[i], en[i], ew[i] = cur[0], cur[1], cur[2], cur[4]
        nxt = by_s.get(s_idx + 1, {}).get(pid)
        if nxt is not None and nxt[3] >= 600:
            nen[i], new[i] = nxt[2], nxt[4]

        w_sum = 0.0; ao = 0.0; ad = 0.0; an = 0.0; mx_n = -10.0; prev_vals = []
        for dt in range(1, 5):
            rec = by_s.get(s_idx - dt, {}).get(pid)
            if rec is not None:
                w = rec[3] * (decay ** (dt - 1))
                ao += w * rec[0]; ad += w * rec[1]; an += w * rec[2]; w_sum += w
                if rec[2] > mx_n: mx_n = rec[2]
                prev_vals.append((dt, rec[2]))
        if w_sum > 0:
            # Lighter shrinkage (k=1000) so recent breakout seasons (Cade, LaMelo) shine through!
            mo = (ao - 0.5 * 1000.0) / (w_sum + 1000.0)
            md = (ad - 0.5 * 1000.0) / (w_sum + 1000.0)
            mn = (an - 1.0 * 1000.0) / (w_sum + 1000.0)
            last1 = prev_vals[0][1] if prev_vals[0][0] == 1 else mn
            has_l1 = 1.0 if prev_vals[0][0] == 1 else 0.0
            trend = (prev_vals[0][1] - prev_vals[1][1]) if len(prev_vals) >= 2 else 0.0
            pf[i] = [mo / 5.0, md / 5.0, mn / 5.0, math.log1p(w_sum) / 10.0,
                     last1 / 5.0, has_l1, trend / 5.0, mx_n / 5.0,
                     (age_z[i] * mn) / 5.0, 1.0]
    return eo, ed, en, ew, nen, new, pf


class DecayPoolHelper(nn.Module):
    def __init__(self, max_len=40, hls=(2.0, 5.0, 12.0, 25.0, 40.0)):
        super().__init__()
        pos = torch.arange(max_len - 1, -1, -1, dtype=torch.float32)
        ws = torch.stack([torch.exp(-pos / h) for h in hls], dim=0)
        self.register_buffer('ws', ws)
        self.n_scales = len(hls)

    def forward(self, seq):
        mask = seq[..., -1]; vals = seq[..., :-1]
        w = self.ws.unsqueeze(0) * mask.unsqueeze(1)
        w = w / w.sum(dim=-1, keepdim=True).clamp(min=1e-6)
        return torch.einsum('bkl,blf->bkf', w, vals).reshape(seq.size(0), -1)


class DecayResNet(nn.Module):
    def __init__(self, seq_dim, stat_dim, d=256, drop=0.22, max_len=40):
        super().__init__()
        self.pool = DecayPoolHelper(max_len)
        in_d = self.pool.n_scales * (seq_dim - 1) + stat_dim
        self.in_l = nn.Sequential(nn.Linear(in_d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop))
        self.blocks = nn.ModuleList([
            nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Dropout(drop), nn.Linear(d, d), nn.Dropout(drop))
            for _ in range(3)
        ])
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, 5)

    def forward(self, seq, stat):
        h = self.in_l(torch.cat([self.pool(seq), stat], dim=-1))
        for b in self.blocks: h = h + b(h)
        return self.head(self.ln(h))


class SwiGLUBlock(nn.Module):
    def __init__(self, d, drop=0.22):
        super().__init__()
        self.ln = nn.LayerNorm(d); self.w12 = nn.Linear(d, 2 * d); self.w3 = nn.Linear(d, d); self.drop = nn.Dropout(drop)

    def forward(self, x):
        a, b = self.w12(self.ln(x)).chunk(2, dim=-1)
        return x + self.drop(self.w3(self.drop(F.silu(a) * b)))


class DecaySwiGLU(nn.Module):
    def __init__(self, seq_dim, stat_dim, d=256, drop=0.22, max_len=40):
        super().__init__()
        self.pool = DecayPoolHelper(max_len)
        in_d = self.pool.n_scales * (seq_dim - 1) + stat_dim
        self.in_l = nn.Sequential(nn.Linear(in_d, d), nn.LayerNorm(d), nn.SiLU(), nn.Dropout(drop))
        self.blocks = nn.ModuleList([SwiGLUBlock(d, drop) for _ in range(3)])
        self.ln = nn.LayerNorm(d); self.head = nn.Linear(d, 5)

    def forward(self, seq, stat):
        h = self.in_l(torch.cat([self.pool(seq), stat], dim=-1))
        for b in self.blocks: h = b(h)
        return self.head(self.ln(h))


class DecayTCNMix(nn.Module):
    def __init__(self, seq_dim, stat_dim, d=192, drop=0.20, max_len=40):
        super().__init__()
        self.pool = DecayPoolHelper(max_len)
        self.in_c = nn.Conv1d(seq_dim, d // 2, 1)
        self.b1 = nn.Sequential(nn.Conv1d(d // 2, d // 2, 3, padding=1, dilation=1), nn.GELU(), nn.Dropout(drop))
        self.b2 = nn.Sequential(nn.Conv1d(d // 2, d // 2, 3, padding=2, dilation=2), nn.GELU(), nn.Dropout(drop))
        self.b3 = nn.Sequential(nn.Conv1d(d // 2, d // 2, 3, padding=4, dilation=4), nn.GELU(), nn.Dropout(drop))
        self.attn = nn.Linear(d // 2, 1)
        in_d = self.pool.n_scales * (seq_dim - 1) + stat_dim + d // 2
        self.net = nn.Sequential(
            nn.Linear(in_d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop),
            nn.Linear(d, d), nn.LayerNorm(d), nn.GELU(), nn.Dropout(drop),
        )
        self.head = nn.Linear(d, 5)

    def forward(self, seq, stat):
        mask = (seq[..., -1] > 0.5)
        x = self.in_c(seq.transpose(1, 2))
        x = x + self.b1(x) + self.b2(x) + self.b3(x)
        xt = x.transpose(1, 2)
        w = torch.softmax(self.attn(xt).squeeze(-1).masked_fill(~mask, -1e9), dim=-1)
        tcn_p = (xt * w.unsqueeze(-1)).sum(1) * mask.any(-1, keepdim=True).float()
        return self.head(self.net(torch.cat([self.pool(seq), stat, tcn_p], dim=-1)))


def make_model(fam, seq_dim, stat_dim, max_len):
    if fam == 'DecayResNet': return DecayResNet(seq_dim, stat_dim, max_len=max_len)
    if fam == 'DecaySwiGLU': return DecaySwiGLU(seq_dim, stat_dim, max_len=max_len)
    if fam == 'DecayTCNMix': return DecayTCNMix(seq_dim, stat_dim, max_len=max_len)
    raise ValueError(fam)


def eval_p1(pred, y1, y5, meta, epm_net, epm_w, label):
    r1 = float(spearmanr(pred, y1).statistic); r5 = float(spearmanr(pred, y5).statistic)
    m = (epm_w > 0)
    by_p = defaultdict(list); gt_p = {}
    for i in np.where(m)[0]:
        pid = int(meta[i, 1]); by_p[pid].append(float(pred[i])); gt_p[pid] = float(epm_net[i])
    r_epm = float(spearmanr([np.mean(by_p[p]) for p in by_p], [gt_p[p] for p in by_p]).statistic) if by_p else float('nan')

    by_g = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, -1])
    for i in range(len(pred)):
        gid = int(meta[i, 2]); ih = int(meta[i, 4]); mn = float(meta[i, 5]); w = int(meta[i, 6])
        g = by_g[gid]
        if ih == 1: g[0] += pred[i] * mn; g[1] += mn; g[4] = w
        else: g[2] += pred[i] * mn; g[3] += mn
    diffs, ys = [], []
    for g in by_g.values():
        if g[1] >= 180 and g[3] >= 180 and g[4] in (0, 1):
            diffs.append(g[0] / g[1] - g[2] / g[3]); ys.append(g[4])
    diffs = np.array(diffs); ys = np.array(ys)
    order = np.arange(len(diffs)); probs = np.zeros(len(diffs))
    for f in range(5):
        te = (order % 5 == f); tr = ~te
        a, b = 0.0, 0.25
        for _ in range(15):
            p = 1.0 / (1.0 + np.exp(-np.clip(a + b * diffs[tr], -20, 20)))
            w_ = p * (1.0 - p) + 1e-6
            g0 = (p - ys[tr]).sum(); g1 = ((p - ys[tr]) * diffs[tr]).sum()
            h00 = w_.sum(); h01 = (w_ * diffs[tr]).sum(); h11 = (w_ * diffs[tr] * diffs[tr]).sum() + 1e-4
            det = h00 * h11 - h01 * h01
            a -= (h11 * g0 - h01 * g1) / det; b -= (-h01 * g0 + h00 * g1) / det
        probs[te] = 1.0 / (1.0 + np.exp(-np.clip(a + b * diffs[te], -20, 20)))
    brier = float(np.mean((probs - ys) ** 2))
    print(f'  [{label:20s}] NextRho={r1:.4f} Fut5Rho={r5:.4f} EPM_Rho={r_epm:.4f} GameBrier={brier:.5f}', flush=True)
    return {'next_rho': round(r1, 5), 'fut5_rho': round(r5, 5), 'epm_rho': round(r_epm, 5) if not np.isnan(r_epm) else None, 'game_brier': round(brier, 5)}


def train_one(fam, seed, seq_tr, stat_tr, y5_tr, eo_tr, ed_tr, en_tr, ew_tr, nen_tr, new_tr, prev_tr,
              seq_va, stat_va, y5_va, en_va, ew_va, dev, lam_smooth=1.0, epochs=28, bs=1024, lr=1.2e-3):
    torch.manual_seed(seed); np.random.seed(seed)
    model = make_model(fam, seq_tr.shape[-1], stat_tr.shape[-1], seq_tr.shape[1]).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=3.5e-2)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    n = len(y5_tr)
    sq_tr_g = torch.from_numpy(seq_tr).to(dev); st_tr_g = torch.from_numpy(stat_tr).to(dev)
    y5_tr_g = torch.from_numpy(y5_tr).to(dev)
    eo_tr_g = torch.from_numpy(eo_tr).to(dev); ed_tr_g = torch.from_numpy(ed_tr).to(dev)
    en_tr_g = torch.from_numpy(en_tr).to(dev); ew_tr_g = torch.from_numpy(ew_tr).to(dev)
    nen_tr_g = torch.from_numpy(nen_tr).to(dev); new_tr_g = torch.from_numpy(new_tr).to(dev)
    pv_tr_g = torch.from_numpy(prev_tr).to(dev)
    sq_va_g = torch.from_numpy(seq_va).to(dev); st_va_g = torch.from_numpy(stat_va).to(dev)
    y5_va_g = torch.from_numpy(y5_va).to(dev); en_va_g = torch.from_numpy(en_va).to(dev); ew_va_g = torch.from_numpy(ew_va).to(dev)

    best_loss, best_st = 1e9, None
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n, device=dev)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            out = model(sq_tr_g[idx], st_tr_g[idx])
            l_gmsc = ((out[:, 0] - y5_tr_g[idx]) ** 2).mean()
            w_e = ew_tr_g[idx]; denom = w_e.sum().clamp(min=1.0)
            l_epm = (w_e * (out[:, 1] - en_tr_g[idx]) ** 2).sum() / denom
            l_od = (w_e * ((out[:, 2] - eo_tr_g[idx]) ** 2 + (out[:, 3] - ed_tr_g[idx]) ** 2)).sum() / denom
            w_n = new_tr_g[idx]; denom_n = w_n.sum().clamp(min=1.0)
            l_next = (w_n * (out[:, 4] - nen_tr_g[idx]) ** 2).sum() / denom_n
            loss = l_gmsc + 4.5 * l_epm + 2.0 * l_od + 4.0 * l_next
            if lam_smooth > 0:
                pv = pv_tr_g[idx]; has_pv = (pv >= 0)
                if has_pv.any():
                    out_p = model(sq_tr_g[pv[has_pv]], st_tr_g[pv[has_pv]])
                    loss = loss + lam_smooth * ((out[has_pv, 0] - out_p[:, 0]) ** 2).mean() \
                                + (lam_smooth * 4.5) * ((out[has_pv, 1] - out_p[:, 1]) ** 2).mean() \
                                + (lam_smooth * 4.0) * ((out[has_pv, 4] - out_p[:, 4]) ** 2).mean()
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
        sched.step()
        model.eval()
        with torch.no_grad():
            ov = torch.cat([model(sq_va_g[i:i + 4096], st_va_g[i:i + 4096]) for i in range(0, len(y5_va_g), 4096)], 0)
            vl = float(((ov[:, 0] - y5_va_g) ** 2).mean().item()) + 4.5 * float(((ew_va_g * (ov[:, 1] - en_va_g) ** 2).sum() / ew_va_g.sum().clamp(min=1.0)).item())
        if vl < best_loss:
            best_loss = vl; best_st = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_st)
    return model


def predict_arr(model, seq_np, stat_np, dev):
    model.eval()
    with torch.no_grad():
        return np.concatenate([model(torch.from_numpy(seq_np[i:i + 4096]).to(dev),
                                     torch.from_numpy(stat_np[i:i + 4096]).to(dev)).cpu().numpy()
                               for i in range(0, len(seq_np), 4096)], axis=0)


def run_split(tag, tr_max, va_idx, te_cond, save_dir, seq, stat, y1, y5, meta, eo, ed, en, ew, nen, new, dev, seeds=5):
    os.makedirs(save_dir, exist_ok=True)
    tr_mask = (meta[:, 0] >= 1) & (meta[:, 0] <= tr_max)
    va_mask = (meta[:, 0] == va_idx)
    te_mask = te_cond(meta[:, 0])
    new_m = np.where(meta[:, 0] <= tr_max - 1, new, 0.0).astype(np.float32)

    mu = stat[tr_mask].mean(axis=0, keepdims=True)
    sd = stat[tr_mask].std(axis=0, keepdims=True) + 1e-6
    stat_n = np.clip((stat - mu) / sd, -6.0, 6.0)

    tr_idx = np.where(tr_mask)[0]
    g2tr = np.full(len(meta), -1, dtype=np.int64); g2tr[tr_idx] = np.arange(len(tr_idx))
    raw_prev = meta[tr_idx, 7].astype(np.int64)
    prev_tr = np.where(raw_prev >= 0, g2tr[np.clip(raw_prev, 0, len(meta) - 1)], -1)

    print(f'=== E-335 {tag} train={tr_mask.sum()} val={va_mask.sum()} test={te_mask.sum()} ===', flush=True)
    fams = ['DecayResNet', 'DecaySwiGLU', 'DecayTCNMix']
    fam_va, fam_te = {}, {}
    fam_stats = {}
    for fam in fams:
        t0 = time.time(); pvas, ptes = [], []
        for s in range(seeds):
            m = train_one(fam, 700 + s * 41, seq[tr_mask], stat_n[tr_mask], y5[tr_mask],
                          eo[tr_mask], ed[tr_mask], en[tr_mask], ew[tr_mask], nen[tr_mask], new_m[tr_mask], prev_tr,
                          seq[va_mask], stat_n[va_mask], y5[va_mask], en[va_mask], ew[va_mask], dev)
            pvas.append(predict_arr(m, seq[va_mask], stat_n[va_mask], dev))
            ptes.append(predict_arr(m, seq[te_mask], stat_n[te_mask], dev))
            if tag == 'prod26':
                torch.save(m.state_dict(), os.path.join(save_dir, f'{fam}_s{s}.pt'))
        fam_va[fam] = np.mean(pvas, axis=0); fam_te[fam] = np.mean(ptes, axis=0)
        fam_stats[fam] = {
            'g_mu': float(fam_va[fam][:, 0].mean()), 'g_sd': float(fam_va[fam][:, 0].std() + 1e-8),
            'e_mu': float(fam_va[fam][:, 1].mean()), 'e_sd': float(fam_va[fam][:, 1].std() + 1e-8),
        }
        print(f'  {fam} done in {round(time.time()-t0)}s', flush=True)

    te_g = np.mean([(fam_te[f][:, 0] - fam_stats[f]['g_mu']) / fam_stats[f]['g_sd'] for f in fams], axis=0)
    te_e = np.mean([(fam_te[f][:, 1] - fam_stats[f]['e_mu']) / fam_stats[f]['e_sd'] for f in fams], axis=0)
    eval_p1(te_e, y1[te_mask], y5[te_mask], meta[te_mask], en[te_mask], ew[te_mask], f'{tag}_epm')
    eval_p1(0.40 * te_g + 0.60 * te_e, y1[te_mask], y5[te_mask], meta[te_mask], en[te_mask], ew[te_mask], f'{tag}_wE60')
    eval_p1(0.30 * te_g + 0.70 * te_e, y1[te_mask], y5[te_mask], meta[te_mask], en[te_mask], ew[te_mask], f'{tag}_wE70')
    if tag == 'prod26':
        json.dump(fam_stats, open(os.path.join(save_dir, 'e335_fam_stats.json'), 'w'), indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True); ap.add_argument('--epm', required=True); ap.add_argument('--out', required=True)
    args = ap.parse_args()
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    d = np.load(args.data)
    stat_soft = soften_age_in_stat(d['stat'].astype(np.float32))
    seq = d['seq'].astype(np.float32); y1 = d['y1'].astype(np.float32); y5 = d['y5'].astype(np.float32); meta = d['meta']
    by_s = load_epm_all(args.epm)
    eo, ed, en, ew, nen, new, pf = build_multiepm_features(by_s, meta, stat_soft, decay=0.35)
    stat = np.concatenate([stat_soft, pf], axis=1)

    run_split('blind25', 9, 10, lambda s: s >= 11, os.path.join(args.out, 'blind25'), seq, stat, y1, y5, meta, eo, ed, en, ew, nen, new, dev, seeds=3)
    run_split('prod26', 10, 11, lambda s: s == 12, os.path.join(args.out, 'weights_prod'), seq, stat, y1, y5, meta, eo, ed, en, ew, nen, new, dev, seeds=5)
    print('ALL_DONE_E335', flush=True)


if __name__ == '__main__':
    main()
