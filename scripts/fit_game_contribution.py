"""單場貢獻值（使用者 2026-10-30 選 A）：用 box score 估每 36 分鐘淨影響，只拿來顯示，不進 OVR。

擬合：2025-26 前半（int(GAME_ID) % 2 == 0，同 E-081 rapm1 的 A 半）每人 box 合計換算每 36 分鐘，
      對 rapm1-A net 做加權最小平方（權重＝rapm1-A poss），人群＝A 半上場 ≥ 300 分鐘。沒有可調參數。
檢驗：權重凍結後套到 B 半（int(GAME_ID) % 2 == 1）box，和 rapm1-B net 比（樣本外）；
      對照組：A 半 RAPM 自己預測 B 半（穩定度上限）、Game Score／36、正負值／36。
基準：用凍結權重算 2025-26 整季每人 box 影響（新賽季頁與 2025-26 頁都拿它當「平均」）。

輸出：reports/game-contribution/{weights.json, baseline-2025-26.json, report.md}
用法：python -I scripts/fit_game_contribution.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data/season-source/player-games.json'
RAPM = ROOT / 'reports/card-0.2.3+E081-age-residual'
OUT = ROOT / 'reports/game-contribution'
FEATS = ['PTS', 'FGA', 'FTA', 'FG3M', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF']
MIN_MIN = 300


def load_games():
    rs = json.loads(SRC.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    return rs['rowSet'], h


def totals(rows, h, half=None):
    """{pid: {MIN, PTS, ...}}；half＝0/1 只取該半，None 取整季。"""
    t = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if half is not None and int(r[h['GAME_ID']]) % 2 != half:
            continue
        d = t[r[h['PLAYER_ID']]]
        d['MIN'] += r[h['MIN']] or 0
        for k in FEATS + ['FGM', 'FTM', 'PLUS_MINUS']:
            d[k] += r[h[k]] or 0
    return t


def per36(d, keys):
    return np.array([d[k] * 36 / d['MIN'] for k in keys])


def gmsc36(d):
    g = (d['PTS'] + 0.4 * d['FGM'] - 0.7 * d['FGA'] - 0.4 * (d['FTA'] - d['FTM']) + 0.7 * d['OREB'] + 0.3 * d['DREB']
         + d['STL'] + 0.7 * d['AST'] + 0.7 * d['BLK'] - 0.4 * d['PF'] - d['TOV'])
    return g * 36 / d['MIN']


def load_rapm(half):
    return {int(r['playerId']): (float(r['net']), float(r['poss']))
            for r in csv.DictReader((RAPM / f'rapm1-{half}.csv').open(encoding='utf-8'))}


def wcorr(x, y, w):
    x, y = np.asarray(x), np.asarray(y)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return float(np.average((x - mx) * (y - my), weights=w) / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w)))


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows, h = load_games()
    tA, tB, tS = totals(rows, h, 0), totals(rows, h, 1), totals(rows, h)
    rA, rB = load_rapm('A'), load_rapm('B')

    pa = [p for p, d in tA.items() if d['MIN'] >= MIN_MIN and p in rA]
    X = np.array([np.r_[1.0, per36(tA[p], FEATS)] for p in pa])
    y = np.array([rA[p][0] for p in pa])
    w = np.array([rA[p][1] for p in pa])
    sw = np.sqrt(w)
    beta = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    fitA = X @ beta

    pb = [p for p, d in tB.items() if d['MIN'] >= MIN_MIN and p in rB]
    box_b = np.array([beta[0] + per36(tB[p], FEATS) @ beta[1:] for p in pb])
    yb = np.array([rB[p][0] for p in pb])
    wb = np.array([rB[p][1] for p in pb])
    both = [i for i, p in enumerate(pb) if p in rA]
    ev = {
        'n_fit': len(pa), 'n_eval': len(pb),
        'in_sample_wr': wcorr(fitA, y, w),
        'box_B_vs_rapmB': {'wPearson': wcorr(box_b, yb, wb), 'spearman': spearman(box_b, yb)},
        'gmsc36_B_vs_rapmB': {'wPearson': wcorr([gmsc36(tB[p]) for p in pb], yb, wb),
                              'spearman': spearman([gmsc36(tB[p]) for p in pb], yb)},
        'pm36_B_vs_rapmB': {'wPearson': wcorr([tB[p]['PLUS_MINUS'] * 36 / tB[p]['MIN'] for p in pb], yb, wb),
                            'spearman': spearman([tB[p]['PLUS_MINUS'] * 36 / tB[p]['MIN'] for p in pb], yb)},
        'rapmA_vs_rapmB': {'n': len(both), 'wPearson': wcorr([rA[pb[i]][0] for i in both], yb[both], wb[both]),
                           'spearman': spearman([rA[pb[i]][0] for i in both], yb[both])},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    weights = {'note': '每 36 分鐘 box → rapm1-A net（每 100 回合）的加權最小平方；只顯示用，不進 OVR',
               'fit': '2025-26 A 半（int(GAME_ID)%2==0），上場 ≥300 分鐘，權重 rapm1-A poss',
               'intercept': float(beta[0]), 'per36': {k: float(b) for k, b in zip(FEATS, beta[1:])}, 'eval': ev}
    (OUT / 'weights.json').write_text(json.dumps(weights, ensure_ascii=False, indent=1), encoding='utf-8')

    base = {str(p): {'box36': round(float(beta[0] + per36(d, FEATS) @ beta[1:]), 3), 'min': round(d['MIN'], 1)}
            for p, d in tS.items() if d['MIN'] > 0}
    (OUT / 'baseline-2025-26.json').write_text(json.dumps(base, separators=(',', ':')), encoding='utf-8')

    f2 = lambda v: f'{v:+.3f}'
    lines = ['# 單場貢獻值（box score → RAPM）', '',
             '只顯示用，不進 OVR。擬合 2025-26 A 半、B 半樣本外檢驗；沒有可調參數。', '',
             '## 權重（每 36 分鐘每多 1 個，貢獻值變多少；單位＝每 100 回合淨分）', '',
             '| 項目 | 權重 |', '|---|---|', f'| 截距 | {f2(beta[0])} |'] + \
            [f'| {k} | {f2(b)} |' for k, b in zip(FEATS, beta[1:])] + \
            ['', '## 檢驗（B 半，樣本外）', '',
             f'擬合 {ev["n_fit"]} 人，檢驗 {ev["n_eval"]} 人（B 半上場 ≥ {MIN_MIN} 分鐘）。', '',
             '| 拿什麼預測 B 半 RAPM | 加權 Pearson | Spearman |', '|---|---|---|',
             f'| 貢獻值（A 半擬合的權重 × B 半 box） | {ev["box_B_vs_rapmB"]["wPearson"]:.3f} | {ev["box_B_vs_rapmB"]["spearman"]:.3f} |',
             f'| Game Score／36（B 半） | {ev["gmsc36_B_vs_rapmB"]["wPearson"]:.3f} | {ev["gmsc36_B_vs_rapmB"]["spearman"]:.3f} |',
             f'| 正負值／36（B 半） | {ev["pm36_B_vs_rapmB"]["wPearson"]:.3f} | {ev["pm36_B_vs_rapmB"]["spearman"]:.3f} |',
             f'| A 半 RAPM 本身（{ev["rapmA_vs_rapmB"]["n"]} 人） | {ev["rapmA_vs_rapmB"]["wPearson"]:.3f} | {ev["rapmA_vs_rapmB"]["spearman"]:.3f} |',
             '', f'樣本內（A 半擬合值對 A 半 RAPM）加權 r＝{ev["in_sample_wr"]:.3f}，只供參考（R-007）。', '']
    (OUT / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(weights, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
