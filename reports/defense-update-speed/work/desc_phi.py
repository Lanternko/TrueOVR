"""描述（不當證據）：2026-27 截至 2026-11-01，各臂下 30 隊的模擬 DRtg（重點看 76 人）。
輸入＝每日球隊評分同一套：live 2026-11-01 的 ranking.csv − 先驗卡 ranking.csv 的引擎差值（scripts/team_ratings_daily.engine_inputs），
輪替＝data/season-source-2026-27/team-ratings.json 各隊 (c) 版。各臂只把 onBall／help 的差值再加上 (窗口值_k − 窗口值_A0)（build_arms.py 的 desc-2026-27.json）。
寫出 out/desc-in-<臂>.json，給 scripts/team_ratings_sim.mjs 跑（5090）。
用法：python -I -X utf8 desc_phi.py"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import team_ratings_daily as T  # noqa: E402

LIVE = ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-01'
OUT = HERE / 'out'
rows = list(csv.DictReader(open(LIVE / 'ranking.csv', encoding='utf-8')))
meta = json.load(open(LIVE / 'meta.json', encoding='utf-8'))
card_csv = ROOT / f"reports/{meta['priorCard'].replace('card ', 'card-')}/ranking.csv"
card_rows = list(csv.DictReader(open(card_csv, encoding='utf-8')))
tr = json.load(open(ROOT / 'data/season-source-2026-27/team-ratings.json', encoding='utf-8'))
tids = sorted(tr['teams'], key=int)
jobs = [{'team': int(t), 'ver': 'c', 'roster': [[r['pid'], r['min']] for r in tr['teams'][t]['c']['rotation']]} for t in tids]
live_pids = {int(r['playerId']) for r in rows}
need = {p for j in jobs for p, _ in j['roster']} - live_pids
base = T.engine_inputs(rows, card_rows, T.base_profiles(need, T.load_base_cards()))
desc = json.load(open(OUT / 'desc-2026-27.json', encoding='utf-8'))
a0 = desc['arms']['A0']['deltas']
live = {r['playerId']: r for r in rows}
w0 = desc['arms']['A0']['phi']
diffs = []
for arm in ('A0', 'A1', 'A2'):
    d = json.loads(json.dumps(base))
    dk = desc['arms'][arm]['deltas']
    n = 0
    for p, x in d['deltas'].items():
        if p in dk and p in a0:
            x['onBall'] += dk[p][0] - a0[p][0]; x['help'] += dk[p][1] - a0[p][1]; n += 1
    inp = {**d, 'jobs': jobs, 'teamIds': [int(t) for t in tids]}
    json.dump(inp, open(OUT / f'desc-in-{arm}.json', 'w', encoding='utf-8'))
    print(arm, 'players shifted', n)
# G2：A0 窗口值應等於 live ranking.csv 的 onBall／help（同一天、同一套算式）
for p, v in w0.items():
    if p in live and 'onBall' in v:
        diffs.append(abs(float(live[p]['onBall']) - v['onBall']))
print('A0 vs live ranking.csv PHI onBall max|diff|', max(diffs) if diffs else None, 'n', len(diffs))
