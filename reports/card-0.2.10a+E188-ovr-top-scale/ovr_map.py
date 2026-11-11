"""E-188 OVR 映射：PR50 以上四節點分段直線 (PR50,70)(PR90,A)(PR95,B)(PR99,99)；g ≤ PR50 與 g ≥ PR99 同舊 two_segment（≥PR99 用舊斜率 29/(PR99−PR50)）。
預註冊 reports/card-0.2.10a+E188-ovr-top-scale/preregistration.md §1；S3：A＝88、B＝92。"""
import numpy as np

S3 = {'A': 88.0, 'B': 92.0}


def qf(vals, mask, prc):
    """同 e094_t.qf（最近名次）。"""
    ref = np.sort(np.asarray(vals)[mask])
    return float(ref[int(round(prc / 100 * (len(ref) - 1)))])


def two_segment(x, p1, p50, p99):
    return np.where(x <= p50, 40 + 30 * (x - p1) / (p50 - p1), 70 + 29 * (x - p50) / (p99 - p50))


def ovr_map(g, an, A=S3['A'], B=S3['B']):
    g = np.asarray(g, float)
    old = two_segment(g, an['PR1'], an['PR50'], an['PR99'])
    mid = np.interp(g, [an['PR50'], an['PR90'], an['PR95'], an['PR99']], [70.0, A, B, 99.0])
    return np.where((g <= an['PR50']) | (g >= an['PR99']), old, mid)
