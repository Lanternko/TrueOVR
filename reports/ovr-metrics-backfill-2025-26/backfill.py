"""補齊審查板「未量測」指標（2025-26）：每層的樣本外 ρ、對 2K27 ρ、卡片球隊指標。

  python reports/ovr-metrics-backfill-2025-26/backfill.py     # 寫 backfill.json（審查板 status_snapshot.py 讀它）

前置：sh reports/ovr-metrics-backfill-2025-26/run-refit.sh（讀 RAPM 的 v53／B12／C1／D1 卡片的全量重現與 A/B 半重擬合）。

口徑與 reports/ovr-v58-holdout-2025-26/evaluate.py 相同：
  評估人群 = 該腳本的 common（E2/F2/G3/H1/v53 正式檔 + 半擬合版共同球員 ∩ 2K27 有 overall2k）∩ 評估半 pooledPoss >= 2500。
  樣本外 ρ = (A 半擬合的卡對 B 半 RAPM 的 ρ + B 半擬合的卡對 A 半 RAPM 的 ρ) / 2，Spearman（tie 平均名次）。
  不讀 RAPM 的層（模擬板、舊版 sim-only）不需重擬合：同一份分數直接對 A 半與 B 半 RAPM 各算一次再平均。
  E2/F2/G3/H1 直接沿用 holdout.json（並用 fitA/fitB 目錄重算一次核對，差 < 1e-9）。
"""
import csv, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
H = ROOT / 'reports/ovr-v58-holdout-2025-26'
THR = 2500
CARD_ORDER = ['legacy', 'v53', 'E2', 'F2', 'G3', 'H1', 'B12', 'C1', 'D1']

# 卡片層：key -> (全量卡片檔, 半擬合目錄)；半擬合目錄 = None 表示不讀 RAPM 或由 holdout 目錄提供
CARDS = {
    'H1': 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv',
    'G3': 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
    'F2': 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv',
    'E2': 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
    'v53': 'reports/ovr-calibrated-2025-26/ranking.csv',
    'blend': 'reports/ovr-blended-2025-26/ranking.csv',
    'B12': 'reports/ovr-v55-finisher-fix-2025-26/card/B12/ranking.csv',
    'C1': 'reports/ovr-v55-card-origin-attr-2025-26/card-C1/ranking.csv',
    'D1': 'reports/ovr-v55-attr-deflate-2025-26/card/D1/ranking.csv',
    'legacy': 'reports/ovr-calibrated-2025-26/legacy-sim-only/ranking.csv',
}
HOLDOUT_FIT = {'E2': 'E2', 'F2': 'F2', 'G3': 'G3', 'H1': 'H1-m0'}  # holdout 目錄 fitA-scale0.5/<dir>/ranking.csv
REFIT = ['v53', 'B12', 'C1', 'D1']  # 本任務重擬合（fit-A/fit-B/fit-full 在 backfill 資料夾）
SIMS = {'sim_v53_raw': ('reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv', 'rawPer36'),
        'sim_v53_v2': ('reports/ovr-v53-shrinkage-2025-26/ranking-v2.csv', 'v2Per36'),
        'sim_v54_raw': ('reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv', 'rawPer36'),
        'sim_v54_v2': ('reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv', 'v2Per36')}


def read(path):
    return list(csv.DictReader(open(path, encoding='utf-8-sig')))


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def score_map(path, col='ovr'):
    return {r['name']: float(r[col]) for r in read(path)}


