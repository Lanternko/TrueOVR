# E-208 追加：分鐘規則 (c) 最近實際分鐘、(d) 照能力值排（預註冊寫死）。prior＝該隊此前最多 10 場的 [[pid,min],…] 列表，pre＝季前預期 (b) 名單。
import collections
GUARD = {'PG', 'SG'}; CENTER = {'C'}
TEMPL = [36, 34, 32, 30, 28, 24, 20, 16, 12, 8]
def norm(items, n=10, total=240.0, cap=48.0):
    items = sorted(items, key=lambda t: -t[1])[:n]; items = [[p, m] for p, m in items if m > 0]
    for _ in range(50):
        t = sum(m for _, m in items); k = total / t; items = [[p, min(m * k, cap)] for p, m in items]
        if abs(sum(m for _, m in items) - total) < 1e-9: break
    return [[p, round(m, 6)] for p, m in items]
def rule_c(prior, pre):
    if not prior: return pre
    tot = collections.Counter()
    for r in prior:
        for p, m in r: tot[p] += m
    return norm([[p, v / len(prior)] for p, v in tot.items()])
def rule_d(prior, pre, ovr, pos):
    cand = []
    for r in prior:
        for p, _ in r:
            if p not in cand: cand.append(p)
    for p, _ in sorted(pre, key=lambda t: -t[1]):   # 不足 10 人：由季前名單依分鐘補
        if len(cand) >= 10: break
        if p not in cand: cand.append(p)
    R = sorted(cand, key=lambda p: (-ovr(p), p))
    S = R[:5]
    for want, st in ((GUARD, 2), (CENTER, 1)):
        while sum(pos(p) in want for p in S) < st:
            out = [p for p in R if p not in S and pos(p) in want]
            if not out: break
            keep = [p for p in S if pos(p) in want]
            drop = [p for p in reversed(S) if pos(p) not in want and not (want is GUARD and pos(p) in CENTER and sum(pos(q) in CENTER for q in S) == 1) and not (want is CENTER and pos(p) in GUARD and sum(pos(q) in GUARD for q in S) <= 2)]
            if not drop: break
            S = [p for p in S if p != drop[0]] + [out[0]]
    S = sorted(S, key=lambda p: (-ovr(p), p)); rest = [p for p in R if p not in S][:5]
    return [[p, float(m)] for p, m in zip(S + rest, TEMPL)]
