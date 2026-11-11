"""E-296 臂公式與映射（離線）。"""
import math, bisect
TAU, REF = 15.0, 36.0
R_REPL = -1.0134715809107337
ANC0 = {'PR1': -0.7540874490232479, 'PR50': 1.0022537396947306, 'PR99': 4.00779517584395, 'PR90': 2.1176, 'PR95': 2.5903}
def W(m): return (1 - math.exp(-m / TAU)) / (1 - math.exp(-REF / TAU))
def g_arm(D, m, arm):
    if arm == 'A0' or D >= 0: return D * W(m)
    kind, ms = arm.split('-')[0], float(arm.split('-')[1])
    if kind == 'A1': return D * W(ms)
    if kind == 'A2': return D * W(ms) * (1 - W(m)) / (1 - W(ms))
    raise ValueError(arm)
def omap(g, a):
    p1, p50, p99, p90, p95 = a['PR1'], a['PR50'], a['PR99'], a['PR90'], a['PR95']
    if g <= p50: return 40 + 30 * (g - p1) / (p50 - p1)
    if g >= p99: return 70 + 29 * (g - p50) / (p99 - p50)
    for x0, x1, y0, y1 in ((p50, p90, 70., 88.), (p90, p95, 88., 92.), (p95, p99, 92., 99.)):
        if g <= x1: return y0 + (y1 - y0) * (g - x0) / (x1 - x0)
def pct(x, s):
    lo, hi = bisect.bisect_left(s, x), bisect.bisect_right(s, x)
    return 100 * (lo + 0.5 * (hi - lo)) / len(s)
def pr1(vals):
    s = sorted(vals); return max(v for v in s if pct(v, s) <= 1)
ARMS = ['A0', 'A1-10', 'A1-15', 'A2-10', 'A2-15']
