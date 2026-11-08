"""E-273： T 各版本重测 prep：集合 A＝2026-27 開季至最新已完賽日（team-games.json 與 league.json 都有比分的場次）。
輸出 work/games.json（每場：賽前陣容＝比賽日前最新 live 夾，同 E-246 prep）、work/rots.json（{folder: {gid: [rot_home, rot_away]}}，
給 R-172「今天的 T」重算過去場次用：名單＝該場實際上場的人＋比賽日前自己的平均分鐘，MPGhat 後備與 OVR 排序用該 live 夾）。不讀比賽結果當特徵。
python -I -X utf8 prep.py"""
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
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


def folders():
    return sorted(x for x in os.listdir(LIVE) if len(x) == 10 and x[:4] == '2026' and os.path.isdir(os.path.join(LIVE, x)))


def folder_for(d, fl):
    c = [f for f in fl if f < d]
    return c[-1] if c else fl[0]


def main():
    league = json.load(open(os.path.join(ROOT, 'data', 'defense-seventh', '2026-27', 'league.json'), encoding='utf-8'))['schedule']
    obs = {x['id']: x for x in league if x.get('observed')}
    pg = tab('player-games.json'); tg = tab('team-games.json')
    fl = folders()
    games = {}
    for r in tg:
        g = games.setdefault(r['GAME_ID'], dict(gid=r['GAME_ID'], date=r['GAME_DATE']))
        s = 'home' if 'vs.' in r['MATCHUP'] else 'away'
        g[s] = str(r['TEAM_ID']); g['pts_' + s] = r['PTS']
    games = {k: v for k, v in games.items() if 'home' in v and 'away' in v and k in obs}
    for k, g in games.items():      # team-games 與 league.json 比分要一致
        o = obs[k]['observed']
        assert (g['pts_home'], g['pts_away']) == (o['homeScore'], o['awayScore']) and g['home'] == str(obs[k]['homeId']), k
    tot = collections.Counter()
    rows = [r for r in pg if r['MIN'] and r['MIN'] > 0]
    for r in rows:
        tot[(r['GAME_ID'], r['TEAM_ID'])] += r['MIN']
    plog = collections.defaultdict(list); played = collections.defaultdict(set)
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
    def rot(g, side, f):
        mpg, ovr = rk(f); base = []
        for p in played[(g['gid'], g[side])]:
            a = M.own_avg([m for dd, _, m in plog[p] if dd < g['date']])
            base.append([p, mpg.get(p, 8.0) if a is None else a])
        return M.rotation([], base, ovr=ovr)
    out = []; rots = collections.defaultdict(dict)
    order = sorted(games, key=lambda k: (games[k]['date'], k))
    for gid in order:
        g = games[gid]; f = folder_for(g['date'], fl); g['folder'] = f
        g['rot_home'] = rot(g, 'home', f); g['rot_away'] = rot(g, 'away', f)
        out.append(g)
    for f in sorted({g['folder'] for g in out}):     # 以該夾為「今天」時，比賽日 < 該夾對應日的場次用該夾重算名單（含當天，只是用不到）
        for g in out:
            rots[f][g['gid']] = [rot(g, 'home', f), rot(g, 'away', f)]
    json.dump(out, open(os.path.join(HERE, 'work', 'games.json'), 'w'))
    json.dump(rots, open(os.path.join(HERE, 'work', 'rots.json'), 'w'))
    print('games', len(out), 'last', out[-1]['date'], 'folders', dict(collections.Counter(g['folder'] for g in out)))


if __name__ == '__main__':
    main()
