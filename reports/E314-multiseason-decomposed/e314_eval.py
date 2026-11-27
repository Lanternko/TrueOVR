"""E-314 雙軌嚴格樣本外評估（對照基準 A1 與原版 B0，評測 M1 / M2 / D1 / M2D1 / D_add）。
用法：
  python -I -X utf8 reports/E314-multiseason-decomposed/e314_eval.py
"""
import csv, hashlib, importlib.util, json, math, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / 'work'
WORK313 = ROOT / 'reports/E313-t-arch-training/work'
ARMS = ('B0', 'A1', 'M1', 'M2', 'D1', 'M2D1', 'D_add')
NEW_ARMS = ('M1', 'M2', 'D1', 'M2D1', 'D_add')
H, SIG = 2.5, 12.0
erf = np.vectorize(math.erf)

_sp = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X269 = importlib.util.module_from_spec(_sp)
sys.modules['e269_eval'] = X269
_sp.loader.exec_module(X269)
P269, Q269 = X269.P, X269.Q

K2D = ['Block', 'Steal', 'Interior Defense', 'Perimeter Defense', 'Help Defense IQ']
K2O = ['Three-Point Shot', 'Mid-Range Shot', 'Close Shot', 'Layup', 'Draw Foul', 'Ball Handle',
       'Pass Accuracy', 'Pass Vision', 'Pass IQ', 'Shot IQ', 'Offensive Consistency']


def z(v):
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-12)


