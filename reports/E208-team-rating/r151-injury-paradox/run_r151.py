"""R-151 傷兵悖論診斷：同一套每日模擬（sim_rep.mjs＝team_ratings_sim.mjs + rep 種子偏移），多組獨立種子重抽。
用法：python -I run_r151.py <phase> <reps> <workers>   phase＝q1（6 隊 c/today + 換人對照）｜bos（BOS 逐格換人與分鐘對照）
名單取自 snapshot-team-ratings.json（commit fd8f3ad 後的當日輸出）。rep=0 與每日版種子完全相同。輸出 out-<phase>.json。"""
import sys, json, subprocess, tempfile, shutil, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import team_ratings_daily as T  # noqa: E402

phase, reps, workers = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
snap = json.loads((HERE / 'snapshot-team-ratings.json').read_text(encoding='utf-8'))
before = json.loads((ROOT / 'reports/E208-team-rating/r151/team-ratings-before.json').read_text(encoding='utf-8'))
abbr2tid = {r['abbr']: t for t, r in snap['teams'].items()}
TEAMS = ['BOS', 'MIN', 'POR', 'BKN', 'IND', 'LAC']
ro = lambda ab, v: [[x['pid'], x['min']] for x in snap['teams'][abbr2tid[ab]][v]['rotation']]
nm = {x['pid']: x['name'] for t in snap['teams'].values() for v in ('c', 'today') for x in t[v]['rotation']}


def replace(roster, out_pid, in_pid):
    return [[in_pid if p == out_pid else p, m] for p, m in roster]


jobs = []   # (team tid, 變體名, roster)
for ab in TEAMS:
    tid = abbr2tid[ab]; c, td = ro(ab, 'c'), ro(ab, 'today')
    cp, tp = [p for p, _ in c], [p for p, _ in td]
    removed = [p for p in cp if p not in tp]; added = [p for p in tp if p not in cp]
    if phase == 'q1':
        jobs += [(tid, 'c', c), (tid, 'today', td)]
        for i, r in enumerate(removed):          # 被拿掉的人，原地換成遞補進來的人（同分鐘），看他單獨的貢獻
            jobs.append((tid, f'c_repl[{nm[r]}->{nm[added[min(i, len(added) - 1)]]}]', replace(c, r, added[min(i, len(added) - 1)])))
    if phase == 'bos' and ab == 'BOS':
        gon = added[0]; geo = removed[0]
        jobs += [(tid, 'c', c), (tid, 'today', td)]
        jobs.append((tid, 'a_today_Gonzalez->George@10', replace(td, gon, geo)))                    # (a) 今日陣容把 George 放回最後一格 10 分鐘
        for p, m in c:                                                                                # (b) 每一格原地換成 González（同分鐘）
            jobs.append((tid, f'b_repl[{nm[p]}@{m:g}]', replace(c, p, gon)))
        # (c) 同一批人（c 的 9 人）、只換分鐘表：用改版前（E-208 (c)）的分鐘
        old = {x['pid']: x['min'] for x in before['teams'][tid]['c']['rotation']}
        jobs.append((tid, 'c_oldminutes_same9', [[p, old[p]] for p, _ in c if p in old]))
        # 同一批人 c，把 George 的分鐘整段改給 White…（遞補式）= today 但 George 留在 10 分鐘格、González 不上
        jobs.append((tid, 'c_George_last10', [[p, m] for p, m in td[:-1]] + [[geo, 10.0]]))
        # George 在 c 的位置，其餘 8 人維持：c 去 George，分鐘不遞補，分給 Walsh 以外的人？—改用「George 36→Walsh/González 平分」不做；保持規格內三個對照。

# 引擎輸入（同 compute）
live_dir = T.default_live_dir()
meta = json.loads((live_dir / 'meta.json').read_text(encoding='utf-8'))
rows = T.read_csv(live_dir / 'ranking.csv')
card_name = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-')
card_csv = T.ROOT / f'reports/{card_name}/ranking.csv'
if not card_csv.exists():
    card_csv = T.ROOT / 'reports/card-0.2.12b/ranking.csv'
card_rows = T.read_csv(card_csv)
live_pids = {int(r['playerId']) for r in rows}
need = {p for _, _, r in jobs for p, _ in r} - live_pids
inp = {**T.engine_inputs(rows, card_rows, T.base_profiles(need, T.load_base_cards())), 'teamIds': sorted(snap['teams'])}
allj = [{'team': t, 'ver': v, 'roster': r, 'rep': k} for k in range(reps) for t, v, r in jobs]
inp['jobs'] = allj
workers = max(1, min(workers, len(allj)))
print(f'phase={phase} 變體 {len(jobs)} × reps {reps} = {len(allj)} 份 × 200 場，workers={workers}', flush=True)
tmp = Path(tempfile.mkdtemp(prefix='r151-', dir=HERE))
try:
    (tmp / 'in.json').write_text(json.dumps(inp), encoding='utf-8')
    procs = [subprocess.Popen(['node', str(HERE / 'sim_rep.mjs'), str(tmp / 'in.json'), str(s), str(workers), str(tmp / f'o{s}.json'), '200'], cwd=str(ROOT),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), stdin=subprocess.DEVNULL)
             for s in range(workers)]
    for p in procs:
        o, e = p.communicate()
        if p.returncode:
            raise SystemExit(f'sim exit {p.returncode}: {(e or o)[-400:]}')
    res = []
    for s in range(workers):
        res += json.load(open(tmp / f'o{s}.json', encoding='utf-8'))['res']
finally:
    shutil.rmtree(tmp, ignore_errors=True)
out = {'phase': phase, 'reps': reps, 'gamesPerRep': 200, 'snapshotSha256': hashlib.sha256((HERE / 'snapshot-team-ratings.json').read_bytes()).hexdigest(),
       'names': {str(k): v for k, v in nm.items()}, 'res': res}
(HERE / f'out-{phase}.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
print('done', len(res))
