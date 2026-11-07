"""能力值格子提示卡（使用者 2026-11-02「其他 attr 的 hover 也補回」）：MID、INS、FT、DRV、FD、PASS、CRT、REB、RIM。
數字取自能力值本身用的窗口（WIN_LEN，預設 246 格＝約三季；近季權重高），顯示窗口內的實際比率（不收縮），PR／名次對頁面名次人群：
- MID／INS／FT／FD／PASS／REB／DRV：window8.Win8 的窗口和（n_w, d_w）；分鐘＝vol 的 d_w×36。
- CRT：window10.Win10 的 crJ（自主出手加權分子，失手照 pu 打折）÷ 窗口分鐘×36；自主比例＝crJ ÷ 窗口出手。
- RIM：NBA.com 籃下 6 呎防守追蹤表，PLUSMINUS（對手命中率比預期）按被出手次數加權；卡片頁只看 2025-26，
  新賽季頁照 rookie_defense.veteran 的季權重（四季＋本季）。
卡片頁＝2025-26 季末窗口（同 Win8.check_season_end）；新賽季頁＝已賽 gamesDone 場的窗口（同 run_c4_live）。
Win8 名單外的人（2026-27 新秀）沒有窗口資料，不給卡。"""
import sys
from pathlib import Path

import numpy as np

import season_nav as sn

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'

# 比率的 PR／名次只比量夠的人（量用同一卡的 per36 或每場數）：(量的鍵, 門檻)
SPECS = {
    'mid': ('中距離', 'MID', '油漆區外到三分線內的<b>命中率與出手量</b>',
            [('命中率', 'mid_pct', '{:.1%}', False, ('mid_36', 1.0)), ('出手量', 'mid_36', '{:.1f}/36', False, None)]),
    'short': ('近框', 'INS', '油漆區內（含籃下，約 15 呎內）的<b>命中率與出手量</b>',
              [('命中率', 'short_pct', '{:.1%}', False, ('short_36', 1.0)), ('出手量', 'short_36', '{:.1f}/36', False, None)]),
    'ft': ('罰球', 'FT', '<b>罰球命中率</b>（罰球沒有防守，只看準度；量已在造犯規）',
           [('命中率', 'ft_pct', '{:.1%}', False, ('fta_36', 1.0)), ('罰球量', 'fta_36', '{:.1f}/36', False, None)]),
    'drive': ('切入', 'DRV', '<b>帶球切入</b>到 10 呎內的自主兩分，量與效率各半',
              [('切入量', 'drive_36', '{:.1f}/36', False, None), ('每次得分', 'drive_eff', '{:.2f} 分', False, ('drive_36', 0.5))]),
    'foulDraw': ('製造犯規', 'FD', '<b>75%</b> 罰球量 ＋ <b>25%</b> 罰球率',
                 [('罰球量', 'fta_36', '{:.1f}/36', False, None), ('罰球率', 'fta_rate', '{:.1%}', False, ('fga_36', 3.0))]),
    'pass': ('傳球', 'PASS', '<b>50%</b> 助攻量 ＋ <b>50%</b> 助攻率',
             [('助攻量', 'ast_36', '{:.1f}/36', False, None), ('助攻率', 'ast_rate', '{:.1%}', False, None)]),
    'creation': ('自主創造', 'CRT', '<b>自己創造</b>的跳投與低位出手（不含切入上籃、補籃、空切）',
                 [('自主出手', 'crj_36', '{:.1f}/36', False, None), ('佔總出手', 'crj_share', '{:.0%}', False, ('fga_36', 3.0))]),
    'rebound': ('籃板', 'REB', '在場時搶下可搶籃板的<b>籃板率</b>',
                [('籃板率', 'reb_rate', '{:.1%}', False, None), ('籃板量', 'reb_36', '{:.1f}/36', False, None)]),
    'help': ('護框', 'RIM', '對手在<b>籃下 6 呎內</b>的命中率比預期低多少',
             [('對手命中差', 'rim_diff', '{:+.1%}', True, ('rim_pg', 2.0)), ('護框次數', 'rim_pg', '{:.1f}/場', False, None)]),
}
VOL_NOTE = {'mid_36': '中距離出手', 'short_36': '近框出手', 'fta_36': '罰球', 'drive_36': '切入', 'fga_36': '出手', 'rim_pg': '護框次數'}


def _div(n, d):
    return np.where(d > 0, n / np.where(d > 0, d, 1), np.nan)


