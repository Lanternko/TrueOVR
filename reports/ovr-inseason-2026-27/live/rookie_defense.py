"""新秀賽中防守（2026-10-30 使用者：「一有數據就馬上更新數值，不準的話後面場次自然會回落」）。

用整季累計的防守追蹤表（scripts/fetch_defense_tracking.mjs）照 card 0.2.7 的同一套公式算 onBall／help，新秀一有數據就直接取代起點（w=1）。
公式本身就帶樣本量收縮，所以少量樣本會被拉回平均，不需要另加 k：
- help＝inverse(PLUSMINUS·n/(n+200), CURVE_DEF_RIM)，n＝FGA_LT_06（scripts/build_season_league.js:100-108，夾 40–99）。
- onBall＝E-060 的 r＝zC3＋zB−zT（reports/card-0.1.1+E060-onball-targeting/components.py），收縮常數同 E-060；
  組平均、聯盟平均與 z 的平均／標準差凍結在 2025-26（stability.json stats['2025-26']），尺度才和 card 0.2.7 一致、開季也不會因池太小亂跳。
  r → 屬性：card 0.2.7（E-101 合併池百分位＋頂底尾巴）在 2025-26 的 (r, onBall) 對照做線性內插；超出範圍用 E-101 的尾巴公式（tail-summary.json）。
用法：python -I -X utf8 rookie_defense.py [--check]（--check：拿 2025-26 原始表重算，對照 card 0.2.7 先驗卡）
"""
import bisect
import csv
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E060 = ROOT / 'reports/card-0.1.1+E060-onball-targeting'
TAIL = ROOT / 'reports/card-0.2.5+E101-crossera/tail-summary.json'
M27B = os.environ.get('CARD_MODE', '029a') in ('029a',)  # 027d 能力值同 027b  # E-128：help 改 E-123 D1 尾巴（027b＝預設，R-085；其他模式逐位元不變）
PRIOR_CARD = HERE / ('prior-2025-26-card027b.json' if M27B else 'prior-2025-26-card027.json')
K_C3, K_B, K_T, K_HELP = 500.0, 1000.0, 1000.0, 200.0
CURVE_DEF_RIM = [(0, 0.150), (40, 0.105), (55, 0.050), (70, 0.004), (85, -0.048), (99, -0.095), (120, -0.125), (150, -0.150)]
CEIL, K_SD = 150.0, 1.96


# E-128 §1.3：help 照 E-123 的 D1 換算（reports/card-0.2.7+E123-tail-3pt-rim-pres/work/build_tails.py 的 inverse_open、MIRROR、A99、sH 逐行複製；
# 參數取自該目錄 tail-summary.json 的 e123.help：S=0.050102046475693295、a99=0.095、lo=0.0），凍結使用，不重擬合。
E123_S_HELP = 0.050102046475693295
MIRROR = [(float(a), -float(y)) for a, y in CURVE_DEF_RIM]   # (attr, x)；x = −shrunk


