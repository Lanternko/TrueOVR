"""RIM（護框）顯示欄加蓋帽（E-305 D30，使用者 2026-11-10「上線 D30」，R 號見 rulings）。只改頁面 RIM 欄的數字：
ranking.csv 的 help、OVR／OFF／DEF、T、模擬、卡片都不動（help 進模型的值不變）。

公式（和 reports/E305-rim-blk/e305_rim_blk.py 的 D30 臂逐步相同，每天用當天資料重算，不用凍結快照，L-117）：
- blk36＝四季滑動窗口（含本季）的每 36 分鐘蓋帽，向名次人群平均收縮（等同 200 分鐘，K_MIN）；窗口權重同 rookie_defense.window_weights
  （E-104 窗口搬到季總計）；新秀只有本季＝本季值；卡片頁（c=0）不讀本季。
- 分數 ＝ 0.7·z(help) ＋ 0.3·z(blk36)，z 在名次人群（sn.mpg_pool）內算；合成後在人群內重標準化，再套 help 在同人群的平均與標準差
  （B0＝只有 help 的臂，經此轉換等於現值）。
- 以 playerId 對人；沒有窗口資料的人（卡片頁新秀）回傳空，呼叫端維持原 help。
旗標 RIM_BLK=0 → 回傳空 dict，頁面逐位元等於現行。任何失敗（缺檔、人群太小）也回傳空 dict 並印警告，退回現行 help。
"""
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
STATS = ROOT / 'reports/E227-lineup-transformer-r2/data'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')
CUR = '2026-27'
SLOTS, WIN, G_TOTAL = 82, 4 * 82, 1230
K_MIN = 200.0
W_HELP, W_BLK = 0.7, 0.3
TIP = '籃下 6 呎被防命中率差 70%＋每 36 分蓋帽 30%'


def enabled():
    return os.environ.get('RIM_BLK', '1') != '0'


def weights(c):
    """同 rookie_defense.window_weights（E-104 窗口搬到季總計）；c＝本季已打場數折成的 82 場格數（c=0 不含本季）。"""
    w = {}
    if c > 0:
        w[CUR] = (WIN - c / 2) / WIN
    for k, s in enumerate(reversed(PAST), 1):
        b = WIN - c - SLOTS * (k - 1)
        a = b - SLOTS
        w[s] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * WIN * SLOTS)
    return {s: v / 2.0 for s, v in w.items()}


def _past_tabs():
    """{季: {pid: (分鐘, 蓋帽總數)}}（E227 stats 檔：blk36 × 分鐘 / 36）。"""
    tabs = {}
    for s in PAST:
        t = {}
        for r in csv.DictReader(open(STATS / f'stats-{s}.csv', encoding='utf-8')):
            m = float(r['minutes'] or 0)
            if m > 0:
                t[int(r['pid'])] = (m, float(r['blk36']) * m / 36 if r['blk36'] != '' else 0.0)
        tabs[s] = t
    return tabs


def _cur_tab(player_games, cutoff):
    d = json.loads(Path(player_games).read_text(encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    h = {k: i for i, k in enumerate(t['headers'])}
    out = {}
    for r in t['rowSet']:
        if r[h['GAME_DATE']] > cutoff or not r[h['MIN']]:
            continue
        a = out.setdefault(int(r[h['PLAYER_ID']]), [0.0, 0.0])
        a[0] += r[h['MIN']]
        a[1] += r[h['BLK']] or 0
    return {k: tuple(v) for k, v in out.items()}


def _window(pids, tabs, ww):
    """{pid: (有效分鐘, 蓋帽)}（每人除以自己有資料那幾季的最大權重）。"""
    out = {}
    for p in pids:
        mm = bb = mx = 0.0
        for s, t in tabs.items():
            if p in t and ww.get(s, 0) > 0:
                m, b = t[p]
                mm += ww[s] * m
                bb += ww[s] * b
                mx = max(mx, ww[s])
        if mx > 0:
            out[p] = (mm / mx, bb / mx)
    return out


def compute(help_by_pid, pool, games_done=None, cutoff=None, player_games=None):
    """help_by_pid＝{playerId(int): help 值（進模型的原值）}；pool＝名次人群 playerId 集合；
    games_done／cutoff／player_games 給了＝賽中頁（含本季），否則＝卡片頁（c=0，只看過去四季）。
    回傳 {playerId: RIM 顯示值}，只含有窗口資料的人；旗標關閉或失敗回傳 {}。"""
    if not enabled():
        return {}
    try:
        tabs = _past_tabs()
        if games_done is not None:
            c = SLOTS * games_done / G_TOTAL
            tabs[CUR] = _cur_tab(player_games, cutoff)
        else:
            c = 0.0
        ww = weights(c)
        win = _window(set(help_by_pid), tabs, ww)
        pp = [p for p in pool if p in help_by_pid]
        wp = [p for p in pp if p in win]
        if len(pp) < 50 or len(wp) < 0.9 * len(pp):
            raise RuntimeError(f'人群太小或蓋帽資料缺太多（pool {len(pp)}，有資料 {len(wp)}）')
        mu = sum(win[p][1] for p in wp) / sum(win[p][0] for p in wp)
        blk = {p: (v[1] + K_MIN * mu) / (v[0] + K_MIN) * 36 for p, v in win.items()}
        h = np.array([help_by_pid[p] for p in pp])
        mu_h, sd_h = h.mean(), h.std()
        b = np.array([blk[p] for p in wp])
        mu_b, sd_b = b.mean(), b.std()
        # 人群內沒有資料的人（極少）以 z(blk)＝0 計入人群分數，和 E-305 腳本一致
        score = lambda p: W_HELP * (help_by_pid[p] - mu_h) / sd_h + W_BLK * ((blk[p] - mu_b) / sd_b if p in blk else 0.0)
        ps = np.array([score(p) for p in pp])
        m, s = ps.mean(), ps.std()
        return {p: float(mu_h + sd_h * (score(p) - m) / s) for p in win if p in help_by_pid}
    except Exception as e:  # noqa: BLE001
        print(f'RIM 加蓋帽失敗，退回現行 help：{e}', file=sys.stderr)
        return {}


def apply(rows, disp, pid_of):
    """rows＝ranking.csv 的列（dict，值為字串，有 'help'）；pid_of(row)→playerId（int 或 None）。
    把有顯示值的人的 help 換成 repr(round(v, 1))（原地改）；回傳換了幾人。
    和其他顯示欄一樣在 sn.display_rows 之後套（help 不在 RESCALE_ATTRS，不受顯示尺影響）。"""
    n = 0
    for r in rows:
        v = disp.get(pid_of(r))
        if v is not None and r.get('help', '') != '':
            r['help'] = repr(round(v, 1))
            n += 1
    return n
