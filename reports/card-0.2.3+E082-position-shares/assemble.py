"""build_card_023.py 的同一組裝規則（rank、ovr、mpg、gRepl 取自 E-075 式 ranking；其餘取自 0.2.2 格式 ranking；列序 = E-075 名次序）。
用法：python -I reports/card-0.2.3+E082-position-shares/assemble.py <off|on>
off：輸出 out/off/ranking-023fmt.csv，只供核對（必須與 reports/card-0.2.3/ranking.csv 逐位元相同）。
on ：輸出 out/on/ranking-023fmt.csv，並複製為 reports/card-0.2.3+E082-position-shares/ranking.csv（候選）。
"""
import csv, hashlib, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
FROM_E075 = ['rank', 'ovr', 'mpg', 'gRepl']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rd(p): return list(csv.DictReader(Path(p).open(encoding='utf-8')))
mode = sys.argv[1]
a = rd(HERE / 'cards' / mode / 'ranking.csv'); b = rd(HERE / 'out' / mode / 'ranking.csv')
cols = list(a[0].keys()); A = {r['name']: r for r in a}
assert len(A) == len(a) == len(b) == 582 and set(A) == {r['name'] for r in b}
for r in b: assert r['mpg'] == r['mpgAvail'], r['name']
rows = []
for r in b:
    o = dict(A[r['name']])
    for c in FROM_E075: o[c] = r[c]
    rows.append(o)
assert [int(o['rank']) for o in rows] == list(range(1, 583))
out = HERE / 'out' / mode / 'ranking-023fmt.csv'
with out.open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)
print(mode, 'sha', sha(out))
if mode == 'on': shutil.copyfile(out, HERE / 'ranking.csv')
