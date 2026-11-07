"""S1 sanity 診斷：釐清與 personal-cards/2024-25.json 的差異來源。

personal-cards 由 reports/defense-tenth/step3-a2/prepare.mjs 產生：
  calibrate(buildCards(target).cards, prior_season)
  = 把 long/mid/short 先正查到機率，套 prior 季（2023-24）calibration-v3 的 shotDelta 邏輯轉換，
    再反查回能力值；其餘 6 個 box 屬性不動。
本檔同時輸出「把同一個轉換套在我方數值上」的差異，用來證明差異完全來自該校準層，
而不是 builder 不同。輸出 data/sanity-diagnosis.json。
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import CURVES, DATA, ROOT, inverse, load_json
import season_attrs as SA
from scipy.stats import spearmanr

ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'stamina']
CURVE_OF = {'long': 'CURVE_3PT', 'mid': 'CURVE_MID', 'short': 'CURVE_SHORT'}


def forward(prob_attr, curve):
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if x0 <= prob_attr <= x1:
            return y0 + (prob_attr - x0) / (x1 - x0) * (y1 - y0)
    return curve[0][1] if prob_attr < curve[0][0] else curve[-1][1]


def calibrate(attr_value, curve, shot_delta):
    v = max(0.001, min(0.999, forward(attr_value, curve)))
    p = 1 / (1 + math.exp(-math.log(v / (1 - v)) - shot_delta))
    return inverse(p, curve)


def main():
    sd = SA.load_season('2024-25')
    stats = SA.aggregate(sd)
    mapping = SA.build_mapping(sd, stats)
    cards = SA.compute_attrs(sd, stats, mapping)
    ref = {int(c['playerId']): c for c in load_json(
        ROOT / 'reports/defense-tenth/step3-a2/personal-cards/2024-25.json')['cards']}
    cal = load_json(ROOT / 'reports/defense-seventh/2023-24/calendar-55/calibration-v3.json')['selected']
    shot_delta = cal.get('shotDelta', 0.0)
    common = sorted(p for p in cards if p in ref)

    def med(xs):
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

    raw, decal = {}, {}
    for a in ATTRS:
        diffs = [abs(cards[p][a] - float(ref[p][a])) for p in common]
        rho = float(spearmanr([cards[p][a] for p in common], [float(ref[p][a]) for p in common]).statistic)
        raw[a] = {'spearman': round(rho, 6), 'medianAbsDiff': round(med(diffs), 4),
                  'nAbsDiffGt5': int(sum(1 for d in diffs if d > 5))}
        if a in CURVE_OF:
            curve = CURVES[CURVE_OF[a]]
            dd = [abs(calibrate(cards[p][a], curve, shot_delta) - float(ref[p][a])) for p in common]
            rho2 = float(spearmanr([calibrate(cards[p][a], curve, shot_delta) for p in common],
                                   [float(ref[p][a]) for p in common]).statistic)
            decal[a] = {'spearman': round(rho2, 6), 'medianAbsDiff': round(med(dd), 4),
                        'nAbsDiffGt5': int(sum(1 for d in dd if d > 5))}
        else:
            decal[a] = raw[a]
    pooled = sorted(abs(cards[p][a] - float(ref[p][a])) for a in ATTRS for p in common)
    out = {
        'reference': 'reports/defense-tenth/step3-a2/personal-cards/2024-25.json',
        'referenceTransform': {
            'source': 'reports/defense-tenth/step3-a2/prepare.mjs::calibrate(next.cards, prior="2023-24")',
            'shotDelta': shot_delta,
            'shotDeltaFile': 'reports/defense-seventh/2023-24/calendar-55/calibration-v3.json',
            'appliesTo': ['long', 'mid', 'short'],
        },
        'nPlayers': len(common),
        'raw': raw,
        'afterUndoingReferenceCalibration': decal,
        'pooledMedianAbsDiffAllNine': round(med(pooled), 4),
        'medianOfPerAttributeMedians': round(med([raw[a]['medianAbsDiff'] for a in ATTRS]), 4),
        'perAttributeMedianCriterion': 'all 9 attributes <= 5 points',
        'perAttributeMedianPass': all(raw[a]['medianAbsDiff'] <= 5 for a in ATTRS),
        'perAttributeMedianPassAfterUnalibrating': all(decal[a]['medianAbsDiff'] <= 5 for a in ATTRS),
    }
    path = DATA / 'sanity-diagnosis.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
