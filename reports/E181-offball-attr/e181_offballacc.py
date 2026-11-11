"""E-181 O2：offBallAcc＝tracking 接球投籃 eFG%，向聯盟均值收縮（固定 k=150 出手），再用與 offBall 相同的 E-101 合併池百分位尺映到屬性值。
規格只寫「照 long 的方式映」，而 long 的曲線 CURVE_3PT 以 3P% 標定、套不到 eFG%；此處改用與 offBall 同一把百分位尺是「規格外的補定義」，
報告中 O2 標為補充臂、不計入判定（L-026：不自行換定義）。用法（repo root）：python -I -B -X utf8 reports/E181-offball-attr/e181_offballacc.py
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from offball_map import Pool, map_merged  # noqa: E402
K = 150
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'

def load(s):
    rs = json.loads((HERE / f'data/catchshoot-{s}.json').read_text(encoding='utf-8'))['resultSets'][0]
    h = rs['headers']; rows = [{k: (v or 0) if k.startswith('CATCH') else v for k, v in zip(h, r)} for r in rs['rowSet']]
    fga = sum(r['CATCH_SHOOT_FGA'] for r in rows); pts = sum(r['CATCH_SHOOT_FGM'] + 0.5 * r['CATCH_SHOOT_FG3M'] for r in rows)
    lg = pts / fga
    d = {int(r['PLAYER_ID']): (r['CATCH_SHOOT_FGM'] + 0.5 * r['CATCH_SHOOT_FG3M'], r['CATCH_SHOOT_FGA']) for r in rows}
    return d, lg

def shr(d, lg, pid):
    e, a = d.get(pid, (0.0, 0))
    return (e + K * lg) / (a + K)

raw = json.loads((E090 / 'work/a0-raw.json').read_text(encoding='utf-8'))['creation']
card_ids = sorted(int(k) for k in raw['r'])
lgj = json.loads(LEAGUE.read_text(encoding='utf-8'))
obs = defaultdict(lambda: {'GP': 0, 'MIN': 0.0})
for t in lgj['teams']:
    for p in t['roster']:
        o = obs[int(p['playerId'])]; o['GP'] += p['observed']['GP']; o['MIN'] += p['observed']['MIN']
d, lg = load('2025-26')
lgs = {'2025-26': lg}
r = {pid: shr(d, lg, pid) for pid in card_ids}
pool_ids = [p for p in obs if obs[p]['GP'] >= 30 and obs[p]['MIN'] / obs[p]['GP'] >= 20]
vals = [shr(d, lg, p) for p in pool_ids]
for s in ('2022-23', '2023-24', '2024-25'):
    d2, l2 = load(s); lgs[s] = l2
    info = json.loads((E101 / f'pool/raw-{s}.json').read_text(encoding='utf-8'))['poolInfo']
    for k, i in info.items():
        if i['GP'] >= 30 and i['MIN'] / i['GP'] >= 20:
            vals.append(shr(d2, l2, int(k)))
pool = Pool(vals)
mapped, an = map_merged(r, pool)
rows = list(csv.DictReader(open(HERE / 'offball-raw.csv', encoding='utf-8')))
with open(HERE / 'offball-raw-o2.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(list(rows[0].keys()) + ['csFga', 'offBallAccRaw', 'offBallAcc'])
    for x in rows:
        pid = int(x['playerId']); w.writerow(list(x.values()) + [d.get(pid, (0, 0))[1], f'{r[pid]:.10f}', f'{mapped[pid]:.10f}'])
(HERE / 'work/offballacc-pool.json').write_text(json.dumps({'k': K, 'leagueEfg': lgs, 'poolN': len(vals), 'anchors': an}, indent=1), encoding='utf-8')
print(lgs, len(vals), an)
