"""E-315 共用模組：多季滑動窗口特徵（可調 decay/k）＋ 嚴格因果跨季 RAPM 先驗（2 欄）。"""
import csv, os
import numpy as np
import torch
import torch.nn as nn

SEASONS_ORD = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def load_minutes(e227_data_dir, season):
    out = {}
    with open(os.path.join(e227_data_dir, f'stats-{season}.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            v = r.get('minutes')
            if v not in ('', None):
                out[r['pid']] = float(v)
    return out


def build_features(target_season, e227_mod, e227_common, decay=0.55, k_shrink=300.0,
                   use_rapm=False, rapm_strict_past=False, rapm_decay=0.65):
    """建立 target_season 的嚴格因果多季特徵表：pid -> (vals[F], mask[F])。
    - 41 欄基礎多季特徵：同 E-314（t <= target_season）。
    - 若 use_rapm=True，追加 2 欄跨季 RAPM (off, def)：
      * rapm_strict_past=True（訓練時）：只用 t < target_season 的 exclnone（零同季洩漏）。
      * rapm_strict_past=False（賽前推論/T-swap）：用 t <= target_season 的 exclnone（對下一季完全為過去季）。
    """
    idx = SEASONS_ORD.index(target_season)
    hist_seasons = SEASONS_ORD[:idx + 1]
    n_attr = len(e227_common.ATTRS)
    F0 = e227_mod.n_feat('stats')
    F = F0 + (2 if use_rapm else 0)

    single = {s: e227_mod.base_feats(s, 'stats') for s in hist_seasons}
    mins = {s: load_minutes(e227_common.DATA, s) for s in hist_seasons}

    # 跨季 RAPM 來源季
    rapm_seasons = SEASONS_ORD[:idx] if rapm_strict_past else SEASONS_ORD[:idx + 1]
    rapm_tables = {s: e227_common.load_rapm(s, 'none') for s in rapm_seasons} if use_rapm else {}

    all_pids = set()
    for s in hist_seasons:
        all_pids.update(single[s].keys())
    for s in rapm_tables:
        all_pids.update(rapm_tables[s].keys())

    out = {}
    for pid in all_pids:
        vals = np.zeros(F, np.float32)
        mask = np.zeros(F, np.float32)

        for j in range(n_attr):
            for s in reversed(hist_seasons):
                p = single[s].get(pid)
                if p is not None and p[1][j] > 0.5:
                    vals[j] = p[0][j]
                    mask[j] = 1.0
                    break

        num = np.zeros(F0 - n_attr, np.float64)
        den = np.zeros(F0 - n_attr, np.float64)
        for t_i, s in enumerate(hist_seasons):
            p = single[s].get(pid)
            if p is None:
                continue
            age = idx - t_i
            m = mins[s].get(pid, 500.0)
            w = m * (decay ** age)
            mk = p[1][n_attr:] > 0.5
            num[mk] += w * p[0][n_attr:][mk]
            den[mk] += w

        has = den > 0
        vals[n_attr:F0][has] = (num[has] / (den[has] + k_shrink)).astype(np.float32)
        mask[n_attr:F0][has] = 1.0

        if use_rapm and rapm_seasons:
            ro_num = rd_num = r_den = 0.0
            last_r_idx = SEASONS_ORD.index(rapm_seasons[-1])
            for s in rapm_seasons:
                q = rapm_tables[s].get(pid)
                if q is not None and q[2] > 0:
                    age_r = last_r_idx - SEASONS_ORD.index(s)
                    w = rapm_decay ** age_r
                    ro_num += w * q[0]
                    rd_num += w * q[1]
                    r_den += w
            if r_den > 0:
                vals[F0] = float(ro_num / r_den)
                vals[F0 + 1] = float(rd_num / r_den)
                mask[F0] = mask[F0 + 1] = 1.0

        out[pid] = (vals, mask)
    return out


class FeatureDropout(nn.Module):
    def __init__(self, p=0.10):
        super().__init__()
        self.p = p

    def forward(self, x):
        if not self.training or self.p <= 0.0:
            return x
        f = x.shape[-1] // 2
        keep = (torch.rand(x.shape[0], x.shape[1], f, device=x.device) >= self.p).float()
        scale = 1.0 / (1.0 - self.p)
        return torch.cat([x[..., :f] * keep * scale, x[..., f:] * keep], dim=-1)


class LineupNetA1(nn.Module):
    def __init__(self, n_feat, d=64, layers=2, heads=4, ff=128, drop=0.1):
        super().__init__()
        self.attr = nn.Linear(2 * n_feat, d)
        self.pos = nn.Embedding(5, d)
        self.side = nn.Embedding(2, d)
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, 3)

    def forward(self, attr, pos, side):
        x = self.attr(attr) + self.pos(pos) + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], 1))
        return self.head(h[:, :2])


