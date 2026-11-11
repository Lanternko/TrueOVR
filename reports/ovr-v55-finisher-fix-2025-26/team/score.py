"""python reports/ovr-v55-finisher-fix-2025-26/team/score.py [--mode B12]
-> scores.json（v53 / v54 / v55 球隊層指標，4 季 x 3 種子）。

v53、v54 的 run 檔直接沿用既有凍結產物（reports/player-impact-v5{3,4}-team/runs），不重跑。
v55 的 run 檔在本目錄 runs/ 底下，用同一個 v47 全季 harness + v53 引擎 + v54 可靠度卡片，
再加 B1（禁區出手來源修正）與 B2（rates 可靠度收縮）。

和 v54 的 score.py 不同：v54 只改 2025-26 卡片，所以舊三季逐位元相同可以斷言；v55 的 B1/B2
逐季套用，舊三季**會**改變，所以這裡不做相同性斷言，而是把三個版本四季併排，讓舊季變化本身
成為一個可檢驗的結果（球隊層不應該因為這個修正而變差）。
"""
import json, sys, importlib.util
from pathlib import Path
R = Path('reports/ovr-v55-finisher-fix-2025-26/team')
V53 = Path('reports/player-impact-v53-team'); V54 = Path('reports/player-impact-v54-team')
mode = sys.argv[sys.argv.index('--mode')+1] if '--mode' in sys.argv else 'B12'
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
protocol = read('reports/player-impact-v47/protocol.json')
spec = importlib.util.spec_from_file_location('box', 'reports/player-box-audit/experiment/score.py')
box = importlib.util.module_from_spec(spec); spec.loader.exec_module(box)

cells = []
for season in protocol['seasons']:
    for v, folder in [('v53', V53), ('v54', V54), (mode, R)]:
        if not all((folder / f'runs/{season}-{v}-{seed}.json').exists() for seed in protocol['seeds']):
            print(f'skip {season} {v}: runs missing'); continue
        s = box.score(season, v, protocol['seeds'], folder)
        cells.append({'season': season, 'variant': v, 'teamMetrics': s['teamMetrics']})

out = {'seeds': protocol['seeds'], 'mode': mode, 'cells': cells,
       'note': 'v53/v54 runs reused from their frozen directories. v55 applies B1+B2 per season, so '
               'unlike v54 the 2022-23/2023-24/2024-25 runs are NOT byte-identical to v53.'}
(R / 'scores.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
for c in cells:
    m = c['teamMetrics']
    print(c['season'], c['variant'], f"winsMAE={m['winsMAE']:.3f} netRMSE={m['netRMSE']:.3f} tov/g={m['tovPerGame']:.2f} pts/g={m['ptsPerGame']:.2f} 3P%={m['threePct']:.2f}")
