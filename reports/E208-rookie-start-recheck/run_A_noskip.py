"""E-208 A 消融：把現行 SKIP=(pressure,drive,tovSkill) 拿掉（跟 E-141 舊答案一樣讓 drive／tovSkill 吃視窗值），看新 vs 舊差多少。輸出 A-noskip.json。"""
import sys, json, statistics as S, csv
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L
en = L.init(); L.install_split_creation(en)
rows = []
for s in L.SEASONS:
    pop = L.read_pop(s)
    rks = [L.make_rk(en, int(r['playerId']), r['name'], int(r['pick']), r['pos'], r['kind'], s) for r in pop]
    with L.mask_creation(en, s):
        rec = L.window_recs(en, s, rks, {rk['playerId']: (0, 20) for rk in rks})
        base = [L.window_ovr(en, rk, rec.get(rk['playerId']))['ovr'] for rk in rks]
        keep = L.RW.SKIP
        L.RW.SKIP = ()
        try:
            ns_ = [L.window_ovr(en, rk, rec.get(rk['playerId']))['ovr'] for rk in rks]
        finally:
            L.RW.SKIP = keep
    for r, rk, a, b in zip(pop, rks, base, ns_):
        rows.append({'season': s, 'pick': rk['pick'], 'kind': rk['kind'], 'g': L.group_of(rk['pick'], rk['kind']), 'new': a, 'noSkip': b, 'old': float(r['ans0'])})
out = {}
for g in ['ALL'] + [x[0] for x in L.GROUPS]:
    xs = [r for r in rows if g == 'ALL' or r['g'] == g]
    out[g] = {'n': len(xs), 'new-old': S.fmean(r['new'] - r['old'] for r in xs), 'noSkip-old': S.fmean(r['noSkip'] - r['old'] for r in xs),
              'noSkip-new': S.fmean(r['noSkip'] - r['new'] for r in xs)}
    print(g, {k: round(v, 2) if isinstance(v, float) else v for k, v in out[g].items()})
json.dump(out, open(L.HERE / 'A-noskip.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
