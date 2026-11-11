"""inseason／card 0.2.12（R-139，E-203）：賽中端 tovSkill 改用持球時間（E-202 KT 臂）。
  定義（預註冊 E-202 §1，卡片端 reports/card-0.2.10j+E202-to-possession/tov_raw.py）：
    r  = shrink_to(n_w, pm_w, t, K=64)       n_w＝window8 的窗口加權失誤；pm_w＝Σ_季 TOP_季 ×（該人該季窗口權重分鐘 ÷ 該季分鐘）
    v  = pm_w ÷ 窗口加權出賽分鐘 × 36；沒有任何持球資料（pm_w＝0）＝池第 10 百分位（topMissing）
    raw = 0.5·z(−r) + 0.5·z(v)；0–99＝凍結池上的 PctMapper（兩端尾巴照卡片 h1）
  t（歷史目標）、K、z 的平均與標準差、池的 raw 分布、v 的第 10 百分位全部凍結在 tov-pool-card0212.json（仿 gravity-pool-card0210j.json）。
  持球分鐘來源：過去季＝reports/handle-E069/raw/<季>/Possessions-FULL.json（同卡片端）；本季＝data/defense-seventh/2026-27/possessions.json
  （scripts/fetch_possessions.mjs 每天抓整季累計；失敗沿用上一份；固定讀最新那份，歷史日重算也一樣，同 gravity.json）。
  本季 TOP 乘的比例＝本季窗口加權分鐘 ÷ 本季到今天的總分鐘。
  新秀（不在卡片名單）：t＝凍結的同位置先驗，用本季整季 TOV／MIN／TOP（不套窗口權重），把握不足時與起點 x0 漸進混合（見 rookie_tov）。
用法：python -I -B -X utf8 tov_live.py freeze   產生凍結檔並核對對卡片 tov-raw.csv 逐位元重現。
開關：TOV_POSS=0 時 window8／run_c4_live_rookie 完全不 import 本檔（重現 0.2.11）。"""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
import e175_lib as L  # noqa: E402

TOUCH = os.environ.get('TOV_TOUCH', '1') != '0'     # 0.2.12c（R-144，E-207）：r 的分母改觸球次數；TOV_TOUCH=0 重現 0.2.12b（凍結檔、先驗、usage 讀 _retired/）
FROZEN = HERE / ('tov-pool-card0212c.json' if TOUCH else '_retired/tov-pool-card0212.json')
CARD = ROOT / ('reports/card-0.2.12c-w246' if TOUCH else 'reports/card-0.2.12-tov')
RAW = ROOT / 'reports/handle-E069/raw'
CUR_FILE = ROOT / 'data/defense-seventh/2026-27/possessions.json'
K, KH, LAM = 64, 256, 0.2
RAMP_MIN = 300.0           # 新秀：新定義的權重隨本季分鐘線性遞增，≥ 此值才全用（R-142，使用者 2026-11-02「300 分鐘就夠」；原 1000）
RND = 9
_CACHE = {}


def _top_file(season):
    return CUR_FILE if season == '2026-27' else RAW / season / 'Possessions-FULL.json'


def top_rows(season, col='TIME_OF_POSS'):
    """{playerId: TIME_OF_POSS 分鐘（col='TOUCHES' 則為觸球次數）}（同卡片端 trk_top 的加總方式）。檔不存在＝{}。"""
    p = _top_file(season)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding='utf-8'))['data']['resultSets']
    rs = d[0] if isinstance(d, list) else d
    h = rs['headers']
    ip, it = h.index('PLAYER_ID'), h.index(col)
    out = {}
    for r in rs['rowSet']:
        out[int(r[ip])] = out.get(int(r[ip]), 0.0) + float(r[it] or 0)
    return out


def top_arr(season, D, col='TIME_OF_POSS'):
    key = (season, col, str(_top_file(season).stat().st_mtime) if _top_file(season).exists() else '')
    if key not in _CACHE:
        top = np.zeros(D.NP)
        for pid, v in top_rows(season, col).items():
            i = D.pidx.get(pid)
            if i is not None:
                top[i] += v
        _CACHE[key] = top
    return _CACHE[key]