def rho(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    k = np.isfinite(x) & np.isfinite(y)
    return (float(spearmanr(x[k], y[k])[0]), int(k.sum())) if k.sum() >= 5 else (float('nan'), int(k.sum()))


def work_path(arm, fn):
    return (WORK313 / fn) if arm in ('B0', 'A1') else (WORK / fn)


# ======================== 軌道一：球隊準度 ========================
def load_games(key):
    fn = 'inputs-2425.json' if key == '2425' else 'inputs.json'
    g = json.load(open(ROOT / 'reports/E208-team-rating' / fn, encoding='utf-8'))['games']
    home = np.array([str(x['home']) for x in g])
    away = np.array([str(x['away']) for x in g])
    y = np.array([float(x['hs'] > x['as']) for x in g])
    diff = np.array([float(x['hs'] - x['as']) for x in g])
    return home, away, y, diff


def load_pred(arm, key, var):
    P = json.load(open(work_path(arm, f'pred-{arm}-{key}-{var}.json'), encoding='utf-8'))
    ms = np.array(P['margin_seed'], dtype=float)
    m = ms.mean(axis=0)
    p = np.clip(0.5 * (1.0 + erf((m + H) / SIG / math.sqrt(2.0))), 1e-6, 1.0 - 1e-6)
    return p, m, ms, P


def team_wins(p, home, away, idx=None):
    idx = np.arange(len(p)) if idx is None else idx
    w = {}
    for i in idx:
        w[home[i]] = w.get(home[i], 0.0) + p[i]
        w[away[i]] = w.get(away[i], 0.0) + (1.0 - p[i])
    return w


def win_mae_and_rho(p, y, home, away, idx=None):
    pw = team_wins(p, home, away, idx)
    aw = team_wins(y, home, away, idx)
    ts = sorted(aw)
    mae = float(np.mean([abs(pw[t] - aw[t]) for t in ts]))
    sp = float(spearmanr([pw[t] for t in ts], [aw[t] for t in ts])[0])
    return mae, sp


def eval_team():
    res = {}
    for var in ('prior', 'same'):
        SS = {}
        for key in ('2425', '2526'):
            home, away, y, diff = load_games(key)
            S = {'home': home, 'away': away, 'y': y, 'diff': diff}
            for arm in ARMS:
                p, m, ms, P = load_pred(arm, key, var)
                assert P['home'] == list(home) and P['away'] == list(away)
                S[arm] = p
                S['m_' + arm] = m
                S['ms_' + arm] = ms
            SS[key] = S

        summary = {}
        for arm in ARMS:
            b_24 = float(((SS['2425'][arm] - SS['2425']['y']) ** 2).mean())
            b_25 = float(((SS['2526'][arm] - SS['2526']['y']) ** 2).mean())
            n24, n25 = len(SS['2425']['y']), len(SS['2526']['y'])
            b_all = (b_24 * n24 + b_25 * n25) / (n24 + n25)
            mae24, sp24 = win_mae_and_rho(SS['2425'][arm], SS['2425']['y'], SS['2425']['home'], SS['2425']['away'])
            mae25, sp25 = win_mae_and_rho(SS['2526'][arm], SS['2526']['y'], SS['2526']['home'], SS['2526']['away'])
            dmae24 = float(np.mean(np.abs((SS['2425']['m_' + arm] + H) - SS['2425']['diff'])))
            dmae25 = float(np.mean(np.abs((SS['2526']['m_' + arm] + H) - SS['2526']['diff'])))
            seed_b = []
            for s_i in range(SS['2526']['ms_' + arm].shape[0]):
                ps = np.clip(0.5 * (1.0 + erf((SS['2526']['ms_' + arm][s_i] + H) / SIG / math.sqrt(2.0))), 1e-6, 1.0 - 1e-6)
                seed_b.append(float(((ps - SS['2526']['y']) ** 2).mean()))
            summary[arm] = {
                'brier_all': round(b_all, 5), 'brier_2425': round(b_24, 5), 'brier_2526': round(b_25, 5),
                'win_mae_avg': round(0.5 * (mae24 + mae25), 3), 'win_mae_2425': round(mae24, 3), 'win_mae_2526': round(mae25, 3),
                'win_rho_avg': round(0.5 * (sp24 + sp25), 4),
                'margin_mae_avg': round(0.5 * (dmae24 + dmae25), 3),
                'seed_sd_2526': round(float(np.std(seed_b)), 5),
            }

        vs_ref = {}
        for ref in ('A1', 'B0'):
            vs_ref[ref] = {}
            for arm in NEW_ARMS:
                rng = np.random.default_rng(20261314)
                db, dm = [], []
                for _ in range(2000):
                    tb = 0.0; tn = 0; md = 0.0
                    for key in ('2425', '2526'):
                        S = SS[key]
                        ix = rng.integers(0, len(S['y']), len(S['y']))
                        d = float(((S[arm][ix] - S['y'][ix]) ** 2 - (S[ref][ix] - S['y'][ix]) ** 2).mean())
                        tb += d * len(ix); tn += len(ix)
                        m_a, _ = win_mae_and_rho(S[arm], S['y'], S['home'], S['away'], ix)
                        m_b, _ = win_mae_and_rho(S[ref], S['y'], S['home'], S['away'], ix)
                        md += 0.5 * (m_a - m_b)
                    db.append(tb / tn); dm.append(md)
                vs_ref[ref][arm] = {
                    'd_brier_all': round(summary[arm]['brier_all'] - summary[ref]['brier_all'], 5),
                    'ci90_brier': [round(float(np.percentile(db, 5)), 5), round(float(np.percentile(db, 95)), 5)],
                    'd_brier_2425': round(summary[arm]['brier_2425'] - summary[ref]['brier_2425'], 5),
                    'd_brier_2526': round(summary[arm]['brier_2526'] - summary[ref]['brier_2526'], 5),
                    'd_win_mae': round(summary[arm]['win_mae_avg'] - summary[ref]['win_mae_avg'], 3),
                    'ci90_win_mae': [round(float(np.percentile(dm, 5)), 3), round(float(np.percentile(dm, 95)), 3)],
                }
        res[var] = {'summary': summary, 'vs': vs_ref}
    return res


# ======================== 軌道二：個人準度 ========================
def load_epm(ids, season, col):
    _, mp = P269.pop_of(season)
    v = {}
    for r in csv.DictReader(open(Q269.EPMDIR / f'epm_{season}.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp:
            val = (float(r['O']) + float(r['D'])) if col == 'TOT' else float(r[col])
            v[p] = val * P269.wfun(mp[p])
    return np.array([v.get(int(p), np.nan) for p in ids])


def eval_player():
    pairs = [('2023-24', '2024-25'), ('2024-25', '2025-26')]
    epm_res = {arm: {} for arm in ARMS}
    add_diag = {}

    for src_s, tgt_s in pairs:
        cur = json.load(open(ROOT / 'reports/E287-offdef-align-t' / f'cur-{src_s}.json', encoding='utf-8'))
        for arm in ARMS:
            T = json.load(open(work_path(arm, f'swap-{arm}-{src_s}.json'), encoding='utf-8'))
            ids = [p for p in sorted(cur) if p in T['ownPts100']]
            to = np.array([T['ownPts100'][p] for p in ids])
            td = -np.array([T['oppPts100'][p] for p in ids])
            tn = to + td
            co = np.array([cur[p]['off0'] for p in ids])
            cd = np.array([cur[p]['def0'] for p in ids])
            bo = 0.5 * z(co) + 0.5 * z(to)
            bd = 0.5 * z(cd) + 0.5 * z(td)
            bn = bo + bd

            yo = load_epm(ids, tgt_s, 'O')
            yd = load_epm(ids, tgt_s, 'D')
            yt = load_epm(ids, tgt_s, 'TOT')
            ro, _ = rho(to, yo); rd, _ = rho(td, yd); rt, nt = rho(tn, yt)
            rbo, _ = rho(bo, yo); rbd, _ = rho(bd, yd); rbt, _ = rho(bn, yt)
            epm_res[arm][src_s] = {
                'n': nt,
                'T_OFF': round(ro, 4), 'T_DEF': round(rd, 4), 'T_NET': round(rt, 4),
                'B50_OFF': round(rbo, 4), 'B50_DEF': round(rbd, 4), 'B50_NET': round(rbt, 4),
            }
            if T.get('addOff'):
                ao = np.array([T['addOff'][p] for p in ids])
                ad = np.array([T['addDef'][p] for p in ids])
                an = ao + ad
                abo = 0.5 * z(co) + 0.5 * z(ao)
                abd = 0.5 * z(cd) + 0.5 * z(ad)
                add_diag.setdefault(arm, {})[src_s] = {
                    'corr_OFF': round(rho(ao, to)[0], 4), 'corr_DEF': round(rho(ad, td)[0], 4),
                    'add_OFF': round(rho(ao, yo)[0], 4), 'add_DEF': round(rho(ad, yd)[0], 4),
                    'add_NET': round(rho(an, yt)[0], 4), 'add_B50_NET': round(rho(abo + abd, yt)[0], 4),
                }

    combined_epm = {}
    for arm in ARMS:
        n1, n2 = epm_res[arm]['2023-24']['n'], epm_res[arm]['2024-25']['n']
        combined_epm[arm] = {}
        for k in ('T_OFF', 'T_DEF', 'T_NET', 'B50_OFF', 'B50_DEF', 'B50_NET'):
            combined_epm[arm][k] = round((epm_res[arm]['2023-24'][k] * n1 + epm_res[arm]['2024-25'][k] * n2) / (n1 + n2), 4)

    k2 = {}
    for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')):
        try:
            k2[P269.norm(r['name'])] = (float(np.mean([float(r[a]) for a in K2O])), float(np.mean([float(r[a]) for a in K2D])))
        except ValueError:
            pass

    cur25 = json.load(open(ROOT / 'reports/E287-offdef-align-t/cur-2025-26.json', encoding='utf-8'))
    k2_res, examples = {}, {}
    for arm in ARMS:
        T = json.load(open(work_path(arm, f'swap-{arm}-2025-26.json'), encoding='utf-8'))
        ids = [p for p in sorted(cur25) if p in T['ownPts100']]
        names = [cur25[p]['name'] for p in ids]
        to = np.array([T['ownPts100'][p] for p in ids])
        td = -np.array([T['oppPts100'][p] for p in ids])
        tn = to + td
        bo = 0.5 * z([cur25[p]['off0'] for p in ids]) + 0.5 * z(to)
        bd = 0.5 * z([cur25[p]['def0'] for p in ids]) + 0.5 * z(td)
        y2o = np.array([k2.get(P269.norm(nm), (np.nan, np.nan))[0] for nm in names])
        y2d = np.array([k2.get(P269.norm(nm), (np.nan, np.nan))[1] for nm in names])
        k2_res[arm] = {
            'T_OFF_2K': round(rho(to, y2o)[0], 4), 'T_DEF_2K': round(rho(td, y2d)[0], 4),
            'B50_OFF_2K': round(rho(bo, y2o)[0], 4), 'B50_DEF_2K': round(rho(bd, y2d)[0], 4),
        }
        examples[arm] = {
            'T_NET_top10': [names[i] for i in np.argsort(-tn)[:10]],
            'T_DEF_top10': [names[i] for i in np.argsort(-td)[:10]],
        }

    return {'epm_by_season': epm_res, 'epm_combined': combined_epm, 'k2_2526': k2_res, 'examples_2526': examples, 'add_diag': add_diag}


def main():
    sha = hashlib.sha256((HERE / 'prereg.md').read_bytes()).hexdigest()
    assert sha == (HERE / 'prereg.sha256').read_text(encoding='utf-8').strip(), 'prereg sha mismatch'
    team = eval_team()
    player = eval_player()

    verdict = {}
    a1_epm = player['epm_combined']['A1']
    for arm in NEW_ARMS:
        vp = team['prior']['vs']['A1'][arm]
        ep = player['epm_combined'][arm]
        d_tnet = round(ep['T_NET'] - a1_epm['T_NET'], 4)
        d_bnet = round(ep['B50_NET'] - a1_epm['B50_NET'], 4)
        d_toff = round(ep['T_OFF'] - a1_epm['T_OFF'], 4)
        d_tdef = round(ep['T_DEF'] - a1_epm['T_DEF'], 4)
        team_ok = (vp['d_brier_all'] <= -0.0005 or vp['ci90_brier'][1] < 0) and (vp['d_brier_2425'] <= 0.0005) and (vp['d_brier_2526'] <= 0.0005) and (d_tnet >= -0.003) and (d_bnet >= -0.003)
        player_ok = (d_bnet >= 0.005 or d_tnet >= 0.005) and (d_toff >= -0.003) and (d_tdef >= -0.003)
        verdict[arm] = {
            'team_upgrade': team_ok, 'player_upgrade': player_ok, 'both': team_ok and player_ok,
            'dBrier_vs_A1': vp['d_brier_all'], 'ci90_vs_A1': vp['ci90_brier'],
            'd_T_NET_vs_A1': d_tnet, 'd_B50_NET_vs_A1': d_bnet,
        }

    out = {'prereg_sha256': sha, 'team': team, 'player': player, 'verdict': verdict}
    json.dump(out, open(HERE / 'eval_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('=== TEAM (prior, 2460 games) ===')
    for arm in ARMS:
        s = team['prior']['summary'][arm]
        d1 = team['prior']['vs']['A1'].get(arm)
        d0 = team['prior']['vs']['B0'].get(arm)
        tail = f" | vs A1: {d1['d_brier_all']:+.5f} {d1['ci90_brier']} | vs B0: {d0['d_brier_all']:+.5f}" if d1 else ''
        print(f"  {arm:5s}: Brier={s['brier_all']:.5f} (24:{s['brier_2425']:.5f}, 25:{s['brier_2526']:.5f}) WinMAE={s['win_mae_avg']:.3f} MarginMAE={s['margin_mae_avg']:.3f} SD={s['seed_sd_2526']:.5f}{tail}")

    print('\n=== TEAM (same, 2460 games) ===')
    for arm in ARMS:
        s = team['same']['summary'][arm]
        d1 = team['same']['vs']['A1'].get(arm)
        tail = f" | vs A1: {d1['d_brier_all']:+.5f} {d1['ci90_brier']}" if d1 else ''
        print(f"  {arm:5s}: Brier={s['brier_all']:.5f} WinMAE={s['win_mae_avg']:.3f}{tail}")

    print('\n=== PLAYER (Combined OOS Next-Season EPM Spearman, n=605) ===')
    for arm in ARMS:
        e = player['epm_combined'][arm]
        print(f"  {arm:5s}: T_NET={e['T_NET']:.4f} (O:{e['T_OFF']:.4f}, D:{e['T_DEF']:.4f}) | B50_NET={e['B50_NET']:.4f} (O:{e['B50_OFF']:.4f}, D:{e['B50_DEF']:.4f})")

    print('\n=== VERDICT (vs A1) ===')
    for arm, v in verdict.items():
        print(f"  {arm:5s}: {v}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
