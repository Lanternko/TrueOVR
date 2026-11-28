# E-208 追加：2024-25 回測輸入。只讀 dnp-2023-24-raw／dnp-2024-25-raw 的 boxscore（repo 內現有，各 1093／1104 場，抓不到補場），輕量本機。
# python -I -X utf8 reports/E208-team-rating/prep_2425.py
import gzip, json, re, glob, hashlib, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def mins(s):
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', s or ''); return int(m[1]) + float(m[2]) / 60 if m else 0.0
def load(season):
    out = []
    for f in sorted(glob.glob(str(ROOT / f'data/season-source/dnp-{season}-raw/boxscore_00*.json.gz'))):
        g = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']
        if not g['gameId'].startswith('002' + season[2:4]): continue
        out.append(g)
    return out
def norm(items, n=10, total=240.0, cap=48.0):
    items = sorted(items, key=lambda t: -t[1])[:n]; items = [[p, m] for p, m in items if m > 0]
    if not items: return []
    for _ in range(50):
        s = sum(m for _, m in items); k = total / s
        items = [[p, min(m * k, cap)] for p, m in items]
        if abs(sum(m for _, m in items) - total) < 1e-9: break
    return [[p, round(m, 6)] for p, m in items]
def side(t):
    pl = []; tot = collections.Counter()
    for p in t['players']:
        s = p['statistics']; mn = mins(s['minutes'])
        for k, kk in (('PTS', 'points'), ('FGA', 'fieldGoalsAttempted'), ('OREB', 'reboundsOffensive'), ('TOV', 'turnovers'), ('FTA', 'freeThrowsAttempted')): tot[k] += s[kk]
        if mn > 0: pl.append([p['personId'], mn])
    return pl, tot
def team_stats(gs):
    out = collections.defaultdict(lambda: {'pf': 0, 'pa': 0, 'poss': 0, 'g': 0})
    for g in gs:
        (_, th), (_, ta) = side(g['homeTeam']), side(g['awayTeam'])
        pa = lambda x: x['FGA'] - x['OREB'] + x['TOV'] + 0.44 * x['FTA']
        poss = (pa(th) + pa(ta)) / 2
        for t, a, b in ((g['homeTeam']['teamId'], th, ta), (g['awayTeam']['teamId'], ta, th)):
            o = out[t]; o['pf'] += a['PTS']; o['pa'] += b['PTS']; o['poss'] += poss; o['g'] += 1
    res = {}
    for t, o in out.items():
        r = {'ortg': 100 * o['pf'] / o['poss'], 'drtg': 100 * o['pa'] / o['poss'], 'margin': (o['pf'] - o['pa']) / o['g'], 'g': o['g'], 'pace': o['poss'] / o['g']}
        r['net'] = r['ortg'] - r['drtg']; res[str(t)] = r
    return res
G25 = sorted(load('2024-25'), key=lambda g: (g['gameTimeLocal'][:10], g['gameId']))
G24 = load('2023-24')
teams = {}; games = []; W = collections.Counter(); L = collections.Counter()
for i, g in enumerate(G25):
    h, a = g['homeTeam'], g['awayTeam']
    for t in (h, a): teams.setdefault(str(t['teamId']), {'name': t['teamCity'] + ' ' + t['teamName'], 'abbr': t['teamTricode']})
    hr, _ = side(h); ar, _ = side(a)
    assert h['score'] != a['score']
    games.append({'i': i, 'id': g['gameId'], 'date': g['gameTimeLocal'][:10], 'home': h['teamId'], 'away': a['teamId'], 'hs': h['score'], 'as': a['score'], 'hr': norm(hr), 'ar': norm(ar)})
    w, l = (h, a) if h['score'] > a['score'] else (a, h); W[str(w['teamId'])] += 1; L[str(l['teamId'])] += 1
for t in teams: teams[t].update(W=W[t], L=L[t])
tg = collections.Counter(); tm = collections.defaultdict(lambda: collections.defaultdict(float))
for g in games: tg[g['home']] += 1; tg[g['away']] += 1
for g in G25:
    for t in (g['homeTeam'], g['awayTeam']):
        for p in t['players']:
            m = mins(p['statistics']['minutes'])
            if m > 0: tm[t['teamId']][p['personId']] += m
seasonAvg = {str(t): norm([[p, m / tg[t]] for p, m in d.items()]) for t, d in tm.items()}
mn = collections.defaultdict(float); gp = collections.Counter()
for g in G24:
    for t in (g['homeTeam'], g['awayTeam']):
        for p in t['players']:
            m = mins(p['statistics']['minutes'])
            if m > 0: mn[p['personId']] += m; gp[p['personId']] += 1
mpg_last = {p: mn[p] / gp[p] for p in mn}
REPL = 12.0
first10 = {}
for t in teams:
    gs = sorted([g for g in games if int(t) in (g['home'], g['away'])], key=lambda g: (g['date'], g['id']))[:10]
    ps = collections.Counter()
    for g in gs:
        for p, m in (g['hr'] if str(g['home']) == t else g['ar']): ps[p] += 1
    first10[t] = list(ps)
pre = {t: norm([[p, mpg_last.get(p, REPL)] for p in first10[t]]) for t in teams}
src = [str(f) for f in sorted(glob.glob(str(ROOT / 'data/season-source/dnp-2024-25-raw/boxscore_00*.json.gz')) + glob.glob(str(ROOT / 'data/season-source/dnp-2023-24-raw/boxscore_00*.json.gz')))]
h = hashlib.sha256()
for f in src: h.update(Path(f).name.encode()); h.update(hashlib.sha256(open(f, 'rb').read()).digest())
out = {'teams': teams, 'games': games, 'seasonAvg': seasonAvg, 'pre': pre, 'first10': first10, 'replMpg': REPL,
       'actual2425': team_stats(G25), 'base2324': team_stats(G24), 'n_games_2425': len(G25), 'n_games_2324': len(G24),
       'sources': {'raw_boxscore_set_sha256': h.hexdigest(), 'n_files': len(src)}}
(Path(__file__).parent / 'inputs-2425.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
newc = sum(1 for t in pre for p, m in pre[t] if p not in mpg_last)
print(len(G25), 'games 2024-25;', len(G24), 'games 2023-24;', len(teams), 'teams; first-10 roster players w/o 2023-24 minutes:', newc, 'of', sum(len(v) for v in pre.values()))
print('games/team 2425', sorted(collections.Counter(tg).values())[:3], 'W sum', sum(v['W'] for v in teams.values()))
