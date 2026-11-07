"""Preregistered gates for small-sample attribute shrinkage (see preregistration.md).

  node scripts/build_season_league.js --shrink
  python reports/ovr-calibrated-2025-26/calibrate.py --target reports/ovr-v53-2025-26/calibration-target-s8-expected.csv --league data/season-league-shrunk.json --out reports/ovr-shrinkage-2025-26/shrunk/calibrate
  python reports/ovr-blended-2025-26/blend.py --league data/season-league-shrunk.json --out reports/ovr-shrinkage-2025-26/shrunk/blend
  python reports/ovr-blended-2025-26/blend.py --out reports/ovr-shrinkage-2025-26/baseline/blend
  python reports/ovr-shrinkage-2025-26/evaluate.py

Baseline and shrunk cards at fixed alpha 0.5 with blend.py's folds (seeds 0-9), same players and targets.
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'reports/ovr-calibrated-2025-26'))
sys.path.insert(0, str(ROOT / 'reports/ovr-blended-2025-26'))
import calibrate  # noqa: E402
import blend  # noqa: E402

ALPHA, LOW_MIN, TOP = 0.5, 500, 50


def heldout(league):
    calibrate.LEAGUE = ROOT / league
    rows = blend.load(blend.TARGET); blend.attach_rapm(rows)
    X, _, _ = blend.design(rows, blend.FORM)
    ev = np.array([r['poss'] >= blend.EVAL_POSS for r in rows])
    preds = [blend.oof(rows, X, ALPHA, rep) for rep in range(10)]
    t, mc = blend.blended(rows, ALPHA); w = blend.fit_weights(X, t, mc)
    full = np.c_[np.ones(len(X)), X] @ blend.wfit(X, t, w, blend.LAM)
    ranking = [(k + 1, rows[i]['name'], rows[i]['MIN']) for k, i in enumerate(np.argsort(-full))]
    return rows, ev, preds, ranking


def main():
    (rb, ev, pb, kb), (rs, ev_s, ps, ks) = heldout('data/season-league.json'), heldout('data/season-league-shrunk.json')
    assert [r['name'] for r in rb] == [r['name'] for r in rs] and (ev == ev_s).all()
    N = np.array([r['N'] for r in rb])[ev]; D = np.array([r['D'] for r in rb])[ev]
    rho = lambda preds, t: float(np.mean([blend.spearman(p[ev], t) for p in preds]))
    res = {k: {'baseline': rho(pb, t), 'shrunk': rho(ps, t)} for k, t in [('net', N), ('defense', D)]}
    for v in res.values():
        v['delta'] = v['shrunk'] - v['baseline']
    mb, ms = np.mean(pb, 0)[ev], np.mean(ps, 0)[ev]
    rng = np.random.default_rng(20261018); boot = {'net': [], 'defense': []}
    for _ in range(2000):
        i = rng.integers(0, len(N), len(N))
        boot['net'].append(blend.spearman(ms[i], N[i]) - blend.spearman(mb[i], N[i]))
        boot['defense'].append(blend.spearman(ms[i], D[i]) - blend.spearman(mb[i], D[i]))
    for k, v in boot.items():
        res[k]['bootstrap95'] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    top = {}
    for name, rk in [('baseline', kb), ('shrunk', ks)]:  # full-data fit at alpha 0.5 (not blend.py's chosen alpha)
        top[name] = {'lowMinuteTop50': [(k, n, round(m)) for k, n, m in rk[:TOP] if m < LOW_MIN],
                     'under1000Top50': sum(m < 1000 for _, _, m in rk[:TOP]), 'ranks': {n: k for k, n, _ in rk}}
        with open(OUT / f'ranking-alpha05-{name}.csv', 'w', encoding='utf-8', newline='') as fh:
            csv.writer(fh).writerows([('rank', 'name', 'MIN')] + [(k, n, round(m)) for k, n, m in rk])
    small = top['shrunk']['ranks']['Javon Small']
    gates = {'net': res['net']['delta'] >= 0, 'defense': res['defense']['delta'] >= 0,
             'lowMinutes': not top['shrunk']['lowMinuteTop50'] and small > TOP}
    gates['adopt'] = all(gates.values())
    focus = ['Norchad Omier', 'Javon Small', 'Ty Jerome', 'Dejounte Murray', 'Obi Toppin', 'Walker Kessler', 'Charles Bassey', 'Karlo Matković']
    league = json.loads((ROOT / 'data/season-league-shrunk.json').read_text(encoding='utf-8'))
    cal = json.loads((OUT / 'shrunk/calibrate/summary.json').read_text(encoding='utf-8'))
    summary = {'preregistration': 'preregistration.md', 'alpha': ALPHA, 'evaluatedPlayers': int(ev.sum()), 'heldOutRho': res,
               'top50': {k: {kk: vv for kk, vv in v.items() if kk != 'ranks'} for k, v in top.items()},
               'focusRanks': {n: {'baseline': top['baseline']['ranks'][n], 'shrunk': top['shrunk']['ranks'][n]} for n in focus},
               'pseudoMinutes': {**{k: v['pseudoMinutes'] for k, v in league['methodology']['shrinkage']['stats'].items()},
                                 'creation': cal['creationShrinkage']['pseudoMinutes']},
               'gates': gates}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
