"""無球兩格（E-301 V 臂，使用者 2026-11-10「做上網站」）：SPOT 空檔射手、CUT 切入順下。只顯示，不進 OVR／OFF／T。
定義（prereg 凍結，不再調）：
  SPOT＝[z(定點 spotup/36)+z(繞掩護 offScreen/36)+z(手遞手 handoff/36)+0.5·z(接球三分%)] / 3.5
  CUT ＝[z(空切 cut/36)+z(順下 PRRollman/36)+z(補籃 OffRebound/36)+z(快攻 Transition/36)+0.5·z(空切每回合得分)] / 4.5
  每 36＝Synergy 回合 ÷ player-games 分鐘；空切得分＝(PTS+30·聯盟)/(POSS+30)；接球三分＝(FG3M+50·聯盟)/(FG3A+50)。
  Synergy 沒列名＝0 回合、空切得分＝聯盟平均；沒有 CatchShoot＝聯盟平均。
窗口：同 pnr（rookie_defense.window_weights(c)＋win_len 246 格＝近三季滑動含本季，每人除以自己有資料那幾季的權重和、下限＝最大單季權重）；
  卡片頁 2025-26＝c=0 不讀本季；新秀只有本季＝本季值。E-301 驗的是單季定義，窗口只是把量平滑（同站上其他能力值）。
尺：各欄 z 用有效分鐘 ≥200 的人；合成後再 z；百分位人群＝有效分鐘 ≥1000（E-301 母體）；0–99＝attr(PR) 再 display_scale。
  頂端（使用者 2026-11-10「為何最高是 97 不是 99 然後可以超過」）：PR≥99 改走同 3PT 的百分位尾巴
  （run_c4_live.m26_top_tail：99＋(150−99)(1−e^(−(z−r99)/(1.96·S)))，S＝max((r99−r90)/1.044, SD)），display_scale 再 −2。
資料：過去季 reports/E239-tracking-full/data/；本季 data/tracking-cells/2026-27/（daily_inseason_update 每天跑 fetch_tracking_cells.mjs）。"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import season_nav as sn  # noqa: E402

PAST_DIR = ROOT / 'reports/E239-tracking-full/data'
CUR, CUR_DIR = '2026-27', ROOT / 'data/tracking-cells/2026-27'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')
PG = {s: ROOT / f'data/defense-seventh/{s}/player-games.json' for s in PAST[:-1]}
PG['2025-26'] = ROOT / 'data/season-source/player-games.json'
PG[CUR] = ROOT / 'data/season-source-2026-27/player-games.json'
SYN = {'spot': 'Spotup', 'offscr': 'OffScreen', 'hand': 'Handoff', 'cut': 'Cut', 'roll': 'PRRollman', 'putback': 'OffRebound', 'trans': 'Transition'}
W = {'SPOT': {'spot': 1, 'offscr': 1, 'hand': 1, 'cs3pct': 0.5},
     'CUT': {'cut': 1, 'roll': 1, 'putback': 1, 'trans': 1, 'cutppp': 0.5}}
K_CUT, K_CS, Z_MIN, PR_MIN = 30.0, 50.0, 200.0, 1000.0
TAIL_CEIL, TAIL_K_SD, TAIL_Z9990 = 150.0, 1.96, 1.044   # 同 run_c4_live.M26_*
LAB = {'spot': '定點投籃', 'offscr': '繞掩護接球', 'hand': '手遞手', 'cs3pct': '接球三分',
       'cut': '空切', 'roll': '擋拆順下', 'putback': '進攻籃板補籃', 'trans': '快攻', 'cutppp': '空切每回合得分'}
HEAD = {'SPOT': ('空檔射手', 'SPOT', '<b>不持球</b>時接球投籃的量（定點、繞掩護、手遞手）與接球三分準度'),
        'CUT': ('切入順下', 'CUT', '<b>不持球</b>時往籃下跑的量（空切、擋拆順下、補籃、快攻）與空切效率')}


def _tab(path):
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding='utf-8'))
    d = d.get('data', d)
    t = d['resultSets'] if 'resultSets' in d else d
    t = t[0] if isinstance(t, list) else t
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


def _mins(pg):
    rows = _tab(pg)
    c = Counter()
    for r in rows or []:
        v = r['MIN']
        m = (int(v.split(':')[0]) + int(v.split(':')[1]) / 60) if isinstance(v, str) and ':' in v else float(v or 0)
        if m > 0:
            c[int(r['PLAYER_ID'])] += m
    return c


def season_counts(s):
    """{pid: {量: 季總數, 'min'}}；Synergy 跨隊列相加。本季檔不在就回 None。"""
    d = CUR_DIR if s == CUR else PAST_DIR
    mins = _mins(PG[s])
    if not mins:
        return None
    out = {p: Counter(min=m) for p, m in mins.items()}
    for k, t in SYN.items():
        rows = _tab(d / f'syn-{t}-{s}.json')
        if rows is None:
            return None
        for r in rows:
            p = int(r['PLAYER_ID'])
            if p in out:
                out[p][k] += float(r['POSS'] or 0)
                if k == 'cut':
                    out[p]['cutpts'] += float(r['PTS'] or 0)
    rows = _tab(d / f'pt-CatchShoot-{s}.json')
    if rows is None:
        return None
    for r in rows:
        p = int(r['PLAYER_ID'])
        if p in out:
            out[p]['fg3a'] += float(r['CATCH_SHOOT_FG3A'] or 0)
            out[p]['fg3m'] += float(r['CATCH_SHOOT_FG3M'] or 0)
    return out


def window(c, cur=True):
    """{pid: 有效量 Counter}（同 pnr_live.window 的每人正規化）、權重、有沒有用到本季。"""
    sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
    import rookie_defense as RD
    import win_len
    win_len.install()   # 同 pnr_live／attr_cell_tips：線上 WIN_LEN 246（近三季）
    ww = RD.window_weights(c)
    seasons = [s for s in PAST if ww.get(s, 0) > 1e-9]
    if cur and c > 0 and ww.get(CUR, 0) > 1e-9:
        seasons.append(CUR)
    acc, den, wmax, used = {}, Counter(), Counter(), []
    for s in seasons:
        tab = season_counts(s)
        if tab is None:
            continue
        used.append(s)
        w = ww[s]; u = w * (c / 82.0 if s == CUR else 1.0)
        for p, x in tab.items():
            a = acc.setdefault(p, Counter())
            for k, v in x.items():
                a[k] += w * v
            den[p] += u; wmax[p] = max(wmax[p], w)
    eff = {p: Counter({k: v / max(den[p], wmax[p]) for k, v in a.items()}) for p, a in acc.items()}
    return eff, {s: round(ww[s], 4) for s in used}


def _tail(d, S):
    return 99 + (TAIL_CEIL - 99) * (1 - np.exp(-max(0.0, d) / (TAIL_K_SD * S)))


def _pct(x, ref):
    return 100.0 * (np.searchsorted(ref, x, 'left') + np.searchsorted(ref, x, 'right')) / 2 / len(ref)


def _attr(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def compute(c, cur=True):
    """{pid: {'SPOT', 'CUT'（0–99 顯示尺）, 'raw': {欄: 原值}, 'min'}}、資訊。"""
    eff, ww = window(c, cur)
    eff = {p: x for p, x in eff.items() if x['min'] > 0}
    lg_cut = sum(x['cutpts'] for x in eff.values()) / max(sum(x['cut'] for x in eff.values()), 1e-9)
    lg_cs = sum(x['fg3m'] for x in eff.values()) / max(sum(x['fg3a'] for x in eff.values()), 1e-9)
    raw = {}
    for p, x in eff.items():
        r = {k: 36 * x[k] / x['min'] for k in SYN}
        r['cutppp'] = (x['cutpts'] + K_CUT * lg_cut) / (x['cut'] + K_CUT)
        r['cs3pct'] = (x['fg3m'] + K_CS * lg_cs) / (x['fg3a'] + K_CS)
        r['cutposs'], r['fg3a'] = x['cut'], x['fg3a']
        raw[p] = r
    zp = [p for p, x in eff.items() if x['min'] >= Z_MIN]
    z = {}
    for k in list(SYN) + ['cutppp', 'cs3pct']:
        v = np.array([raw[p][k] for p in zp]); mu, sd = v.mean(), v.std()
        z[k] = {p: (raw[p][k] - mu) / sd for p in raw}
    out = {p: {'raw': raw[p], 'min': eff[p]['min']} for p in raw}
    for cell, w in W.items():
        comp = {p: sum(z[k][p] * x for k, x in w.items()) / sum(w.values()) for p in raw}
        v = np.array([comp[p] for p in zp]); mu, sd = v.mean(), v.std()
        ref = np.sort([(comp[p] - mu) / sd for p, x in eff.items() if x['min'] >= PR_MIN])
        r90 = min(v for v in ref if _pct(v, ref) >= 90)
        r99 = min(v for v in ref if _pct(v, ref) >= 99)
        S = max((r99 - r90) / TAIL_Z9990, float(ref.std()))
        for p in raw:
            zz = (comp[p] - mu) / sd
            pr = float(_pct(zz, ref))
            a = _tail(zz - r99, S) if pr >= 99 else _attr(max(1.0, pr))
            out[p][cell] = round(float(sn.display_scale(a)), 1)
            out[p]['z' + cell] = float(zz)
    return out, {'weights': ww, 'lgCutPPP': round(lg_cut, 3), 'lgCs3': round(lg_cs, 3), 'nZ': len(zp),
                 'nPR': sum(x['min'] >= PR_MIN for x in eff.values())}


def tips(cells, pool, note):
    """{pid: {'spot': tip, 'cutroll': tip}}；pool＝名次人群（pid 集合，同其他提示卡）。"""
    dist = {k: [cells[p]['raw'][k] for p in pool if p in cells] for k in LAB}
    out = {}
    for p, o in cells.items():
        inpool = p in pool
        t = {}
        for cell, key in (('SPOT', 'spot'), ('CUT', 'cutroll')):
            rows = []
            for k in W[cell]:
                x = o['raw'][k]
                pr, rk = sn.pr_rank(x, dist[k]) if dist[k] else (None, None)
                if k == 'cs3pct':
                    val = f'{x:.1%}（{o["raw"]["fg3a"]:.0f} 投）' if o['raw']['fg3a'] >= 1 else '—（沒有接球三分）'
                elif k == 'cutppp':
                    val = f'{x:.2f}（{o["raw"]["cutposs"]:.0f} 回合）' if o['raw']['cutposs'] >= 1 else '—（沒有空切）'
                else:
                    val = f'{x:.1f}/36'
                rows.append((LAB[k], val, pr, rk if inpool else None))
            n, s, d = HEAD[cell]
            foot = ['回合／36＝Synergy 每 36 分鐘回合數；命中率、得分已向聯盟平均收縮', '只顯示，不進 OVR' + note]
            if not inpool:
                foot.append(sn.NO_RANK_FOOT)
            t[key] = sn.cell_tip(n, s, round(o[cell]), rows, d=d, foot=foot)
        out[p] = t
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    c = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    cells, info = compute(c, cur=c > 0)
    print(info)
    names = {}
    for s in ('2025-26', CUR):
        for r in _tab(PG[s]) or []:
            names[int(r['PLAYER_ID'])] = r['PLAYER_NAME']
    for cell in ('SPOT', 'CUT'):
        top = sorted((p for p in cells if cells[p]['min'] >= PR_MIN), key=lambda p: -cells[p][cell])[:12]
        print(cell, [(names.get(p, p), cells[p][cell]) for p in top])
