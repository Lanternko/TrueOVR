"""E-216 POR 調查（只調查、不修）：用 team-ratings.json 的 POR 近況／今日輪替，逐人換成聯盟平均球員（同分鐘）看每人的邊際值，
另跑「近況版拿掉 Morant＋Sharpe」。用法：python -I -X utf8 reports/E208-team-rating/por_probe.py [seeds=600] [abbr=POR]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import team_ratings_daily as T

seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 600
abbr = sys.argv[2] if len(sys.argv) > 2 else 'POR'
doc = json.loads(T.RATINGS.read_text(encoding='utf-8'))
tid, team = next((k, v) for k, v in doc['teams'].items() if v['abbr'] == abbr)
live_dir = T.default_live_dir()
meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
card_rows = T.read_csv(ROOT / f"reports/{(meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-')}/ranking.csv")
rows = T.read_csv(live_dir / 'ranking.csv')
c = [(r['pid'], r['min']) for r in team['c']['rotation']]
td = [(r['pid'], r['min']) for r in team['today']['rotation']]
names = {r['pid']: r['name'] for v in ('c', 'today') for r in team[v]['rotation']}
allp = {p for p, _ in c + td}
inp = T.engine_inputs(rows, card_rows, T.base_profiles(allp - {int(r['playerId']) for r in rows}, T.load_base_cards()))
jobs = [{'team': tid, 'ver': 'c', 'roster': c}, {'team': tid, 'ver': 'today', 'roster': td}]
for i, (p, m) in enumerate(c):
    jobs.append({'team': tid, 'ver': f'c-rep-{p}', 'roster': [[9000000 + i if q == p else q, mm] for q, mm in c]})
for i, (p, m) in enumerate(td):
    jobs.append({'team': tid, 'ver': f'today-rep-{p}', 'roster': [[9100000 + i if q == p else q, mm] for q, mm in td]})
# 第二階段（只在 abbr=POR）：Morant 的邊際值會不會隨「同隊其他控衛／後場」在不在而變（重疊假說）
rep2 = lambda drop: [[9200000 + i if q in drop else q, mm] for i, (q, mm) in enumerate(c)]
PAIRS = {}
if abbr == 'POR':
    ids = {n: p for p, n in names.items()}
    M = ids['Ja Morant']
    for o in ('Damian Lillard', 'Jrue Holiday', 'Scoot Henderson', 'Deni Avdija', 'Donovan Clingan'):
        PAIRS[o] = ids[o]
        jobs.append({'team': tid, 'ver': f'c-no-{o}', 'roster': rep2({ids[o]})})
        jobs.append({'team': tid, 'ver': f'c-no-{o}-no-Morant', 'roster': rep2({ids[o], M})})
inp.update(jobs=jobs, teamIds=sorted(doc['teams']))
res = T.run_sim(inp, seeds, 10)['res']
mg = lambda v: res[(tid, v)]['msum'] / res[(tid, v)]['n']
out = {'team': abbr, 'seeds': seeds, 'c': mg('c'), 'today': mg('today'), 'marginal': {}}
for v, ros in (('c', c), ('today', td)):
    for p, m in ros:
        out['marginal'][f'{v}:{names[p]}'] = {'min': round(m, 1), 'value_vs_avg_player': round(mg(v) - mg(f'{v}-rep-{p}'), 2)}
for o in PAIRS:
    out['marginal'][f'c:Morant 在沒有 {o} 時'] = round(mg(f'c-no-{o}') - mg(f'c-no-{o}-no-Morant'), 2)
print(json.dumps(out, ensure_ascii=False, indent=1))
Path(__file__).with_name(f'probe-{abbr}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
