"""card 0.2.10g vs 0.2.10f：前 20 進出、前 100 內名次移動 >=10 的人數（R-109 字母版本門檻：前 20 變動 <=1、前 100 移動 <=25）、代表球員 -> cmp.json"""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
rd = lambda p: {r['name']: r for r in csv.DictReader((ROOT / p).open(encoding='utf-8'))}
REP = ['Nikola Jokić', 'Victor Wembanyama', 'Shai Gilgeous-Alexander', 'Jalen Williams', 'Franz Wagner', 'Cooper Flagg']


def main():
    o, n = rd('reports/card-0.2.10f/ranking.csv'), rd('reports/card-0.2.10g/ranking.csv')
    assert set(o) == set(n)
    ro, rn = {k: int(v['rank']) for k, v in o.items()}, {k: int(v['rank']) for k, v in n.items()}
    top = lambda r, k: {x for x, i in r.items() if i <= k}
    t20_in, t20_out = sorted(top(rn, 20) - top(ro, 20), key=rn.get), sorted(top(ro, 20) - top(rn, 20), key=ro.get)
    mv = [(x, ro[x], rn[x]) for x in o if (ro[x] <= 100 or rn[x] <= 100)]
    big = [(x, a, b) for x, a, b in mv if abs(a - b) >= 10]
    in100 = [(x, a, b) for x, a, b in big if a <= 100 and b <= 100]
    out = {'top20_in': [(x, ro[x], rn[x]) for x in t20_in], 'top20_out': [(x, ro[x], rn[x]) for x in t20_out],
           'top20_changes': len(t20_in), 'moved10_both_in_top100': len(in100), 'moved10_any_top100': len(big),
           'top100_enter': sorted([(x, ro[x], rn[x]) for x in top(rn, 100) - top(ro, 100)], key=lambda t: t[2]),
           'top100_exit': sorted([(x, ro[x], rn[x]) for x in top(ro, 100) - top(rn, 100)], key=lambda t: t[1]),
           'rep': {x: {'rank_old': ro[x], 'rank_new': rn[x], 'ovr_old': float(o[x]['ovr']), 'ovr_new': float(n[x]['ovr'])} for x in REP if x in o},
           'top20_new': [(x, rn[x], float(n[x]['ovr']), ro[x], float(o[x]['ovr'])) for x in sorted(rn, key=rn.get)[:20]],
           'ovr_diff_players_ge1': sum(abs(float(o[x]['ovr']) - float(n[x]['ovr'])) >= 1 for x in o),
           'rank_changed': sum(ro[x] != rn[x] for x in o), 'n': len(o)}
    (HERE / 'cmp.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k not in ('top20_new',)}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
