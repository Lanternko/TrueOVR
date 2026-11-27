"""E-313 雙軌嚴格樣本外評估（球隊 2,460 場盲測 + 個人 T-swap 跨季 EPM & 2K27）。
用法：
  python -I -X utf8 reports/E313-t-arch-training/e313_eval.py
"""
import csv, hashlib, importlib.util, json, math, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / 'work'
ARMS = ('B0', 'A1', 'A2', 'A3', 'A4')
H, SIG = 2.5, 12.0
erf = np.vectorize(math.erf)

# 載入 E-287 / E-269 共用 EPM 評估工具
_sp = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X269 = importlib.util.module_from_spec(_sp)
sys.modules['e269_eval'] = X269
_sp.loader.exec_module(X269)
P269, Q269 = X269.P, X269.Q

K2D = ['Block', 'Steal', 'Interior Defense', 'Perimeter Defense', 'Help Defense IQ']
K2O = ['Three-Point Shot', 'Mid-Range Shot', 'Close Shot', 'Layup', 'Draw Foul', 'Ball Handle',
       'Pass Accuracy', 'Pass Vision', 'Pass IQ', 'Shot IQ', 'Offensive Consistency']
NAMED = ['Kevin Durant', 'Fred VanVleet', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert',
         'Alex Caruso', 'Amen Thompson', 'Jaren Jackson Jr.', 'Bam Adebayo', 'Draymond Green',
         'Trae Young', 'Nikola Jokić', 'Shai Gilgeous-Alexander', 'Luka Dončić', 'Giannis Antetokounmpo']


def z(v):
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-12)


