"""card 0.2.10i 對 0.2.10g：R-109 版號統計（MIN≥500 依 OVR 排名；前 20 名進出、前 100 名移動 ≥10 名人數）＋證據表（前 25＋E-190 15 人）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/cmp_0210i.py → cmp.json"""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
rd = lambda p: {r['name']: r for r in csv.DictReader(Path(p).open(encoding='utf-8'))}
E190_15 = ['Nikola Jokić', 'Shai Gilgeous-Alexander', 'Luka Dončić', 'Giannis Antetokounmpo', 'Victor Wembanyama', 'Jalen Brunson', 'Anthony Edwards',
           'Tyrese Maxey', 'Cade Cunningham', 'Donovan Mitchell', 'Stephen Curry', 'Devin Booker', 'Ja Morant', 'Zion Williamson', 'Jamal Murray']


def rk(rows):
    rr = sorted(((n, float(r['ovr'])) for n, r in rows.items() if float(r['MIN']) >= 500), key=lambda x: -x[1])
    return {n: i + 1 for i, (n, _) in enumerate(rr)}


def main():
    a, b = rd(ROOT / 'reports/card-0.2.10g/ranking.csv'), rd(HERE / 'ranking.csv')
    assert set(a) == set(b) and len(a) == 582
    ra, rb = rk(a), rk(b)
    t20o = sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20)
    t20i = sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)
    m100 = sorted((n for n in ra if ra[n] <= 100 and abs(rb[n] - ra[n]) >= 10), key=lambda n: ra[n])
    names = [n for n, _ in sorted(rb.items(), key=lambda x: x[1]) if rb[n] <= 25]
    names += [n for n in E190_15 if n in b and n not in names]
    f = lambda r, k: float(r[k])
    tab = [{'name': n, 'rank_g': ra.get(n), 'rank_i': rb.get(n), 'ovr_g': f(a[n], 'ovr'), 'ovr_i': f(b[n], 'ovr'),
            'drive_g': f(a[n], 'drive'), 'drive_i': f(b[n], 'drive'), 'creation_g': f(a[n], 'creation'), 'creation_i': f(b[n], 'creation')} for n in names]
    mv = sorted(((n, ra[n], rb[n]) for n in ra if ra[n] <= 100), key=lambda x: x[2] - x[1])
    res = {'top20_out': t20o, 'top20_in': t20i, 'moved10_top100': len(m100), 'moved10_top100_names': [(n, ra[n], rb[n]) for n in m100],
           'moved10_top300': sum(1 for n in ra if ra[n] <= 300 and abs(rb[n] - ra[n]) >= 10),
           'biggest_up_top100': mv[:8], 'biggest_down_top100': mv[-8:], 'table': tab,
           'version_rule': 'R-109：字母版條件＝前 100 名移動 ≥10 名 ≤25 人'}
    (HERE / 'cmp.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'table'}, ensure_ascii=False, indent=1))
    for r in tab:
        print(f"{r['name']:<26} {r['rank_g']!s:>4}->{r['rank_i']!s:<4} OVR {r['ovr_g']:5.1f}->{r['ovr_i']:5.1f}  DRV {r['drive_g']:5.1f}->{r['drive_i']:5.1f}  CRE {r['creation_g']:5.1f}->{r['creation_i']:5.1f}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
