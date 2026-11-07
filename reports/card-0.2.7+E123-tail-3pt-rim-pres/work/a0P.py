import sys, json, csv
sys.path.insert(0, 'work')
import e123lib as L
E = L.ROOT / 'reports/card-0.2.0+E071-pressure'
card = {r['name']: r for r in csv.DictReader(open(L.ROOT / 'reports/card-0.2.7/ranking.csv', encoding='utf-8'))}
res = {}
# 2025-26（卡片池）
p26 = L.p_season('2025-26', use_card_pool=True)
ref26 = {int(r['playerId']): r for r in csv.DictReader(open(E / 'force-2025-26.csv', encoding='utf-8'))}
d_force = max(abs(p26[i]['force'] - float(r['force'])) for i, r in ref26.items())
res['force2025-26_maxdiff'] = d_force; res['n26'] = len(ref26)
res['pool26'] = sum(1 for v in p26.values() if v['inPool'])
# 2024-25
p25 = L.p_season('2024-25')
ref25 = {int(r['playerId']): r for r in csv.DictReader(open(E / 'force-2024-25.csv', encoding='utf-8'))}
res['force2024-25_maxdiff'] = max(abs(p25[i]['force'] - float(r['force'])) for i, r in ref25.items()); res['n25'] = len(ref25)
# pressure / presDisplay vs card 0.2.7（以 name 對，卡片值 1 位小數）
dp, dd, n = [], [], 0
byname = {}
for i, v in p26.items(): byname.setdefault(v['name'], []).append(v)
worst = []
for nm, r in card.items():
    vs = byname.get(nm) or []
    if len(vs) != 1: continue
    v = vs[0]
    if not v['inPool'] and False: continue
    n += 1
    dp.append((abs(v['pressure'] - float(r['pressure'])), nm)); dd.append((abs(v['presDisplay'] - float(r['presDisplay'])), nm))
dp.sort(reverse=True); dd.sort(reverse=True)
res['matched'] = n; res['pressure_maxdiff'] = dp[:3]; res['presDisplay_maxdiff'] = dd[:3]
print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
json.dump(res, open('work/a0P-result.json', 'w'), default=float, indent=1)
