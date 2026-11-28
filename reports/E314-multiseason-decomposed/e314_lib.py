"""E-314 共用模組：嚴格因果多季滑動窗口特徵（零洩漏）＋小容量強正則加性分解架構。"""
import csv, os
import numpy as np
import torch
import torch.nn as nn

SEASONS_ORD = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def load_minutes(e227_data_dir, season):
    """回傳 pid -> minutes (float) from stats-{season}.csv。"""
    out = {}
    fn = os.path.join(e227_data_dir, f'stats-{season}.csv')
    with open(fn, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            v = r.get('minutes')
            if v not in ('', None):
                out[r['pid']] = float(v)
    return out


def multi_season_feats(target_season, e227_mod, e227_common, decay=0.55, k_shrink=300.0):
    """嚴格因果多季滑動窗口特徵（只使用 t <= target_season）：
    - 前 15 欄 ATTRS（已是卡片多季窗口）：當季有值沿用，當季缺值往前補最近一季有值者。
    - 後 26 欄 STATS（單季統計）：分鐘 × decay^age 加權平均，並向 0 做 k_shrink=300 分鐘經驗貝氏收縮。
    回傳 pid -> (vals[41], mask[41])。"""
    idx = SEASONS_ORD.index(target_season)
    hist_seasons = SEASONS_ORD[:idx + 1]
    n_attr = len(e227_common.ATTRS)
    F = e227_mod.n_feat('stats')

    single = {s: e227_mod.base_feats(s, 'stats') for s in hist_seasons}
    mins = {s: load_minutes(e227_common.DATA, s) for s in hist_seasons}

    all_pids = set()
    for s in hist_seasons:
        all_pids.update(single[s].keys())

    out = {}
    for pid in all_pids:
        vals = np.zeros(F, np.float32)
        mask = np.zeros(F, np.float32)

        # 1. 前 15 欄 ATTRS：取 <= target_season 最近一季有值者
        for j in range(n_attr):
            for s in reversed(hist_seasons):
                p = single[s].get(pid)
                if p is not None and p[1][j] > 0.5:
                    vals[j] = p[0][j]
                    mask[j] = 1.0
                    break

        # 2. 後 26 欄 STATS：分鐘 × decay^age 加權 + 向 0 收縮
        num = np.zeros(F - n_attr, np.float64)
        den = np.zeros(F - n_attr, np.float64)
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
        vals[n_attr:][has] = (num[has] / (den[has] + k_shrink)).astype(np.float32)
        mask[n_attr:][has] = 1.0
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
    """現行 E-227 LineupNet（M2 用，與 A1 完全相同架構）。"""
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


class DecomposedSmall(nn.Module):
    """選項 B 主臂（D1 / M2D1）：小容量 d=64、強正則、加性個人主效應頭＋低幅度交互殘差。"""
    def __init__(self, n_feat, d=64, layers=2, heads=4, ff=128, drop=0.15, feat_drop=0.10):
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
        self.side = nn.Embedding(2, d)
        self.add_head = nn.Linear(d, 2)
        nn.init.normal_(self.add_head.weight, std=0.02)
        nn.init.zeros_(self.add_head.bias)

        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True, activation='gelu')
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.inter_head = nn.Linear(d, 3)
        nn.init.normal_(self.inter_head.weight, std=0.01)
        nn.init.zeros_(self.inter_head.bias)
        # 可學習殘差縮放，初始 0.1 抑制交互過擬合
        self.inter_scale = nn.Parameter(torch.tensor(0.1))

    def player_effects(self, attr, pos):
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        return p, self.add_head(p)

    def forward(self, attr, pos, side):
        p, eff = self.player_effects(attr, pos)
        eff_a, eff_b = eff[:, :5], eff[:, 5:]
        base_a = eff_a[..., 0].mean(dim=1) - eff_b[..., 1].mean(dim=1)
        base_b = eff_b[..., 0].mean(dim=1) - eff_a[..., 1].mean(dim=1)
        base = torch.stack([base_a, base_b], dim=1)

        x = p + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], dim=1))
        inter = self.inter_head(h[:, :2])
        out = inter.clone()
        out[..., 0] = base + self.inter_scale * inter[..., 0]
        return out


class AdditiveOnlyNet(nn.Module):
    """純加性個人模型（D_add）：無 Transformer 交互，直接加總五人攻防貢獻（同時預測 pts/tov/orb）。"""
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
        # 輸出 6 維：(off_pts, def_pts, off_tov, def_tov, off_orb, def_orb)
        self.add_head = nn.Linear(d, 6)
        nn.init.normal_(self.add_head.weight, std=0.02)
        nn.init.zeros_(self.add_head.bias)
        self.bias = nn.Parameter(torch.tensor([0.0, -1.9, -1.1]))

    def player_effects(self, attr, pos):
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        eff6 = self.add_head(p)
        return p, eff6[..., :2]

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
        out_a = torch.stack([pts_a, tov_a, orb_a], dim=-1)
        out_b = torch.stack([pts_b, tov_b, orb_b], dim=-1)
        return torch.stack([out_a, out_b], dim=1)


def build_model(arm, n_feat):
    if arm in ('A1', 'M1', 'M2'):
        return LineupNetA1(n_feat)
    if arm in ('D1', 'M2D1'):
        return DecomposedSmall(n_feat)
    if arm == 'D_add':
        return AdditiveOnlyNet(n_feat)
    raise ValueError(f'unknown arm {arm}')


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
    tot = l_pts + l_tov + l_orb
    return tot, (l_pts.item(), l_tov.item(), l_orb.item())
