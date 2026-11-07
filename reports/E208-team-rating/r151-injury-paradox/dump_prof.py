"""把 6 隊 c／today 全部球員在模擬裡實際使用的屬性（含 live delta／底卡）dump 出來：dump_prof.mjs → profiles.json"""
import sys, json, subprocess, tempfile, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import team_ratings_daily as T
snap = json.loads((HERE / 'snapshot-team-ratings.json').read_text(encoding='utf-8'))
pids = sorted({x['pid'] for t in snap['teams'].values() for v in ('c', 'today') for x in t[v]['rotation']})
live_dir = T.default_live_dir(); meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
rows = T.read_csv(live_dir / 'ranking.csv')
cn = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-'); cc = T.ROOT / f'reports/{cn}/ranking.csv'
if not cc.exists(): cc = T.ROOT / 'reports/card-0.2.12b/ranking.csv'
live = {int(r['playerId']) for r in rows}
inp = {**T.engine_inputs(rows, T.read_csv(cc), T.base_profiles(set(pids) - live, T.load_base_cards())), 'dump': pids, 'teamIds': sorted(snap['teams']), 'jobs': []}
tmp = Path(tempfile.mkdtemp(prefix='dump-', dir=HERE))
try:
    (tmp / 'in.json').write_text(json.dumps(inp), encoding='utf-8')
    r = subprocess.run(['node', str(HERE / 'dump_prof.mjs'), str(tmp / 'in.json'), str(HERE / 'profiles.json')], cwd=str(ROOT), capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), stdin=subprocess.DEVNULL)
    print(r.returncode, (r.stderr or r.stdout)[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
