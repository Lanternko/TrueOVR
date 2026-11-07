import sys, json, csv
sys.path.insert(0, 'work')
import e123lib as L
h = L.h_season('2025-26')
ref = {int(r['playerId']): r for r in csv.DictReader(open(L.ROOT/'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv', encoding='utf-8'))}
card = {r['name']: float(r['help']) for r in csv.DictReader(open(L.ROOT/'reports/card-0.2.7/ranking.csv', encoding='utf-8'))}
diffs = []; nodata = 0
for pid, r in ref.items():
    v = h[pid]['help'] if pid in h else 70.0
    if pid not in h: nodata += 1
    diffs.append((abs(v - float(r['new_help'])), r['name']))
diffs.sort(reverse=True)
# 以姓名對卡 0.2.7
dn = []
for pid, r in ref.items():
    v = h[pid]['help'] if pid in h else 70.0
    if r['name'] in card: dn.append((abs(v - card[r['name']]), r['name']))
dn.sort(reverse=True)
res = dict(n=len(ref), nodata70=nodata, maxdiff_vs_defSource=diffs[:3], maxdiff_vs_card=dn[:3], matched=len(dn), rows2526=len(h))
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open('work/a0H-result.json','w'), ensure_ascii=False, indent=1)
