# E-208 forward freeze inputs: live (inseason 0.2.12b) minus card-0.2.12b (2025-26 end) attribute deltas, current rosters/minutes.
import csv, json, re, unicodedata, hashlib, collections
SCR = 'C:/Users/柯子捷/AppData/Local/Temp/claude/D--Projects-CODING-basketball-autochess/0c2bf552-198f-4fad-9877-1bdf42131258/scratchpad/xplayers.json'
LIVE = 'data/_inseason_build/shell-l08r9i_q/ranking.csv'; CARD = 'reports/card-0.2.12b/ranking.csv'
A = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina']
def nn(s): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
live = list(csv.DictReader(open(LIVE, encoding='utf-8'))); card = list(csv.DictReader(open(CARD, encoding='utf-8')))
inp = json.load(open('reports/E208-team-rating/inputs.json', encoding='utf-8'))
xp = {p['id']: p for p in json.load(open(SCR, encoding='utf-8'))}
cardN = {nn(r['name']): r for r in card}
W = sum(float(r['MIN']) for r in card)
cmean = {a: sum(float(r[a]) * float(r['MIN']) for r in card) / W for a in A}
abbr2id = {v['abbr']: int(k) for k, v in inp['teams'].items()}
abbr2id.update({'BKN': abbr2id.get('BKN', abbr2id.get('BRK')), 'PHX': abbr2id.get('PHX')})
deltas = {}; newp = []; unmatched = []
for r in live:
    pid = int(r['playerId']); c = cardN.get(nn(r['name']))
    if pid in xp and c is not None:
        deltas[pid] = {a: float(r[a]) - float(c[a]) for a in A}
    else:
        newp.append(pid); deltas[pid] = {a: float(r[a]) - cmean[a] for a in A}  # absolute vs league mean; applied to average profile
        if pid in xp: unmatched.append(r['name'])
def norm(items, n=10, total=240.0, cap=48.0):
    items = sorted(items, key=lambda t: -t[1])[:n]; items = [[p, m] for p, m in items if m > 0]
    for _ in range(50):
        s = sum(m for _, m in items); k = total / s; items = [[p, min(m * k, cap)] for p, m in items]
        if abs(sum(m for _, m in items) - total) < 1e-9: break
    return [[p, round(m, 6)] for p, m in items]
by = collections.defaultdict(list)
for r in live: by[r['team']].append([int(r['playerId']), float(r['MPGhat'])])
rosters = {}
for ab, items in by.items():
    if ab not in abbr2id: raise SystemExit('unknown team ' + ab)
    rosters[str(abbr2id[ab])] = norm(items)
lg = json.load(open('data/defense-seventh/2026-27/league.json', encoding='utf-8'))
played = [{'id': g['id'], 'date': g['date'], 'home': g['homeId'], 'away': g['awayId'], 'hs': g['observed']['homeScore'], 'as': g['observed']['awayScore']} for g in lg['schedule']]
sofar = collections.defaultdict(lambda: [0, 0])
for g in played:
    h = g['hs'] > g['as']; sofar[str(g['home'])][0 if h else 1] += 1; sofar[str(g['away'])][1 if h else 0] += 1
meta = json.load(open('data/_inseason_build/shell-l08r9i_q/meta.json', encoding='utf-8'))
out = {'version': meta['version'], 'card': meta['priorCard'], 'dataCutoff': meta['dataCutoff'], 'rosters': rosters, 'deltas': {str(k): v for k, v in deltas.items()},
       'newPlayers': newp, 'cardMean': cmean, 'played': played, 'sofar': dict(sofar), 'teams': inp['teams'], 'attrs': A,
       'sources': {LIVE: hashlib.sha256(open(LIVE, 'rb').read()).hexdigest(), CARD: hashlib.sha256(open(CARD, 'rb').read()).hexdigest(),
                   'data/defense-seventh/2026-27/league.json': hashlib.sha256(open('data/defense-seventh/2026-27/league.json', 'rb').read()).hexdigest()}}
json.dump(out, open('reports/E208-team-rating/forward-inputs.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(rosters), 'teams', len(newp), 'new', 'unmatched-by-name', unmatched[:10], 'games played', len(played), meta['version'], meta['priorCard'], meta['dataCutoff'])
print(sorted(abbr2id.items())[:3], min(len(v) for v in rosters.values()))
