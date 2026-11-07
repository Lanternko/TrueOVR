"""E-142：合併 2K 判定用檔（errata-2 §4）。規則在看任何結果前寫定：
2K24／2K25／2K26 優先用補抓的 data/external-impact/2k/2k{24,25,26}-launch.csv（同一人多列取 snapshot_date 最早者），
補抓檔沒有的人退回舊檔 2k_yearly_ovr.csv；2K27 用舊檔。姓名用 c0l_check.norm 對齊，輸出用舊檔的姓名（新檔獨有者用新檔姓名）。"""
import csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from c0l_check import norm

R = Path(__file__).resolve().parents[2]
OLD = R / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv'
NEW = {ed: R / f'data/external-impact/2k/{ed.lower()}-launch.csv' for ed in ('2K24', '2K25', '2K26')}
OUT = R / 'data/external-impact/2k/2k-merged-e142.csv'
EDS = ['2K24', '2K25', '2K26', '2K27']

rows = {}
for r in csv.DictReader(open(OLD, encoding='utf-8')):
    rows[norm(r['name'])] = {'name': r['name'], **{e: r.get(e, '') for e in EDS}, 'src': {e: 'old' for e in EDS if r.get(e)}}
for ed, path in NEW.items():
    best = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        k = norm(r['name'])
        if r['ovr'] and (k not in best or r['snapshot_date'] < best[k]['snapshot_date']):
            best[k] = r
    for k, r in best.items():
        row = rows.setdefault(k, {'name': r['name'], **{e: '' for e in EDS}, 'src': {}})
        row[ed] = r['ovr']
        row['src'][ed] = 'launch:' + r['snapshot_date']
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['name'] + EDS + ['source'])
    for row in rows.values():
        w.writerow([row['name']] + [row[e] for e in EDS] + [';'.join(f'{e}={s}' for e, s in sorted(row['src'].items()))])
print(OUT, len(rows))
