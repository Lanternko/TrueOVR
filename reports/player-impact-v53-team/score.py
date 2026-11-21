"""python reports/player-impact-v53-team/score.py -> scores.json (v53 vs v47 team metrics, 4 seasons x 3 seeds)."""
import json, importlib.util
from pathlib import Path
R = Path('reports/player-impact-v53-team'); V47 = Path('reports/player-impact-v47')
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
protocol = read(V47 / 'protocol.json')
spec = importlib.util.spec_from_file_location('box', 'reports/player-box-audit/experiment/score.py'); box = importlib.util.module_from_spec(spec); spec.loader.exec_module(box)
original = box.read
box.read = lambda p: original(Path(p).with_name(Path(p).name.replace('-v47-', '-v47-full-')) if Path(p).parent == V47 / 'runs' else p)
a = read(R / 'runs/2025-26-v47-20261012.json'); b = read(V47 / 'runs/2025-26-v47-full-20261012.json')
same = [(t['wins'], t['stats']) for t in a['teams']] == [(t['wins'], t['stats']) for t in b['teams']]
cells = []
for season in protocol['seasons']:
    for v, folder in [('v47', V47), ('v53', R)]:
        s = box.score(season, v, protocol['seeds'], folder)
        cells.append({'season': season, 'variant': v, 'teamMetrics': s['teamMetrics'],
                      'tovPer100UsesMAE': s['summary']['ALL']['tovPer100Uses']['mae'], 'stl36MAE': s['summary']['ALL']['stl36']['mae']})
out = {'harnessReproducesV47': same, 'seeds': protocol['seeds'],
       'note': 'tovNonSteal coefficients are pooled 2022-26 four-factor RAPM, so every season is in-sample for the pressure input.', 'cells': cells}
(R / 'scores.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('harness reproduces v47:', same)
for c in cells:
    m = c['teamMetrics']; print(c['season'], c['variant'], f"winsMAE={m['winsMAE']:.3f} netRMSE={m['netRMSE']:.3f} tov/g={m['tovPerGame']:.2f} pts/g={m['ptsPerGame']:.2f} tovUsesMAE={c['tovPer100UsesMAE']:.3f}")
