"""python reports/player-impact-v54-team/score.py -> scores.json (v53 vs v54 team metrics, 4 seasons x 3 seeds).

v53 baseline runs are reused as-is from reports/player-impact-v53-team/runs (not re-run). v54 runs use the
same v47-full-season harness and v53 engine, but with 2025-26 long/short cards replaced by the
reliability-aware (empirical-Bayes) version (see reports/ovr-v54-2025-26/shooting-eb.mjs). Other seasons
are untouched by the v54 change (build_season_league.js --shooting-eb only ever produces 2025-26 cards),
so as a sanity check this also asserts the 2022-23/2023-24/2024-25 run files are byte-identical to v53's.
"""
import json, importlib.util
from pathlib import Path
R = Path('reports/player-impact-v54-team'); V53 = Path('reports/player-impact-v53-team')
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
protocol = read('reports/player-impact-v47/protocol.json')
spec = importlib.util.spec_from_file_location('box', 'reports/player-box-audit/experiment/score.py')
box = importlib.util.module_from_spec(spec); spec.loader.exec_module(box)

unaffected = [s for s in protocol['seasons'] if s != '2025-26']
identical = {}
for season in unaffected:
    for seed in protocol['seeds']:
        a = (V53 / f'runs/{season}-v53-{seed}.json').read_text(encoding='utf-8')
        b = (R / f'runs/{season}-v54-{seed}.json').read_text(encoding='utf-8')
        identical[f'{season}-{seed}'] = a == b

cells = []
for season in protocol['seasons']:
    for v, folder in [('v53', V53), ('v54', R)]:
        s = box.score(season, v, protocol['seeds'], folder)
        cells.append({'season': season, 'variant': v, 'teamMetrics': s['teamMetrics']})

out = {'seeds': protocol['seeds'],
       'unaffectedSeasonsByteIdenticalToV53': identical,
       'note': 'v53 and v54 share pressure/tovNonSteal coefficients, spread scale, and engine; the only '
               'difference is the 2025-26 long/short card values. 2022-23/2023-24/2024-25 run files are '
               'expected to be byte-identical between v53 and v54 (see unaffectedSeasonsByteIdenticalToV53).',
       'cells': cells}
(R / 'scores.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('unaffected seasons byte-identical to v53:', all(identical.values()), identical)
for c in cells:
    m = c['teamMetrics']
    print(c['season'], c['variant'], f"winsMAE={m['winsMAE']:.3f} netRMSE={m['netRMSE']:.3f} tov/g={m['tovPerGame']:.2f} pts/g={m['ptsPerGame']:.2f}")
