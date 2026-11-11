# -*- coding: utf-8 -*-
"""C1 vs 官方卡片(v53)/v54/B12 的四向比較：對照
reports/ovr-v55-finisher-fix-2025-26/card-compare.py 的邏輯（下修名單、不誤傷名單、原型層
Δrank、對 2K27／多季 RAPM／單季 RAPM 的 Spearman ρ，含 <800/800-1300/1300+/all 分桶），
但一次放四個變體而不是三個，並直接用任務點名的驗收門檻產生 pass/fail 表。

  python reports/ovr-v55-card-origin-attr-2025-26/compare-c1.py

輸出：reports/ovr-v55-card-origin-attr-2025-26/compare-C1.json
"""
import csv, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
FIX = ROOT / 'reports/ovr-v55-finisher-fix-2025-26'
VARIANTS = {
    'v53': FIX / 'card/v53/ranking.csv',
    'v54': FIX / 'card/v54/ranking.csv',
    'B12': FIX / 'card/B12/ranking.csv',
    'C1': HERE / 'card-C1/ranking.csv',
}
DOWN = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza']
KEEP = ['Neemias Queta', 'Rudy Gobert', 'Jalen Smith']
KEEP_TOL = 15
BUCKETS = [('<800', 0, 800), ('800-1300', 800, 1300), ('1300+', 1300, float('inf')), ('all', 0, float('inf'))]
ARCHETYPES = ['吃餅長人', '持球創造', '3D', '其他']


def rk(path):
    return {r['name']: {'rank': int(r['rank']), 'ovr': float(r['ovr'])} for r in csv.DictReader(open(path, encoding='utf-8-sig'))}


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


if __name__ == '__main__':
    cards = {v: rk(p) for v, p in VARIANTS.items()}
    merged = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv', encoding='utf-8-sig'))}
    minutes = {r['name']: r for r in csv.DictReader(open(FIX / 'card/v53/ranking.csv', encoding='utf-8-sig'))}

    def row(n):
        m = merged.get(n, {})
        o = {'name': n, 'archetype': m.get('archetype'),
             'rank2k': float(m['rank2k']) if m.get('rank2k') else None,
             'rapmPooledRank': float(m['rapmPooledRank']) if m.get('rapmPooledRank') else None,
             'rapmLastRank': float(m['rapmLastRank']) if m.get('rapmLastRank') else None}
        for v in cards:
            o[v] = cards[v][n]['rank'] if n in cards[v] else None
        for v in ('v54', 'B12', 'C1'):
            o[f'delta_{v}_vs_v53'] = None if o['v53'] is None or o[v] is None else o[v] - o['v53']
        return o

    down = [row(n) for n in DOWN]
    keep = [row(n) for n in KEEP]

    # 原型層 Δrank（相對 v53；正值=名次變差=下修）
    archetype = {}
    for a in ARCHETYPES:
        ns = [n for n, m in merged.items() if m['archetype'] == a and all(n in cards[v] for v in cards)]
        archetype[a] = {'players': len(ns)}
        for v in ('v54', 'B12', 'C1'):
            d = [cards[v][n]['rank'] - cards['v53'][n]['rank'] for n in ns]
            archetype[a][v] = {'meanDelta': float(np.mean(d)), 'medianDelta': float(np.median(d))}

    # 對 2K27 / 多季 RAPM / 單季 RAPM 的 Spearman ρ，整體與分鐘桶
    def minutes_of(n):
        r = minutes.get(n)
        return float(r['MIN']) if r else None

    agreement = {}
    for key, poss_key, lim in [('rank2k', None, None), ('rapmPooledRank', 'pooledPoss', 5000), ('rapmLastRank', 'lastPoss', 500)]:
        base = [n for n, m in merged.items() if m.get(key) and all(n in cards[v] for v in cards)]
        if poss_key:
            base = [n for n in base if merged[n].get(poss_key) and float(merged[n][poss_key]) >= lim]
        agreement[key] = {'players': len(base), 'buckets': {}}
        for label, lo, hi in BUCKETS:
            ns = [n for n in base if minutes_of(n) is not None and lo <= minutes_of(n) < hi]
            if not ns:
                agreement[key]['buckets'][label] = {'players': 0}
                continue
            t = [float(merged[n][key]) for n in ns]
            agreement[key]['buckets'][label] = {
                'players': len(ns),
                **{v: round(spearman([cards[v][n]['rank'] for n in ns], t), 4) for v in cards},
            }

    verdict_down = {}
    for r in down:
        d = r['delta_C1_vs_v53']
        thresh = 10 if r['name'] == 'Karlo Matković' else 1
        verdict_down[r['name']] = {'v53': r['v53'], 'C1': r['C1'], 'B12': r['B12'], 'deltaC1vsV53': d,
                                    'requireMinDrop': thresh, 'pass': d is not None and d >= thresh}
    verdict_keep = {}
    for r in keep:
        d = r['delta_C1_vs_v53']
        verdict_keep[r['name']] = {'v53': r['v53'], 'C1': r['C1'], 'B12': r['B12'], 'deltaC1vsV53': d,
                                    'tolerance': KEEP_TOL, 'pass': d is not None and d <= KEEP_TOL}

    overall_rho = {
        'multiSeasonRAPM': {'C1': agreement['rapmPooledRank']['buckets']['all'].get('C1'),
                             'B12': agreement['rapmPooledRank']['buckets']['all'].get('B12'),
                             'pass': agreement['rapmPooledRank']['buckets']['all'].get('C1', -9) >= agreement['rapmPooledRank']['buckets']['all'].get('B12', 9)},
        'rank2k': {'C1': agreement['rank2k']['buckets']['all'].get('C1'),
                   'B12': agreement['rank2k']['buckets']['all'].get('B12'),
                   'pass': agreement['rank2k']['buckets']['all'].get('C1', -9) >= agreement['rank2k']['buckets']['all'].get('B12', 9)},
    }

    archetype_verdict = {
        'finishersMedianMovesDown': archetype['吃餅長人']['C1']['medianDelta'] > 0,
        'finishersMedianDeltaC1': archetype['吃餅長人']['C1']['medianDelta'],
        'creatorsNotWorse': archetype['持球創造']['C1']['medianDelta'] <= archetype['持球創造']['B12']['medianDelta'] + 1e-9,
        'creatorsMedianDeltaC1': archetype['持球創造']['C1']['medianDelta'],
        'creatorsMedianDeltaB12': archetype['持球創造']['B12']['medianDelta'],
    }

    out = {
        'variants': list(VARIANTS.keys()), 'down': down, 'keep': keep,
        'archetypeDelta': archetype, 'agreement': agreement,
        'verdict': {'down': verdict_down, 'keep': verdict_keep, 'overallRho': overall_rho, 'archetype': archetype_verdict,
                    'allPass': all(v['pass'] for v in verdict_down.values()) and all(v['pass'] for v in verdict_keep.values())
                               and overall_rho['multiSeasonRAPM']['pass'] and overall_rho['rank2k']['pass']},
    }
    (HERE / 'compare-C1.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['verdict'], ensure_ascii=False, indent=1))
