"""E-208 A 彙整：分組表（新 vs 舊）、斜率（描述用）。輸出 A-tables.json／A-tables.md。"""
import csv, json, statistics, math, sys
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L

rows = list(csv.DictReader(open(L.HERE / 'A-players.csv', encoding='utf-8')))
for r in rows:
    for k in ('curve', 'start', 'win20', 'seasonEnd', 'win20C', 'seasonEndC', 'old_ans0', 'old_ans5', 'old_ans10'):
        r[k] = float(r[k])
    r['pick'] = int(r['pick'])
    r['g'] = L.group_of(r['pick'], r['kind'])
    r['lnp'] = math.log(61 if r['kind'] == 'undrafted' else r['pick'])


def q(v, p):
    v = sorted(v)
    i = p * (len(v) - 1)
    j = int(i)
    return v[j] + (i - j) * (v[min(j + 1, len(v) - 1)] - v[j])


def tab(sub):
    out = {}
    for g, *_ in L.GROUPS:
        xs = [r for r in sub if r['g'] == g]
        if not xs:
            continue
        w = [r['win20'] for r in xs]
        wc = [r['win20C'] for r in xs]
        e = [r['seasonEnd'] for r in xs]
        ec = [r['seasonEndC'] for r in xs]
        o = [r['old_ans0'] for r in xs]
        cv = [r['curve'] for r in xs]
        out[g] = {'n': len(xs), 'curveMed': statistics.median(cv), 'newMed': statistics.median(w), 'newP75': q(w, .75),
                  'newAbove': sum(a > c for a, c in zip(w, cv)) / len(xs),
                  'newCMed': statistics.median(wc), 'newCP75': q(wc, .75), 'newCAbove': sum(a > c for a, c in zip(wc, cv)) / len(xs),
                  'endMed': statistics.median(e), 'endP75': q(e, .75), 'endAbove': sum(a > c for a, c in zip(e, cv)) / len(xs),
                  'endCMed': statistics.median(ec),
                  'oldMed': statistics.median(o), 'oldP75': q(o, .75), 'oldAbove': sum(a > c for a, c in zip(o, cv)) / len(xs),
                  'diffMean': statistics.fmean(a - b for a, b in zip(w, o)), 'diffMedian': statistics.median(a - b for a, b in zip(w, o)),
                  'diffC': statistics.fmean(a - b for a, b in zip(wc, o)),
                  'sdDiff': statistics.pstdev([a - b for a, b in zip(w, o)])}
    return out


def ols(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def slopes(sub):
    x = [r['lnp'] for r in sub]
    return {k: ols(x, [r[k] for r in sub]) for k in ('win20', 'win20C', 'seasonEnd', 'old_ans0', 'curve')}


res = {'all': tab(rows), 'D1-D3': tab([r for r in rows if r['season'] in ('D1', 'D2', 'D3')]),
       'D3': tab([r for r in rows if r['season'] == 'D3']),
       'Y2-Y6': tab([r for r in rows if r['season'] in ('Y2', 'Y3', 'Y5', 'Y6')]),
       'slopes': {'all': slopes(rows), 'D1-D3': slopes([r for r in rows if r['season'] in ('D1', 'D2', 'D3')])}}
per = {}
for s in L.SEASONS:
    sub = [r for r in rows if r['season'] == s]
    per[s] = {'n': len(sub), 'newMed': statistics.median(r['win20'] for r in sub), 'oldMed': statistics.median(r['old_ans0'] for r in sub),
              'curveMed': statistics.median(r['curve'] for r in sub), 'diffMean': statistics.fmean(r['win20'] - r['old_ans0'] for r in sub),
              'newAbove': sum(r['win20'] > r['curve'] for r in sub) / len(sub), 'oldAbove': sum(r['old_ans0'] > r['curve'] for r in sub) / len(sub)}
res['perSeason'] = per
res['overall'] = {'n': len(rows), 'diffMean': statistics.fmean(r['win20'] - r['old_ans0'] for r in rows),
                  'diffMeanC': statistics.fmean(r['win20C'] - r['old_ans0'] for r in rows),
                  'newAbove': sum(r['win20'] > r['curve'] for r in rows) / len(rows),
                  'oldAbove': sum(r['old_ans0'] > r['curve'] for r in rows) / len(rows)}
json.dump(res, open(L.HERE / 'A-tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k in ('all', 'D1-D3', 'D3', 'Y2-Y6'):
    print('==', k)
    for g, v in res[k].items():
        print(f"{g:6s} n={v['n']:3d} curve {v['curveMed']:.1f} | new med {v['newMed']:.1f} P75 {v['newP75']:.1f} above {v['newAbove']:.0%} | newC med {v['newCMed']:.1f} | end med {v['endMed']:.1f} above {v['endAbove']:.0%} | old med {v['oldMed']:.1f} P75 {v['oldP75']:.1f} above {v['oldAbove']:.0%} | diff mean {v['diffMean']:.1f} (C {v['diffC']:.1f})")
print(json.dumps(res['slopes'], ensure_ascii=False))
print(json.dumps(res['perSeason'], ensure_ascii=False, indent=0))
print(res['overall'])
