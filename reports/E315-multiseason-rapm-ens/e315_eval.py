"""E-315 雙軌評估：比較 B0 / A1 / M2 / D_add / ENS_MD / M2_RAPM / D_add_RAPM / ENS_RAPM / M2_L / D_add_L。"""
import csv, hashlib, importlib.util, json, math, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W313 = ROOT / 'reports/E313-t-arch-training/work'
W314 = ROOT / 'reports/E314-multiseason-decomposed/work'
W315 = HERE / 'work'
H, SIG = 2.5, 12.0
erf = np.vectorize(math.erf)

_sp = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X269 = importlib.util.module_from_spec(_sp); sys.modules['e269_eval'] = X269; _sp.loader.exec_module(X269)
P269, Q269 = X269.P, X269.Q
K2D = ['Block', 'Steal', 'Interior Defense', 'Perimeter Defense', 'Help Defense IQ']
K2O = ['Three-Point Shot', 'Mid-Range Shot', 'Close Shot', 'Layup', 'Draw Foul', 'Ball Handle',
       'Pass Accuracy', 'Pass Vision', 'Pass IQ', 'Shot IQ', 'Offensive Consistency']

BASE_ARMS = ('B0', 'A1', 'M2', 'D_add', 'M2_RAPM', 'D_add_RAPM', 'M2_L', 'D_add_L')
ALL_ARMS = ('B0', 'A1', 'M2', 'D_add', 'ENS_MD', 'M2_RAPM', 'D_add_RAPM', 'ENS_RAPM', 'M2_L', 'D_add_L', 'ENS_L')


def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-12)


