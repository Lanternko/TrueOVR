"""樣本外評估：用 A 半 RAPM 擬合的卡片，對 B 半 RAPM 算 Spearman ρ（再對調取平均）。

  python reports/ovr-v58-holdout-2025-26/evaluate.py     # 寫 holdout.json

卡片集合
  v53              reports/ovr-calibrated-2025-26/ranking.csv        （只有全量版；校準腳本未接 --rapm，無法半份重擬合）
  E2/F2/G3/H1      正式檔（全量 RAPM 擬合）= 'frozen'；fitA-* / fitB-* = 只用該半 RAPM 重擬合 = 'holdout'
ρ 的人群 = 所有卡片都有、2K27 有 overall2k、且「評估半」pooledPoss >= 門檻 的球員（所有卡共用同一組人）。
"""
import csv, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
THR_MAIN, THR_ALT = 2500, (1500, 5000)  # 半份資料的回合數約為全量的一半，全量門檻 5000 對應 2500
FROZEN = {'v53': 'reports/ovr-calibrated-2025-26/ranking.csv',
          'E2': 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv',
          'F2': 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5/ranking.csv',
          'G3': 'reports/ovr-v57-card-2025-26/card-G3-delta0.25/ranking.csv',
          'H1': 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv'}
REFIT = ['E2', 'F2', 'G3', 'H1']
REFIT_DIR = {'E2': 'E2', 'F2': 'F2', 'G3': 'G3', 'H1': 'H1-m0'}
FOUR = ['Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren']


def read(path, enc='utf-8-sig'):
    return list(csv.DictReader(open(path, encoding=enc)))


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def ovr_map(path):
    return {r['name']: float(r['ovr']) for r in read(path)}


def rapm_map(path):
    return {r['name']: r for r in read(path) if r['name']}


def main():
    rapm = {'A': rapm_map(HERE / 'rapm-A.csv'), 'B': rapm_map(HERE / 'rapm-B.csv'), 'full': rapm_map(ROOT / 'reports/impact-rapm/rapm.csv')}
    k2 = {r['name']: float(r['overall2k']) for r in read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    cards = {('frozen', k): ovr_map(ROOT / p) for k, p in FROZEN.items()}
    for scale in ('0.5', '1.0'):
        for fit in 'AB':
            for k in REFIT:
                cards[(f'fit{fit}-s{scale}', k)] = ovr_map(HERE / f'fit{fit}-scale{scale}' / REFIT_DIR[k] / 'ranking.csv')
    common = set.intersection(*[set(c) for c in cards.values()]) & set(k2)

    def pool(ev, thr):
        return sorted(n for n in common if n in rapm[ev] and float(rapm[ev][n]['pooledPoss']) >= thr)

    def evaluate(card_key, ev, thr):
        """card 對評估半 RAPM 的 ρ(淨值, 防守)；ev = 'A' / 'B' / 'full'。"""
        c = cards[card_key]; names = pool(ev, thr); x = [c[n] for n in names]
        return {'n': len(names), 'net': rho(x, [float(rapm[ev][n]['pooledNet']) for n in names]),
                'def': rho(x, [float(rapm[ev][n]['pooledD']) for n in names])}

    def avg(a, b):
        return {'n': [a['n'], b['n']], 'net': (a['net'] + b['net']) / 2, 'def': (a['def'] + b['def']) / 2}

    def rho2k(card_key):
        c = cards[card_key]; names = sorted(common)
        return rho([c[n] for n in names], [k2[n] for n in names])

    result = {'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'split': 'rapm-split.py：4 季合併比賽依 int(gameId) 奇偶切 A/B 各擬合一次（見 split-summary.json）',
              'poolDefinition': f'卡片共同球員 {len(common)} 人 ∩ 2K27 有 overall2k ∩ 評估半 pooledPoss ≥ 門檻；主要門檻 {THR_MAIN}（約為全量 5000 的一半）',
              'thresholdMain': THR_MAIN, 'thresholdAlt': list(THR_ALT), 'commonPlayers': len(common), 'cards': {}}
    for k in FROZEN:
        e = {'label': k, 'rho2k': rho2k(('frozen', k))}
        e['inSampleFull5000'] = evaluate(('frozen', k), 'full', 5000)  # 與審查板同口徑（人群 = 共同球員）
        e['frozenOnB'] = evaluate(('frozen', k), 'B', THR_MAIN)  # 全量版對 B 半：B 半資料已在擬合內，仍屬樣本內
        e['frozenOnA'] = evaluate(('frozen', k), 'A', THR_MAIN)
        e['frozenAvgAB'] = avg(e['frozenOnA'], e['frozenOnB'])
        if k in REFIT:
            for scale in ('0.5', '1.0'):
                tag = f's{scale}'
                aB = evaluate((f'fitA-{tag}', k), 'B', THR_MAIN); bA = evaluate((f'fitB-{tag}', k), 'A', THR_MAIN)
                own = avg(evaluate((f'fitA-{tag}', k), 'A', THR_MAIN), evaluate((f'fitB-{tag}', k), 'B', THR_MAIN))
                alt = {str(t): avg(evaluate((f'fitA-{tag}', k), 'B', t), evaluate((f'fitB-{tag}', k), 'A', t)) for t in THR_ALT}
                e[f'holdout_scale{scale}'] = {'fitA_evalB': aB, 'fitB_evalA': bA, 'avg': avg(aB, bA), 'sameHalfInSampleAvg': own,
                                              'sensitivityThreshold': alt,
                                              'rho2k': float(np.mean([rho2k((f'fitA-{tag}', k)), rho2k((f'fitB-{tag}', k))]))}
        result['cards'][k] = e

    # 配對 bootstrap：H1 − E2 的 Δρ（主要設定 scale 0.5，A→B 與 B→A 各算一次）
    rng = np.random.default_rng(20261021); boot = {}
    for fit, ev in (('A', 'B'), ('B', 'A')):
        names = pool(ev, THR_MAIN)
        h = np.array([cards[(f'fit{fit}-s0.5', 'H1')][n] for n in names]); e2 = np.array([cards[(f'fit{fit}-s0.5', 'E2')][n] for n in names])
        for key, col in (('net', 'pooledNet'), ('def', 'pooledD')):
            t = np.array([float(rapm[ev][n][col]) for n in names]); d = []
            for _ in range(2000):
                i = rng.integers(0, len(names), len(names)); d.append(rho(h[i], t[i]) - rho(e2[i], t[i]))
            boot[f'fit{fit}_eval{ev}_{key}'] = {'delta': rho(h, t) - rho(e2, t), 'ci95': [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]}
    result['bootstrapH1minusE2_scale0.5'] = boot

    # 參考上限：A 半 RAPM 直接當預測 B 半 RAPM 的 ρ（分半信度，兩半都 >= 門檻的共同球員）
    both = sorted(n for n in common if n in rapm['A'] and n in rapm['B']
                  and float(rapm['A'][n]['pooledPoss']) >= THR_MAIN and float(rapm['B'][n]['pooledPoss']) >= THR_MAIN)
    result['splitHalfReliability'] = {'n': len(both), **{key: rho([float(rapm['A'][n][col]) for n in both], [float(rapm['B'][n][col]) for n in both])
                                                         for key, col in (('net', 'pooledNet'), ('def', 'pooledD'))}}

    def top10(path):
        return [r['name'] for r in read(path)[:10]]
    tops = {'frozenH1': top10(ROOT / FROZEN['H1'])}
    for fit in 'AB':
        for scale in ('0.5', '1.0'):
            tops[f'fit{fit}-s{scale}'] = top10(HERE / f'fit{fit}-scale{scale}' / 'H1-m0' / 'ranking.csv')
    result['top10H1'] = {k: {'names': v, 'fourStillIn': {n: n in v for n in FOUR}, 'overlapWithFrozen': len(set(v) & set(tops['frozenH1']))}
                         for k, v in tops.items()}
    result['top10Others'] = {f'{k}-fitA-s0.5': top10(HERE / 'fitA-scale0.5' / REFIT_DIR[k] / 'ranking.csv') for k in REFIT}
    (HERE / 'holdout.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')

    f3 = lambda v: f'{v:.3f}'
    print('common', len(common))
    for k, e in result['cards'].items():
        line = (f"{k:4s} 2K {f3(e['rho2k'])} inFull5000 net {f3(e['inSampleFull5000']['net'])} def {f3(e['inSampleFull5000']['def'])} "
                f"(n={e['inSampleFull5000']['n']}) frozenAvgAB net {f3(e['frozenAvgAB']['net'])} def {f3(e['frozenAvgAB']['def'])}")
        for sc in ('0.5', '1.0'):
            h = e.get(f'holdout_scale{sc}')
            if h:
                line += (f" | s{sc} holdout net {f3(h['avg']['net'])} def {f3(h['avg']['def'])} "
                         f"(AB {f3(h['fitA_evalB']['net'])}/{f3(h['fitB_evalA']['net'])}) sameHalf net {f3(h['sameHalfInSampleAvg']['net'])} n={h['avg']['n']}")
        print(line)
    print('reliability', result['splitHalfReliability'])
    print(json.dumps(boot, indent=1))
    for k, v in result['top10H1'].items():
        print(k, v['overlapWithFrozen'], v['fourStillIn'], v['names'])


if __name__ == '__main__':
    main()
