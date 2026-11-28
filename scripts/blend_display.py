"""3PT／FT 顯示欄：量＋準混合（R-168，E-242／E-244 的結論；使用者 2026-11-05 選「只換顯示欄」）。
只改頁面上的 3PT、FT 兩欄數字：ranking.csv、OVR、名次、模擬用值（long、ft 進回歸、sim 的 threeRate）完全不動。

定義（自己決定、凍結，R-165）：
- 量 vol：3PT＝窗口加權 3PA／窗口 MIN×36（向池平均收縮，等同 200 分鐘，K_MIN）；FT＝窗口 FTA／窗口 MIN×36（和能力值同一個 WIN_LEN 窗口）。
- 準 acc：收縮命中率 (n + k·μ)/(a + k)。3PT 用 n＝難度調整分子（abilityC），k＝294.667，μ＝聯盟三分%（同現行 threeValue）；
  FT 用 n＝FTM，k＝26（E-244 五季 beta-binomial 估計 22.7～28.2 的近季值），μ＝聯盟窗口加權罰球%。
- 分數 score＝w·z(vol) ＋ (1−w)·z(acc)：z 為池（窗口 MIN ≥ 500）內原始值的標準化（不轉百分位，極端值才看得出來）；3PT w＝0.6、FT w＝0（罰球只看命中率：
  罰球沒有防守，量已由 foulDraw 算過；2026-11-05 使用者裁定）。
- 轉能力值：score 在池內的百分位 → attr()（PR50→70，線性到 99）；PR≥99 之後每多 1 個 score 標準差加 10 分（無上限，使用者 2026-11-05 規則），
  再套 season_nav.display_scale（和其他百分位型能力值同一把尺）。
- 池外有資料的人（窗口 MIN < 500）照池的分布算位置；沒有窗口資料的人（新秀）回傳空，呼叫端退回原值。
"""
import json
import math
import bisect
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
W_THREE, W_FT = 0.6, 0.0
K_THREE, K_FT = 294.667, 26.0
POOL_MIN = 500.0
K_MIN = 200.0                                # 出手量的小樣本收縮：等同 200 分鐘的池平均出手率（分鐘很少的人量不會被放大成極端值）
TAIL_PER_SD = 10.0                           # PR99 以上每多 1 個 score 標準差加的分數


def league_3p(card):
    """聯盟三分% μ：和 run_c4_live.three_value_columns 同口徑。卡片頁＝2025-26；賽中頁＝2025-26＋2026-27 合併。"""
    paths = [ROOT / 'data/season-source/player-games.json']
    if not card:
        paths.append(ROOT / 'data/defense-seventh/2026-27/player-games.json')
    m = a = 0.0
    for p in paths:
        rs = json.loads(p.read_text(encoding='utf-8'))['data']['resultSets']
        t = rs[0] if isinstance(rs, list) else rs
        h = {k: i for i, k in enumerate(t['headers'])}
        for r in t['rowSet']:
            m += r[h['FG3M']] or 0
            a += r[h['FG3A']] or 0
    return m / a


def _pct(x, s):
    lo, hi = bisect.bisect_left(s, x), bisect.bisect_right(s, x)
    return 100 * (lo + 0.5 * (hi - lo)) / len(s)


def _attr(p):
    return max(40, min(99, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def blend(items, w):
    """items＝{key: (vol, acc, window_min)} → {key: attr（未換顯示尺）}。池＝window_min ≥ POOL_MIN 的人。"""
    ok = {k: v for k, v in items.items() if all(np.isfinite(x) for x in v) and v[2] > 0}
    pool = [v for v in ok.values() if v[2] >= POOL_MIN]
    mv, dv = float(np.mean([v[0] for v in pool])), float(np.std([v[0] for v in pool]))
    ma, da = float(np.mean([v[1] for v in pool])), float(np.std([v[1] for v in pool]))
    score = lambda v: w * (v[0] - mv) / dv + (1 - w) * (v[1] - ma) / da
    ps = sorted(score(v) for v in pool)
    sd = float(np.std(ps))
    r99 = min(x for x in ps if _pct(x, ps) >= 99)
    out = {}
    for k, v in ok.items():
        x = score(v)
        p = _pct(x, ps)
        out[k] = (99 + TAIL_PER_SD * (x - r99) / sd) if p >= 99 else _attr(p)
    return out


def build(stats, card):
    """stats＝attr_cell_tips.window_stats 的輸出 → {pid: {'threeValue': attr, 'ft': attr}}（只含有窗口資料者）。
    三分：vol＝tp_a／tp_min×36、acc＝(tp_n＋K_THREE·μ)/(tp_a＋K_THREE)。罰球：acc＝(ft_m＋K_FT·μ)/(ft_a＋K_FT)（w＝0 只看這個；vol 仍算進去但權重為 0）。"""
    mu3 = league_3p(card)
    pa_ = sum(s['tp_a'] for s in stats.values() if s.get('tp_min', 0) >= POOL_MIN)
    pm_ = sum(s['tp_min'] for s in stats.values() if s.get('tp_min', 0) >= POOL_MIN)
    r3 = pa_ / pm_
    t3 = {p: ((s['tp_a'] + K_MIN * r3) / (s['tp_min'] + K_MIN) * 36, (s['tp_n'] + K_THREE * mu3) / (s['tp_a'] + K_THREE), s['tp_min'])
          for p, s in stats.items() if s.get('tp_min', 0) > 0}
    fm = sum(s['ft_m'] for s in stats.values() if 'ft_m' in s)
    fa = sum(s['ft_a'] for s in stats.values() if 'ft_a' in s)
    muf = fm / fa
    tf = {p: (s['fta_36'], (s['ft_m'] + K_FT * muf) / (s['ft_a'] + K_FT), s['min_w'])
          for p, s in stats.items() if s.get('min_w', 0) > 0 and 'fta_36' in s}
    out = {}
    for p, v in blend(t3, W_THREE).items():
        out.setdefault(p, {})['threeValue'] = v
    for p, v in blend(tf, W_FT).items():
        out.setdefault(p, {})['ft'] = v
    return out
