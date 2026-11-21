"""POR 診斷第二輪（2026-11-07）：「其他」殘差拆籃板／失誤／罰球／出手量，球員場上產出 vs OVR。python -I -X utf8 por2.py"""
import collections, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'data/season-source-2026-27')


def rows(f):
    d = json.load(open(os.path.join(SRC, f), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


TG = rows('team-games.json'); PG = rows('player-games.json')
R = json.load(open(os.path.join(SRC, 'team-ratings.json'), encoding='utf-8'))
by = collections.defaultdict(dict)
for r in TG:
    by[r['GAME_ID']][r['TEAM_ABBREVIATION']] = r
ST = ['PTS', 'FGA', 'FG3A', 'FTA', 'FTM', 'OREB', 'DREB', 'TOV', 'STL', 'FGM', 'FG3M', 'PF']
team = collections.defaultdict(lambda: {'n': 0, 'own': collections.Counter(), 'opp': collections.Counter()})
for gid, g in by.items():
    if len(g) != 2:
        continue
    a, b = list(g)
    for x, y in ((a, b), (b, a)):
        t = team[x]; t['n'] += 1
        t['own'].update({k: g[x][k] for k in ST}); t['opp'].update({k: g[y][k] for k in ST})


def poss(c):
    return c['FGA'] + 0.44 * c['FTA'] + c['TOV'] - c['OREB']


lg = collections.Counter(); N = 0
for t in team.values():
    lg.update(t['own']); N += t['n']
ppp = lg['PTS'] / poss(lg); pfga = (lg['PTS'] - lg['FTM']) / lg['FGA']; pft = lg['FTM'] / lg['FTA']
print(f"聯盟：每回合 {ppp:.3f} 分、每次出手 {pfga:.3f} 分、罰球 {pft:.3f}")


def per(t, side, k):
    return t[side][k] / t['n']


def rank(k, side, hi=True):
    v = sorted(team, key=lambda a: -per(team[a], side, k) if hi else per(team[a], side, k))
    return v.index('POR') + 1


P = team['POR']; out = {}
print(f"\nPOR {P['n']} 場，每場（自己／對手／聯盟）")
for k in ['PTS', 'FGA', 'FG3A', 'FTA', 'OREB', 'DREB', 'TOV', 'STL', 'PF']:
    print(f"  {k:5s} {per(P, 'own', k):6.1f} (第{rank(k, 'own')}) ／ {per(P, 'opp', k):6.1f} (對手第{rank(k, 'opp')}) ／ {lg[k] / N:6.1f}")
po, pd = poss(P['own']) / P['n'], poss(P['opp']) / P['n']
print(f"  回合  {po:.1f} ／ {pd:.1f} ／ {poss(lg) / N:.1f}")
# 出手次數差（自己 − 對手）來源：進攻籃板差、失誤差、罰球
d_oreb = per(P, 'own', 'OREB') - per(P, 'opp', 'OREB'); d_tov = per(P, 'opp', 'TOV') - per(P, 'own', 'TOV')
d_fga = per(P, 'own', 'FGA') - per(P, 'opp', 'FGA'); d_fta = per(P, 'own', 'FTA') - per(P, 'opp', 'FTA')
print(f"\n出手次數差 {d_fga:+.1f}／場：進攻籃板差 {d_oreb:+.1f}、對手多失誤 {d_tov:+.1f}；罰球出手差 {d_fta:+.1f}")
val = dict(籃板=d_oreb * pfga, 失誤=d_tov * ppp, 罰球=d_fta * pft)
fga_other = d_fga - d_oreb - d_tov
val['其餘出手差（罰球回合、犯規等）'] = fga_other * pfga
print('換算成分（用聯盟平均效率）：' + '、'.join(f"{k} {v:+.1f}" for k, v in val.items()) + f"，合計 {sum(val.values()):+.1f}")
for k in ['OREB', 'TOV']:
    pass
# 進攻籃板率、失誤率
orb = P['own']['OREB'] / (P['own']['OREB'] + P['opp']['DREB']); dorb = P['opp']['OREB'] / (P['opp']['OREB'] + P['own']['DREB'])
lorb = lg['OREB'] / (lg['OREB'] + lg['DREB'])
print(f"進攻籃板率 {orb:.3f}、對手進攻籃板率 {dorb:.3f}（聯盟 {lorb:.3f}）；失誤率 {P['own']['TOV'] / poss(P['own']):.3f}／對手 {P['opp']['TOV'] / poss(P['opp']):.3f}（聯盟 {lg['TOV'] / poss(lg):.3f}）")

# 球員
tm = [v for v in R['teams'].values() if v['abbr'] == 'POR'][0]
ovr = {}; mexp = {}
for r in tm['c']['rotation']:
    ovr[r['pid']] = r['ovr']; mexp[r['pid']] = r['min']
pl = collections.defaultdict(collections.Counter); gp = collections.Counter(); name = {}
for r in PG:
    if r['TEAM_ABBREVIATION'] != 'POR' or not r['MIN']:
        continue
    p = r['PLAYER_ID']; name[p] = r['PLAYER_NAME']; gp[p] += 1
    pl[p].update({k: r[k] or 0 for k in ['MIN', 'PTS', 'FGA', 'FTA', 'FG3A', 'OREB', 'DREB', 'AST', 'TOV', 'STL', 'BLK', 'PLUS_MINUS']})
print(f"\n球員（POR 全隊淨 {(P['own']['PTS'] - P['opp']['PTS']) / P['n']:+.1f}／場）")
print('  球員               OVR  場  分/場  T預期分  每36: 分  TS%   籃板 進攻板 助攻 失誤 抄截 火鍋  場上±/36')
for p in sorted(pl, key=lambda p: -pl[p]['MIN']):
    c = pl[p]; m = c['MIN']; f = 36 / m if m else 0
    ts = c['PTS'] / (2 * (c['FGA'] + 0.44 * c['FTA'])) if c['FGA'] + c['FTA'] else 0
    print(f"  {name[p][:18]:18s} {ovr.get(p, float('nan')):5.1f} {gp[p]:2d} {m / gp[p]:5.1f} {mexp.get(p, 0):6.1f}   {c['PTS'] * f:5.1f} {ts:.3f} {(c['OREB'] + c['DREB']) * f:5.1f} {c['OREB'] * f:5.1f} {c['AST'] * f:4.1f} {c['TOV'] * f:4.1f} {c['STL'] * f:4.1f} {c['BLK'] * f:4.1f}  {c['PLUS_MINUS'] * f:+6.1f}")
