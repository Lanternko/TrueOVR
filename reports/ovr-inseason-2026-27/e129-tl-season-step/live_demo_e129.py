"""E-129 §2.5 live 示範合併：young(2026-27 bio AGE<=23)取 c=0.25 的 ovr，其餘取 c=0.5；基準 c=1。報告用，已看過資料，不算證據。"""
import csv, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S = Path(sys.argv[1])
def rd(c):
    with open(S / f'live_c{c}' / 'ranking.csv', encoding='utf-8') as f:
        return {r['playerId']: r for r in csv.DictReader(f)}
b, y, v = rd('1'), rd('0.25'), rd('0.5')
bio = json.load(open(ROOT / 'data/defense-seventh/2026-27/bio.json', encoding='utf-8'))
d = bio['data']
rs = d['resultSets'][0] if 'resultSets' in d else d
hd = rs['headers']; ix = {h: i for i, h in enumerate(hd)}
age = {str(r[ix['PLAYER_ID']]): r[ix['AGE']] for r in rs['rowSet']}
rows = []
for pid, r in b.items():
    a = age.get(pid)
    young = a is not None and float(a) <= 23
    w = (y if young else v).get(pid)
    if not w: continue
    rows.append({'playerId': pid, 'name': r['name'], 'team': r['team'], 'N': r['N'], 'age': a, 'group': 'young' if young else 'vet',
                 'ovr_base': r['ovr'], 'ovr_wstar': w['ovr'], 'dOVR': round(float(w['ovr']) - float(r['ovr']), 2)})
rows.sort(key=lambda r: -abs(r['dOVR']))
names = ['Cooper Flagg', 'Caleb Martin', 'Kon Knueppel', 'Stephon Castle']
sel = [r for r in rows if r['name'] in names]
top = rows[:10]
out = sel + [r for r in top if r not in sel]
with open(HERE / 'live-demo.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(out)
print(len(rows), 'players; max|dOVR|', abs(rows[0]['dOVR']))
for r in out: print(r)
