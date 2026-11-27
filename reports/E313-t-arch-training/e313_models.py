"""E-313 模型架構與損失函數（B0 / A1 / A2 / A3 / A4）。
所有模型的 forward(attr, pos, side) 皆回傳 [B, 2, out_dim]，
其中 out[..., 0] 一律為每回合得分相對季均值的預測（pts/poss - mean），
與既有 t_lib / e287_swap 推論介面完全相容。"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class LineupNetB0(nn.Module):
    """現行 E-227 LineupNet（B0 / A1 / A2 用）。"""
    def __init__(self, n_feat, out_dim=3, d=64, layers=2, heads=4, ff=128, drop=0.1):
        super().__init__()
        self.attr = nn.Linear(2 * n_feat, d)
        self.pos = nn.Embedding(5, d)
        self.side = nn.Embedding(2, d)
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, out_dim)

    def forward(self, attr, pos, side):
        x = self.attr(attr) + self.pos(pos) + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], 1))
        return self.head(h[:, :2])


class FeatureDropout(nn.Module):
    """對輸入特徵做隨機遮蔽（同時遮蔽 val 與對應 mask），抑制 noisy stat 過擬合。"""
    def __init__(self, p=0.10):
        super().__init__()
        self.p = p

    def forward(self, x):
        if not self.training or self.p <= 0.0:
            return x
        f = x.shape[-1] // 2
        keep = (torch.rand(x.shape[0], x.shape[1], f, device=x.device) >= self.p).float()
        scale = 1.0 / (1.0 - self.p)
        vals = x[..., :f] * keep * scale
        mask = x[..., f:] * keep
        return torch.cat([vals, mask], dim=-1)


class DecomposedLineupNet(nn.Module):
    """A3：加性個人主效應頭 + 2 層 Pre-LN Transformer 協同交互殘差。"""
    def __init__(self, n_feat, out_dim=5, d=96, layers=2, heads=4, ff=192, drop=0.15, feat_drop=0.10):
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
        # 加性主效應頭：輸出每個球員的基礎 (off_i, def_i)
        self.add_head = nn.Linear(d, 2)
        nn.init.normal_(self.add_head.weight, std=0.02)
        nn.init.zeros_(self.add_head.bias)

        # 交互殘差 Transformer
        self.cls = nn.Parameter(torch.zeros(2, d))
        enc = nn.TransformerEncoderLayer(d, heads, ff, dropout=drop, batch_first=True, norm_first=True, activation='gelu')
        self.enc = nn.TransformerEncoder(enc, layers, enable_nested_tensor=False)
        self.inter_head = nn.Linear(d, out_dim)
        nn.init.normal_(self.inter_head.weight, std=0.01)
        nn.init.zeros_(self.inter_head.bias)

    def player_effects(self, attr, pos):
        """回傳每個球員的加性 (off_i, def_i)，shape [B, 10, 2]。"""
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        return p, self.add_head(p)

    def forward(self, attr, pos, side):
        p, eff = self.player_effects(attr, pos)
        eff_a, eff_b = eff[:, :5], eff[:, 5:]
        # Team A 基礎得分 = mean(off_A) - mean(def_B)，Team B 對稱
        base_a = eff_a[..., 0].mean(dim=1) - eff_b[..., 1].mean(dim=1)
        base_b = eff_b[..., 0].mean(dim=1) - eff_a[..., 1].mean(dim=1)
        base = torch.stack([base_a, base_b], dim=1)  # [B, 2]

        x = p + self.side(side)
        c = self.cls.unsqueeze(0).expand(x.shape[0], -1, -1) + self.side.weight.unsqueeze(0)
        h = self.enc(torch.cat([c, x], dim=1))
        inter = self.inter_head(h[:, :2])  # [B, 2, out_dim]
        out = inter.clone()
        out[..., 0] = base + inter[..., 0]
        return out


class CrossAttnBlock(nn.Module):
    """Pre-LN Cross-Attention + FFN：進攻隊 (Q) attend 到防守隊 (K, V)。"""
    def __init__(self, d=96, heads=4, ff=192, drop=0.15):
        super().__init__()
        self.norm_q = nn.LayerNorm(d)
        self.norm_kv = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, heads, dropout=drop, batch_first=True)
        self.drop1 = nn.Dropout(drop)
        self.norm2 = nn.LayerNorm(d)
        self.ffn = nn.Sequential(
            nn.Linear(d, ff),
            nn.GELU(),
            nn.Dropout(drop),
            nn.Linear(ff, d),
            nn.Dropout(drop),
        )

    def forward(self, q, kv):
        h, _ = self.attn(self.norm_q(q), self.norm_kv(kv), self.norm_kv(kv), need_weights=False)
        q = q + self.drop1(h)
        q = q + self.ffn(self.norm2(q))
        return q


class TeamSelfCrossNet(nn.Module):
    """A4：嚴格對稱隊內 Self-Attention + 隊間 Cross-Attention + 加性個人主效應頭。
    結構保證交換 A/B 兩隊必然輸出精確對調結果。"""
    def __init__(self, n_feat, out_dim=5, d=96, heads=4, ff=192, drop=0.15, feat_drop=0.10):
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
        self.add_head = nn.Linear(d, 2)
        nn.init.normal_(self.add_head.weight, std=0.02)
        nn.init.zeros_(self.add_head.bias)

        # 隊內 Self-Attention（兩隊共享權重）
        self.self_layer = nn.TransformerEncoderLayer(
            d, heads, ff, dropout=drop, batch_first=True, norm_first=True, activation='gelu'
        )
        # 隊間 Cross-Attention（進攻 5 人 attend 防守 5 人，兩方向共享權重）
        self.cross_layer = CrossAttnBlock(d, heads, ff, drop)

        # Attention Pooling（將 5 人聚合為 1 個隊伍進攻表徵，並與對手防守平均拼接）
        self.pool_q = nn.Parameter(torch.randn(1, 1, d) * 0.02)
        self.pool_attn = nn.MultiheadAttention(d, heads, dropout=drop, batch_first=True)
        self.pool_norm = nn.LayerNorm(d)
        self.inter_head = nn.Sequential(
            nn.Linear(2 * d, d),
            nn.GELU(),
            nn.Dropout(drop),
            nn.Linear(d, out_dim),
        )
        nn.init.normal_(self.inter_head[-1].weight, std=0.01)
        nn.init.zeros_(self.inter_head[-1].bias)

    def player_effects(self, attr, pos):
        p = self.player_mlp(self.fdrop(attr)) + self.pos(pos)
        return p, self.add_head(p)

    def _side_out(self, own, opp):
        q = self.pool_q.expand(own.shape[0], -1, -1)
        pooled, _ = self.pool_attn(q, own, own, need_weights=False)
        own_vec = self.pool_norm(pooled.squeeze(1))
        opp_vec = opp.mean(dim=1)
        return self.inter_head(torch.cat([own_vec, opp_vec], dim=-1))

    def forward(self, attr, pos, side=None):
        p, eff = self.player_effects(attr, pos)
        pa, pb = p[:, :5], p[:, 5:]
        eff_a, eff_b = eff[:, :5], eff[:, 5:]

        base_a = eff_a[..., 0].mean(dim=1) - eff_b[..., 1].mean(dim=1)
        base_b = eff_b[..., 0].mean(dim=1) - eff_a[..., 1].mean(dim=1)
        base = torch.stack([base_a, base_b], dim=1)

        # 1. 隊內協同（兩隊並行且完全共享權重）
        sa = self.self_layer(pa)
        sb = self.self_layer(pb)

        # 2. 隊間對位（A 攻 vs B 守；B 攻 vs A 守，完全對稱）
        ma = self.cross_layer(sa, sb)
        mb = self.cross_layer(sb, sa)

        inter = torch.stack([self._side_out(ma, sb), self._side_out(mb, sa)], dim=1)
        out = inter.clone()
        out[..., 0] = base + inter[..., 0]
        return out


def build_model(arm, n_feat):
    if arm in ('B0', 'A1'):
        return LineupNetB0(n_feat, out_dim=3)
    if arm == 'A2':
        return LineupNetB0(n_feat, out_dim=5)
    if arm == 'A3':
        return DecomposedLineupNet(n_feat, out_dim=5)
    if arm == 'A4':
        return TeamSelfCrossNet(n_feat, out_dim=5)
    raise ValueError(f'unknown arm {arm}')


def loss_b0(out, y, stats):
    """現行 B0/A1 損失：l_pts + l_tov + l_orb（總和早停）。"""
    pts, poss, tov, orb, opp, mean = y[..., :6].unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    l_pts = (poss * (out[..., 0] - rate) ** 2).sum() / poss.sum() / stats['sigma2']
    p_t = torch.sigmoid(out[..., 1]).clamp(1e-5, 1 - 1e-5)
    tv = tov.clamp(max=poss)
    l_tov = -(tv * p_t.log() + (poss - tv).clamp(min=0) * (1 - p_t).log()).sum() / poss.sum()
    p_o = torch.sigmoid(out[..., 2]).clamp(1e-5, 1 - 1e-5)
    ob = orb.clamp(max=opp)
    l_orb = -(ob * p_o.log() + (opp - ob).clamp(min=0) * (1 - p_o).log()).sum() / opp.sum().clamp(min=1)
    tot = l_pts + l_tov + l_orb
    return tot, tot.item(), (l_pts.item(), l_tov.item(), l_orb.item())


def loss_a2(out, y, stats):
    """A2/A3/A4 損失：l_pts + 0.5*l_net + 0.15*l_aux；早停看 l_pts + 0.5*l_net。"""
    pts, poss, tov, orb, opp, mean, fga, efg_num, ftm = y.unbind(-1)
    rate = torch.where(poss > 0, pts / poss.clamp(min=1e-6), mean) - mean
    l_pts = (poss * (out[..., 0] - rate) ** 2).sum() / poss.sum().clamp(min=1e-6) / stats['sigma2']

    # 淨勝分差 loss（抵消同場吹罰/節奏共同雜訊）
    poss_min = torch.minimum(poss[:, 0], poss[:, 1])
    net_true = rate[:, 0] - rate[:, 1]
    net_pred = out[:, 0, 0] - out[:, 1, 0]
    l_net = (poss_min * (net_pred - net_true) ** 2).sum() / poss_min.sum().clamp(min=1e-6) / stats['sigma2_net']

    # 輔助四要素：TOV%, ORB%, eFG%, FTr
    p_t = torch.sigmoid(out[..., 1]).clamp(1e-5, 1 - 1e-5)
    tv = tov.clamp(max=poss)
    l_tov = -(tv * p_t.log() + (poss - tv).clamp(min=0) * (1 - p_t).log()).sum() / poss.sum().clamp(min=1e-6)

    p_o = torch.sigmoid(out[..., 2]).clamp(1e-5, 1 - 1e-5)
    ob = orb.clamp(max=opp)
    l_orb = -(ob * p_o.log() + (opp - ob).clamp(min=0) * (1 - p_o).log()).sum() / opp.sum().clamp(min=1)

    efg_true = torch.where(fga > 0, efg_num / fga.clamp(min=1e-6), torch.zeros_like(fga)) - stats['mean_efg']
    l_efg = (fga * (out[..., 3] - efg_true) ** 2).sum() / fga.sum().clamp(min=1e-6) / stats['sigma2_efg']

    ftr_true = torch.where(fga > 0, ftm / fga.clamp(min=1e-6), torch.zeros_like(fga)) - stats['mean_ftr']
    l_ftr = (fga * (out[..., 4] - ftr_true) ** 2).sum() / fga.sum().clamp(min=1e-6) / stats['sigma2_ftr']

    l_aux = l_tov + l_orb + l_efg + l_ftr
    main = l_pts + 0.5 * l_net
    tot = main + 0.15 * l_aux
    return tot, main.item(), (l_pts.item(), l_net.item(), l_aux.item())
