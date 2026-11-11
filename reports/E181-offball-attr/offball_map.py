"""E-181 共用：合併池百分位 → 屬性值（複製 E-101 build_e101.py 的 Pool／attr_of／top_tail／bot_tail／percentile_attr_merged，數式不變）。"""
import math
import numpy as np
CEIL, K_SD, Z9990 = 150.0, 1.96, 1.044


class Pool:
    def __init__(self, vals):
        self.v = [float(x) for x in vals]
        self.s = np.sort(np.array(self.v))
        self.n = len(self.v)

    def pct(self, x):
        lo = int(np.searchsorted(self.s, x, 'left'))
        hi = int(np.searchsorted(self.s, x, 'right'))
        return 100 * (lo + 0.5 * (hi - lo)) / self.n

    def r_at_least(self, q):
        return min(v for v in self.s.tolist() if self.pct(v) >= q)

    def r_at_most(self, q):
        return max(v for v in self.s.tolist() if self.pct(v) <= q)

    def anchors(self):
        r90, r99, r1 = self.r_at_least(90), self.r_at_least(99), self.r_at_most(1)
        sd = float(np.std(self.v))
        gap = (r99 - r90) / Z9990
        return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd), 'poolN': self.n}


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def top_tail(d, sd):
    return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, d) / (K_SD * sd)))


def bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


def map_merged(vals, pool, top=True, bot=True):
    an = pool.anchors()
    out = {}
    for pid, x in vals.items():
        p = pool.pct(x)
        if p >= 99 and top:
            out[pid] = top_tail(x - an['r99'], an['S'])
        elif p <= 1 and bot:
            out[pid] = bot_tail(an['r1'] - x, an['SD_pool'])
        else:
            out[pid] = attr_of(p)
    return out, an
