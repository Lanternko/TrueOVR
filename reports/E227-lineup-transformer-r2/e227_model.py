"""E-227（R-159）模型與資料張量。Transformer 與 E-225 同結構（d64／2 層／4 頭，無分鐘、無球員 ID），三個臂只差球員 token 的特徵：
R2-abil＝15 能力值；R2-stats＝＋26 項統計向量；R2-stats-rapm＝再＋訓練 stint RAPM（進攻、防守）。每個特徵＝季內 z 分數＋缺值遮罩（遮罩另成一欄）。
只讀 data/（內含 split=train，測試場次根本不在目錄）。"""
import time

import numpy as np
import torch
import torch.nn as nn

from e227_common import ARMS, ATTRS, SEASONS, STATS, load_player_table, load_rapm, load_rows

_CACHE = {}


def base_feats(season, kind):
    """pid -> (vals[F0], mask[F0])，F0＝能力值（＋統計）；z 分數於季內，樣本<10 或常數的欄位整欄缺值。"""
    k = (season, kind)
    if k in _CACHE:
        return _CACHE[k]
    tab = load_player_table(season); cols = ATTRS + (STATS if kind != 'abil' else [])
    out = {p: (np.zeros(len(cols), np.float32), np.zeros(len(cols), np.float32)) for p in tab}
    for j, c in enumerate(cols):
        v = [d[c] for d in tab.values() if d.get(c) is not None]
        if len(v) < 10 or np.std(v) < 1e-9:
            continue
        mu, sd = float(np.mean(v)), float(np.std(v))
        for p, d in tab.items():
            if d.get(c) is not None:
                out[p][0][j] = (d[c] - mu) / sd; out[p][1][j] = 1.0
    _CACHE[k] = out
    return out


def n_feat(kind):
    return len(ATTRS) + (len(STATS) if kind != 'abil' else 0) + (2 if kind == 'stats-rapm' else 0)


def season_means(rows):
    out = {}
    for s in SEASONS:
        rs = [r for r in rows if r['season'] == s]
        if rs:
            out[s] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
    return out


def rapm_key(r, mode):
    """mode 'val'：驗證列（fold 0）用排除 fold 0 的擬合；'train'：訓練列在 fold k 用排除 {0,k} 的 out-of-fold 擬合。"""
    if mode == 'test':   # 測試／前向列：用全部 train 場次擬合的版本（key none）
        return 'none'
    return '0' if mode == 'val' else f"0-{r['fold']}"


def tensors(rows, kind, means, mode):
    """回傳 attr[N,10,2F]、pos[N,10]、side[N,10]、y[N,2,6]（pts,poss,tov,orb,rebOpp,mean）。"""
    F = n_feat(kind); F0 = F - (2 if kind == 'stats-rapm' else 0); N = len(rows)
    attr = np.zeros((N, 10, 2 * F), np.float32); pos = np.zeros((N, 10), np.int64)
    side = np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (N, 1)); y = np.zeros((N, 2, 6), np.float32)
    B = {s: base_feats(s, kind) for s in {r['season'] for r in rows}}; RC = {}
    for i, r in enumerate(rows):
        Bs = B[r['season']]; t = 0
        if kind == 'stats-rapm':
            kk = (r['season'], rapm_key(r, mode))
            if kk not in RC:
                RC[kk] = load_rapm(*kk)
            Rs = RC[kk]
        for x in 'ab':
            for j in range(5):
                pid = r[x + str(j)]; p = Bs.get(pid)
                if p is not None:
                    attr[i, t, :F0], attr[i, t, F:F + F0] = p[0], p[1]
                if kind == 'stats-rapm':
                    q = Rs.get(pid)
                    if q is not None and q[2] > 0:
                        attr[i, t, F0], attr[i, t, F0 + 1] = q[0], q[1]; attr[i, t, F + F0] = attr[i, t, F + F0 + 1] = 1.0
                pos[i, t] = r[f'p{x}{j}']; t += 1
        for k, x in enumerate('ab'):
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], means[r['season']]]
    return [torch.from_numpy(a) for a in (attr, pos, side, y)]


