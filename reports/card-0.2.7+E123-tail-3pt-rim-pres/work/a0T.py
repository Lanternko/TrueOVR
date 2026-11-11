import sys, json, csv
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import e123lib as L
ref = list(csv.DictReader(open(L.ROOT/'reports/card-0.1.1+E057-three-value/three-value.csv', encoding='utf-8')))
t = L.t_season('2025-26')
nl = json.loads((L.V62/'new-long.json').read_text(encoding='utf-8'))
# E-057 規則：has = 在 new-long 且有 full 資料；池 = 三分 csv 的 MIN>=500（卡片 MIN）
rows = []
for r in ref:
    pid = int(r['playerId']); has = (str(pid) in nl) and (pid in t)
    rows.append(dict(pid=pid, name=r['name'], MIN=float(r['MIN']), has=has, ref=float(r['tv_main'])))
pool = [x for x in rows if x['MIN'] >= 500 and x['has']]
pv = [t[x['pid']]['value'] for x in pool]
diffs = []
for x in rows:
    v = L.attr_of(L.pct_js(t[x['pid']]['value'], pv)) if x['has'] else 70.0
    x['new'] = v; diffs.append((abs(v - x['ref']), x['name']))
diffs.sort(reverse=True)
# abilityC 對 new-long
dac = max(abs(t[int(k)]['acc'] - v['abilityC']) for k, v in nl.items() if int(k) in t and v['abilityC'] is not None and v['ability'] != v['abilityC'] or True and int(k) in t)
print(dict(n=len(rows), pool=len(pool), maxdiff=diffs[0], top3=diffs[:3], maxAbilityCdiff=dac))
json.dump(dict(n=len(rows), pool=len(pool), maxdiff=diffs[0][0], who=diffs[0][1], maxAbilityCdiff=dac), open('work/a0T-result.json','w'))
