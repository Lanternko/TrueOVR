"""E-229b prep：已完賽每場的兩隊陣容（d 之前資訊＋該場實際出賽名單）與 live 資料夾分組。不讀比賽結果（結果只在 eval.py 用）。
python -I -X utf8 prep.py → work/games.json"""
import json, os, sys, collections, csv
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import team_ratings_daily as M
SD = os.path.join(ROOT, 'data', 'season-source-2026-27')
LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)


def tab(f):
    d = json.load(open(os.path.join(SD, f), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    H = t['headers']
    return [dict(zip(H, r)) for r in t['rowSet']]


def folders():
    return sorted(x for x in os.listdir(LIVE) if len(x) == 10 and x[:4] == '2026' and os.path.isdir(os.path.join(LIVE, x)))


def folder_for(d, fl):
    c = [f for f in fl if f < d]
    return c[-1] if c else fl[0]


def main():
    pg = tab('player-games.json'); tg = tab('team-games.json')
    fl = folders()
    games = {}
    for r in tg:
        g = games.setdefault(r['GAME_ID'], dict(gid=r['GAME_ID'], date=r['GAME_DATE']))
        s = 'home' if 'vs.' in r['MATCHUP'] else 'away'
        g[s] = str(r['TEAM_ID']); g['pts_' + s] = r['PTS']
    games = {k: v for k, v in games.items() if 'home' in v and 'away' in v}
    tot = collections.Counter()
    rows = [r for r in pg if r['MIN'] and r['MIN'] > 0]
    for r in rows:
        tot[(r['GAME_ID'], r['TEAM_ID'])] += r['MIN']
    plog = collections.defaultdict(list)
    played = collections.defaultdict(set)
    for r in rows:
        plog[r['PLAYER_ID']].append((r['GAME_DATE'], r['GAME_ID'], r['MIN'] * 240.0 / tot[(r['GAME_ID'], r['TEAM_ID'])]))
        played[(r['GAME_ID'], str(r['TEAM_ID']))].add(r['PLAYER_ID'])
    for p in plog:
        plog[p].sort()
    cache = {}
    def rk(f):
        if f not in cache:
            R = list(csv.DictReader(open(os.path.join(LIVE, f, 'ranking.csv'), encoding='utf-8')))
            cache[f] = ({int(x['playerId']): float(x['MPGhat']) for x in R}, {int(x['playerId']): float(x['ovr']) for x in R})
        return cache[f]
    out = []; nfb = 0; ntot = 0
    for gid in sorted(games, key=lambda k: (games[k]['date'], k)):
        g = games[gid]; d = g['date']; f = folder_for(d, fl); g['folder'] = f
        mpg, ovr = rk(f)
        for side in ('home', 'away'):
            base = []
            for p in played[(gid, g[side])]:
                a = M.own_avg([m for dd, _, m in plog[p] if dd < d]); ntot += 1
                if a is None:
                    nfb += 1; a = mpg.get(p, 8.0)
                base.append([p, a])
            g['rot_' + side] = M.rotation([], base, ovr=ovr)
        out.append(g)
    json.dump(out, open(os.path.join(HERE, 'work', 'games.json'), 'w'))
    print('games', len(out), 'folders', dict(collections.Counter(g['folder'] for g in out)), 'players w/o prior log', nfb, '/', ntot)


if __name__ == '__main__':
    main()