# ------------------------------------------------------------------ 凍結
def freeze_touch():
    """0.2.12c（W246 重擬合，2026-11-02）：凍結觸球分母臂；card_chain 以 328 建池／映射器後 L.WIN 改 246，
    窗口觸球、z 平均與標準差、池 raw 分布、v_p10 皆 W246（reports/card-0.2.12c-fit246/tov_raw246.py）。
    CARD/tov-raw.csv／info 由 card-0.2.12c-w246/build_0212c.py 放入；這裡重算 t、ρ、W246 窗口觸球，逐位核對 tovSkill。"""
    import shutil
    sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
    import e175_card as C
    E206 = ROOT / 'reports/card-0.2.12+E206-to-touches'
    CARD.mkdir(parents=True, exist_ok=True)
    pass  # tov-raw.csv／info 由 card-0.2.12c-w328/build_0212c.py 放進 CARD
    pass
    D = L.Data(); inp = C.load_inputs()
    out = C.card_chain(D, inp, 'U')
    pids = inp['pids']; ix = np.array([D.pidx[p] for p in pids]); pos_card = [inp['cards'][p]['pos'] for p in pids]
    L.WIN = 246     # card_chain 之後才改（同 tov_raw246.py）
    cur = L.TEST; G = D.G[cur]
    top_cur = top_arr(cur, D); tch_cur = top_arr(cur, D, 'TOUCHES')
    rho = float(tch_cur[ix].sum() / top_cur[ix].sum())
    tov_cur = D.tab[cur]['tovSkill'].agg()[0]
    m = L.prior_vec(tov_cur[ix], tch_cur[ix], 'position', pos_card)
    hn, hd = np.zeros((3, D.NP)), np.zeros((3, D.NP))
    for j in range(3):
        hs = L.SEASONS[L.SEASONS.index(cur) - 1 - j]
        hn[j] = D.tab[hs]['tovSkill'].agg()[0]; hd[j] = top_arr(hs, D, 'TOUCHES')
    t = L.hist_target(hn[:, ix], hd[:, ix], m, LAM, KH * rho)
    # W246 窗口（c＝SLOTS）的觸球：同 E-206 tov_raw.py
    w = L.window_w(L.SLOTS * G / G)
    tc_w = np.zeros(D.NP)
    for s in [cur] + [L.SEASONS[L.SEASONS.index(cur) - k] for k in (1, 2, 3)]:
        tch = top_arr(s, D, 'TOUCHES')
        min_s = D.tab[s]['vol'].agg()[1] * 36
        if s == cur:
            tab = D.tab[s]['tovSkill']; tv = D.tab[s]['vol']
            u = (L.WIN - L.SLOTS + L.SLOTS * (tab.gi + 0.5) / G) / L.WIN
            mw = tv.agg(0, G, w=u)[1] * 36
        else:
            mw = w[L.SEASONS.index(cur) - L.SEASONS.index(s)] * min_s
        tc_w += tch * np.divide(mw, min_s, out=np.zeros(D.NP), where=min_s > 0)
    rows = list(csv.DictReader(open(CARD / 'tov-raw.csv', encoding='utf-8')))
    info = json.loads((CARD / 'tov-raw-info.json').read_text(encoding='utf-8'))
    assert [int(r['playerId']) for r in rows] == [int(p) for p in pids], '卡片名單順序與 tov-raw.csv 不同'
    pool = [i for i, r in enumerate(rows) if r['inPool'] == '1']
    r_ = np.array([float(r['r']) for r in rows]); v_ = np.array([float(r['v']) for r in rows])
    raw = np.array([float(r['raw']) for r in rows])
    mu_r, sd_r = float((-r_[pool]).mean()), float((-r_[pool]).std())
    mu_v, sd_v = float(v_[pool].mean()), float(v_[pool].std())
    pos_m = {}
    for p in sorted(set(pos_card)):
        pos_m[p] = float(m[pos_card.index(p)])
    doc = {'version': 'card 0.2.12c', 'denom': 'touch', 'rho': rho, 'K': K * rho, 'KH': KH * rho, 'pool_raw': [float(x) for x in raw[pool]],
           'top': bool(info['h1_tov']['top']), 'bot': bool(info['h1_tov']['bot']),
           'mu_r': mu_r, 'sd_r': sd_r, 'mu_v': mu_v, 'sd_v': sd_v, 'v_p10': float(info['v_p10']),
           't': {str(int(p)): float(t[i]) for i, p in enumerate(pids)}, 'pos_m': pos_m,
           'source': {'tov_raw_csv_sha256': hashlib.sha256((CARD / 'tov-raw.csv').read_bytes()).hexdigest(), 'pool_n': len(pool), 'window': 246}}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    F = frozen(reload=True)
    n = np.array([float(r['n_w']) for r in rows]); d = np.array([float(r['possMin_w']) for r in rows]); Tm = np.array([float(r['min_w']) for r in rows])
    got = map_values(F, [str(int(p)) for p in pids], n, d, Tm, tc=tc_w[ix])
    want = np.array([float(r['tovSkill']) for r in rows])
    diff = float(np.abs(got - want).max())
    assert diff < 1e-6, f'凍結池無法重現 W246 tovSkill：max|diff|={diff}'
    print('freeze_touch OK pool', len(pool), 'players', len(pids), 'rho', rho, 'max|diff|', diff)


