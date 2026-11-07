"""E-181 §2：offBall 原值（pbp 的被助攻進球得分／36 分鐘）→ 合併池百分位 → 屬性值。寫 offball-raw.csv、work/offball-pool.json。
原值＝球員自己出手、有隊友助攻的進球得分（2 分球 2、3 分球 3，罰球不算）÷ 分鐘 × 36。
窗與池照 creation：2025-26 卡片池（GP>=30 且 MPG>=20）＋ 2022-23／2023-24／2024-25 池（同門檻，poolInfo），每球員季一筆；
百分位／頂端尺 S／底端尺照 E-101（offball_map.py；creation 用同一函式逐位重現 tail-e123a.csv，見 results.json）。
分鐘：player-games.json 的 MIN，只算有 pbp 的場次（2025-26 缺 3 場，2024-25 缺 1 場；規格外的揭露項）。
用法（repo root）：python -I -B -X utf8 reports/E181-offball-attr/e181_offball.py
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from offball_map import Pool, map_merged  # noqa: E402
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
PBP = {'2025-26': ROOT / 'data/defense-a-source/pbp', **{s: ROOT / f'data/defense-seventh/{s}/pbp' for s in ('2022-23', '2023-24', '2024-25')}}
PG = {'2025-26': ROOT / 'data/season-source/player-games.json', **{s: ROOT / f'data/defense-seventh/{s}/player-games.json' for s in ('2022-23', '2023-24', '2024-25')}}


def season_raw(s):
    """回傳 {pid: (assisted_pts, minutes_in_pbp_games)}、pbp 場數。"""
    ap = defaultdict(int)
    games = set()
    for f in sorted(PBP[s].glob('*.json')):
        g = json.loads(f.read_text(encoding='utf-8'))['data']['game']
        games.add(g['gameId'])
        for a in g['actions']:
            if a.get('actionType') in ('2pt', '3pt') and a.get('shotResult') == 'Made' and a.get('assistPersonId'):
                ap[int(a['personId'])] += 3 if a['actionType'] == '3pt' else 2
    rs = json.loads(PG[s].read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = rs['headers']
    mn = defaultdict(float)
    for r in rs['rowSet']:
        if r[h.index('GAME_ID')] in games:
            mn[int(r[h.index('PLAYER_ID')])] += float(r[h.index('MIN')] or 0)
    return ap, mn, len(games)


def main():
    raw = json.loads((E090 / 'work/a0-raw.json').read_text(encoding='utf-8'))['creation']
    card_ids = sorted(int(k) for k in raw['r'])
    lg = json.loads(LEAGUE.read_text(encoding='utf-8'))
    obs = defaultdict(lambda: {'GP': 0, 'MIN': 0.0})
    nm = {}
    for t in lg['teams']:
        for p in t['roster']:
            o = obs[int(p['playerId'])]
            o['GP'] += p['observed']['GP']; o['MIN'] += p['observed']['MIN']; nm[int(p['playerId'])] = p['name']
    ap, mn, ng = season_raw('2025-26')
    print('2025-26 pbp games', ng)
    r = {}
    miss = []
    for pid in card_ids:
        if mn.get(pid, 0) <= 0:
            miss.append(pid); continue
        r[pid] = ap.get(pid, 0) / mn[pid] * 36
    if miss:
        raise SystemExit(f'卡片球員無 pbp 季分鐘：{miss}')
    pool_ids = [p for p in obs if obs[p]['GP'] >= 30 and obs[p]['MIN'] / obs[p]['GP'] >= 20]
    assert len(pool_ids) == len(raw['pool']), (len(pool_ids), len(raw['pool']))
    vals = [ap.get(p, 0) / mn[p] * 36 for p in pool_ids if mn.get(p, 0) > 0]
    assert len(vals) == len(pool_ids)
    per = {'2025-26': len(vals)}
    for s in ('2022-23', '2023-24', '2024-25'):
        a2, m2, _ = season_raw(s)
        info = json.loads((E101 / f'pool/raw-{s}.json').read_text(encoding='utf-8'))['poolInfo']
        n = 0
        for k, i in info.items():
            if i['GP'] >= 30 and i['MIN'] / i['GP'] >= 20:
                pid = int(k)
                if m2.get(pid, 0) <= 0:
                    raise SystemExit(f'{s} 池內球員 {pid} 無 pbp 分鐘')
                vals.append(a2.get(pid, 0) / m2[pid] * 36); n += 1
        per[s] = n
    pool = Pool(vals)
    mapped, an = map_merged(r, pool)
    # 對照：creation 同函式重現 tail-e123a.csv
    cv = [float(x) for x in raw['pool']]
    for s in ('2022-23', '2023-24', '2024-25'):
        d = json.loads((E101 / f'pool/raw-{s}.json').read_text(encoding='utf-8'))
        cv += [v for k, v in d['attrs']['creation'].items() if d['poolInfo'].get(k) and d['poolInfo'][k]['GP'] >= 30 and d['poolInfo'][k]['MIN'] / d['poolInfo'][k]['GP'] >= 20]
    cm, can = map_merged({int(k): v for k, v in raw['r'].items()}, Pool(cv))
    tail = {int(x['playerId']): float(x['creation']) for x in csv.DictReader(open(ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv', encoding='utf-8'))}
    cdiff = max(abs(cm[k] - tail[k]) for k in cm)
    with open(HERE / 'offball-raw.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['playerId', 'name', 'assistedPts', 'minutesPbpGames', 'offBallRaw', 'offBallPct', 'offBall'])
        for pid in card_ids:
            w.writerow([pid, nm.get(pid, ''), ap.get(pid, 0), mn[pid], f'{r[pid]:.10f}', f'{pool.pct(r[pid]):.6f}', f'{mapped[pid]:.10f}'])
    (HERE / 'work').mkdir(exist_ok=True)
    (HERE / 'work/offball-pool.json').write_text(json.dumps({'anchors': an, 'poolPerSeason': per, 'pbpGames2025-26': ng, 'creationReproMaxAbsDiff': cdiff, 'creationAnchors': can}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(an, per, 'creation repro maxdiff', cdiff, 'n', len(r))


main()