class LineupNet(nn.Module):
    def __init__(self, n_feat, d=64, layers=2, heads=4, ff=128, drop=0.1):
        super().__init__()
        self.attr = nn.Linear(2 * n_feat, d); self.pos = nn.Embedding(5, d); self.side = nn.Embedding(2, d)
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, 3)

    def forward(self, attr, pos, side):
        x = self.attr(attr) + self.pos(pos) + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], 1))
        return self.head(h[:, :2])


def loss_fn(out, y, sigma2):
    pts, poss, tov, orb, opp, mean = y.unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    l_pts = (poss * (out[..., 0] - rate) ** 2).sum() / poss.sum() / sigma2
    p_t = torch.sigmoid(out[..., 1]).clamp(1e-5, 1 - 1e-5); tv = tov.clamp(max=poss)
    l_tov = -(tv * p_t.log() + (poss - tv).clamp(min=0) * (1 - p_t).log()).sum() / poss.sum()
    p_o = torch.sigmoid(out[..., 2]).clamp(1e-5, 1 - 1e-5); ob = orb.clamp(max=opp)
    l_orb = -(ob * p_o.log() + (opp - ob).clamp(min=0) * (1 - p_o).log()).sum() / opp.sum().clamp(min=1)
    return l_pts + l_tov + l_orb, (l_pts.item(), l_tov.item(), l_orb.item())


def sigma2_of(rows, means):
    num = den = 0.0
    for r in rows:
        for x in 'ab':
            p = r['poss' + x]
            if p > 0:
                num += p * (r['pts' + x] / p - means[r['season']]) ** 2; den += p
    return num / den


def predict(net, T, dev, bs=4096):
    net.eval(); outs = []
    with torch.no_grad():
        for b in range(0, len(T[0]), bs):
            outs.append(net(*(t[b:b + bs].to(dev) for t in T[:3])).cpu())
    return torch.cat(outs)


def run(arm, lr, wd, seed, Tt, Tv, sigma2, dev, max_epochs=60, patience=5, bs=1024, return_state=False):
    """folds 1-4 訓練、fold 0 驗證與早停（看驗證總損失）。"""
    torch.manual_seed(seed); np.random.seed(seed)
    F = Tt[0].shape[-1] // 2
    net = LineupNet(F).to(dev); opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=wd)
    Tt_d = [t.to(dev) for t in Tt]; Tv_d = [t.to(dev) for t in Tv]
    best, best_ep, best_state, bad, hist, best_parts = 1e9, 0, None, 0, [], None
    t0 = time.time()
    for ep in range(1, max_epochs + 1):
        net.train(); perm = torch.randperm(len(Tt_d[0]), device=dev)
        for b in range(0, len(perm), bs):
            ix = perm[b:b + bs]
            loss, _ = loss_fn(net(*(t[ix] for t in Tt_d[:3])), Tt_d[3][ix], sigma2)
            opt.zero_grad(); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            tot, parts = loss_fn(net(*Tv_d[:3]), Tv_d[3], sigma2)
        hist.append(round(tot.item(), 5))
        if tot.item() < best - 1e-6:
            best, best_ep, bad = tot.item(), ep, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}; best_parts = parts
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(best_state)
    pred = predict(net, Tv, dev)
    info = {'arm': arm, 'lr': lr, 'wd': wd, 'seed': seed, 'valLoss': round(best, 5), 'bestEpoch': best_ep, 'epochs': len(hist),
            'parts(pts,tov,orb)': [round(v, 5) for v in best_parts], 'params': sum(p.numel() for p in net.parameters()),
            'seconds': round(time.time() - t0, 1), 'hist': hist}
    return (info, pred.numpy(), {k: v.cpu() for k, v in best_state.items()}) if return_state else (info, pred.numpy())
