# E-208 prep: builds inputs.json (game rosters/minutes, preseason rosters, 2024-25 baseline, 2025-26 actuals). Light, local.
import json, collections, hashlib, sys
def rs(path):
    d = json.load(open(path, encoding='utf-8'))['data']['resultSets']
    d = d[0] if isinstance(d, list) else d
    return d['headers'], d['rowSet']
def norm(items, n=10, total=240.0, cap=48.0):
    items = sorted(items, key=lambda t: -t[1])[:n]
    items = [[p, m] for p, m in items if m > 0]
    if not items: return []
    for _ in range(50):
        s = sum(m for _, m in items); k = total / s
        items = [[p, min(m * k, cap)] for p, m in items]
        if abs(sum(m for _, m in items) - total) < 1e-9: break
    return [[p, round(m, 6)] for p, m in items]
H, R = rs('data/season-source/player-games.json')
c = {h: i for i, h in enumerate(H)}
H4, R4 = rs('data/season-source-2024-25/player-games.json')
league = json.load(open('data/season-league.json', encoding='utf-8'))
teams = {t['id']: {'name': t['name'], 'W': t['observed']['W'], 'L': t['observed']['L']} for t in league['teams']}
abbr = {}
for r in R: abbr[r[c['TEAM_ID']]] = r[c['TEAM_ABBREVIATION']]
for t in teams: teams[t]['abbr'] = abbr[t]
byGame = collections.defaultdict(dict)  # gid -> pid -> (min, team)
for r in R:
    if (r[c['MIN']] or 0) > 0: byGame[r[c['GAME_ID']]][r[c['PLAYER_ID']]] = (float(r[c['MIN']]), r[c['TEAM_ID']])
games = []
for i, g in enumerate(league['schedule']):
    bg = byGame[g['id']]
    def side(tid, ids):
        items = [[p, bg[p][0]] for p in ids if p in bg and bg[p][1] == tid]
        # also anyone listed in box for that team but not in id list
        items += [[p, v[0]] for p, v in bg.items() if v[1] == tid and p not in ids]
        return items
    hr = side(g['homeId'], set(g['homePlayerIds'])); ar = side(g['awayId'], set(g['awayPlayerIds']))
    games.append({'i': i, 'id': g['id'], 'date': g['date'], 'home': g['homeId'], 'away': g['awayId'],
                  'hs': g['observed']['homeScore'], 'as': g['observed']['awayScore'],
                  'hr': norm(hr), 'ar': norm(ar)})
# season-average rosters (a, rating): total minutes on team / team games
tg = collections.Counter(); tm = collections.defaultdict(lambda: collections.defaultdict(float))
for g in games: tg[g['home']] += 1; tg[g['away']] += 1
for r in R:
    if (r[c['MIN']] or 0) > 0: tm[r[c['TEAM_ID']]][r[c['PLAYER_ID']]] += float(r[c['MIN']])
seasonAvg = {t: norm([[p, m / tg[t]] for p, m in d.items()]) for t, d in tm.items()}
# 2024-25 MPG (any team) and per-team stats
c4 = {h: i for i, h in enumerate(H4)}
mins = collections.defaultdict(float); gp = collections.Counter()
for r in R4:
    if (r[c4['MIN']] or 0) > 0: mins[r[c4['PLAYER_ID']]] += float(r[c4['MIN']]); gp[r[c4['PLAYER_ID']]] += 1
mpg_last = {p: mins[p] / gp[p] for p in mins}
REPL_MPG = 12.0  # pre-fixed: newcomers/rookies without 2024-25 minutes
first10 = {}
for t in teams:
    gs = sorted([g for g in games if t in (g['home'], g['away'])], key=lambda g: (g['date'], g['id']))[:10]
    ps = collections.Counter()
    for g in gs:
        for p, m in (g['hr'] if g['home'] == t else g['ar']): ps[p] += 1
    first10[t] = list(ps)
pre = {t: norm([[p, mpg_last.get(p, REPL_MPG)] for p in first10[t]]) for t in teams}
def team_stats(Rr, cc, season):
    # per-game team totals -> ortg/drtg/net per 100 using FGA-OREB+TOV+0.44FTA, plus mean margin
    tot = collections.defaultdict(lambda: collections.defaultdict(float)); per = collections.defaultdict(dict)
    for r in Rr:
        g = r[cc['GAME_ID']]; t = r[cc['TEAM_ID']]
        for k in ('PTS', 'FGA', 'OREB', 'TOV', 'FTA'): tot[(g, t)][k] += (r[cc[k]] or 0)
        per[g][t] = 1
    out = collections.defaultdict(lambda: {'pf': 0, 'pa': 0, 'poss': 0, 'g': 0})
    for g, d in per.items():
        ts = list(d)
        if len(ts) != 2: continue
        a, b = ts
        pa = lambda x: tot[(g, x)]['FGA'] - tot[(g, x)]['OREB'] + tot[(g, x)]['TOV'] + 0.44 * tot[(g, x)]['FTA']
        poss = (pa(a) + pa(b)) / 2
        for x, y in ((a, b), (b, a)):
            o = out[x]; o['pf'] += tot[(g, x)]['PTS']; o['pa'] += tot[(g, y)]['PTS']; o['poss'] += poss; o['g'] += 1
    res = {}
    for t, o in out.items():
        res[t] = {'ortg': 100 * o['pf'] / o['poss'], 'drtg': 100 * o['pa'] / o['poss'], 'margin': (o['pf'] - o['pa']) / o['g'], 'g': o['g'], 'pace': o['poss'] / o['g']}
        res[t]['net'] = res[t]['ortg'] - res[t]['drtg']
    return res
a25 = team_stats(R, c, '2025-26'); a24 = team_stats(R4, c4, '2024-25')
adv = json.load(open('data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets']
adv = adv[0] if isinstance(adv, list) else adv
ha = {h: i for i, h in enumerate(adv['headers'])}
official = {r[ha['TEAM_ID']]: {'ortg': r[ha['E_OFF_RATING']] if 'E_OFF_RATING' in ha and False else r[ha['OFF_RATING']], 'drtg': r[ha['DEF_RATING']], 'net': r[ha['NET_RATING']], 'pace': r[ha['PACE']]} for r in adv['rowSet']}
# league-wide 2024-25 mean to also give B0 for teams
out = {'teams': {str(t): v for t, v in teams.items()}, 'games': games,
       'seasonAvg': {str(t): v for t, v in seasonAvg.items()}, 'pre': {str(t): v for t, v in pre.items()},
       'first10': {str(t): v for t, v in first10.items()}, 'replMpg': REPL_MPG,
       'actual2526': {str(t): v for t, v in a25.items()}, 'base2425': {str(t): v for t, v in a24.items()},
       'official2526': {str(t): v for t, v in official.items()},
       'sources': {f: hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in
                   ['data/season-league.json', 'data/season-source/player-games.json', 'data/season-source-2024-25/player-games.json', 'data/defense-source/advanced-teams.json']}}
json.dump(out, open('reports/E208-team-rating/inputs.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(games), 'games', sum(1 for g in games if len(g['hr']) < 5 or len(g['ar']) < 5), 'games with <5 players',
      'teams2024', len(a24), 'missing24', [t for t in teams if t not in a24])
print({k: round(v, 2) for k, v in list(a25[1610612737].items())}, official[1610612737])
print(pre[str(1610612737)] if str(1610612737) in pre else pre[1610612737])
