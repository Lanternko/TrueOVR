"""POR 診斷第三輪（2026-11-07）：球員去年每 36 分鐘 × 今年分鐘 ＝ 陣容預期 box，對照實際；防守端用對手自己的季平均當預期。
python -I -X utf8 por3.py"""
import collections, glob, gzip, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'data/season-source-2026-27'); TEAM = 'POR'
KS = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'AST', 'TOV', 'STL', 'BLK', 'PF']
BOXK = dict(PTS='points', FGM='fieldGoalsMade', FGA='fieldGoalsAttempted', FG3M='threePointersMade', FG3A='threePointersAttempted',
            FTM='freeThrowsMade', FTA='freeThrowsAttempted', OREB='reboundsOffensive', DREB='reboundsDefensive', AST='assists',
            TOV='turnovers', STL='steals', BLK='blocks', PF='foulsPersonal')


def mins(s):
    m = re.match(r'PT(\d+)M([\d.]+)S', s or '')
    return int(m.group(1)) + float(m.group(2)) / 60 if m else 0.0


def prior(season):
    acc = collections.defaultdict(collections.Counter)
    for f in glob.glob(os.path.join(ROOT, f'data/season-source/dnp-{season}-raw/boxscore_*.json.gz')):
        g = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']
        for s in ('homeTeam', 'awayTeam'):
            for p in g[s]['players']:
                st = p.get('statistics') or {}; m = mins(st.get('minutes'))
                if m:
                    acc[p['personId']].update({'MIN': m, **{k: st[v] for k, v in BOXK.items()}})
    return acc


def rows(f):
    d = json.load(open(os.path.join(SRC, f), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


P25, P24 = prior('2025-26'), prior('2024-25')
PG, TG = rows('player-games.json'), rows('team-games.json')
cur = collections.defaultdict(collections.Counter); nm = {}; games = set()
for r in PG:
    if r['TEAM_ABBREVIATION'] == TEAM and r['MIN']:
        cur[r['PLAYER_ID']].update({'MIN': r['MIN'], **{k: r[k] or 0 for k in KS}}); nm[r['PLAYER_ID']] = r['PLAYER_NAME']; games.add(r['GAME_ID'])
N = len(games)


def base(p):
    for src, tag in ((P25, '25-26'), (P24, '24-25')):
        if src.get(p, {}).get('MIN', 0) >= 300:
            return src[p], tag
    return None, '無'


ts = lambda c: c['PTS'] / (2 * (c['FGA'] + 0.44 * c['FTA'])) if c['FGA'] + c['FTA'] else 0.0
exp_t, act_t = collections.Counter(), collections.Counter(); per = {}
for p, c in cur.items():
    b, tag = base(p)
    if b is None:
        continue
    f = c['MIN'] / b['MIN']; e = collections.Counter({k: b[k] * f for k in KS}); e['MIN'] = c['MIN']
    exp_t.update(e); act_t.update(c)
    tsa = c['FGA'] + 0.44 * c['FTA']
    per[p] = dict(tag=tag, mpg=c['MIN'] / N, d={k: (c[k] - e[k]) / N for k in KS}, ts0=ts(b), ts1=ts(c),
                  eff=(c['PTS'] - 2 * ts(b) * tsa) / N, dvol=(tsa - (e['FGA'] + 0.44 * e['FTA'])) / N)
cov = act_t['MIN'] / sum(c['MIN'] for c in cur.values())
print(f"{TEAM} {N} 場；有去年（或前年）≥300 分鐘基準的球員佔分鐘 {cov:.0%}")
print('\n【進攻／個人 box】陣容預期（去年每36 × 今年分鐘） vs 實際，每場')
for k in KS:
    print(f"  {k:5s} 預期 {exp_t[k] / N:6.1f}  實際 {act_t[k] / N:6.1f}  差 {(act_t[k] - exp_t[k]) / N:+5.1f}")
tsa_a = act_t['FGA'] + 0.44 * act_t['FTA']
print(f"  TS%  預期 {ts(exp_t):.3f}  實際 {ts(act_t):.3f} → 同樣出手量多得 {(act_t['PTS'] - ts(exp_t) * 2 * tsa_a) / N:+.1f} 分／場")
print(f"  三分% 預期 {exp_t['FG3M'] / exp_t['FG3A']:.3f} 實際 {act_t['FG3M'] / act_t['FG3A']:.3f}；兩分% 預期 {(exp_t['FGM'] - exp_t['FG3M']) / (exp_t['FGA'] - exp_t['FG3A']):.3f} 實際 {(act_t['FGM'] - act_t['FG3M']) / (act_t['FGA'] - act_t['FG3A']):.3f}；罰球% 預期 {exp_t['FTM'] / exp_t['FTA']:.3f} 實際 {act_t['FTM'] / act_t['FTA']:.3f}")

# 防守：對手在對 POR 這場 vs 對手自己其他場的平均
by = collections.defaultdict(dict); tot = collections.defaultdict(collections.Counter); gp = collections.Counter()
for r in TG:
    by[r['GAME_ID']][r['TEAM_ABBREVIATION']] = r
for gid, g in by.items():
    if len(g) != 2:
        continue
    a, b = list(g)
    for x, y in ((a, b), (b, a)):
        tot[x].update({k: g[x][k] for k in KS}); tot[x].update({'o' + k: g[y][k] for k in KS}); gp[x] += 1
print('\n【防守】對手打 POR vs 對手本季其他場平均（扣掉對 POR 那場），每場')
dd = collections.Counter()
for gid, g in by.items():
    if TEAM not in g or len(g) != 2:
        continue
    o = [t for t in g if t != TEAM][0]; n = gp[o] - 1
    if n <= 0:
        continue
    for k in KS:
        dd[k] += g[o][k] - (tot[o][k] - g[o][k]) / n
        dd['opp_of_' + k] += g[TEAM][k] - (tot[o]['o' + k] - g[TEAM][k]) / n   # POR 對這個對手 vs 這個對手平常讓人拿多少
    dd['n'] += 1
for k in ['PTS', 'FGA', 'FG3A', 'FG3M', 'FTA', 'OREB', 'TOV', 'AST']:
    print(f"  對手 {k:5s} 比平常 {dd[k] / dd['n']:+5.1f}    ｜ POR {k:5s} 比對手平常讓人拿 {dd['opp_of_' + k] / dd['n']:+5.1f}")

print('\n【球員】今年 − 去年基準（換算到今年分鐘），每場')
print('  球員               基準  分鐘  ΔPTS 效率分 Δ出手量  TS 去年→今年  ΔAST ΔTOV ΔOREB ΔDREB ΔSTL ΔBLK')
for p in sorted(per, key=lambda p: -per[p]['mpg']):
    v = per[p]; d = v['d']
    print(f"  {nm[p][:18]:18s} {v['tag']} {v['mpg']:4.1f} {d['PTS']:+5.1f} {v['eff']:+5.1f}  {v['dvol']:+5.1f}   {v['ts0']:.3f}→{v['ts1']:.3f}  {d['AST']:+4.1f} {d['TOV']:+4.1f} {d['OREB']:+5.1f} {d['DREB']:+5.1f} {d['STL']:+4.1f} {d['BLK']:+4.1f}")
for p in cur:
    if p not in per:
        print(f"  無基準：{nm[p]} {cur[p]['MIN'] / N:.1f} 分鐘／場")
