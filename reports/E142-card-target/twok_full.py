"""E-142 補抓舊代 2K 開賣名單的涵蓋率與對齊。只數涵蓋率與和舊檔的 OVR 差異，不比任何卡片/目標/薪水。
用法：python -I twok_full.py   輸入 data/external-impact/2k/2k{24,25,26}-launch.csv，輸出 twok-full.json
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from c0l_check import norm, population, PG, R

MAP = {'2022-23': '2K24', '2023-24': '2K25', '2024-25': '2K26'}
D = R / 'data/external-impact/2k'


def pop_all(s):
    pg = PG.get(s) or (R / f'data/defense-seventh/{s}/player-games.json')
    d = json.loads(pg.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    mins, nm = defaultdict(float), {}
    for r in d['rowSet']:
        if r[h['MIN']]:
            mins[r[h['PLAYER_ID']]] += r[h['MIN']]
            nm[r[h['PLAYER_ID']]] = r[h['PLAYER_NAME']]
    return {p: nm[p] for p, m in mins.items() if m >= 500}


def main():
    old = {norm(r['name']): r for r in csv.DictReader(open(R / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv', encoding='utf-8'))}
    out = {}
    for s, ed in MAP.items():
        rows = list(csv.DictReader(open(D / f'{ed.lower()}-launch.csv', encoding='utf-8')))
        new = {}
        for r in sorted(rows, key=lambda r: (r['snapshot_date'], r['team'] == 'free-agency')):
            new.setdefault(norm(r['name']), r)
        pop = pop_all(s)
        miss_old = [n for n in pop.values() if not (old.get(norm(n), {}).get(ed) or '').strip()]
        miss_new = [n for n in pop.values() if norm(n) not in new]
        miss_union = [n for n in pop.values() if norm(n) not in new and not (old.get(norm(n), {}).get(ed) or '').strip()]
        diffs = []
        for k, r in new.items():
            o = (old.get(k, {}).get(ed) or '').strip()
            if o:
                diffs.append((int(r['ovr']) - int(o), r['name'], int(o), int(r['ovr'])))
        big = sorted([d for d in diffs if abs(d[0]) >= 3], key=lambda d: -abs(d[0]))
        dates = sorted({r['snapshot_date'] for r in rows})
        n = len(pop)
        out[s] = {'edition': ed, 'pop': n, 'rows': len(rows), 'uniqueNames': len(new),
                  'cov_old': round(1 - len(miss_old) / n, 4), 'cov_new': round(1 - len(miss_new) / n, 4),
                  'cov_union': round(1 - len(miss_union) / n, 4),
                  'missing_new_only': sorted(miss_new), 'missing_union': sorted(miss_union),
                  'overlap': len(diffs), 'diff_exact': sum(d[0] == 0 for d in diffs), 'diff_within2': sum(abs(d[0]) <= 2 for d in diffs),
                  'diff_ge3': [{'name': d[1], 'old': d[2], 'new': d[3]} for d in big],
                  'snapshot_dates': {'min': dates[0], 'max': dates[-1], 'distinct': len(dates)}}
        print(s, ed, {k: v for k, v in out[s].items() if not isinstance(v, (list, dict))})
    (here / 'twok-full.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
