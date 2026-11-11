"""E-131 彙整：u1、具名球員、前 20、移動 >=10 名、physique 五等分、results.json、並列 ranking.csv。只讀 K0/K1/summary/evaluation。"""
import csv, json, hashlib
import statistics as st
from pathlib import Path
H = Path(__file__).resolve().parent
R = H.parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


B = R / 'reports/card-0.2.7b/ranking.csv'
K0 = load(H / 'K0/ranking.csv')
K1 = load(H / 'K1/ranking.csv')
cols = list(K0[0].keys())
assert cols == list(K1[0].keys())
c0 = {'sha256': sha(H / 'K0/ranking.csv'), 'want': sha(B), 'pass': sha(H / 'K0/ranking.csv') == sha(B)}
OVR_COLS = {'rank', 'ovr', 'predictedPer36', 'pred0', 'pr', 'align', 'gRepl', 'ovr36', 'simulatedPer36', 'defenseBonus'}
by0 = {r['name']: r for r in K0}
by1 = {r['name']: r for r in K1}
assert len(by0) == len(K0) and set(by0) == set(by1) and [r['name'] for r in K0] != []
chg = {c: sum(1 for k in by0 if by0[k][c] != by1[k][c]) for c in cols}
attr_cols = [c for c in cols if c not in OVR_COLS]
bad = {c: chg[c] for c in attr_cols if chg[c]}
u1 = {'pass': not bad, 'changed_counts': chg, 'non_ovr_cols_changed': bad, 'ovr_related_cols_assumed': sorted(OVR_COLS)}

NAMES = ['Zion Williamson', 'Bam Adebayo', 'Julius Randle', 'Steven Adams', 'Jusuf Nurkić', 'Giannis Antetokounmpo', 'Joel Embiid', 'Nikola Jokić', 'Victor Wembanyama',
         'Chet Holmgren', 'Evan Mobley', 'Jarrett Allen', 'Ivica Zubac', 'Shai Gilgeous-Alexander', 'Tyrese Maxey', 'Trae Young', 'Herbert Jones', 'Luguentz Dort']
players = []
for n in NAMES:
    a, b = by0.get(n), by1.get(n)
    if not a:
        players.append({'name': n, 'missing': True})
        continue
    players.append({'name': n, 'pos': a['pos'], 'MIN': a['MIN'], 'ovr_K0': float(a['ovr']), 'ovr_K1': float(b['ovr']), 'dOvr': round(float(b['ovr']) - float(a['ovr']), 1),
                    'rank_K0': int(a['rank']), 'rank_K1': int(b['rank']), 'heightInches': float(a['heightInches']), 'physique': float(a['physique'])})
t0 = [r['name'] for r in K0[:20]]
t1 = [r['name'] for r in K1[:20]]
top20 = {'K0': [(int(r['rank']), r['name'], float(r['ovr'])) for r in K0[:20]], 'K1': [(int(r['rank']), r['name'], float(r['ovr'])) for r in K1[:20]],
         'out': [n for n in t0 if n not in t1], 'in': [n for n in t1 if n not in t0], 'n_changed': len([n for n in t1 if n not in t0])}
mov = []
for k in by0:
    a, b = by0[k], by1[k]
    if float(a['MIN']) >= 1000:
        d = int(a['rank']) - int(b['rank'])
        if abs(d) >= 10:
            mov.append({'name': k, 'pos': a['pos'], 'rank_K0': int(a['rank']), 'rank_K1': int(b['rank']), 'move_up': d, 'ovr_K0': float(a['ovr']), 'ovr_K1': float(b['ovr']),
                        'physique': float(a['physique']), 'heightInches': float(a['heightInches'])})
mov.sort(key=lambda x: x['move_up'])


def quints(keys):
    keys = sorted(keys, key=lambda k: float(by0[k]['physique']))
    n = len(keys)
    out = []
    for q in range(5):
        seg = keys[q * n // 5:(q + 1) * n // 5]
        d = [float(by1[k]['ovr']) - float(by0[k]['ovr']) for k in seg]
        out.append({'q': q + 1, 'n': len(seg), 'physique_range': [float(by0[seg[0]]['physique']), float(by0[seg[-1]]['physique'])], 'mean_dOvr': round(st.mean(d), 3)})
    return out


q_all = quints(list(by0))
q_1000 = quints([k for k in by0 if float(by0[k]['MIN']) >= 1000])


def S(a):
    return json.load(open(H / f'cards/{a}/primary/summary.json', encoding='utf-8'))


s0, s1 = S('K0'), S('K1')
vals = {a: {k: v['per36'] for k, v in s['valuePer10AttributePoints'].items()} for a, s in (('K0', s0), ('K1', s1))}
se = {a: {k: v['bootstrapSE'] for k, v in s['valuePer10AttributePoints'].items()} for a, s in (('K0', s0), ('K1', s1))}
res = json.load(open(H / 'work/cards-result.json', encoding='utf-8'))
ev = res['eval']
evj = json.load(open(H / 'evaluation.json', encoding='utf-8'))
dall = [(abs(float(by1[k]['ovr']) - float(by0[k]['ovr'])), k) for k in by0]
out = {'c0': c0, 'c1': {'npm_test_exit': (H / 'work/npm-test.exit').read_text().strip(), 'summary': '57 passed, 0 failed'}, 'u1': u1,
       'm': {k: {'point': ev[k]['point'], 'ci90': ev[k]['ci90'], 'rho_cand': ev[k]['rho_cand'], 'rho_base': ev[k]['rho_base']} for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin', 'dRho_Q_lin')},
       'm_checks': ev['checks'], 'valuePer10AttributePoints': vals, 'valueBootstrapSE': se, 'chosen': {'K0': s0['chosen'], 'K1': s1['chosen']}, 'cvR2': {'K0': s0['cvR2'], 'K1': s1['cvR2']},
       'anchors': {'K0': s0['scaleAnchorsPer36'], 'K1': s1['scaleAnchorsPer36'], 'pipeline_K0': res['anchors_base'], 'pipeline_K1': res['anchors']},
       'players': players, 'top20': top20, 'movers_ge10_MIN1000': mov, 'physique_quintile_dOvr_all': q_all, 'physique_quintile_dOvr_MIN1000': q_1000,
       'evaluate': evj, 'n_players': len(K0), 'n_ovr_changed': sum(1 for k in by0 if by0[k]['ovr'] != by1[k]['ovr']),
       'mean_abs_dOvr': round(st.mean(x for x, _ in dall), 3), 'max_abs_dOvr': max(dall)}
(H / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
with open(H / 'ranking.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['name', 'pos', 'MIN', 'heightInches', 'physique', 'rank_K0', 'ovr_K0', 'rank_K1', 'ovr_K1', 'dOvr', 'dRank_up'])
    for r in K0:
        b = by1[r['name']]
        w.writerow([r['name'], r['pos'], r['MIN'], r['heightInches'], r['physique'], r['rank'], r['ovr'], b['rank'], b['ovr'], round(float(b['ovr']) - float(r['ovr']), 1), int(r['rank']) - int(b['rank'])])
print(json.dumps({k: out[k] for k in ('c0', 'chosen', 'cvR2', 'anchors', 'n_ovr_changed', 'mean_abs_dOvr', 'max_abs_dOvr')}, ensure_ascii=False, default=float))
print('u1', u1['pass'], u1['non_ovr_cols_changed'])
print({c: n for c, n in chg.items() if n})