def rho(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    k = np.isfinite(x) & np.isfinite(y)
    return (float(spearmanr(x[k], y[k])[0]), int(k.sum())) if k.sum() >= 5 else (float('nan'), int(k.sum()))


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
    P = json.load(open(WORK / f'pred-{arm}-{key}-{var}.json', encoding='utf-8'))
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
            # 分差 MAE（含主場 +2.5）
            dmae24 = float(np.mean(np.abs((SS['2425']['m_' + arm] + H) - SS['2425']['diff'])))
            dmae25 = float(np.mean(np.abs((SS['2526']['m_' + arm] + H) - SS['2526']['diff'])))
            # 單模型 Brier 標準差（看穩定度）
            seed_b = []
            for s_i in range(SS['2526']['ms_' + arm].shape[0]):
                ps = np.clip(0.5 * (1.0 + erf((SS['2526']['ms_' + arm][s_i] + H) / SIG / math.sqrt(2.0))), 1e-6, 1.0 - 1e-6)
                seed_b.append(float(((ps - SS['2526']['y']) ** 2).mean()))

            summary[arm] = {
                'brier_all': round(b_all, 5), 'brier_2425': round(b_24, 5), 'brier_2526': round(b_25, 5),
                'win_mae_avg': round(0.5 * (mae24 + mae25), 3), 'win_mae_2425': round(mae24, 3), 'win_mae_2526': round(mae25, 3),
                'win_rho_avg': round(0.5 * (sp24 + sp25), 4),
                'margin_mae_avg': round(0.5 * (dmae24 + dmae25), 3),
                'single_model_brier_std_2526': round(float(np.std(seed_b)), 5),
            }

        # 成對 bootstrap (vs B0)
        diffs = {}
        for arm in ARMS[1:]:
            rng = np.random.default_rng(20261313)
            db, dm, db24, db25 = [], [], [], []
            for _ in range(2000):
                tb = 0.0; tn = 0; md = 0.0
                for key in ('2425', '2526'):
                    S = SS[key]
                    ix = rng.integers(0, len(S['y']), len(S['y']))
                    d = float(((S[arm][ix] - S['y'][ix]) ** 2 - (S['B0'][ix] - S['y'][ix]) ** 2).mean())
                    if key == '2425': db24.append(d)
                    else: db25.append(d)
                    tb += d * len(ix); tn += len(ix)
                    m_a, _ = win_mae_and_rho(S[arm], S['y'], S['home'], S['away'], ix)
                    m_b, _ = win_mae_and_rho(S['B0'], S['y'], S['home'], S['away'], ix)
                    md += 0.5 * (m_a - m_b)
                db.append(tb / tn); dm.append(md)
            pt_b = summary[arm]['brier_all'] - summary['B0']['brier_all']
            pt_m = summary[arm]['win_mae_avg'] - summary['B0']['win_mae_avg']
            diffs[arm] = {
                'd_brier_all': round(pt_b, 5),
                'ci90_brier': [round(float(np.percentile(db, 5)), 5), round(float(np.percentile(db, 95)), 5)],
                'd_brier_2425': round(summary[arm]['brier_2425'] - summary['B0']['brier_2425'], 5),
                'd_brier_2526': round(summary[arm]['brier_2526'] - summary['B0']['brier_2526'], 5),
                'd_win_mae': round(pt_m, 3),
                'ci90_win_mae': [round(float(np.percentile(dm, 5)), 3), round(float(np.percentile(dm, 95)), 3)],
                'd_margin_mae': round(summary[arm]['margin_mae_avg'] - summary['B0']['margin_mae_avg'], 3),
            }
        res[var] = {'summary': summary, 'vs_B0': diffs}
    return res


# ======================== 軌道二：個人準度 ========================
def load_epm(ids, season, col):
    _, mp = P269.pop_of(season)
    v = {}
    for r in csv.DictReader(open(Q269.EPMDIR / f'epm_{season}.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp:
            if col == 'TOT':
                val = float(r['O']) + float(r['D'])
            else:
                val = float(r[col])
            v[p] = val * P269.wfun(mp[p])
    return np.array([v.get(int(p), np.nan) for p in ids])


def eval_player():
    # 1. 兩組跨季樣本外 EPM：2023-24 -> 2024-25 EPM, 2024-25 -> 2025-26 EPM
    pairs = [('2023-24', '2024-25'), ('2024-25', '2025-26')]
    epm_res = {arm: {} for arm in ARMS}
    add_diag = {}

    for src_s, tgt_s in pairs:
        cur = json.load(open(ROOT / 'reports/E287-offdef-align-t' / f'cur-{src_s}.json', encoding='utf-8'))
        for arm in ARMS:
            T = json.load(open(WORK / f'swap-{arm}-{src_s}.json', encoding='utf-8'))
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
            ro, no = rho(to, yo); rd, nd = rho(td, yd); rt, nt = rho(tn, yt)
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
                add_diag.setdefault(arm, {})[src_s] = {
                    'corr_with_swap_OFF': round(rho(ao, to)[0], 4),
                    'corr_with_swap_DEF': round(rho(ad, td)[0], 4),
                    'add_EPM_OFF': round(rho(ao, yo)[0], 4),
                    'add_EPM_DEF': round(rho(ad, yd)[0], 4),
                    'add_EPM_NET': round(rho(an, yt)[0], 4),
                }

    # 兩季合併人數加權 EPM Spearman
    combined_epm = {}
    for arm in ARMS:
        n1, n2 = epm_res[arm]['2023-24']['n'], epm_res[arm]['2024-25']['n']
        combined_epm[arm] = {}
        for k in ('T_OFF', 'T_DEF', 'T_NET', 'B50_OFF', 'B50_DEF', 'B50_NET'):
            v = (epm_res[arm]['2023-24'][k] * n1 + epm_res[arm]['2024-25'][k] * n2) / (n1 + n2)
            combined_epm[arm][k] = round(v, 4)

    # 2. 2025-26 2K27 & 代表性球員檢查
    k2 = {}
    for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')):
        try:
            k2[P269.norm(r['name'])] = (
                float(np.mean([float(r[a]) for a in K2O])),
                float(np.mean([float(r[a]) for a in K2D])),
                float(r['ovr']) if 'ovr' in r and r['ovr'] else float(r.get('OVR', np.nan)),
            )
        except ValueError:
            pass

    cur25 = json.load(open(ROOT / 'reports/E287-offdef-align-t/cur-2025-26.json', encoding='utf-8'))
    k2_res = {}
    examples = {}
    for arm in ARMS:
        T = json.load(open(WORK / f'swap-{arm}-2025-26.json', encoding='utf-8'))
        ids = [p for p in sorted(cur25) if p in T['ownPts100']]
        names = [cur25[p]['name'] for p in ids]
        pos = [cur25[p]['pos'] for p in ids]
        ovr = np.array([cur25[p]['ovr'] for p in ids])
        to = np.array([T['ownPts100'][p] for p in ids])
        td = -np.array([T['oppPts100'][p] for p in ids])
        tn = to + td
        bo = 0.5 * z([cur25[p]['off0'] for p in ids]) + 0.5 * z(to)
        bd = 0.5 * z([cur25[p]['def0'] for p in ids]) + 0.5 * z(td)

        y2o = np.array([k2.get(P269.norm(nm), (np.nan, np.nan, np.nan))[0] for nm in names])
        y2d = np.array([k2.get(P269.norm(nm), (np.nan, np.nan, np.nan))[1] for nm in names])
        y2ovr = np.array([k2.get(P269.norm(nm), (np.nan, np.nan, np.nan))[2] for nm in names])
        k2_res[arm] = {
            'T_OFF_2K': round(rho(to, y2o)[0], 4), 'T_DEF_2K': round(rho(td, y2d)[0], 4), 'T_NET_2KOVR': round(rho(tn, y2ovr)[0], 4),
            'B50_OFF_2K': round(rho(bo, y2o)[0], 4), 'B50_DEF_2K': round(rho(bd, y2d)[0], 4),
        }
        rk_def = {nm: int((bd > bd[i]).sum() + 1) for i, nm in enumerate(names)}
        rk_tdef = {nm: int((td > td[i]).sum() + 1) for i, nm in enumerate(names)}
        examples[arm] = {
            'T_NET_top10': [names[i] for i in np.argsort(-tn)[:10]],
            'T_DEF_top10': [names[i] for i in np.argsort(-td)[:10]],
            'Durant_vs_FVV_B50_DEF': {'Durant': rk_def.get('Kevin Durant'), 'VanVleet': rk_def.get('Fred VanVleet')},
            'Durant_vs_FVV_T_DEF': {'Durant': rk_tdef.get('Kevin Durant'), 'VanVleet': rk_tdef.get('Fred VanVleet')},
            'named_B50_DEF': {nm: rk_def.get(nm) for nm in NAMED},
        }

    return {'epm_by_season': epm_res, 'epm_combined': combined_epm, 'k2_2526': k2_res, 'examples_2526': examples, 'add_diag': add_diag}


def main():
    sha = hashlib.sha256((HERE / 'prereg.md').read_bytes()).hexdigest()
    assert sha == (HERE / 'prereg.sha256').read_text(encoding='utf-8').strip(), 'prereg sha mismatch'
    team = eval_team()
    player = eval_player()

    # 判定規則檢查
    verdict = {}
    b0_epm = player['epm_combined']['B0']
    for arm in ARMS[1:]:
        vp = team['prior']['vs_B0'][arm]
        vs = team['same']['vs_B0'][arm]
        team_pass = (vp['d_brier_all'] <= 0) and (vs['d_brier_all'] <= 0) and (vp['d_brier_2425'] <= 0.001) and (vp['d_brier_2526'] <= 0.001)
        team_sig = team_pass and (vp['ci90_brier'][1] < 0)

        ep = player['epm_combined'][arm]
        d_net = round(ep['T_NET'] - b0_epm['T_NET'], 4)
        d_off = round(ep['T_OFF'] - b0_epm['T_OFF'], 4)
        d_def = round(ep['T_DEF'] - b0_epm['T_DEF'], 4)
        player_pass = (d_net >= 0) and (d_off >= -0.005) and (d_def >= -0.005)
        player_sig = (d_net >= 0.005) and (d_off >= -0.002) and (d_def >= -0.002)
        verdict[arm] = {
            'team_pass': team_pass, 'team_sig': team_sig,
            'player_pass': player_pass, 'player_sig': player_sig,
            'd_T_NET': d_net, 'd_T_OFF': d_off, 'd_T_DEF': d_def,
        }

    out = {'prereg_sha256': sha, 'team': team, 'player': player, 'verdict': verdict}
    json.dump(out, open(HERE / 'eval_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('=== TEAM (prior, 2460 games) ===')
    for arm in ARMS:
        s = team['prior']['summary'][arm]
        d = team['prior']['vs_B0'].get(arm, {})
        print(f"  {arm}: Brier={s['brier_all']:.5f} (24-25:{s['brier_2425']:.5f}, 25-26:{s['brier_2526']:.5f}) WinMAE={s['win_mae_avg']:.3f} MarginMAE={s['margin_mae_avg']:.3f} SeedSD={s['single_model_brier_std_2526']:.5f}"
              + (f" | dBrier={d['d_brier_all']:+.5f} {d['ci90_brier']}" if d else ''))

    print('\n=== TEAM (same, 2460 games) ===')
    for arm in ARMS:
        s = team['same']['summary'][arm]
        d = team['same']['vs_B0'].get(arm, {})
        print(f"  {arm}: Brier={s['brier_all']:.5f} WinMAE={s['win_mae_avg']:.3f}"
              + (f" | dBrier={d['d_brier_all']:+.5f} {d['ci90_brier']}" if d else ''))

    print('\n=== PLAYER (Combined OOS Next-Season EPM Spearman) ===')
    for arm in ARMS:
        e = player['epm_combined'][arm]
        print(f"  {arm}: T_NET={e['T_NET']:.4f} (O:{e['T_OFF']:.4f}, D:{e['T_DEF']:.4f}) | B50_NET={e['B50_NET']:.4f} (O:{e['B50_OFF']:.4f}, D:{e['B50_DEF']:.4f})")

    print('\n=== VERDICT ===')
    for arm, v in verdict.items():
        print(f"  {arm}: {v}")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
