"""E-274 評估（prereg.md 已凍結）。python -I -B -X utf8 reports/E274-def-display-transformer/e274_eval.py
讀 d2-<t>.json（e274_swap.py 在 5090 產生，對手每 100 回合得分，越小越好 → 取負）。"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X = importlib.util.module_from_spec(s); sys.modules['e269_eval'] = X; s.loader.exec_module(X)
E, P, SN, sp = X.E, X.P, X.SN, X.sp
E269 = X.HERE
FOLDS = [('2022-23', '2023-24'), ('2023-24', '2024-25'), ('2024-25', '2025-26')]
ARMS = ['D0', 'D1', 'D2', 'D3', 'D4']
NAMED = ['Kevin Durant', 'Stephen Curry', 'Fred VanVleet', 'Victor Wembanyama', 'Rudy Gobert', 'Alex Caruso', 'Amen Thompson',
         'Alperen Sengun', 'Nikola Jokić', 'Trae Young']
EPMDIR = ROOT / 'data/external-impact/epm_self'


def rapm_raw(s, sign):
    j = json.loads((E.E126 / f'rapm-{s}.json').read_text(encoding='utf-8'))['players']
    return {int(p): (sign * v['D'], v['poss']) for p, v in j.items()}


def d1_centered(t):
    """D1：defenseBonus 換成兩側 centered（0.75·D − 同位置平均）。回 {name: centered}（possW<2500 退回 defenseBonus）、posMean、退回人數。"""
    card = {r['name']: r for r in csv.DictReader(open(E269 / f'ranking-A0-{t}.csv', encoding='utf-8-sig'))}
    dl = {r['playerId']: (float(r['D']), float(r['poss'])) for r in csv.DictReader(open(
        E269 / f'work/A0/base-S-{t}/{t}/def-L-primary.csv', encoding='utf-8'))}
    pop, _ = P.pop_of(t)
    pid_of = {i['name']: p for p, i in pop.items()}
    pm = lambda r: {'G': 'SG', 'F': 'SF'}.get(r['pos'], r['pos'])
    byname = {}
    for n, r in card.items():
        p = str(pid_of.get(n, ''))
        if p in dl:
            byname[n] = (0.75 * dl[p][0], dl[p][1], r)
    mean = {}
    for ps in {pm(r) for r in card.values()}:
        back = sorted(v[0] - float(v[2]['defenseBonus']) for v in byname.values() if pm(v[2]) == ps and float(v[2]['defenseBonus']) > 0)
        mean[ps] = back[len(back) // 2] if back else 0.0
    out, nfall = {}, 0
    for n, r in card.items():
        v = byname.get(n)
        if v and v[1] >= 2500:
            out[n] = v[0] - mean[pm(r)]
        else:
            out[n] = float(r['defenseBonus']); nfall += 1
    return out, card, mean, nfall


def z(v):
    return (v - v.mean()) / v.std()


def main():
    sign = {}
    for s_ in ['2022-23', '2023-24', '2024-25', '2025-26']:
        j = [x for x in json.loads((E.E126 / f'rapm-{s_}.json').read_text(encoding='utf-8'))['players'].values() if x['poss'] >= 1000]
        net, o, dd = (np.array([x[k] for x in j]) for k in ('net', 'O', 'D'))
        sign[s_] = 1.0 if np.corrcoef(net, o + dd)[0, 1] > np.corrcoef(net, o - dd)[0, 1] else -1.0
    assert len(set(sign.values())) == 1, sign
    sg = sign['2022-23']
    res = {'sign': sg, 'folds': {}}
    for t, u in FOLDS:
        d = X.load('A0', t)
        ids, names = d['ids'], d['names']
        w = json.loads(open(HERE / f'd2-{t}.json').read())['oppPts100']
        d2 = np.array([-w[str(p)] if str(p) in w else np.nan for p in ids])
        d1c, card, mean, nfall = d1_centered(t)
        q = [r for r in card.values() if float(r['MIN']) >= 500]
        mub = np.mean([float(r['defenseBonus']) for r in q])
        mud1 = np.mean([d1c[r['name']] for r in q])
        d1 = d['def'] - np.array([float(card[n]['defenseBonus']) for n in names]) + mub + np.array([d1c[n] for n in names]) - mud1
        rt = rapm_raw(t, sg)
        d4 = np.array([rt[p][0] if p in rt and rt[p][1] >= 1000 else np.nan for p in ids])
        _, mp = P.pop_of(u)
        ru = rapm_raw(u, sg)
        Wf = lambda p: P.wfun(mp[p])
        ok = lambda p: p in ru and ru[p][1] >= 1000 and p in mp
        yD = np.array([ru[p][0] * Wf(p) if ok(p) else np.nan for p in ids])
        yRaw = np.array([ru[p][0] if ok(p) else np.nan for p in ids])
        ep = {}
        for r in csv.DictReader(open(EPMDIR / f'epm_{u}.csv', encoding='utf-8-sig')):
            if float(r['stintPoss']) >= 1000 and int(r['playerId']) in mp:
                ep[int(r['playerId'])] = float(r['D']) * Wf(int(r['playerId']))
        yE = np.array([ep.get(p, np.nan) for p in ids])
        com = np.isfinite(d2) & np.isfinite(d4) & np.isfinite(yD)
        d3 = np.full(len(ids), np.nan)
        d3[com] = 0.5 * z(d2[com]) + 0.5 * z(d4[com])
        A = {'D0': d['def'], 'D1': d1, 'D2': d2, 'D3': d3, 'D4': d4}
        fo = {'n': int(com.sum()), 'rho': {}, 'rho_rawD': {}, 'rho_epmD': {}}
        for a in ARMS:
            fo['rho'][a] = sp(A[a][com], yD[com])
            kr = com & np.isfinite(yRaw)
            fo['rho_rawD'][a] = sp(A[a][kr], yRaw[kr])
            ke = com & np.isfinite(yE)
            fo['rho_epmD'][a] = sp(A[a][ke], yE[ke]); fo['n_epm'] = int(ke.sum())
        big = np.isfinite(d2) & np.isfinite(yD)
        fo['n_big'] = int(big.sum()); fo['rho_big'] = {a: sp(A[a][big], yD[big]) for a in ['D0', 'D1', 'D2']}
        fo['d1_fallback_n'] = nfall; fo['d1_posMean'] = mean
        ex = np.isfinite(d2) & np.isfinite(d4)
        exi = np.where(ex)[0]
        nm = [names[j] for j in exi]
        ranks = {}
        for a in ARMS:
            v = A[a][ex]
            ranks[a] = {n_: int((v > val).sum() + 1) for n_, val in zip(nm, v)}
        bigs = [n for n, p, o in sorted(zip(d['all_names'], d['all_pos'], d['all_ovr']), key=lambda r: -r[2]) if p == 'C'][:10]
        show = NAMED + [b for b in bigs if b not in NAMED]
        fo['examples'] = {'n_pop': int(ex.sum()), 'bigs': bigs,
                          'ranks': {n: {a: ranks[a].get(n) for a in ARMS} for n in show},
                          'val': {n: {'D0': float(A['D0'][names.index(n)]), 'D1': float(A['D1'][names.index(n)]), 'D2': float(d2[names.index(n)])}
                                  for n in show if n in names}}
        res['folds'][t] = fo
    ns = np.array([res['folds'][t]['n'] for t, _ in FOLDS], float)
    comb = {}
    for key in ('rho', 'rho_rawD', 'rho_epmD'):
        comb[key] = {a: float(sum(res['folds'][t][key][a] * res['folds'][t]['n'] for t, _ in FOLDS) / ns.sum()) for a in ARMS}
    res['combined'] = comb
    base = comb['rho']['D0']
    gate = {}
    for a in ['D1', 'D2', 'D3']:
        g = {'combined_rho': comb['rho'][a], 'delta_vs_D0': comb['rho'][a] - base,
             'highest_of_D0-D3': bool(comb['rho'][a] >= max(comb['rho'][b] for b in ['D0', 'D1', 'D2', 'D3'])),
             'delta>=.03': bool(comb['rho'][a] - base >= 0.03),
             'every_fold>=D0': bool(all(res['folds'][t]['rho'][a] >= res['folds'][t]['rho']['D0'] for t, _ in FOLDS))}
        g['pass'] = bool(g['highest_of_D0-D3'] and g['delta>=.03'] and g['every_fold>=D0'])
        gate[a] = g
    res['gate'] = gate
    res['adopt'] = max([a for a in ['D2', 'D3'] if gate[a]['pass']], key=lambda a: comb['rho'][a], default=None)
    res['d1_only'] = bool(gate['D1']['pass'] and not res['adopt'])
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('sign', sg)
    for t, _ in FOLDS:
        f = res['folds'][t]
        print(t, 'n', f['n'], 'rho', {a: round(v, 3) for a, v in f['rho'].items()}, 'n_big', f['n_big'], {a: round(v, 3) for a, v in f['rho_big'].items()})
    print('combined rho', {a: round(v, 3) for a, v in comb['rho'].items()})
    print('combined rawD', {a: round(v, 3) for a, v in comb['rho_rawD'].items()})
    print('combined epmD', {a: round(v, 3) for a, v in comb['rho_epmD'].items()})
    print('gate', json.dumps(gate, ensure_ascii=False)); print('adopt', res['adopt'], 'd1_only', res['d1_only'])


if __name__ == '__main__':
    main()