def inverse_open(p, curve, lo, hi):
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(lo, min(hi, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    x = curve[0][0] if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else curve[-1][0]
    return max(lo, min(hi, x))


A99 = inverse_open(99, [(y, a) for a, y in MIRROR], -1e9, 1e9)
SH = K_SD * E123_S_HELP


def help_e123(shrunk):
    """shrunk＝PLUSMINUS·n/(n+200)；x＝−shrunk。x>a99 走頂端尾巴（上限 150、不夾 99），否則反查曲線（下限 0.0）。"""
    x = -shrunk
    if x > A99:
        return 99 + (CEIL - 99) * (1 - math.exp(-(x - A99) / SH))
    return inverse_open(x, MIRROR, 0.0, 99.0)


def help_map(shrunk):
    return help_e123(shrunk) if M27B else inverse(shrunk, CURVE_DEF_RIM)


def table(path):
    d = json.load(open(path, encoding='utf-8'))['data']
    s = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return [dict(zip(s['headers'], r)) for r in s['rowSet']]


def inverse(p, curve):
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if min(y0, y1) <= p <= max(y0, y1):
            return max(40.0, min(99.0, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    return 40.0 if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else 99.0


def help_of(rim_rows):
    out = {}
    for r in rim_rows:
        n, d = r.get('FGA_LT_06'), r.get('PLUSMINUS')
        if n and n > 0 and d is not None:
            out[r['CLOSE_DEF_PERSON_ID']] = help_map(d * n / (n + K_HELP))
    return out


def frozen_stats():
    return json.load(open(E060 / 'stability.json', encoding='utf-8'))['stats']['2025-26']


def onball_acc(tabs):
    """E-060 components.compute 的原始累計量（可加權相加）：{pid: {c3, min, ppu, load, pp, tx0, tx1, pos}}。"""
    adv = {}
    for r in tabs['advanced']:
        u = r.get('USG_PCT')
        if u is not None:
            adv[r['PLAYER_ID']] = u * 100 if u <= 1 else u
    pos = {}
    for r in tabs['three']:
        pos.setdefault(r['CLOSE_DEF_PERSON_ID'], (r['PLAYER_POSITION'] or '').split('-')[0])
    out = {}

    def get(pid):
        return out.setdefault(pid, dict(c3=0.0, min=0.0, ppu=0.0, load=0.0, pp=0.0, tx0=0.0, tx1=0.0, pos=pos.get(pid)))
    for r in tabs['hustle']:
        if r['CONTESTED_SHOTS_3PT'] is None or not r['MIN']:
            continue
        h = get(r['PLAYER_ID'])
        h['c3'] += r['CONTESTED_SHOTS_3PT']; h['min'] += r['MIN']
    pair = {}
    for r in tabs['matchups']:
        d = r['DEF_PLAYER_ID']; a = get(d)
        a['pp'] += r['PARTIAL_POSS'] or 0
        u = adv.get(r['OFF_PLAYER_ID'])
        if u is not None:
            a['ppu'] += r['PARTIAL_POSS'] or 0; a['load'] += (r['PARTIAL_POSS'] or 0) * u
        q = pair.setdefault((d, r['OFF_PLAYER_ID']), [0.0, 0.0])
        q[0] += r['MATCHUP_FGA'] or 0; q[1] += r['PARTIAL_POSS'] or 0
    tot = {}
    for (d, o), (f_, p_) in pair.items():
        t = tot.setdefault(o, [0.0, 0.0]); t[0] += f_; t[1] += p_
    for (d, o), (f_, p_) in pair.items():
        if p_ <= 0:
            continue
        F, P = tot[o]
        if P - p_ <= 0:
            continue
        x = out[d]; x['tx0'] += f_; x['tx1'] += p_ * (F - f_) / (P - p_)
        x['tx'] = True
    for pid in out:
        out[pid]['adv'] = pid in adv
    return out


def acc_sum(parts):
    """[(權重, onball_acc 結果)] → 加權相加；pos 取最新（列表最後）有值的那季，adv／tx 任一季有就算有。"""
    out = {}
    for w, acc in parts:
        for pid, a in acc.items():
            o = out.setdefault(pid, dict(c3=0.0, min=0.0, ppu=0.0, load=0.0, pp=0.0, tx0=0.0, tx1=0.0, pos=None, adv=False, tx=False))
            for k in ('c3', 'min', 'ppu', 'load', 'pp', 'tx0', 'tx1'):
                o[k] += w * a[k]
            o['pos'] = a['pos'] or o['pos']
            o['adv'] = o['adv'] or a['adv']; o['tx'] = o['tx'] or a.get('tx', False)
    return out


def r_of_acc(acc, st, pos_fallback=None):
    """累計量 → E-060 r（組平均／z 用凍結的 st）。回傳 {pid: r}（缺任何一個分量就不給）。"""
    pos_fallback = pos_fallback or {}
    gm, zc, zb, zt, lmb = st['groupMeanC3'], st['zC3'], st['zB'], st['zT'], st['leagueMeanB']
    out = {}
    for pid, m in acc.items():
        g = m['pos'] or pos_fallback.get(pid)
        if not m['adv'] or g not in gm or m['min'] <= 0 or m['ppu'] <= 0 or m['pp'] <= 0 or not m.get('tx'):
            continue
        C3 = (m['min'] * (36 * m['c3'] / m['min']) + K_C3 * gm[g]) / (m['min'] + K_C3)
        B = (m['ppu'] * (m['load'] / m['ppu']) + K_B * lmb) / (m['ppu'] + K_B)
        T = (m['pp'] / (m['pp'] + K_T)) * (100 * (m['tx0'] - m['tx1']) / m['pp'])
        out[pid] = (C3 - zc[g][0]) / zc[g][1] + (B - zb[0]) / zb[1] - (T - zt[0]) / zt[1]
    return out


def comps_of_acc(acc, st, pos_fallback=None):
    """累計量 → E-060 三個收縮後分量與位置組 {pid: (C3, B, T, 組)}（名單頁 PER D 提示卡用；算式同 r_of_acc）。"""
    pos_fallback = pos_fallback or {}
    gm, lmb = st['groupMeanC3'], st['leagueMeanB']
    out = {}
    for pid, m in acc.items():
        g = m['pos'] or pos_fallback.get(pid)
        if not m['adv'] or g not in gm or m['min'] <= 0 or m['ppu'] <= 0 or m['pp'] <= 0 or not m.get('tx'):
            continue
        out[pid] = ((m['min'] * (36 * m['c3'] / m['min']) + K_C3 * gm[g]) / (m['min'] + K_C3),
                    (m['ppu'] * (m['load'] / m['ppu']) + K_B * lmb) / (m['ppu'] + K_B),
                    (m['pp'] / (m['pp'] + K_T)) * (100 * (m['tx0'] - m['tx1']) / m['pp']), g)
    return out


def onball_r(tabs, st, pos_fallback=None):
    return r_of_acc(onball_acc(tabs), st, pos_fallback)


class OnBallScale:
    """r → card 0.2.7 onBall：2025-26 的 (r, onBall) 對照內插；範圍外用 E-101 尾巴。"""

    def __init__(self):
        card = {p['playerId']: p['onBall'] for p in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']}
        pts = {}
        for r in csv.DictReader(open(E060 / 'components-2025-26.csv', encoding='utf-8')):
            pid = int(r['pid'])
            if pid in card and '' not in (r['zC3'], r['zB'], r['zT']):
                pts[float(r['zC3']) + float(r['zB']) - float(r['zT'])] = float(card[pid])
        self.xs = sorted(pts)
        self.ys = [pts[x] for x in self.xs]
        self.tail = json.load(open(TAIL, encoding='utf-8'))['e101']['onBall']

    def __call__(self, r):
        t, xs, ys = self.tail, self.xs, self.ys
        if r > xs[-1]:
            return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, r - t['r99']) / (K_SD * t['S'])))
        if r < xs[0]:
            return 40 - 15 * (1 - math.exp(-max(0.0, t['r1'] - r) / t['SD_pool']))
        i = bisect.bisect_left(xs, r)
        if xs[i] == r:
            return ys[i]
        return ys[i - 1] + (r - xs[i - 1]) / (xs[i] - xs[i - 1]) * (ys[i] - ys[i - 1])


def inseason_comps(season='2026-27', pos_fallback=None):
    """新秀本季的 E-060 分量 {pid: (C3, B, T, 組)}（同 inseason 的 onBall 來源）；沒抓到表回傳 {}。"""
    d = ROOT / 'data/defense-seventh' / season / 'tracking'
    if not all((d / f'{k}.json').exists() for k in KINDS):
        return {}
    return comps_of_acc(onball_acc({k: table(d / f'{k}.json') for k in KINDS}), frozen_stats(), pos_fallback)


def inseason(season='2026-27', pos_fallback=None):
    """{pid: {'onBall': v 或缺, 'help': v 或缺, 'n3': 守三分出手, 'nRim': 守禁區出手}}；沒抓到表回傳 {}。"""
    d = ROOT / 'data/defense-seventh' / season / 'tracking'
    kinds = ('rim', 'three', 'hustle', 'advanced', 'matchups')
    if not all((d / f'{k}.json').exists() for k in kinds):
        return {}
    tabs = {k: table(d / f'{k}.json') for k in kinds}
    scale = OnBallScale()
    out = {}
    for pid, v in help_of(tabs['rim']).items():
        out.setdefault(pid, {})['help'] = v
    for pid, r in onball_r(tabs, frozen_stats(), pos_fallback).items():
        out.setdefault(pid, {})['onBall'] = scale(r)
    for r in tabs['rim']:
        out.get(r['CLOSE_DEF_PERSON_ID'], {}).update(nRim=r['FGA_LT_06'])
    for r in tabs['three']:
        if r['CLOSE_DEF_PERSON_ID'] in out:
            out[r['CLOSE_DEF_PERSON_ID']]['n3'] = r.get('FG3A')
    return out


PAST_RAW = ROOT / 'reports/defense-tenth/step4-t2/raw'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')     # 由舊到新
KINDS = ('rim', 'three', 'hustle', 'advanced', 'matchups')
SLOTS, WIN = 82, 4 * 82


def window_weights(c):
    """E-104 TL 的逐場線性遞減搬到季總計（2026-10-30 使用者：老將防守「用 TUL 類似的做法」，四季窗口）。
    聯盟時間每季 82 格、窗口 328 格，最近一格 u≈1、窗口最舊 u≈0；本季已過 c 格（聯盟已賽場數／1230·82），整個窗口往後推 c 格，
    最舊那季被推出窗口的部分權重 0。追蹤表只有季總計，所以每季的量乘上「該季那段的平均 u」（假設比賽在季內平均分布）。
    再除以整個窗口的權重總和（328 格平均 u＝0.5 → 2 季）。回傳 {季: 權重}。
    實際用時還要再照每人自己有資料的季數正規化（veteran 的 season_units），見 veteran。"""
    w = {}
    if c > 0:
        w['2026-27'] = (WIN - c / 2) / WIN
    for k, s in enumerate(reversed(PAST), 1):
        b = WIN - c - SLOTS * (k - 1)
        a = b - SLOTS
        w[s] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * WIN * SLOTS)
    return {s: v / 2.0 for s, v in w.items()}


def veteran(c, season='2026-27', pos_fallback=None, comps=False, cur=True):
    """老將四季窗口加權的 onBall／help：{pid: {'onBall', 'help'}}（缺分量的不給）；另回傳權重。本季表沒抓到就只用往年四季。
    comps=True 時改回傳 ({pid: (C3, B, T, 組)}, 權重)：同一個窗口累計量的 E-060 分量（名單頁提示卡用）。
    cur=False：同一個 c 的權重但不讀本季表（＝每人本季 0 場時的值；ΔOVR 基準用，R-112）。"""
    parts = []
    for s in PAST:
        parts.append((s, {k: table(PAST_RAW / s / f'0-{k}.json') for k in KINDS}))
    d = ROOT / 'data/defense-seventh' / season / 'tracking'
    if cur and c > 0 and all((d / f'{k}.json').exists() for k in KINDS):
        parts.append((season, {k: table(d / f'{k}.json') for k in KINDS}))
    ww = window_weights(c)
    ww = {s: ww[s] for s, _ in parts if s in ww}
    # 2026-10-30 使用者選 2：有效樣本照每人實際有資料的季數算，不整體 ÷2（只打過一兩季的人不多收縮）。
    # 每人除以自己有資料那幾季的權重和（本季只算已過的 c/82 季）→ 各季量的加權平均；只有 2025-26 的人＝卡片原值。
    # 除數下限＝他各季權重的最大值：只有本季幾場的人不會被放大成超過實際樣本（等於新秀 R-075 的 w=1 本季值）。
    units = {s: ww[s] * (c / SLOTS if s == season else 1.0) for s in ww}
    rim, rim_f = {}, {}
    for s, tabs in parts:
        for r in tabs['rim']:
            n, dd = r.get('FGA_LT_06'), r.get('PLUSMINUS')
            if n and n > 0 and dd is not None:
                pid = r['CLOSE_DEF_PERSON_ID']
                x = rim.setdefault(pid, [0.0, 0.0])
                x[0] += ww[s] * n; x[1] += ww[s] * n * dd
                f = rim_f.setdefault(pid, [0.0, 0.0]); f[0] += units[s]; f[1] = max(f[1], ww[s])
    out = {}
    for pid, (n, nd) in rim.items():
        if n > 0:
            n_eff = n / max(rim_f[pid])
            out.setdefault(pid, {})['help'] = help_map((nd / n) * n_eff / (n_eff + K_HELP))
    accs = [(s, onball_acc(tabs)) for s, tabs in parts]
    acc = acc_sum([(ww[s], a) for s, a in accs])
    ob_f = {}
    for s, a in accs:
        for pid in a:
            f = ob_f.setdefault(pid, [0.0, 0.0]); f[0] += units[s]; f[1] = max(f[1], ww[s])
    for pid, m in acc.items():
        for k in ('c3', 'min', 'ppu', 'load', 'pp', 'tx0', 'tx1'):
            m[k] /= max(ob_f[pid])
    if comps:
        return comps_of_acc(acc, frozen_stats(), pos_fallback), ww
    scale = OnBallScale()
    for pid, r in r_of_acc(acc, frozen_stats(), pos_fallback).items():
        out.setdefault(pid, {})['onBall'] = scale(r)
    return out, ww


def check():
    """2025-26 原始表重算 → 對照 card 0.2.7 先驗卡（help、onBall 都應逐人吻合）。"""
    raw = ROOT / 'reports/defense-tenth/step4-t2/raw/2025-26'
    tabs = {k: table(raw / f'0-{k}.json') for k in ('rim', 'three', 'hustle', 'advanced', 'matchups')}
    card = {p['playerId']: p for p in json.load(open(PRIOR_CARD, encoding='utf-8'))['players']}
    hp = help_of(tabs['rim'])
    rr = onball_r(tabs, frozen_stats())
    scale = OnBallScale()
    dh = [abs(hp[p] - float(card[p]['help'])) for p in card if p in hp]
    do = [abs(scale(rr[p]) - float(card[p]['onBall'])) for p in card if p in rr]
    res = {'help': {'n': len(dh), 'maxAbs': max(dh), 'n>0.1': sum(x > 0.1 for x in dh)},
           'onBall': {'n': len(do), 'maxAbs': max(do), 'n>0.1': sum(x > 0.1 for x in do)}}
    print(json.dumps(res, ensure_ascii=False))
    return res


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--check' in sys.argv:
        check()
    else:
        print(json.dumps(inseason(), ensure_ascii=False)[:2000])
