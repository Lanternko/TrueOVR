"""產出 rookies-2026.csv 與 results.json（含前後 sha256）。"""
import csv
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'ovr-inseason-2026-27' / 'live'
SCR = Path(sys.argv[1])           # scratchpad
det = json.load(open(LIVE / 'e116-check-rookie/rookies-detail.json', encoding='utf-8'))
ABIL = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall',
        'help', 'stamina', 'creation', 'pressure', 'foulDraw']
cols = ['name', 'team', 'pick', 'pos', 'gp', 'ovr', 'lastOVR', 'rank'] + [f'x0_{a}' for a in ABIL] + \
       [f'w_{a}' for a in ABIL]
rows = []
for d in sorted(det, key=lambda d: d['pick']):
    r = {'name': d['name'], 'team': d['team'], 'pick': d['pick'], 'pos': d['pos'], 'gp': d['N'],
         'ovr': d['ovr'], 'lastOVR': d['lastOVR'], 'rank': d['rank']}
    for a in ABIL:
        r[f'x0_{a}'] = round(d['x0'][a], 1)
        w = d['w'].get(a)
        r[f'w_{a}'] = '' if w is None else round(w, 3)
    rows.append(r)
with open(HERE / 'rookies-2026.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, cols)
    w.writeheader()
    w.writerows(rows)

flags = subprocess.CREATE_NO_WINDOW
out = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(HERE / 'hashes.py'), str(SCR / 'hash-after.json')],
                     capture_output=True, text=True, creationflags=flags)
before = json.load(open(SCR / 'hash-before.json', encoding='utf-8'))
after = json.load(open(SCR / 'hash-after.json', encoding='utf-8'))
changed = {k: [before.get(k), after.get(k)] for k in set(before) | set(after) if before.get(k) != after.get(k)}
bt = json.load(open(HERE / 'backtest-results.json', encoding='utf-8'))
acc = json.load(open(HERE / 'accept.json', encoding='utf-8'))
fit = json.load(open(HERE / 'fit.json', encoding='utf-8'))
res = {'experiment': 'E-116', 'date': '2026-10-30', 'fit': {'nRookies': fit['nRookies'], 'perSeason': fit['perSeason']},
       'backtest': bt, 'acceptance': acc, 'sha256_before': before, 'sha256_after': after,
       'sha256_changed_inputs': changed, 'inputsUnchanged': not changed}
json.dump(res, open(HERE / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('changed', changed, 'rows', len(rows))
print(out.stdout[-300:], out.stderr[-300:])
for r in rows[:12]:
    print(r['name'], r['pick'], r['pos'], r['gp'], r['ovr'], r['lastOVR'], r['rank'])
