"""評分 M10 參數與驗收（E-169，預註冊：reports/rating-m10-scurve/preregistration.md）。

借用 fit_rating_m8 的 eval／a5 程式（同口徑），只換臂定義與輸出目錄，另加低效率護欄（同 E-168）。
用法（順序固定）：
  python -I scripts/fit_rating_m10.py fit    各臂在 2025-26 A 半重定 a、c；另用整季算上線版 → params.json
                                             （寫完先單獨 commit，之後才准跑 eval／a5）
  python -I scripts/fit_rating_m10.py eval   2025-26 B 半驗收 M4／M6／Z1／Z2／C2 → eval.json
  python -I scripts/fit_rating_m10.py a5     A5 範例（2026-27，上線版常數）＋ 2025-26 低效率大量單場 → a5.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_rating_m3 as f3  # noqa: E402
import fit_rating_m6 as f6  # noqa: E402
import fit_rating_m8 as f8  # noqa: E402
import rating_m6 as m6  # noqa: E402
import rating_m9  # noqa: E402
import rating_m10 as m10  # noqa: E402
from rating_m3 import Table, season_dir  # noqa: E402

PRE = m10.OUT / 'preregistration.md'
LOWK = '低效率大量(TSA>=25, TS<TS_lg-0.08)'
f8.ARMS, f8.OUT, f8.PRE, f8.score_arrays = m10.ARMS, m10.OUT, PRE, m10.score_arrays


def fit():
    cur = Table('2025-26')
    p6 = json.loads(f8.M6P.read_text(encoding='utf-8'))
    for k in ('chosen', 'prod'):  # pow δ=0.10 p=1 逐位元重現 rating_m6；C2 重現 E-168
        assert np.array_equal(m10.bonus(cur, p6[k]['C'], 'pow', 0.10, 1.0)[1], m6.bonus(cur, p6[k]['C'])[1])
        assert np.array_equal(m10.bonus(cur, p6[k]['C'], 'pow', 0.20, 2.0)[1], rating_m9.bonus(cur, p6[k]['C'], 0.20, 2.0)[1])
    A, allm = cur.half == 0, np.ones(len(cur), bool)
    out = dict(prereg_sha256=f3.sha(PRE), fit_data='M6 constants reused; a/c per arm: 2025-26 A half >=10 min (chosen), whole 2025-26 (prod)',
               arms={k: dict(kind=s, a=a, b=b) for k, (s, a, b) in m10.ARMS.items()},
               inputs={'player-games 2025-26': f3.sha(season_dir('2025-26') / 'player-games.json'), 'm6 params': f3.sha(f8.M6P)},
               chosen=dict(P4=p6['chosen']['P4'], **{k: f8.scale(cur, A, p6['chosen']['P4'], p6['chosen']['C'], k) for k in m10.ARMS}),
               prod=dict(P4=p6['prod']['P4'], **{k: f8.scale(cur, allm, p6['prod']['P4'], p6['prod']['C'], k) for k in m10.ARMS}))
    (m10.OUT / 'params.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['chosen'], indent=1))


def evaluate():
    f8.evaluate()
    p = m10.OUT / 'eval.json'
    res = json.loads(p.read_text(encoding='utf-8'))
    ref = json.loads((rating_m9.OUT / 'eval.json').read_text(encoding='utf-8'))  # C2 應與 E-168 相同
    res['c0_C2_vs_E168'] = bool(all(abs(res['C2'][m] - v) < 1e-9 for m, v in ref['C2'].items() if isinstance(v, (int, float)))
                                and abs(res['P1']['C2']['p90'] - ref['P1']['C2']['p90']) < 1e-9)
    judge, low = res['judge'], res['report_only'][LOWK]
    for k in m10.ARMS:
        judge[k]['低效率護欄'] = bool(low[k] <= low['M6'] + 0.4)
        judge[k]['all_pass'] = all(v for x, v in judge[k].items() if x != 'all_pass')
    passing = [k for k in m10.ARMS if judge[k]['all_pass']]
    if passing:
        best = min(res['P1'][k]['p90'] for k in passing)
        judge['pick'] = next(k for k in m10.ARMS if k in passing and res['P1'][k]['p90'] - best < 0.05)
    else:
        judge['pick'] = 'M6（維持）'
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print('c0_C2_vs_E168', res['c0_C2_vs_E168'])
    print('judge(final)', json.dumps(judge, ensure_ascii=False, indent=1))


def a5():
    f8.a5()
    p = m10.OUT / 'a5.json'
    out = json.loads(p.read_text(encoding='utf-8'))
    P = json.loads((m10.OUT / 'params.json').read_text(encoding='utf-8'))['prod']
    P6 = json.loads(f8.M6P.read_text(encoding='utf-8'))['prod']
    t = Table('2025-26')
    sc = f8.all_scores(t, P6['P4'], P6['C'], P)
    _, ts = f6.tsa_ts(t)
    fgm = np.array([r[t.h['FGM']] or 0 for r in t.rows], float)
    row = lambda i: dict(name=str(t.name[i]), date=str(t.date[i]), mn=float(t.mn[i]), pts=int(t.pts[i]), fg=f'{int(fgm[i])}/{int(t.fga[i])}',
                         fta=int(t.fta[i]), ts=round(float(ts[i]), 3), **{k: round(float(S[i]), 2) for k, S in sc.items()})
    ex = [row(i) for nm, d in (('Cade Cunningham', '2025-11-10'), ('Jaylen Brown', '2026-03-30'), ('Alperen', '2025-11-16'),
                               ('Gilgeous', '2026-03-27'), ('Tyrese Maxey', '2026-03-01'))
          for i in range(len(t)) if nm in str(t.name[i]) and str(t.date[i]).startswith(d)]
    out['examples_2025_26'] = ex
    out['z1_top_gain_2025_26'] = [row(i) for i in np.argsort(-(sc['Z1'] - sc['M6']), kind='stable')[:10]]
    out['z1_top_loss_2025_26'] = [row(i) for i in np.argsort(sc['Z1'] - sc['M6'], kind='stable')[:10]]
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('named', 'examples_2025_26', 'z1_top_gain_2025_26', 'z1_top_loss_2025_26')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'fit': fit, 'eval': evaluate, 'a5': a5}[sys.argv[1]]()
