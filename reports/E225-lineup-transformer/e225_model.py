"""E-225 第一版（R-157）：資料張量、Transformer、訓練迴圈。只讀 split=train（e225_common 硬擋）。
球員 token＝Linear([15 項能力值 z（T-min 再加每場上場時間 z）⊕ 缺值遮罩]) ＋ 位置 embedding（每段 stint 依當下五人推定）＋ 隊別 embedding（A／B）。
沒有 OVR、沒有球員 ID embedding、沒有球員×季偏移、沒有「少見球員」向量。"""
import time

import numpy as np
import torch
import torch.nn as nn

from e225_common import ATTRS, FEATS, load_players, load_rows

SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']
ARMS = {'T-min': True, 'T-nomin': False}   # arm -> 是否放每場上場時間


class LineupNet(nn.Module):
    def __init__(self, n_feat, d=64, layers=2, heads=4, ff=128, drop=0.1):
        super().__init__()
        self.attr = nn.Linear(2 * n_feat, d); self.pos = nn.Embedding(5, d); self.side = nn.Embedding(2, d)
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, 3)   # 每回合得分（偏離該季聯盟平均）、失誤 logit、進攻籃板 logit

    def forward(self, attr, pos, side):
        x = self.attr(attr) + self.pos(pos) + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], 1))
        return self.head(h[:, :2])   # [B, 2(A 進攻, B 進攻), 3]


def season_means(rows):
    out = {}
    for s in SEASONS:
        rs = [r for r in rows if r['season'] == s]
        out[s] = sum(r['ptsa'] + r['ptsb'] for r in rs) / sum(r['possa'] + r['possb'] for r in rs)
    return out


def tensors(rows, use_min, means, seasons=None):
    """回傳 attr[N,10,2F], pos[N,10], side[N,10], y[N,2,6]（pts,poss,tov,orb,rebOpp,mean）。"""
    P = {s: load_players(s, use_min) for s in (seasons or SEASONS)}
    F = len(FEATS) if use_min else len(ATTRS); N = len(rows)
    attr = np.zeros((N, 10, 2 * F), np.float32); pos = np.zeros((N, 10), np.int64)
    side = np.tile(np.r_[np.zeros(5), np.ones(5)].astype(np.int64), (N, 1))
    y = np.zeros((N, 2, 6), np.float32)
    for i, r in enumerate(rows):
        Ps = P[r['season']]; t = 0
        for x in 'ab':
            for j in range(5):
                p = Ps.get(r[x + str(j)])
                if p is not None:
                    attr[i, t, :F], attr[i, t, F:] = p[0], p[1]
                pos[i, t] = r[f'p{x}{j}']; t += 1
        for k, x in enumerate('ab'):
            y[i, k] = [r['pts' + x], r['poss' + x], r['tov' + x], r['orb' + x], r['rebOpp' + x], means[r['season']]]
    return [torch.from_numpy(a) for a in (attr, pos, side, y)]


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
    """訓練一次：folds 1-4 訓練、fold 0 驗證、早停（看驗證總損失），回傳 dict 與最佳 epoch 的驗證預測。"""
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
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
            best_parts = parts
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