class AdditiveOnlyNet(nn.Module):
    def __init__(self, n_feat, d=64, drop=0.15, feat_drop=0.10):
        super().__init__()
        self.fdrop = FeatureDropout(feat_drop)
        self.player_mlp = nn.Sequential(
            nn.Linear(2 * n_feat, d),
            nn.LayerNorm(d),
            nn.GELU(),
            nn.Dropout(drop),
            nn.Linear(d, d),
            nn.LayerNorm(d),
        )
        self.pos = nn.Embedding(5, d)
        self.add_head = nn.Linear(d, 6)
        nn.init.normal_(self.add_head.weight, std=0.02)
        nn.init.zeros_(self.add_head.bias)
        self.bias = nn.Parameter(torch.tensor([0.0, -1.9, -1.1]))

    def player_effects(self, attr, pos):
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        return p, self.add_head(p)[..., :2]

    def forward(self, attr, pos, side=None):
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        e = self.add_head(p)
        ea, eb = e[:, :5], e[:, 5:]
        pts_a = ea[..., 0].mean(1) - eb[..., 1].mean(1) + self.bias[0]
        pts_b = eb[..., 0].mean(1) - ea[..., 1].mean(1) + self.bias[0]
        tov_a = ea[..., 2].mean(1) + eb[..., 3].mean(1) + self.bias[1]
        tov_b = eb[..., 2].mean(1) + ea[..., 3].mean(1) + self.bias[1]
        orb_a = ea[..., 4].mean(1) - eb[..., 5].mean(1) + self.bias[2]
        orb_b = eb[..., 4].mean(1) - ea[..., 5].mean(1) + self.bias[2]
        return torch.stack([torch.stack([pts_a, tov_a, orb_a], -1), torch.stack([pts_b, tov_b, orb_b], -1)], 1)


ARM_CFG = {
    'M2_RAPM':    dict(arch='lineup', decay=0.55, k=300.0, use_rapm=True,  wd=0.10),
    'D_add_RAPM': dict(arch='add',    decay=0.55, k=300.0, use_rapm=True,  wd=0.15),
    'M2_L':       dict(arch='lineup', decay=0.70, k=500.0, use_rapm=False, wd=0.10),
    'D_add_L':    dict(arch='add',    decay=0.70, k=500.0, use_rapm=True,  wd=0.15),
}


def build_model(arm, n_feat):
    return LineupNetA1(n_feat) if ARM_CFG[arm]['arch'] == 'lineup' else AdditiveOnlyNet(n_feat)


def loss_b0(out, y, sigma2):
    pts, poss, tov, orb, opp, mean = y.unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    l_pts = (poss * (out[..., 0] - rate) ** 2).sum() / poss.sum() / sigma2
    p_t = torch.sigmoid(out[..., 1]).clamp(1e-5, 1 - 1e-5)
    tv = tov.clamp(max=poss)
    l_tov = -(tv * p_t.log() + (poss - tv).clamp(min=0) * (1 - p_t).log()).sum() / poss.sum()
    p_o = torch.sigmoid(out[..., 2]).clamp(1e-5, 1 - 1e-5)
    ob = orb.clamp(max=opp)
    l_orb = -(ob * p_o.log() + (opp - ob).clamp(min=0) * (1 - p_o).log()).sum() / opp.sum().clamp(min=1)
    return l_pts + l_tov + l_orb, (l_pts.item(), l_tov.item(), l_orb.item())
