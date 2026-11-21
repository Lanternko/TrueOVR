"""F-129 D1 real side: per defensive stint-row (same rows/order as f129lib.real_rows) attribute opponent FTs to the fouler using pbp.
Rows get: fta, sf {"fouler|zone": FTs from SHOOTING fouls}, nsf {fouler: FTs from non-shooting fouls (bonus etc.)}, oth (technical/flagrant/unlinked),
sfa {zone: shooting-foul trips}, A{short,mid,long} = recorded FGA by zone. FT -> row by FT action index in [startIndex, endIndex).
cwd = repo root; light, pure python/json."""
import json, collections, re, sys
sys.stdout.reconfigure(encoding='utf-8')
def zone(a):
    if a in ('Restricted Area', 'In The Paint (Non-RA)'): return 'short'
    if a in ('Mid-Range',): return 'mid'
    if a and ('3' in a): return 'long'
    return None
def game_links(acts):
    """-> {action index of FT: (fouler, kind, zone, tripId)}; kind in sh/nsh/oth; also list of trips"""
    pend = []; ftmap = {}; trips = []
    for i, x in enumerate(acts):
        t = x.get('actionType')
        if t == 'foul':
            q = [m for m in x.get('qualifiers', []) if m.endswith('freethrow')]
            if not q: continue
            n = int(q[0][0]); st = x.get('subType'); d = x.get('descriptor')
            kind = 'oth' if st != 'personal' or (d and d.startswith('flagrant')) or d == 'clear-path' else ('sh' if d == 'shooting' else 'nsh')
            z = zone(x.get('area')) if kind == 'sh' else None
            trip = {'idx': i, 'fouler': x['personId'], 'team': x['teamId'], 'kind': kind, 'zone': z, 'n': n, 'left': n, 'ft': []}
            pend.append(trip); trips.append(trip)
        elif t == 'freethrow':
            for tr in pend:
                if tr['left'] > 0 and tr['team'] != x['teamId']:
                    tr['left'] -= 1; tr['ft'].append(i); ftmap[i] = tr; break
            pend = [tr for tr in pend if tr['left'] > 0 or tr is pend[-1]]
    return ftmap, trips
def build():
    st = collections.defaultdict(list)
    for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
        s = json.loads(l); st[s['id']].append(s)
    out = {0: [], 1: []}; stat = collections.Counter(); order = []
    for l in open('reports/defense-b1/stints.jsonl', encoding='utf-8'): order.append(json.loads(l)['id'])
    games = {}
    for g in dict.fromkeys(order): games[g] = json.load(open(f'data/defense-a-source/pbp/{g}.json', encoding='utf-8'))['data']['game']['actions']
    links = {g: game_links(games[g]) for g in games}
    for g in games:
        acts = games[g]; ftmap, trips = links[g]; h = int(g) & 1; rows = {}
        for si, s in enumerate(st[g]):
            for k in (0, 1):
                t = s['teams'][k]; o = t['opponent']
                rows[(si, s['teams'][k]['teamId'])] = {'o': s['teams'][1 - k]['players'], 'd': t['players'], 'poss': t['defensivePossessions'], 'gid': g, 'fta_stint': o['fta'], 'ftm': o['ftm'], 'fga': o['fga'],
                       'pts': o['points'], 'shortA': o['shortA'], 'midA': o['midA'], 'longA': o['longA'], 'sf': {}, 'nsf': {}, 'oth': 0, 'sfa': {}, 'ordk': (si, k)}
        bounds = [(s['startIndex'], s['endIndex']) for s in st[g]]
        def stint_of(i):
            for si, (a0, a1) in enumerate(bounds):
                if a0 <= i < a1: return si
            return None
        used = set()
        for tr in trips:
            if not tr['ft']: continue
            si = stint_of(tr['idx']); row = rows.get((si, tr['team'])) if si is not None else None
            if row is None: stat['trip_no_stint'] += len(tr['ft']); continue
            used.update(tr['ft']); m = len(tr['ft'])
            if tr['kind'] == 'sh' and tr['zone']:
                key = f"{tr['fouler']}|{tr['zone']}"; row['sf'][key] = row['sf'].get(key, 0) + m; row['sfa'][tr['zone']] = row['sfa'].get(tr['zone'], 0) + 1; stat['ft_sh'] += m
                if tr['fouler'] not in row['d']: stat['fouler_not_in_lineup'] += m
            elif tr['kind'] == 'nsh': key = str(tr['fouler']); row['nsf'][key] = row['nsf'].get(key, 0) + m; stat['ft_nsh'] += m
            else: row['oth'] += m; stat['ft_oth'] += m
        for si, s in enumerate(st[g]):
            tid = [t['teamId'] for t in s['teams']]
            for k in (0, 1):
                for i in range(s['startIndex'], s['endIndex']):
                    x = acts[i]
                    if x.get('actionType') == 'freethrow' and x.get('teamId') == tid[1 - k] and i not in used:
                        rows[(si, tid[k])]['oth'] += 1; stat['ft_unlinked'] += 1
        for si, s in enumerate(st[g]):
            for k in (0, 1):
                row = rows[(si, s['teams'][k]['teamId'])]
                if row['poss'] <= 0:
                    stat['rows_p0_lost_fta'] += sum(row['sf'].values()) + sum(row['nsf'].values()) + row['oth']; continue
                row['fta'] = sum(row['sf'].values()) + sum(row['nsf'].values()) + row['oth']; stat['fta_foultime'] += row['fta']; stat['fta_stint'] += row['fta_stint']
                out[h].append(row)
    print(dict(stat), {h: len(out[h]) for h in out}); return out
if __name__ == '__main__':
    out = build(); json.dump(out, open('reports/F129-center-ft-defense-diag/real_d1_rows.json', 'w'))
