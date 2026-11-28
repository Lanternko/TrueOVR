# E-208 追加：2026-27 前瞻凍結的 (c)(d) 分鐘。資料截止同原凍結檔 (forward-inputs.json)。
# python -I -X utf8 reports/E208-team-rating/prep_forward_minutes.py  (從 repo 根目錄) -> forward-inputs-c.json, forward-inputs-d.json, forward-minutes-compare.json
import json, os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from minutes_rules import norm, rule_c, rule_d
fi = json.load(open(f'{HERE}/forward-inputs.json', encoding='utf-8'))
pa = json.load(open(f'{HERE}/players-attrs.json', encoding='utf-8')); A = pa['attrs']
def mins(s):
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', s or ''); return int(m[1]) + float(m[2]) / 60 if m else 0.0
games = []
for f in sorted(glob.glob('data/defense-seventh/2026-27/boxes/*.json')):
    g = json.load(open(f, encoding='utf-8'))['data']['game']
    if g.get('gameStatus') != 3: continue
    r = {}
    for k in ('homeTeam', 'awayTeam'):
        t = g[k]; r[k] = (str(t['teamId']), norm([[p['personId'], mins(p['statistics']['minutes'])] for p in t['players']]))
    games.append((g['gameTimeUTC'], g['gameId'], r))
games.sort(); hist = collections.defaultdict(list)
for _, _, r in games:
    for k in r: hist[r[k][0]].append(r[k][1])
newset = set(fi['newPlayers'])
def prof(pid):
    b = pa['players'].get(str(pid)); d = fi['deltas'].get(str(pid))
    if pid in newset or b is None:
        p = dict(pa['avg']); p['pos'] = 'SF'
        if d: p = {**p, **{a: max(0, min(120, pa['avg'][a] + d[a])) for a in A}}
        return p
    p = dict(b)
    if d:
        for a in A: p[a] = max(0, min(120, p[a] + d[a]))
    return p
ovr = lambda pid: sum(prof(pid)[a] for a in A) / len(A); pos = lambda pid: prof(pid)['pos']
out = {'c': {}, 'd': {}}
for t, pre in fi['rosters'].items():
    pr = hist[t][-10:]; out['c'][t] = rule_c(pr, pre); out['d'][t] = rule_d(pr, pre, ovr, pos)
for tag in 'cd':
    json.dump({**fi, 'rosters': out[tag], 'rosters_b_original': fi['rosters'], 'n_box_games': len(games)}, open(f'{HERE}/forward-inputs-{tag}.json', 'w', encoding='utf-8'), ensure_ascii=False)
nm = {p['id']: p['name'] for p in json.load(open(os.path.join(HERE, 'xplayers_names.json'), encoding='utf-8'))} if os.path.exists(os.path.join(HERE, 'xplayers_names.json')) else {}
cmp = {t: {'b': fi['rosters'][t], 'c': out['c'][t], 'd': out['d'][t], 'pos_ovr': {str(p): [pos(p), round(ovr(p), 1)] for tag in 'bcd' for p, _ in (fi['rosters'] if tag == 'b' else out[tag])[t]}} for t in fi['rosters']}
json.dump(cmp, open(f'{HERE}/forward-minutes-compare.json', 'w', encoding='utf-8'))
print(len(games), 'box games;', 'min prior games', min(len(v) for v in hist.values()))
mem = '1610612763'
for tag in 'bcd': print('MEM', tag, [(p, round(m, 1), cmp[mem]['pos_ovr'][str(p)]) for p, m in (fi['rosters'] if tag == 'b' else out[tag])[mem]])
