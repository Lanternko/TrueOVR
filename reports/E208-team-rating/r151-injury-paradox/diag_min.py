"""BOS c／today 在模擬裡每人實際上場分鐘（200 場平均）與每 36 分鐘得分，確認模擬分鐘有沒有照分鐘表。"""
import sys, json, subprocess, tempfile, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import team_ratings_daily as T
snap = json.loads((HERE / 'snapshot-team-ratings.json').read_text(encoding='utf-8'))
tid = next(t for t, r in snap['teams'].items() if r['abbr'] == sys.argv[1])
ro = lambda v: [[x['pid'], x['min']] for x in snap['teams'][tid][v]['rotation']]
jobs = [{'team': tid, 'ver': v, 'roster': ro(v)} for v in ('c', 'today')]
pids = sorted({p for j in jobs for p, _ in j['roster']})
live_dir = T.default_live_dir(); meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
rows = T.read_csv(live_dir / 'ranking.csv')
cn = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-'); cc = T.ROOT / f'reports/{cn}/ranking.csv'
if not cc.exists(): cc = T.ROOT / 'reports/card-0.2.12b/ranking.csv'
live = {int(r['playerId']) for r in rows}
teamIds = sorted(snap['teams'])
inp = {**T.engine_inputs(rows, T.read_csv(cc), T.base_profiles(set(pids) - live, T.load_base_cards())), 'dump': pids, 'teamIds': teamIds, 'jobs': jobs, 'ti': teamIds.index(tid)}
tmp = Path(tempfile.mkdtemp(prefix='diag-', dir=HERE))
try:
    (tmp / 'in.json').write_text(json.dumps(inp), encoding='utf-8')
    r = subprocess.run(['node', str(HERE / 'diag_min.mjs'), str(tmp / 'in.json'), str(HERE / f'diag-min-{sys.argv[1]}.json')], cwd=str(ROOT), capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), stdin=subprocess.DEVNULL)
    print(r.returncode, (r.stderr or r.stdout)[-400:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
d = json.load(open(HERE / f'diag-min-{sys.argv[1]}.json', encoding='utf-8'))
for o in d:
    print(o['ver'])
    for n, a in o['players'].items(): print('  ', n[:22].ljust(22), a)
