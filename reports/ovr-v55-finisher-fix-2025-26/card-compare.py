# -*- coding: utf-8 -*-
"""追問驗收 1、2：卡片名次在 fix B 前後的變化，以及與 2K27／RAPM 的一致度。

  python reports/ovr-v55-finisher-fix-2025-26/card-compare.py [B12]

輸入：card/{v53,v54,<mode>}/ranking.csv（由 card-target.py + ovr-calibrated-2025-26/calibrate.py 產生）
      reports/ovr-v55-2k27-compare/merged.csv（唯讀，提供 rank2k / rapmPooledRank / rapmLastRank / archetype）
輸出：card/compare-<變體>.json 與 stdout 的表格。

v53 欄就是官方卡片（已驗證 card/v53/ranking.csv 與 reports/ovr-calibrated-2025-26/ranking.csv
逐人同名次，最大差 1 名、來自目標檔的四捨五入），所以「修正前」用它，v54 欄把 v53->v54 與
v54->fix B 兩段效果分開。
"""
import csv, json, sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).parent / 'card'
ROOT = Path(__file__).resolve().parents[2]
DOWN = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza']       # 要明顯下修
KEEP = ['Neemias Queta', 'Rudy Gobert', 'Jalen Smith']                          # 不得明顯下滑（<=15 名）
KEEP_TOL = 15
EXTRA = ['Charles Bassey', 'Jaxson Hayes', 'Jordan Walsh', 'Josh Minott',
         'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Luka Dončić', 'Trae Young', 'Victor Wembanyama']


def rk(variant):
    f = OUT / variant / 'ranking.csv'
    return {r['name']: {'rank': int(r['rank']), 'ovr': float(r['ovr'])}
            for r in csv.DictReader(open(f, encoding='utf-8-sig'))}


def spearman(a, b):
    return float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'B12'
    cards = {v: rk(v) for v in ['v53', 'v54', mode]}
    merged = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv', encoding='utf-8-sig'))}

    def row(n):
        m = merged.get(n, {})
        o = {'name': n, 'archetype': m.get('archetype'),
             'rank2k': float(m['rank2k']) if m.get('rank2k') else None,
             'rapmPooledRank': float(m['rapmPooledRank']) if m.get('rapmPooledRank') else None,
             'rapmLastRank': float(m['rapmLastRank']) if m.get('rapmLastRank') else None}
        for v in cards:
            o[v] = cards[v][n]['rank'] if n in cards[v] else None
        o['deltaV53'] = None if o['v53'] is None or o[mode] is None else o[mode] - o['v53']
        o['deltaV54'] = None if o['v54'] is None or o[mode] is None else o[mode] - o['v54']
        return o

    down = [row(n) for n in DOWN]
    keep = [row(n) for n in KEEP]
    extra = [row(n) for n in EXTRA]

    # 原型層的平均名次變化（Δ>0 = 名次變差＝下修）
    groups = {}
    for a in ['吃餅長人', '持球創造', '3D', '其他']:
        ns = [n for n, m in merged.items() if m['archetype'] == a and n in cards['v53'] and n in cards[mode]]
        d53 = [cards[mode][n]['rank'] - cards['v53'][n]['rank'] for n in ns]
        d54 = [cards[mode][n]['rank'] - cards['v54'][n]['rank'] for n in ns]
        groups[a] = {'players': len(ns), 'meanDeltaVsV53': float(np.mean(d53)), 'medianDeltaVsV53': float(np.median(d53)),
                     'meanDeltaVsV54': float(np.mean(d54)), 'medianDeltaVsV54': float(np.median(d54))}

    # 與 2K27 / RAPM 的一致度（只取有對照值的人）
    agree = {}
    for key, poss in [('rank2k', None), ('rapmPooledRank', 'pooledPoss'), ('rapmLastRank', 'lastPoss')]:
        ns = [n for n, m in merged.items() if m.get(key) and n in cards['v53']]
        if poss:
            lim = 5000 if poss == 'pooledPoss' else 500
            ns = [n for n in ns if merged[n].get(poss) and float(merged[n][poss]) >= lim]
        t = [float(merged[n][key]) for n in ns]
        agree[key] = {'players': len(ns),
                      **{v: {'spearman': spearman([cards[v][n]['rank'] for n in ns], t),
                             'meanAbsRankGap': float(np.mean([abs(cards[v][n]['rank'] - float(merged[n][key])) for n in ns]))}
                         for v in cards}}
        # 吃餅長人子群的平均 (對照名次 - 卡片名次)：正值＝卡片比對照高估
        fin = [n for n in ns if merged[n]['archetype'] == '吃餅長人']
        agree[key]['finishersMeanTargetMinusCard'] = {v: float(np.mean([float(merged[n][key]) - cards[v][n]['rank'] for n in fin])) for v in cards}
        agree[key]['finishers'] = len(fin)

    verdict = {
        'down': {r['name']: {'v53': r['v53'], mode: r[mode], 'delta': r['deltaV53'],
                             'rank2k': r['rank2k'], 'rapmPooledRank': r['rapmPooledRank']} for r in down},
        'keep': {r['name']: {'v53': r['v53'], mode: r[mode], 'delta': r['deltaV53'], 'withinTolerance': r['deltaV53'] <= KEEP_TOL} for r in keep},
        'keepTolerance': KEEP_TOL,
        'downAllMoved': None, 'keepAllWithinTolerance': all(r['deltaV53'] <= KEEP_TOL for r in keep),
    }
    verdict['downAllMoved'] = all(r['deltaV53'] >= 10 for r in down)
    out = {'mode': mode, 'down': down, 'keep': keep, 'extra': extra, 'archetypeDelta': groups, 'agreement': agree, 'verdict': verdict}
    (OUT / f'compare-{mode}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    hdr = f"{'name':26s} {'arch':6s} {'v53':>4s} {'v54':>4s} {mode:>5s} {'dV53':>5s} {'2K':>5s} {'RAPM':>5s}"
    print(hdr)
    for tag, rows in [('下修', down), ('不誤傷', keep), ('參考', extra)]:
        print('--', tag)
        for r in rows:
            print(f"{r['name']:26s} {(r['archetype'] or ''):6s} {r['v53']!s:>4s} {r['v54']!s:>4s} {r[mode]!s:>5s} {r['deltaV53']!s:>5s} "
                  f"{('' if r['rank2k'] is None else int(r['rank2k']))!s:>5s} {('' if r['rapmPooledRank'] is None else int(r['rapmPooledRank']))!s:>5s}")
    print(json.dumps({'archetypeDelta': groups, 'verdict': {k: v for k, v in verdict.items() if k.endswith('Tolerance') or k.startswith(('downAll', 'keepAll'))}}, ensure_ascii=False, indent=1))
