"""E-316 第二層評估：在 4 季輪換盲測（4,910 場）上比較 C0 / C1 / C2 / C3 / C3_ENS（嚴格 LOSO 零洩漏）。"""
import json, math, os
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
WORK = HERE / 'work'
VAL_SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
H, SIG = 2.5, 12.0
erf = np.vectorize(math.erf)


def team_win_mae(p, y, home, away):
    pw, aw = {}, {}
    for i in range(len(p)):
        pw[home[i]] = pw.get(home[i], 0.0) + p[i]; pw[away[i]] = pw.get(away[i], 0.0) + (1.0 - p[i])
        aw[home[i]] = aw.get(home[i], 0.0) + y[i]; aw[away[i]] = aw.get(away[i], 0.0) + (1.0 - y[i])
    return float(np.mean([abs(pw[t] - aw[t]) for t in aw]))


def main():
    per_s = {}
    for vs in VAL_SEASONS:
        G = json.load(open(DATA / f't1-games-{vs}.json', encoding='utf-8'))['games']
        L = json.load(open(WORK / f'loso-{vs}.json', encoding='utf-8'))
        m_m2 = np.array(L['m_m2'], float); m_da = np.array(L['m_da'], float)
        m_ens = 0.5 * (m_m2 + m_da)
        y = np.array([g['y'] for g in G], float)
        home = [g['home'] for g in G]; away = [g['away'] for g in G]

        # 構造嚴格賽前／賽中情境特徵
        X1, X2 = [], []
        for k, g in enumerate(G):
            hc, ac = g['h_ctx'], g['a_ctx']
            rest_d = hc['rest'] - ac['rest']
            b2b_d = ac['b2b'] - hc['b2b']        # >0 代表客隊背靠背、對主隊有利
            g34_d = ac['g3in4'] - hc['g3in4']
            road_d = ac['road'] - hc['road']
            snet_d = hc['s_net'] - ac['s_net']
            l10_d = hc['l10_net'] - ac['l10_net']
            prog = 0.5 * (hc['gp'] + ac['gp']) / 82.0
            f1 = [m_ens[k], m_m2[k] - m_da[k], rest_d, b2b_d, g34_d, road_d]
            f2 = f1 + [snet_d, l10_d, prog * snet_d]
            X1.append(f1); X2.append(f2)

        p0 = np.clip(0.5 * (1.0 + erf((m_ens + H) / SIG / math.sqrt(2.0))), 1e-6, 1.0 - 1e-6)
        per_s[vs] = {'y': y, 'home': home, 'away': away, 'p0': p0, 'X1': np.array(X1), 'X2': np.array(X2), 'm_ens': m_ens}

    # 四折 LOSO 第二層評估
    preds = {arm: {} for arm in ('C0', 'C1', 'C2', 'C3', 'C3_ENS')}
    for vs in VAL_SEASONS:
        preds['C0'][vs] = per_s[vs]['p0']
        trs = [s for s in VAL_SEASONS if s != vs]
        y_tr = np.concatenate([per_s[s]['y'] for s in trs])
        X1_tr = np.concatenate([per_s[s]['X1'] for s in trs])
        X2_tr = np.concatenate([per_s[s]['X2'] for s in trs])

        m1 = make_pipeline(StandardScaler(), LogisticRegression(C=0.5)).fit(X1_tr, y_tr)
        preds['C1'][vs] = np.clip(m1.predict_proba(per_s[vs]['X1'])[:, 1], 1e-6, 1.0 - 1e-6)

        m2 = make_pipeline(StandardScaler(), LogisticRegression(C=0.5)).fit(X2_tr, y_tr)
        p2 = np.clip(m2.predict_proba(per_s[vs]['X2'])[:, 1], 1e-6, 1.0 - 1e-6)
        preds['C2'][vs] = p2

        m3 = HistGradientBoostingClassifier(max_depth=3, min_samples_leaf=80, l2_regularization=10.0,
                                            learning_rate=0.05, max_iter=150, random_state=316).fit(X2_tr, y_tr)
        p3 = np.clip(m3.predict_proba(per_s[vs]['X2'])[:, 1], 1e-6, 1.0 - 1e-6)
        preds['C3'][vs] = p3
        preds['C3_ENS'][vs] = 0.5 * (p2 + p3)

    summary = {}
    print('=== E-316 T1 4-SEASON LOSO RESULTS (4,910 games) ===')
    for arm in ('C0', 'C1', 'C2', 'C3', 'C3_ENS'):
        bs = {s: float(((preds[arm][s] - per_s[s]['y']) ** 2).mean()) for s in VAL_SEASONS}
        ns = {s: len(per_s[s]['y']) for s in VAL_SEASONS}
        b_all = sum(bs[s] * ns[s] for s in VAL_SEASONS) / sum(ns.values())
        w_mae = float(np.mean([team_win_mae(preds[arm][s], per_s[s]['y'], per_s[s]['home'], per_s[s]['away']) for s in VAL_SEASONS]))

        # 成對 bootstrap vs C0
        if arm != 'C0':
            rng = np.random.default_rng(20261316)
            db = []
            for _ in range(2000):
                tb = 0.0; tn = 0
                for s in VAL_SEASONS:
                    ix = rng.integers(0, ns[s], ns[s])
                    tb += float(((preds[arm][s][ix] - per_s[s]['y'][ix]) ** 2 - (preds['C0'][s][ix] - per_s[s]['y'][ix]) ** 2).mean()) * ns[s]
                    tn += ns[s]
                db.append(tb / tn)
            ci = [round(float(np.percentile(db, 5)), 5), round(float(np.percentile(db, 95)), 5)]
            wins_n = sum(1 for s in VAL_SEASONS if bs[s] < summary['C0']['by_season'][s])
        else:
            ci, wins_n = None, 0

        summary[arm] = {'brier_all': round(b_all, 5), 'by_season': {s: round(v, 5) for s, v in bs.items()},
                        'win_mae_avg': round(w_mae, 3), 'd_vs_C0': round(b_all - summary['C0']['brier_all'], 5) if arm != 'C0' else 0.0,
                        'ci90': ci, 'seasons_better': wins_n}
        print(f"  {arm:6s}: Brier={b_all:.5f} (22:{bs['2022-23']:.5f} 23:{bs['2023-24']:.5f} 24:{bs['2024-25']:.5f} 25:{bs['2025-26']:.5f}) WinMAE={w_mae:.3f}"
              + (f" | d={summary[arm]['d_vs_C0']:+.5f} {ci} ({wins_n}/4 seasons)" if ci else ''))

    json.dump(summary, open(HERE / 'eval_results.json', 'w', encoding='utf-8'), indent=2)


if __name__ == '__main__':
    main()