def main():
    rapm = {k: {r['name']: r for r in read(p) if r['name']} for k, p in
            {'A': H / 'rapm-A.csv', 'B': H / 'rapm-B.csv', 'full': ROOT / 'reports/impact-rapm/rapm.csv'}.items()}
    k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    holdout = json.loads((H / 'holdout.json').read_text(encoding='utf-8'))

    full = {k: score_map(ROOT / p) for k, p in CARDS.items()}
    for k, (p, col) in SIMS.items():
        full[k] = score_map(ROOT / p, col)
    fitmaps = {}  # (fit, key) -> {name: ovr}
    for fit in 'AB':
        for k, d in HOLDOUT_FIT.items():
            fitmaps[(fit, k)] = score_map(H / f'fit{fit}-scale0.5' / d / 'ranking.csv')
        for k in REFIT:
            fitmaps[(fit, k)] = score_map(HERE / f'fit-{fit}' / k / 'ranking.csv')
    # blend 與 v53 校準檔逐名相同（下方核對），重擬合版共用
    for fit in 'AB':
        fitmaps[(fit, 'blend')] = fitmaps[(fit, 'v53')]

    # 全量重現核對：重跑全量版 vs 原 ranking 的 OVR 最大差
    repro = {}
    for k in REFIT:
        again = score_map(HERE / 'fit-full' / k / 'ranking.csv')
        repro[k] = {'players': len(again), 'maxAbsOvrDiff': max(abs(again[n] - full[k][n]) for n in full[k]), 'sameNames': set(again) == set(full[k])}
    repro['blend'] = {'players': len(full['blend']), 'maxAbsOvrDiff': max(abs(full['blend'][n] - full['v53'][n]) for n in full['v53']),
                      'sameNames': set(full['blend']) == set(full['v53']), 'note': 'blend.py 的 α=0.5 與 calibrate.py --alpha 0.5 輸出逐名相同，故共用 v53 重擬合版'}

    # 評估人群：與 evaluate.py 完全相同的 common（E2/F2/G3/H1/v53 + 其半擬合版）∩ 2K27
    base_sets = [set(full[k]) for k in ('v53', 'E2', 'F2', 'G3', 'H1')] + [set(fitmaps[(f, k)]) for f in 'AB' for k in HOLDOUT_FIT]
    common = set.intersection(*base_sets) & set(k2)

    def pool(ev):
        return sorted(n for n in common if n in rapm[ev] and float(rapm[ev][n]['pooledPoss']) >= THR)
    pools = {'A': pool('A'), 'B': pool('B')}
    assert len(common) == holdout['commonPlayers'], (len(common), holdout['commonPlayers'])
    # 所有層都要涵蓋這組人（否則同一人群的前提不成立）
    coverage = {}
    for k, m in {**full, **{f'fit{f}-{k}': fitmaps[(f, k)] for (f, k) in fitmaps}}.items():
        need = set(pools['A']) | set(pools['B']) | common
        coverage[k] = len(need - set(m))
    assert not any(coverage.values()), {k: v for k, v in coverage.items() if v}

    def ev_card(m, ev):
        names = pools[ev]; x = [m[n] for n in names]
        return {'n': len(names), 'net': rho(x, [float(rapm[ev][n]['pooledNet']) for n in names]),
                'def': rho(x, [float(rapm[ev][n]['pooledD']) for n in names])}

    def avg(a, b):
        return {'n': [a['n'], b['n']], 'net': (a['net'] + b['net']) / 2, 'def': (a['def'] + b['def']) / 2}

    # 2K27 人群：所有層（含模擬板、舊版）共有且有 2K 值
    common2k = sorted(set.intersection(*[set(m) for m in full.values()]) & set(k2))

    def r2k(m):
        return rho([m[n] for n in common2k], [k2[n] for n in common2k])

    layers = {}
    for k in list(SIMS) + ['legacy']:  # 不讀 RAPM：樣本內即樣本外
        out = avg(ev_card(full[k], 'B'), ev_card(full[k], 'A'))
        layers[k] = {'kind': 'no-rapm', 'out': out, 'rho2k': r2k(full[k])}
    for k in HOLDOUT_FIT:  # 沿用 holdout.json，另用 fit 目錄核對
        h = holdout['cards'][k]['holdout_scale0.5']['avg']
        mine = avg(ev_card(fitmaps[('A', k)], 'B'), ev_card(fitmaps[('B', k)], 'A'))
        assert abs(mine['net'] - h['net']) < 1e-9 and abs(mine['def'] - h['def']) < 1e-9, (k, mine, h)
        layers[k] = {'kind': 'holdout-json', 'out': {'n': h['n'], 'net': h['net'], 'def': h['def']}, 'rho2k': r2k(full[k]),
                     'fromHoldoutJson': True}
    for k in REFIT + ['blend']:  # 本任務重擬合
        out = avg(ev_card(fitmaps[('A', k)], 'B'), ev_card(fitmaps[('B', k)], 'A'))
        layers[k] = {'kind': 'refit', 'out': out, 'rho2k': r2k(full[k]), 'refit': repro[k] if k in repro else None}
    for k, v in layers.items():
        v['holdoutRho'] = f"{v['out']['net']:.3f} / {v['out']['def']:.3f}"

    # 卡片球隊指標：2025-26 球隊名單上場分鐘加權的平均卡片 OVR vs 實際每場分差（PLUS_MINUS / GP）
    league = json.loads((ROOT / 'data/season-league.json').read_text(encoding='utf-8'))
    teams = []
    for t in league['teams']:
        o = t['observed']
        teams.append({'team': t['name'], 'gp': o['GP'], 'wins': o['W'], 'marginPerGame': o['PLUS_MINUS'] / o['GP'],
                      'roster': [(p['name'], p['observed']['MIN']) for p in t['roster']]})
    margin = [t['marginPerGame'] for t in teams]
    team_cards, team_detail = [], {t['team']: {'team': t['team'], 'wins': t['wins'], 'marginPerGame': round(t['marginPerGame'], 3)} for t in teams}
    for k in CARD_ORDER:
        if k not in full:
            continue
        m = full[k]; vals = []; cover = []
        for t in teams:
            w = [(m[n], mn) for n, mn in t['roster'] if n in m and mn > 0]
            tot = sum(mn for n, mn in t['roster'] if mn > 0)
            vals.append(sum(v * mn for v, mn in w) / sum(mn for _, mn in w)); cover.append(sum(mn for _, mn in w) / tot)
            team_detail[t['team']][k] = round(vals[-1], 2)
        team_cards.append({'card': k, 'teams': len(teams), 'pearsonR': float(np.corrcoef(vals, margin)[0, 1]), 'spearmanRho': rho(vals, margin),
                           'minutesCoverageMin': min(cover)})

    result = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'threshold': THR,
              'commonPlayers': len(common), 'poolSizes': {k: len(v) for k, v in pools.items()}, 'rho2kPlayers': len(common2k),
              'rho2kPoolNote': '所有層（含模擬板與舊版 sim-only）共有且 merged.csv 有 overall2k 的球員',
              'layers': layers, 'refitReproduction': repro,
              'teamCard': {'source': 'data/season-league.json 球隊 observed.PLUS_MINUS / GP（每場分差）；名單 observed.MIN 為權重',
                           'cards': team_cards, 'teams': sorted(team_detail.values(), key=lambda r: -r['marginPerGame'])}}
    (HERE / 'backfill.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print('common', len(common), 'pools', result['poolSizes'], 'rho2k players', len(common2k))
    for k, v in layers.items():
        print(f"{k:12s} out {v['holdoutRho']}  2k {v['rho2k']:.3f}  [{v['kind']}]")
    for c in team_cards:
        print(f"team {c['card']:7s} r {c['pearsonR']:.3f} rho {c['spearmanRho']:.3f} cover>={c['minutesCoverageMin']:.3f}")
    print('repro', {k: (v['maxAbsOvrDiff'], v['sameNames']) for k, v in repro.items()})


if __name__ == '__main__':
    main()