def rho(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    k = np.isfinite(x) & np.isfinite(y)
    return (float(spearmanr(x[k], y[k])[0]), int(k.sum())) if k.sum() >= 5 else (float('nan'), int(k.sum()))


def wpath(arm, fn):
    if arm in ('B0', 'A1'): return W313 / fn
    if arm in ('M2', 'D_add'): return W314 / fn
    return W315 / fn


def load_games(key):
    fn = 'inputs-2425.json' if key == '2425' else 'inputs.json'
    g = json.load(open(ROOT / 'reports/E208-team-rating' / fn, encoding='utf-8'))['games']
    return (np.array([str(x['home']) for x in g]), np.array([str(x['away']) for x in g]),
            np.array([float(x['hs'] > x['as']) for x in g]), np.array([float(x['hs'] - x['as']) for x in g]))


def m_to_p(m):
    return np.clip(0.5 * (1.0 + erf((m + H) / SIG / math.sqrt(2.0))), 1e-6, 1.0 - 1e-6)


def team_wins(p, home, away, idx=None):
    idx = np.arange(len(p)) if idx is None else idx
    w = {}
    for i in idx:
        w[home[i]] = w.get(home[i], 0.0) + p[i]; w[away[i]] = w.get(away[i], 0.0) + (1.0 - p[i])
    return w


def win_mae(p, y, home, away, idx=None):
    pw, aw = team_wins(p, home, away, idx), team_wins(y, home, away, idx)
    return float(np.mean([abs(pw[t] - aw[t]) for t in aw]))


def eval_team():
    SS = {}
    for key in ('2425', '2526'):
        home, away, y, diff = load_games(key)
        S = {'home': home, 'away': away, 'y': y, 'diff': diff}
        for arm in BASE_ARMS:
            P = json.load(open(wpath(arm, f'pred-{arm}-{key}-prior.json'), encoding='utf-8'))
            m = np.array(P['margin_seed'], float).mean(0)
            S['m_' + arm] = m; S[arm] = m_to_p(m)
        for ename, a, b in (('ENS_MD', 'M2', 'D_add'), ('ENS_RAPM', 'M2_RAPM', 'D_add_RAPM'), ('ENS_L', 'M2_L', 'D_add_L')):
            m = 0.5 * (S['m_' + a] + S['m_' + b])
            S['m_' + ename] = m; S[ename] = m_to_p(m)
        SS[key] = S

    summary = {}
    for arm in ALL_ARMS:
        b24 = float(((SS['2425'][arm] - SS['2425']['y']) ** 2).mean())
        b25 = float(((SS['2526'][arm] - SS['2526']['y']) ** 2).mean())
        n24, n25 = len(SS['2425']['y']), len(SS['2526']['y'])
        ball = (b24 * n24 + b25 * n25) / (n24 + n25)
        w24 = win_mae(SS['2425'][arm], SS['2425']['y'], SS['2425']['home'], SS['2425']['away'])
        w25 = win_mae(SS['2526'][arm], SS['2526']['y'], SS['2526']['home'], SS['2526']['away'])
        d24 = float(np.mean(np.abs((SS['2425']['m_' + arm] + H) - SS['2425']['diff'])))
        d25 = float(np.mean(np.abs((SS['2526']['m_' + arm] + H) - SS['2526']['diff'])))
        summary[arm] = {'brier_all': round(ball, 5), 'brier_2425': round(b24, 5), 'brier_2526': round(b25, 5),
                        'win_mae': round(0.5 * (w24 + w25), 3), 'margin_mae': round(0.5 * (d24 + d25), 3)}

    vs_dadd = {}
    for arm in ALL_ARMS:
        if arm in ('B0', 'A1', 'D_add'): continue
        rng = np.random.default_rng(20261315)
        db = []
        for _ in range(2000):
            tb = 0.0; tn = 0
            for key in ('2425', '2526'):
                S = SS[key]; ix = rng.integers(0, len(S['y']), len(S['y']))
                tb += float(((S[arm][ix] - S['y'][ix]) ** 2 - (S['D_add'][ix] - S['y'][ix]) ** 2).mean()) * len(ix)
                tn += len(ix)
            db.append(tb / tn)
        vs_dadd[arm] = {'d_vs_D_add': round(summary[arm]['brier_all'] - summary['D_add']['brier_all'], 5),
                        'ci90': [round(float(np.percentile(db, 5)), 5), round(float(np.percentile(db, 95)), 5)],
                        'd_vs_B0': round(summary[arm]['brier_all'] - summary['B0']['brier_all'], 5)}
    return {'summary': summary, 'vs_D_add': vs_dadd}


def load_epm(ids, season, col):
    _, mp = P269.pop_of(season); v = {}
    for r in csv.DictReader(open(Q269.EPMDIR / f'epm_{season}.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp:
            val = (float(r['O']) + float(r['D'])) if col == 'TOT' else float(r[col])
            v[p] = val * P269.wfun(mp[p])
    return np.array([v.get(int(p), np.nan) for p in ids])


def load_swap_dict(arm, season):
    ens_map = {'ENS_MD': ('M2', 'D_add'), 'ENS_RAPM': ('M2_RAPM', 'D_add_RAPM'), 'ENS_L': ('M2_L', 'D_add_L')}
    if arm in ens_map:
        a, b = ens_map[arm]
        Ta, Tb = load_swap_dict(a, season), load_swap_dict(b, season)
        pids = sorted(set(Ta['ownPts100']) & set(Tb['ownPts100']))
        return {'ownPts100': {p: 0.5 * (Ta['ownPts100'][p] + Tb['ownPts100'][p]) for p in pids},
                'oppPts100': {p: 0.5 * (Ta['oppPts100'][p] + Tb['oppPts100'][p]) for p in pids}}
    return json.load(open(wpath(arm, f'swap-{arm}-{season}.json'), encoding='utf-8'))


def eval_player():
    pairs = [('2023-24', '2024-25'), ('2024-25', '2025-26')]
    epm_by = {arm: {} for arm in ALL_ARMS}
    for src_s, tgt_s in pairs:
        cur = json.load(open(ROOT / 'reports/E287-offdef-align-t' / f'cur-{src_s}.json', encoding='utf-8'))
        for arm in ALL_ARMS:
            T = load_swap_dict(arm, src_s)
            ids = [p for p in sorted(cur) if p in T['ownPts100']]
            to = np.array([T['ownPts100'][p] for p in ids]); td = -np.array([T['oppPts100'][p] for p in ids]); tn = to + td
            bo = 0.5 * z([cur[p]['off0'] for p in ids]) + 0.5 * z(to)
            bd = 0.5 * z([cur[p]['def0'] for p in ids]) + 0.5 * z(td)
            bn = bo + bd
            yo, yd, yt = load_epm(ids, tgt_s, 'O'), load_epm(ids, tgt_s, 'D'), load_epm(ids, tgt_s, 'TOT')
            epm_by[arm][src_s] = {'n': rho(tn, yt)[1], 'T_OFF': round(rho(to, yo)[0], 4), 'T_DEF': round(rho(td, yd)[0], 4),
                                  'T_NET': round(rho(tn, yt)[0], 4), 'B50_OFF': round(rho(bo, yo)[0], 4),
                                  'B50_DEF': round(rho(bd, yd)[0], 4), 'B50_NET': round(rho(bn, yt)[0], 4)}
    comb = {}
    for arm in ALL_ARMS:
        n1, n2 = epm_by[arm]['2023-24']['n'], epm_by[arm]['2024-25']['n']
        comb[arm] = {k: round((epm_by[arm]['2023-24'][k] * n1 + epm_by[arm]['2024-25'][k] * n2) / (n1 + n2), 4)
                     for k in ('T_OFF', 'T_DEF', 'T_NET', 'B50_OFF', 'B50_DEF', 'B50_NET')}

    k2 = {}
    for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')):
        try: k2[P269.norm(r['name'])] = (float(np.mean([float(r[a]) for a in K2O])), float(np.mean([float(r[a]) for a in K2D])))
        except ValueError: pass
    cur25 = json.load(open(ROOT / 'reports/E287-offdef-align-t' / 'cur-2025-26.json', encoding='utf-8'))
    k2_res = {}
    for arm in ALL_ARMS:
        T = load_swap_dict(arm, '2025-26')
        ids = [p for p in sorted(cur25) if p in T['ownPts100']]
        names = [cur25[p]['name'] for p in ids]
        to = np.array([T['ownPts100'][p] for p in ids]); td = -np.array([T['oppPts100'][p] for p in ids])
        bo = 0.5 * z([cur25[p]['off0'] for p in ids]) + 0.5 * z(to); bd = 0.5 * z([cur25[p]['def0'] for p in ids]) + 0.5 * z(td)
        y2o = np.array([k2.get(P269.norm(nm), (np.nan, np.nan))[0] for nm in names])
        y2d = np.array([k2.get(P269.norm(nm), (np.nan, np.nan))[1] for nm in names])
        k2_res[arm] = {'B50_OFF_2K': round(rho(bo, y2o)[0], 4), 'B50_DEF_2K': round(rho(bd, y2d)[0], 4)}
    return {'epm_combined': comb, 'epm_by_season': epm_by, 'k2_2526': k2_res}


def main():
    sha = hashlib.sha256((HERE / 'prereg.md').read_bytes()).hexdigest()
    assert sha == (HERE / 'prereg.sha256').read_text(encoding='utf-8').strip()
    team = eval_team(); player = eval_player()
    json.dump({'prereg_sha256': sha, 'team': team, 'player': player}, open(HERE / 'eval_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('=== TEAM (prior, 2460 games) ===')
    for arm in ALL_ARMS:
        s = team['summary'][arm]; d = team['vs_D_add'].get(arm)
        tail = f" | vs D_add: {d['d_vs_D_add']:+.5f} {d['ci90']} | vs B0: {d['d_vs_B0']:+.5f}" if d else ''
        print(f"  {arm:10s}: Brier={s['brier_all']:.5f} (24:{s['brier_2425']:.5f}, 25:{s['brier_2526']:.5f}) WinMAE={s['win_mae']:.3f} MarginMAE={s['margin_mae']:.3f}{tail}")

    print('\n=== PLAYER (Combined OOS Next-Season EPM, n=605 & 2K27) ===')
    for arm in ALL_ARMS:
        e = player['epm_combined'][arm]; k = player['k2_2526'][arm]
        print(f"  {arm:10s}: T_NET={e['T_NET']:.4f} (O:{e['T_OFF']:.4f}, D:{e['T_DEF']:.4f}) | B50_NET={e['B50_NET']:.4f} | 2K(O/D)={k['B50_OFF_2K']:.3f}/{k['B50_DEF_2K']:.3f}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
