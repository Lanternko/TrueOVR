"""E-208 A 消融：D1–D3 把 creation 遮掉（模擬 Y2–Y6 沒有逐場 creationJ），看差多少。輸出 A-ablate.json。"""
import sys, json, statistics
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L
en = L.init(); L.install_split_creation(en)
res = {}
for s in ('D1', 'D2', 'D3'):
    pop = L.read_pop(s)
    rks = [L.make_rk(en, int(r['playerId']), r['name'], int(r['pick']), r['pos'], r['kind'], s) for r in pop]
    out = {}
    for tag, mask in (('with', False), ('masked', True)):
        old = en.SA.SEASON_MIN_SAMPLE['creation']
        if mask:
            en.SA.SEASON_MIN_SAMPLE['creation'] = 1e12
        rec = L.window_recs(en, s, rks, {rk['playerId']: (0, 20) for rk in rks})
        o = [L.window_ovr(en, rk, rec.get(rk['playerId'])) for rk in rks]
        en.SA.SEASON_MIN_SAMPLE['creation'] = old
        out[tag] = {'win20': [x['ovr'] for x in o], 'win20C': [x['ovrC'] for x in o]}
    d = [a - b for a, b in zip(out['masked']['win20'], out['with']['win20'])]
    dC = [a - b for a, b in zip(out['masked']['win20C'], out['with']['win20C'])]
    res[s] = {'n': len(rks), 'meanMaskedMinusWith': statistics.fmean(d), 'meanMaskedMinusWithC': statistics.fmean(dC),
              'medWith': statistics.median(out['with']['win20']), 'medMasked': statistics.median(out['masked']['win20'])}
    print(s, res[s])
json.dump(res, open(L.HERE / 'A-ablate.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