def freeze():
    if TOUCH:
        return freeze_touch()
    sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
    import e175_card as C
    D = L.Data(); inp = C.load_inputs()
    out = C.card_chain(D, inp, 'U')
    pids = inp['pids']; ix = np.array([D.pidx[p] for p in pids]); pos_card = [inp['cards'][p]['pos'] for p in pids]
    cur = L.TEST
    top_cur = top_arr(cur, D)
    tov_cur = D.tab[cur]['tovSkill'].agg()[0]
    m = L.prior_vec(tov_cur[ix], top_cur[ix], 'position', pos_card)
    hn, hd = np.zeros((3, D.NP)), np.zeros((3, D.NP))
    for j in range(3):
        hs = L.SEASONS[L.SEASONS.index(cur) - 1 - j]
        hn[j] = D.tab[hs]['tovSkill'].agg()[0]; hd[j] = top_arr(hs, D)
    t = L.hist_target(hn[:, ix], hd[:, ix], m, LAM, KH)
    rows = list(csv.DictReader(open(CARD / 'tov-raw.csv', encoding='utf-8')))
    info = json.loads((CARD / 'tov-raw-info.json').read_text(encoding='utf-8'))
    assert [int(r['playerId']) for r in rows] == [int(p) for p in pids], '卡片名單順序與 tov-raw.csv 不同'
    pool = [i for i, r in enumerate(rows) if r['inPool'] == '1']
    r_ = np.array([float(r['r']) for r in rows]); v_ = np.array([float(r['v']) for r in rows])
    raw = np.array([float(r['raw']) for r in rows])
    mu_r, sd_r = float((-r_[pool]).mean()), float((-r_[pool]).std())
    mu_v, sd_v = float(v_[pool].mean()), float(v_[pool].std())
    pos_m = {}
    for p in sorted(set(pos_card)):
        i = pos_card.index(p)
        pos_m[p] = float(m[i])
    doc = {'version': 'card 0.2.12', 'K': K, 'pool_raw': [float(x) for x in raw[pool]],
           'top': bool(info['h1_tov']['top']), 'bot': bool(info['h1_tov']['bot']),
           'mu_r': mu_r, 'sd_r': sd_r, 'mu_v': mu_v, 'sd_v': sd_v, 'v_p10': float(info['v_p10']),
           't': {str(int(p)): float(t[i]) for i, p in enumerate(pids)}, 'pos_m': pos_m,
           'source': {'tov_raw_csv_sha256': hashlib.sha256((CARD / 'tov-raw.csv').read_bytes()).hexdigest(), 'pool_n': len(pool)}}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    # 核對：用凍結值重算卡片 tovSkill，逐位元（浮點）對 tov-raw.csv
    F = frozen(reload=True)
    n = np.array([float(r['n_w']) for r in rows]); d = np.array([float(r['possMin_w']) for r in rows]); Tm = np.array([float(r['min_w']) for r in rows])
    got = map_values(F, [str(int(p)) for p in pids], n, d, Tm)
    want = np.array([float(r['tovSkill']) for r in rows])
    diff = float(np.abs(got - want).max())
    assert diff < 1e-6, f'凍結池無法重現卡片 tovSkill（容差 1e-6，因 raw 取到 1e-9）：max|diff|={diff}'
    print('freeze OK pool', len(pool), 'players', len(pids), 'max|diff|', diff)


def frozen(reload=False):
    if 'F' not in _CACHE or reload:
        doc = json.loads(FROZEN.read_text(encoding='utf-8'))
        doc['mapper'] = L.PctMapper([round(x, RND) for x in doc['pool_raw']], doc['top'], doc['bot'])
        _CACHE['F'] = doc
    return _CACHE['F']