def window_stats(card, games_done=None):
    """{pid: {指標: 值}}。card=True：2025-26 季末窗口；False：新賽季已賽 games_done 場的窗口（meta.window8.gamesDone）。"""
    sys.path.insert(0, str(LIVE))
    import window10 as W10
    import rookie_defense as RD
    import win_len
    win_len.install()   # E-204：提示卡的窗口值跟線上同一個 WIN_LEN
    W = W10.Win10()
    D = W.D
    if card:
        S, G = W10.PRIOR, D.G[W10.PRIOR]
        g = G
        s8 = {a: W.sums(a, G, D.tab[S][a], G, S) for a in W10.W8.ORDER}
        s10 = {a: W.sums10(a, G, W.T10[S], G, S) for a in ('crJ', 'cr')}
    else:
        tabs, gd = W.cur_tabs()
        g, G, S = min(gd, games_done), W10.G_TOTAL, W10.TARGET
        s8 = {a: W.sums(a, g, tabs[a], G, S) for a in W10.W8.ORDER}
        s10 = {a: W.sums10(a, g, tabs, G, S) for a in ('crJ', 'cr')}
    r = lambda a: _div(*s8[a])
    mn36 = s8['vol'][1]                         # 窗口分鐘 / 36
    per36 = lambda n: _div(n, mn36)
    m = {'mid_pct': r('mid'), 'mid_36': per36(s8['mid'][1]), 'short_pct': r('short'), 'short_36': per36(s8['short'][1]),
         'ft_pct': r('ft'), 'fta_36': r('vol'), 'fta_rate': r('foulDraw'), 'fga_36': per36(s8['foulDraw'][1]),
         'drive_36': 36 * r('driveVol'), 'drive_eff': r('driveEff'), 'ast_36': r('astvol'), 'ast_rate': r('pass'),
         'reb_rate': r('rebound'), 'reb_36': per36(s8['rebound'][0]),
         'crj_36': 36 * _div(*s10['crJ']), 'crj_share': _div(s10['crJ'][0], s10['cr'][0]),
         # R-168 混合顯示值原料（blend_display.py）：罰球窗口 FTM／FTA／分鐘、三分窗口難度調整分子／加權 3PA／加權 MIN
         'ft_m': s8['ft'][0], 'ft_a': s8['ft'][1], 'min_w': mn36 * 36}
    if card:
        tp = W.tv_raw(G, W.T10[S], S, G)
    else:
        tp = W.tv_raw(g, tabs)
    m.update(tp_n=tp[0], tp_a=tp[1], tp_min=tp[2])
    out = {}
    for p, i in D.pidx.items():
        if mn36[i] > 0:
            out[int(p)] = {k: float(v[i]) for k, v in m.items() if np.isfinite(v[i])}
    # RIM：籃下 6 呎防守（每季總計表）
    if card:
        parts = [(1.0, RD.table(RD.PAST_RAW / '2025-26' / '0-rim.json'))]
    else:
        ww = RD.window_weights(RD.SLOTS * g / G)
        parts = [(ww[s], RD.table(RD.PAST_RAW / s / '0-rim.json')) for s in RD.PAST if ww.get(s, 0) > 0]
        cur = ROOT / 'data/defense-seventh/2026-27/tracking/rim.json'
        if g > 0 and cur.exists():
            parts.append((ww['2026-27'], RD.table(cur)))
    acc = {}
    for w, rows in parts:
        for x in rows:
            n, dd, gp = x.get('FGA_LT_06'), x.get('PLUSMINUS'), x.get('GP')
            if n and dd is not None and gp:
                a = acc.setdefault(int(x['CLOSE_DEF_PERSON_ID']), [0.0, 0.0, 0.0])
                a[0] += w * n; a[1] += w * n * dd; a[2] += w * gp
    for p, (n, nd, gp) in acc.items():
        if p in out and n > 0:
            out[p].update(rim_diff=nd / n, rim_pg=n / gp)
    return out

NEAR_RIM_FT = 5.0     # 低位：距離 < 5 呎（含座標佔位的補籃／灌籃），和 NBA.com Less Than 5 ft 同口徑（Wemby 2026-27 7 場 49/69＝71.0% 對上）
UNDER_RIM_FT = 2.0    # 籃下：距離 < 2 呎（含座標佔位）
TAP_DESC = ('tip', 'putback')    # 補籃：pbp descriptor；補籃優先於上籃／灌籃，不重複算


