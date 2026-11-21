"""e123a 判定（任務 spec）：m1–m3、c1、c3、c4、help／pressure／presDisplay 對 E-123 e123、R-064 三數。從任何目錄跑：python -I -X utf8 judge.py"""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
E123 = HERE.parent
ROOT = E123.parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
ATTR = ['long','mid','short','ft','drive','foulDraw','tovSkill','pass','rebound','physique','onBall','help','stamina','creation','pressure','foulDisc','presDisplay']
a = rd(ROOT / 'reports/card-0.2.7a/ranking.csv'); b = rd(HERE / 'e123a/ranking.csv'); e = rd(E123 / 'e123/ranking.csv')
A = {r['name']: r for r in a}; B = {r['name']: r for r in b}; E = {r['name']: r for r in e}
tv = {r['name']: float(r['tv_main_new']) for r in rd(E123 / 'three-value-e123.csv')}
cards = json.loads((HERE / 'work/cards-result.json').read_text(encoding='utf-8'))
ch = cards['eval']['checks']
ev = {c['label']: c for c in json.loads((HERE / 'evaluation.json').read_text(encoding='utf-8'))['candidates']}
out = {}
out['m'] = {k: {'point': ch[k]['value']['point'], 'ci90': ch[k]['value']['ci90'], 'pass': ch[k]['pass']} for k in ('m1', 'm2', 'm3')}
out['c1'] = (HERE / 'npm-test.exit').read_text().strip() == '0'
out['c3'] = {k: f"{ev[k]['gates']['pass']}/{ev[k]['gates']['of']}" for k in ev}
out['c3_pass'] = ev['e123a']['gates']['pass'] >= 18
o140 = [(r['name'], c, float(r[c])) for r in b for c in ATTR if float(r[c]) > 140] + [(n, 'threeValue', v) for n, v in tv.items() if v > 140 and n in B]
out['c4'] = {'n': len(o140), 'list': o140, 'pass': len(o140) <= 2, 'max_tv': max(tv.values())}
# help／pressure／presDisplay 對 E-123 e123
cmp = {}
for c in ('help', 'pressure', 'presDisplay'):
    d = [(n, E[n][c], B[n][c]) for n in B if E[n][c] != B[n][c]]
    cmp[c] = {'n_diff': len(d), 'diffs': d[:40], 'maxabs': max([abs(float(x) - float(y)) for _, x, y in d] or [0])}
out['vs_e123'] = cmp
# 其他欄對 0.2.7a 的差異數
out['cols_diff_vs_027a'] = {c: sum(A[n][c] != B[n][c] for n in B) for c in a[0].keys() if any(A[n][c] != B[n][c] for n in B)}
# R-064
ra = {n: int(r['rank']) for n, r in A.items()}; rb = {n: int(r['rank']) for n, r in B.items()}
t20a = {n for n, k in ra.items() if k <= 20}; t20b = {n for n, k in rb.items() if k <= 20}
mv = [(n, ra[n], rb[n]) for n in rb if ra[n] <= 300 and abs(rb[n] - ra[n]) >= 10]
mv_any = [(n, ra[n], rb[n]) for n in rb if abs(rb[n] - ra[n]) >= 10]
out['R064'] = {'top20_out': sorted(t20a - t20b), 'top20_in': sorted(t20b - t20a), 'top20_swaps': len(t20a - t20b),
               'top20_rank_moves': [(n, ra[n], rb[n]) for n in sorted(t20b, key=rb.get) if ra[n] != rb[n]],
               'top300_movers_ge10': len(mv), 'movers_list': sorted(mv, key=lambda x: x[2] - x[1]), 'all_movers_ge10_any_rank': len(mv_any),
               'evaluate_drop': ev['e123a']['gates']['pass'] < ev['card-0.2.7a']['gates']['pass']}
out['R064']['small'] = out['R064']['top20_swaps'] <= 2 and out['R064']['top300_movers_ge10'] <= 30 and not out['R064']['evaluate_drop']
out['R061'] = {'Wagner': rb['Franz Wagner'], 'Wembanyama': rb['Victor Wembanyama'], 'pass': rb['Franz Wagner'] > rb['Victor Wembanyama']}
NAMES = ['Victor Wembanyama', 'Franz Wagner', 'Chet Holmgren', 'Matisse Thybulle', 'Alex Caruso', 'Dru Smith', 'Cason Wallace', 'Ausar Thompson', 'Rudy Gobert', 'Evan Mobley', 'Stephen Curry', 'Giannis Antetokounmpo', 'Nikola Jokic', 'Shai Gilgeous-Alexander']
out['named'] = {n: {'rank_027a': ra[n], 'rank_e123a': rb[n], 'ovr_027a': A[n]['ovr'], 'ovr_e123a': B[n]['ovr'], 'help': (A[n]['help'], B[n]['help']), 'pressure': (A[n]['pressure'], B[n]['pressure']), 'presDisplay': (A[n]['presDisplay'], B[n]['presDisplay'])} for n in NAMES if n in B}
out['anchors'] = cards['anchors']
out['c0'] = json.loads((HERE / 'work/c0-result.json').read_text(encoding='utf-8'))['pass']
(HERE / 'work/judge.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, default=float))