def map_values(F, spids, n, d, Tm, t=None, tc=None):
    """n、d（持球分鐘）、Tm（出賽分鐘）皆已是窗口加權和；spids＝frozen t 的 key（str pid）；t 可直接給（新秀）。
    tc＝窗口觸球次數（凍結檔 denom＝touch 時 r 的分母，F['K']＝64·ρ 已含換算）；v 一律用 d。→ 0–99 向量"""
    tv = np.array([F['t'][p] for p in spids]) if t is None else np.asarray(t, float)
    r = L.shrink_to(n, d if F.get('denom') != 'touch' else tc, tv, F['K'])
    v = np.divide(d, Tm, out=np.zeros(len(n)), where=Tm > 0) * 36
    v = np.where(d <= 0, F['v_p10'], v)
    raw = 0.5 * ((-r) - F['mu_r']) / F['sd_r'] + 0.5 * (v - F['mu_v']) / F['sd_v']
    return F['mapper'](np.round(raw, RND))      # 四捨五入到 1e-9：窗口和的加總順序造成的 1e-13 抖動不該讓池內的人跳一格名次


# ------------------------------------------------------------------ 賽中（老將）
def window_pm(W, g, tabs, G, S, cur_name):
    return _window(W, g, tabs, G, S, cur_name, 'TIME_OF_POSS')


def window_tch(W, g, tabs, G, S, cur_name):
    """窗口加權觸球次數 tc_w（同 window_pm 的權重，欄位換 TOUCHES；0.2.12c r 的分母）。"""
    return _window(W, g, tabs, G, S, cur_name, 'TOUCHES')


def _window(W, g, tabs, G, S, cur_name, col):
    """窗口加權持球分鐘 pm_w（全 D.NP 長）。S＝Win8.sums 的基準季（同 sums 的 S 參數）。cur_name＝本季名稱（'2026-27'；季末核對時是 PRIOR）。"""
    D = W.D
    c = L.SLOTS * g / G
    w = L.window_w(c)
    pm = np.zeros(D.NP)
    base = L.SEASONS.index(S) if S in L.SEASONS else len(L.SEASONS)
    for k in range(1, 5):
        i = base - k
        if i < 0 or w[k] <= 0:
            continue
        s = L.SEASONS[i]
        min_s = D.tab[s]['vol'].agg()[1] * 36
        mw = w[k] * min_s
        pm += top_arr(s, D, col) * np.divide(mw, min_s, out=np.zeros(D.NP), where=min_s > 0)
    if g > 0:
        tv = tabs['vol']
        u = (L.WIN - c + L.SLOTS * (tv.gi + 0.5) / G) / L.WIN
        mw = tv.agg(0, g, w=u)[1] * 36
        tot = tv.agg(0, g)[1] * 36
        pm += top_arr(cur_name, D, col) * np.divide(mw, tot, out=np.zeros(D.NP), where=tot > 0)
    return pm


def vet_values(W, S, pm, tc=None):
    """S＝Win8 的窗口和 dict（要 'tovSkill'、'vol'）；pm＝window_pm；tc＝window_tch（TOUCH 時用）。→ 卡片名單順序的 tovSkill 向量（0–99）。"""
    F = frozen()
    ix = W.ix
    n = S['tovSkill'][0][ix]
    Tm = S['vol'][1][ix] * 36
    return map_values(F, [str(int(p)) for p in W.pids], n, pm[ix], Tm, tc=None if tc is None else tc[ix])


# ------------------------------------------------------------------ 新秀
def rookie_tov(rows, pid, pos, x0):
    """rows＝這個人本季逐場（要 MIN、TOV）；pos＝卡片位置（SG／SF／C，已轉換）。
    → (值, 權重, 本季分鐘)；沒有本季持球資料（或不在 possessions.json）＝(None, 0, 分鐘)。
    值＝新定義（t＝凍結同位置先驗、整季不加窗口權重）與起點 x0 依 w＝min(1, 分鐘/RAMP_MIN) 線性混合。"""
    F = frozen()
    mins = float(sum(r['MIN'] for r in rows))
    tov = float(sum(r.get('TOV') or 0 for r in rows))
    d = top_rows('2026-27').get(int(pid), 0.0)
    if d <= 0 or mins <= 0:
        return None, 0.0, mins
    tc = np.array([top_rows('2026-27', 'TOUCHES').get(int(pid), 0.0)])
    val = float(map_values(F, [None], np.array([tov]), np.array([d]), np.array([mins]), tc=tc, t=[F['pos_m'].get(pos, np.mean(list(F['pos_m'].values())))])[0])
    w = min(1.0, mins / RAMP_MIN)
    return x0 + w * (val - x0), w, mins


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) > 1 and sys.argv[1] == 'freeze':
        freeze()
    else:
        print(__doc__)
