"""F-130: real 2025-26 FTA split from pbp (shooting / bonus-nonshooting / technical) per team and per player, plus box FGA/FTA/min.
cwd = repo root. Writes real130.json."""
import glob, json, re, sys
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/F130-team-ftdraw-spread-diag/'
ids = [t['id'] for t in json.load(open('reports/E140-foul-on-recal/team-ids.json', encoding='utf-8'))]
pos = {i: k for k, i in enumerate(ids)}
T = lambda: {'fta2': 0, 'g': 0, 'min48': 0.0, 'fga': 0, 'fta': 0, 'oreb': 0, 'ft': defaultdict(int)}
team = defaultdict(T); player = defaultdict(lambda: {'fga': 0, 'fta': 0, 'ft': defaultdict(int)})
for f in sorted(glob.glob('data/defense-source/boxes/*.json')):
    d = json.load(open(f, encoding='utf-8'))['data']; b = d.get('boxScoreTraditional') or d['game']
    gmin = 48 + 5 * (b['period'] - 4) if 'period' in b else int(b['homeTeam']['statistics']['minutes'].split(':')[0]) / 5
    for me in ('homeTeam', 'awayTeam'):
        t = team[pos[b[me]['teamId']]]; s = b[me]['statistics']
        t['g'] += 1; t['min48'] += gmin / 48; t['fga'] += s['fieldGoalsAttempted']; t['fta'] += s['freeThrowsAttempted']; t['fta2'] += (s['freeThrowsAttempted'] / (gmin / 48)) ** 2; t['oreb'] += s['reboundsOffensive']
        for p in b[me]['players']:
            q = player[p['personId']]; q['fga'] += p['statistics']['fieldGoalsAttempted']; q['fta'] += p['statistics']['freeThrowsAttempted']
npbp = 0
for f in sorted(glob.glob('data/defense-a-source/pbp/*.json')):
    g = json.load(open(f, encoding='utf-8'))['data']['game']['actions']; npbp += 1
    for i, a in enumerate(g):
        if a['actionType'] != 'freethrow': continue
        j = i - 1
        skip = ('substitution', 'timeout', 'freethrow', 'violation', 'instantreplay', 'stoppage', 'ejection') + (('rebound',) if not a['subType'].startswith('1 of') and a['subType'] != 'Technical' else ())
        while j >= 0 and g[j]['actionType'] in skip: j -= 1
        pr = g[j]
        if pr['actionType'] == 'foul' and pr['subType'] == 'technical': k = 'technical'
        elif pr['actionType'] == 'foul' and 'shooting' in pr['description']: k = 'shooting'
        elif pr['actionType'] == 'foul': k = 'nonshooting'
        else: k = 'other'
        team[pos[a['teamId']]]['ft'][k] += 1; player[a['personId']]['ft'][k] += 1
print('pbp games', npbp)
tot = defaultdict(int)
for t in team.values():
    for k, v in t['ft'].items(): tot[k] += v
print(dict(tot), 'box FTA', sum(t['fta'] for t in team.values()), 'pbp FTA', sum(tot.values()))
json.dump({'team': {k: {**v, 'ft': dict(v['ft'])} for k, v in team.items()}, 'player': {k: {**v, 'ft': dict(v['ft'])} for k, v in player.items()}, 'npbp': npbp},
          open(D + 'real130.json', 'w', encoding='utf-8'))