def season_near_rim():
    """本季（只看 2026-27，不含過去三季）近框出手細項，直接讀 pbp：{pid: {'gp', 'short', 'low', 'under', 'layup', 'dunk', 'tap'}}，
    各項 [出手, 命中]；'short' 同 window8._zone 的近框區（F-157 佔位座標歸近框）。低位／籃下不限區域；上籃／灌籃／補籃依 subType／descriptor，距離不限。"""
    import json
    sys.path.insert(0, str(LIVE))
    import window8 as W8
    d26 = ROOT / 'data/defense-seventh/2026-27'
    gp, games = {}, set()
    for r in W8._rows(d26 / 'player-games.json'):
        if r['MIN']:
            gp[int(r['PLAYER_ID'])] = gp.get(int(r['PLAYER_ID']), 0) + 1
            games.add(r['GAME_ID'])
    acc = {}
    for g in sorted(games):
        f = d26 / 'pbp' / f'{g}.json'
        if not f.exists():
            continue
        for a in json.loads(f.read_text(encoding='utf-8'))['data']['game']['actions']:
            if a.get('actionType') != '2pt' or a.get('isFieldGoal') != 1 or not a.get('personId'):
                continue
            d, x, y = a.get('shotDistance'), a.get('xLegacy'), a.get('yLegacy')
            ph = x == 0 and y == 0 and d == 0           # 佔位座標（99.5% 是上籃／灌籃／補籃）
            dist = 0.0 if ph else d
            made = a.get('shotResult') == 'Made'
            tap = (a.get('descriptor') or '') in TAP_DESC
            st = a.get('subType')
            flags = {'short': W8._zone(a) == 1,
                     'low': dist is not None and dist < NEAR_RIM_FT,
                     'under': dist is not None and dist < UNDER_RIM_FT,
                     'layup': st == 'Layup' and not tap, 'dunk': st == 'DUNK' and not tap, 'tap': tap}
            v = acc.setdefault(int(a['personId']), {k: [0, 0] for k in flags})
            for k, on in flags.items():
                if on:
                    v[k][0] += 1
                    v[k][1] += made
    return {p: dict(v, gp=gp[p]) for p, v in acc.items() if p in gp}


NEAR_RIM_ROWS = [('short', '本季近框'), ('low', '　低位（5 呎內）'), ('under', '　籃下（2 呎內）'),
                 ('layup', '　上籃'), ('dunk', '　灌籃'), ('tap', '　補籃（tip／putback）')]
NEAR_RIM_FOOT = '本季＝只算 2026-27 已賽場次，不含過去三季；低位同 NBA.com Less Than 5 ft；上籃／灌籃／補籃依出手動作分類，補籃優先、不重複算'


def near_rim_rows(s):
    """s＝season_near_rim() 的單人資料 -> 提示卡列（無 PR／名次）；出手 0 的細項不列。"""
    rows = []
    for k, lab in NEAR_RIM_ROWS:
        a, m = s[k]
        if a:
            rows.append((lab, f'{m / a:.0%} · {m}/{a} · {a / s["gp"]:.1f}/場', None, None))
    return rows


def build(stats, pool, season=None):
    """{pid: {attr: (rows, foot)}}；pool＝名次人群（pid 集合）。season＝season_near_rim() 結果時，INS 提示卡多列本季近框細項。"""
    P = [stats[p] for p in pool if p in stats]
    out = {}
    for attr, (_, _, _, items) in SPECS.items():
        dist = {}
        for _, k, _, low, vm in items:
            dist[k] = [s[k] for s in P if k in s and (vm is None or s.get(vm[0], 0) >= vm[1])]
        for p, s in stats.items():
            if not all(k in s for _, k, _, _, _ in items):
                continue
            inpool = p in pool
            rows, foot = [], []
            for lab, k, fmt, low, vm in items:
                ok = vm is None or s.get(vm[0], 0) >= vm[1]
                pr, rk = sn.pr_rank(s[k], dist[k], low) if ok and dist[k] else (None, None)
                rows.append((lab, fmt.format(s[k]), pr, rk if inpool else None))
                if vm:
                    foot.append(f'{lab}名次只比{VOL_NOTE[vm[0]]}{" ≥ %g" % vm[1]}{"/場" if vm[0] == "rim_pg" else "/36"} 的人')
            if attr == 'short' and season and p in season and season[p]['short'][0]:
                rows += near_rim_rows(season[p])
                foot = foot + [NEAR_RIM_FOOT]
            out.setdefault(p, {})[attr] = (rows, foot + ([] if inpool else [sn.NO_RANK_FOOT]))
    return out


def tip(attr, v, sub, note):
    n, s, d, _ = SPECS[attr]
    rows, foot = sub
    return sn.cell_tip(n, s, round(v), rows, d=d, foot=foot)
