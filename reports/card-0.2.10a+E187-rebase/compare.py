"""E-187 改疊 0.2.10a 的比較：0.2.10a（凍結係數）、K6U（修正後 T6 只重擬合）、KAU、KRU、KJU。名次＝MIN>=900、平手取平均（同 F-125）；分段殘差＝JW 對修正後 T6 的殘差減前 25 名平均（L-100，同 E-187 top25_resid）。"""
import csv, hashlib, json, pickle, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
T6 = ROOT / 'reports/E142-card-target/phase1-work/cands/T6-2025-26.pkl'
ARMS = {'0.2.10a': ROOT / 'reports/card-0.2.10a/ranking.csv'} | {a: HERE / f'work/{a}-2025-26/out/ranking.csv' for a in ('K6U', 'KAU', 'KRU', 'KJU')}
KEY = ['Jalen Williams', 'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Victor Wembanyama', 'Anthony Edwards', 'Jalen Johnson', 'Scottie Barnes',
       'Franz Wagner', 'Paolo Banchero', 'Kevin Durant', 'Herbert Jones', 'Kon Knueppel', 'Cooper Flagg', 'LeBron James']
JW = 'Jalen Williams'
pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8-sig'))}
cand = pickle.load(open(T6, 'rb'))


def load(p):
    rows = [r for r in csv.DictReader(open(p, encoding='utf-8-sig')) if float(r['MIN']) >= 900]
    rk = rankdata(-np.array([float(r['ovr']) for r in rows]))
    return rows, {r['name']: float(k) for r, k in zip(rows, rk)}


def seg(rows, rk):
    ok = [r for r in rows if r['name'] in pid and pid[r['name']] in cand]
    o = np.array([float(r['ovr']) for r in ok]); y = np.array([cand[pid[r['name']]][0] for r in ok])
    X = np.c_[np.ones_like(o), o]; res = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    nm = [r['name'] for r in ok]; top = [i for i, n in enumerate(nm) if rk[n] <= 25]; j = nm.index(JW)
    return float(res[j] - res[top].mean())


out = {'T6_sha256': hashlib.sha256(T6.read_bytes()).hexdigest(), 'ranking_sha256': {a: hashlib.sha256(p.read_bytes()).hexdigest() for a, p in ARMS.items()}, 'arms': {}}
D = {a: load(p) for a, p in ARMS.items()}
base = D['0.2.10a'][1]
for a, (rows, rk) in D.items():
    ov = {r['name']: float(r['ovr']) for r in rows}
    out['arms'][a] = {'n900': len(rows), 'JW_rank': rk[JW], 'JW_ovr': ov[JW], 'seg_resid_vs_T6fixed': seg(rows, rk),
                      'moved10_top100_vs_0210a': sum(1 for n, k in base.items() if k <= 100 and abs(rk[n] - k) >= 10),
                      'key': {n: [rk.get(n), ov.get(n)] for n in KEY}}
(HERE / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print('arm', *[f'{k}' for k in ('JW_rank', 'JW_ovr', 'seg', 'moved')])
for a, v in out['arms'].items():
    print(a, v['JW_rank'], round(v['JW_ovr'], 1), round(v['seg_resid_vs_T6fixed'], 2), v['moved10_top100_vs_0210a'])
for n in KEY:
    print(n, ' | '.join(f"{out['arms'][a]['key'][n][0]}/{round(out['arms'][a]['key'][n][1] or 0,1)}" for a in out['arms']))
