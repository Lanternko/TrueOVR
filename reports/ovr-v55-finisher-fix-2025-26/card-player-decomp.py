# -*- coding: utf-8 -*-
"""把「某位球員的卡片預測值為什麼變了」拆成每個屬性的貢獻。

  python reports/ovr-v55-finisher-fix-2025-26/card-player-decomp.py B12

為什麼需要這支：追問要求在 B12 誤傷 Jalen Smith 的情況下指出「哪個係數／屬性」。
卡片 OVR 是 predictedPer36 的單調映射，而 predictedPer36 = intercept + Σ_j b_j x_ij
（x 是標準化後的屬性，含位置交互項；見 reports/ovr-calibrated-2025-26/calibrate.py 的
design()）。兩個版本的 league 檔完全相同，所以 attributeMean / attributeSD 一樣，x_ij
也一樣，於是

    Δpredicted_i = Σ_j (b_j^mode − b_j^v53) · x_ij

可以逐項拆乾淨——每一項就是「某個係數改變 × 這位球員在該屬性上的偏離」。
這不是近似，是恆等式；summary.json 的 valuePer10AttributePoints 只是同一組係數的邊際摘要。

輸出：card/decomp-<mode>.json
"""
import csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).parent / 'card'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
POS = ['PG', 'SG', 'SF', 'PF', 'C']
INTERACT = ['long', 'short', 'pass', 'rebound', 'help']
NAMES = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza',
         'Neemias Queta', 'Rudy Gobert', 'Jalen Smith']

sys.path.insert(0, str(ROOT / 'reports/ovr-calibrated-2025-26'))
import calibrate as K


def features(mode):
    """重用 calibrate.py 自己的 load()/design()，確保 creation、pressure 的衍生口徑一致。"""
    rows = K.load(D / f'calibration-target-{mode}.csv')
    X, mean, sd = K.design(rows, 'position-interactions')
    cols = list(ATTRS)
    for p in POS[:-1]:
        cols += [f'{a}×{p}' for a in INTERACT]
    return rows, X, cols


def labels(cols):
    return cols


def main(mode):
    rows, X, cols = features(mode)
    assert X.shape[1] == len(cols), (X.shape, len(cols))
    b = {v: np.array(json.loads((D / v / 'summary.json').read_text(encoding='utf-8'))['formula']['coefficientsOnStandardized'])
         for v in ('v53', 'v54', mode)}
    c0 = {v: json.loads((D / v / 'summary.json').read_text(encoding='utf-8'))['formula']['intercept'] for v in ('v53', 'v54', mode)}
    rank = {}
    for v in ('v53', 'v54', mode):
        r = list(csv.DictReader(open(D / v / 'ranking.csv', encoding='utf-8')))
        rank[v] = {x['name']: x for x in r}
    out = {'mode': mode, 'players': {}}
    idx = {r['name']: i for i, r in enumerate(rows)}
    for name in NAMES:
        i = idx[name]
        x = X[i]
        d = (b[mode] - b['v53']) * x
        terms = sorted(zip(cols, d.tolist(), x.tolist()), key=lambda t: -abs(t[1]))
        out['players'][name] = {
            'pos': rows[i]['pos'],
            'rank': {v: int(rank[v][name]['rank']) for v in ('v53', 'v54', mode)},
            'ovr': {v: float(rank[v][name]['ovr']) for v in ('v53', 'v54', mode)},
            'predictedPer36': {v: float(rank[v][name]['predictedPer36']) for v in ('v53', 'v54', mode)},
            'simulatedPer36': {v: float(rank[v][name]['simulatedPer36']) for v in ('v53', 'v54', mode)},
            'interceptDelta': c0[mode] - c0['v53'],
            'deltaPredictedFromCoefficients': float(d.sum() + c0[mode] - c0['v53']),
            'topTerms': [{'feature': f, 'contribution': round(v, 4), 'z': round(z, 3)} for f, v, z in terms[:8]],
        }
    (D / f'decomp-{mode}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for name, p in out['players'].items():
        print(f"{name:20s} {p['pos']:2s} rank {p['rank']['v53']:4d}->{p['rank'][mode]:4d} "
              f"pred {p['predictedPer36']['v53']:+.3f}->{p['predictedPer36'][mode]:+.3f} "
              f"(Δ{p['deltaPredictedFromCoefficients']:+.3f}, 截距{p['interceptDelta']:+.3f})")
        print('   ' + ' | '.join(f"{t['feature']}{t['contribution']:+.3f}(z{t['z']:+.2f})" for t in p['topTerms'][:6]))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'B12')
