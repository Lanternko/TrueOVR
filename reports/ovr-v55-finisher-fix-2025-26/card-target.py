# -*- coding: utf-8 -*-
"""把模擬板轉成卡片校準目標 CSV（reports/ovr-calibrated-2025-26/calibrate.py 吃的格式）。

  python reports/ovr-v55-finisher-fix-2025-26/card-target.py v53   # 口徑驗證：對照凍結檔
  python reports/ovr-v55-finisher-fix-2025-26/card-target.py B12

為什麼需要這支：追問的驗收 1、2 看的是**卡片名次**，不是模擬板名次。卡片名次由
reports/ovr-calibrated-2025-26/calibrate.py 產生，它的輸入是一張
`name,position,healthy_minutes,centered_contribution,standard_error` 的目標 CSV，
官方卡片那張是 reports/ovr-v53-2025-26/calibration-target-s8-expected.csv（v53 板）。
所以要讓 fix B 影響卡片，必須把 v55 板換算成同格式的目標再跑一次 calibrate.py。

口徑（與凍結檔逐項對齊，v53 模式會逐行比對驗證）：
  healthy_minutes      = 板上的 minutes（每場分鐘）
  centered_contribution= 位置中心化後的每場分差貢獻 = per36Centered / 36 * minutes
                         （calibrate.py 會再 /minutes*36 還原回 per-36）
  standard_error       = 全體一律 0.5734（實測每人標準誤的中位數；見
                         reports/ovr-calibrated-2025-26/report.md）
"""
import csv, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import shrink as S

OUT = Path(__file__).parent / 'card'
SE = 0.5734
FROZEN = S.ROOT / 'reports/ovr-v53-2025-26/calibration-target-s8-expected.csv'


def build(variant):
    players = S.load(variant)
    x, _ = S.board(players, set(range(8)))
    rows = []
    for i, p in enumerate(players):
        rows.append({'name': p['name'], 'position': p['pos'], 'healthy_minutes': p['m'],
                     'centered_contribution': float(x[i]) / 36 * p['m'], 'standard_error': SE})
    rows.sort(key=lambda r: -r['centered_contribution'] / r['healthy_minutes'])
    return rows


def write(variant, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f'calibration-target-{variant}.csv'
    with open(f, 'w', encoding='utf-8', newline='') as fh:
        wr = csv.DictWriter(fh, ['name', 'position', 'healthy_minutes', 'centered_contribution', 'standard_error'])
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    return f


def verify(rows):
    """v53 模式：跟凍結的官方目標檔比 per-36 目標值（calibrate.py 真正用到的量）。"""
    frozen = {r['name']: r for r in csv.DictReader(open(FROZEN, encoding='utf-8-sig'))}
    d = []
    for r in rows:
        g = frozen.get(r['name'])
        if g is None:
            continue
        a = r['centered_contribution'] / r['healthy_minutes'] * 36
        b = float(g['centered_contribution']) / float(g['healthy_minutes']) * 36
        d.append(abs(a - b))
    return {'matched': len(d), 'frozenRows': len(frozen), 'builtRows': len(rows),
            'maxAbsDiffPer36': max(d), 'meanAbsDiffPer36': float(np.mean(d))}


if __name__ == '__main__':
    variant = sys.argv[1]
    rows = build(variant)
    f = write(variant, rows)
    out = {'variant': variant, 'rows': len(rows), 'file': str(f)}
    if variant == 'v53':
        out['verifyVsFrozen'] = verify(rows)
    import json
    print(json.dumps(out, ensure_ascii=False, indent=1))
