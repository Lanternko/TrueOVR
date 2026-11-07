"""E-127 特徵建構：每季每人 MIN、ap、mp、L、age、y、d、主隊（定義照 e094.py scope_feats('full')，MIN 改用 player-games 全季加總）。
只讀 data/；不讀任何 RAPM 值。"""
import gzip, importlib.util, json, re, sys
from collections import defaultdict
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
import numpy as np
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
sp = importlib.util.spec_from_file_location('e094', E94 / 'e094.py'); M = importlib.util.module_from_spec(sp); sp.loader.exec_module(M)
AGE_Y, D_THR = M.AGE_Y, M.D_THR
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
COACH = {'INACTIVE_GLEAGUE_TWOWAY', 'INACTIVE_GLEAGUE_ON_ASSIGNMENT', 'INACTIVE_COACH', 'DNP_COACH'}
UNAV = ('INJURY', 'ILLNESS', 'PERSONAL', 'SUSPENSION', 'REST', 'NOT_WITH_TEAM')


def jl(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def _mins(s):
    m = re.match(r'PT(\d+)M([\d.]+)S', s or '')
    return round(int(m.group(1)) + float(m.group(2)) / 60, 4) if m else 0.0


def _cat(status, reason, mn):
    if mn > 0: return 'played'
    r = (reason or '').strip()
    if r in COACH or (status == 'ACTIVE' and not r): return 'coach'
    return 'unavail'


def dnp_from_raw(season):
    raw = ROOT / f'data/season-source/dnp-{season}-raw'; games = {}
    for f in sorted(raw.glob('boxscore_*.json.gz')):
        g = json.loads(gzip.open(f).read())['game']; rows = []
        for side in ('homeTeam', 'awayTeam'):
            t = g[side]
            for p in t['players']:
                mn = _mins(p['statistics'].get('minutes')); rs = (p.get('notPlayingReason') or '').strip()
                rows.append([p['personId'], t['teamId'], p['status'], rs, mn, _cat(p['status'], rs, mn)])
        games[g['gameId']] = {'players': rows}
    return {'games': games}


def paths(season):
    if season == '2025-26':
        return (ROOT / 'data/season-source/player-games.json', ROOT / 'data/season-source/team-games.json', ROOT / 'data/benchmark-source/bio.json')
    b = ROOT / f'data/defense-seventh/{season}'
    return b / 'player-games.json', b / 'team-games.json', b / 'bio.json'


def build(season):
    ppg, ptg, pbio = paths(season)
    pg = jl(ppg)['data']['resultSets'][0]; h = pg['headers']
    ip, it, ia, im = (h.index(k) for k in ('PLAYER_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'MIN'))
    tmin = defaultdict(lambda: defaultdict(float)); abbr = {}
    for r in pg['rowSet']:
        abbr[r[it]] = r[ia]
        if r[im]: tmin[r[ip]][r[it]] += r[im]
    tg = jl(ptg)['data']['resultSets'][0]; h = tg['headers']
    it_, ig, idt, iw = h.index('TEAM_ID'), h.index('GAME_ID'), h.index('GAME_DATE'), h.index('WL')
    sch = defaultdict(list); wl = defaultdict(lambda: [0, 0])
    for r in tg['rowSet']:
        sch[r[it_]].append((r[idt], int(r[ig]))); wl[r[it_]][1] += 1; wl[r[it_]][0] += 1 if r[iw] == 'W' else 0
    sched = {t: [g for _, g in sorted(v)] for t, v in sch.items()}
    winrate = {t: w / n for t, (w, n) in wl.items()}
    bio = jl(pbio)['data']['resultSets'][0]; h = bio['headers']
    age = {r[h.index('PLAYER_ID')]: r[h.index('AGE')] for r in bio['rowSet'] if r[h.index('AGE')] is not None}
    dnp = jl(ROOT / 'data/season-source/dnp-2025-26.json') if season == '2025-26' else dnp_from_raw(season)
    M.D['dnp'], M.D['sched'] = dnp, sched
    M.D['sidx'] = {t: {g: i for i, g in enumerate(v)} for t, v in sched.items()}
    C = M.classify(M.BASE_OPTS)
    pids = sorted(tmin)
    out = {}
    for q in pids:
        MIN = sum(tmin[q].values())
        a = C['agg'].get(q)
        ap = (a['A'][0] + a['B'][0]) if a else 0
        mp = MIN / ap if ap > 0 else 0.0
        main = max(sorted(tmin[q].items()), key=lambda kv: kv[1])[0]
        ag = age.get(q)
        y = 1.0 if (ag is not None and ag <= AGE_Y) else 0.0
        d = 1.0 if winrate[main] < D_THR else 0.0
        out[q] = {'MIN': MIN, 'ap': ap, 'mp': mp, 'L': float(np.log1p(mp)), 'age': ag, 'y': y, 'd': d, 'main': main, 'mainAbbr': abbr[main]}
    meta = {'nGamesDnp': len(dnp['games']), 'nPlayers': len(out), 'winrate': {abbr[t]: round(w, 4) for t, w in winrate.items()},
            'tankTeams': sorted(abbr[t] for t, w in winrate.items() if w < D_THR)}
    return out, meta
