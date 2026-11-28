"""E-302 評估：六臂（A0、M、MR、MA、MAp、MAR）在同一把尺逐日歷史上的 R1／R2／R3 與只報項目（預註冊 prereg.md）。
輸入：today-{r0,ra,rap}/ovr-history.json（逐場點，pts 為 dict）、live-{arm}/ovr-history-cache.json（每天全員，最後一天用）、
      live/2026-11-08 的 games-box-*.json（rt、min、pm）、E-296 part_a.json（A2-15-R 的 PR1）、E-299 map.json（s＝a＋b·rt）。
用法：python -I -X utf8 reports/E302-attr-anchor/eval.py → eval.json、series.json"""
import glob
import json
import math
import sys
from datetime import date
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
E296 = ROOT / 'reports/E296-neg-g-minutes'
E299 = ROOT / 'reports/E299-game-anchor-nonneg'
sys.path.insert(0, str(E296))
from armlib import W, g_arm, omap, ANC0, R_REPL  # noqa: E402

LAST = '2026-11-08'
MP = json.load(open(E299 / 'map.json'))
A_, B_ = MP['a'], MP['b']
PR1_A2 = json.load(open(E296 / 'part_a.json', encoding='utf8'))['A2-15-R']['PR1']
ANC_A2 = dict(ANC0, PR1=PR1_A2)
# 臂：(窗口快照, 分鐘臂, 錨點, β0, h)
ARMS = {'A0': ('r0', 'A0', ANC0, 0, 0), 'M': ('r0', 'A2-15', ANC_A2, 0, 0), 'MR': ('r0', 'A2-15', ANC_A2, .5, 10),
        'MA': ('ra', 'A2-15', ANC_A2, 0, 0), 'MAp': ('rap', 'A2-15', ANC_A2, 0, 0), 'MAR': ('ra', 'A2-15', ANC_A2, .25, 10)}
ATTRS = ('long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'creation', 'onBall', 'help', 'threeValue')

pg = json.load(open(ROOT / 'data/defense-seventh/2026-27/player-games.json', encoding='utf8'))['data']['resultSets'][0]
hd = pg['headers']
iP, iD, iG = hd.index('PLAYER_ID'), hd.index('GAME_DATE'), hd.index('GAME_ID')
gid_of, gdate = {}, {}
for r in pg['rowSet']:
    gid_of[(str(r[iP]), r[iD])] = r[iG]
    gdate[r[iG]] = r[iD]
DATES = sorted(set(gdate.values()))
played_by = {d: sum(1 for gd in gdate.values() if gd <= d) for d in DATES}


def fade(d):
    n = max([v for k, v in played_by.items() if k <= d] or [0])
    return float(np.clip((1230 - n) / (0.2 * 1230), 0, 1))


def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


box = {}
for f in glob.glob(str(ROOT / f'reports/ovr-inseason-2026-27/live/{LAST}/games-box-*.json')):
    for gid, g in json.load(open(f, encoding='utf8'))['games'].items():
        for side in ('home', 'away'):
            if isinstance(g.get(side), list):
                for p in g[side]:
                    if p.get('rt') is not None and p.get('min'):
                        box[(str(p['pid']), gid)] = (p['rt'], p['min'], p.get('pm') or 0)

HIST = {s: json.load(open(EXP / f'today-{s}/ovr-history.json', encoding='utf8'))['players'] for s in ('r0', 'ra', 'rap')}
CACHE = {s: json.load(open(EXP / f'live-{s}/ovr-history-cache.json', encoding='utf8'))['days'] for s in ('r0', 'ra', 'rap')}
NAME = {pid: v['name'] for pid, v in HIST['r0'].items()}


def wovr(pt, arm, anc):
    return omap(g_arm(pt['predNew'] - R_REPL, pt['MPGhat'], arm), anc) + (pt['mixBonus'] or 0)


def anchor(games, b0, h, d):
    """games＝[(date, s, min, rt, pm)]（到 d 為止）→ (A, β)。β 含 n/(n+5)、季末 fade、缺陣衰減。"""
    k = len(games) - 1
    w = np.array([g[2] * 0.5 ** ((k - j) / h) for j, g in enumerate(games)])
    A = float((w * np.array([g[1] for g in games])).sum() / w.sum())
    n = w.sum() / 36
    gap = days(games[-1][0], d)
    beta = b0 * n / (n + 5) * fade(d) * 0.5 ** (max(0, gap - 3) / 14)
    return A, beta


def run_arm(key):
    snap, arm, anc, b0, h = ARMS[key]
    H = HIST[snap]
    X, Y, good, drop, absd, Fx, Fpm, Frt = [], [], 0, 0, [], [], [], []
    ser, games_of = {}, {}
    for pid, hh in H.items():
        pts = [(d, pt) for d, pt in hh['pts'] if pt and pt.get('predNew') is not None]
        games, disp = [], []
        for d, pt in pts:
            gid = gid_of.get((pid, d))
            bx = box.get((pid, gid)) if gid else None
            if bx:
                games.append((d, A_ + B_ * bx[0], bx[1], bx[0], bx[2]))
            Wv = wovr(pt, arm, anc)
            O = Wv
            if b0 and games:
                A, beta = anchor(games, b0, h, d)
                O = Wv + beta * (A - Wv)
            disp.append((d, O, bx, Wv))
        ser[pid] = [(d, round(O, 2), round(Wv, 2)) for d, O, _, Wv in disp]
        games_of[pid] = games
        hist = []
        for i, (d, O, bx, _) in enumerate(disp):
            if bx and i > 0:
                dO = O - disp[i - 1][1]
                X.append(bx[0])
                Y.append(dO)
                absd.append(abs(dO))
                if hist and bx[1] >= 15 and bx[0] >= np.mean(hist) + 1:
                    good += 1
                    drop += dO < 0
            if bx:
                hist.append(bx[0])
                fut = [x for _, _, x, _ in disp[i + 1:] if x][:5]
                if fut:
                    mn = sum(x[1] for x in fut)
                    Fx.append(O)
                    Fpm.append(sum(x[2] for x in fut) / mn * 36)
                    Frt.append(sum(x[0] * x[1] for x in fut) / mn)
    # 最後一天：全員（快取裡 LAST 那天），錨點項用到 LAST 為止的比賽、缺陣衰減照距上一場天數
    last, term = {}, {}
    for pid, pt in CACHE[snap][LAST]['ovr'].items():
        if not pt or pt.get('predNew') is None:
            continue
        Wv = wovr(pt, arm, anc)
        O, t = Wv, 0.0
        g = games_of.get(pid) or []
        if b0 and g:
            A, beta = anchor(g, b0, h, LAST)
            t = beta * (A - Wv)
            O = Wv + t
        last[pid] = O
        if (pt.get('N') or 0) >= 3:
            term[pid] = abs(t)
    res = dict(B1=spearmanr(X, Y).correlation, n=len(X), good=good, drop=int(drop), drop_rate=drop / good,
               absd_med=float(np.median(absd)), absd_max=float(np.max(absd)),
               F_pm=spearmanr(Fx, Fpm).correlation, F_rt=spearmanr(Fx, Frt).correlation, nF=len(Fx),
               R3_term_med=float(np.median(list(term.values()))), R3_n=len(term))
    return res, ser, last


def recon_check():
    """r0：omap(D·W(MPGhat))＋mixBonus 能不能重建快照算出的 ovr（每天全員）。"""
    worst = 0.0
    for d, day in CACHE['r0'].items():
        for pid, pt in day['ovr'].items():
            if pt and pt.get('predNew') is not None and pt.get('ovr') is not None:
                worst = max(worst, abs(wovr(pt, 'A0', ANC0) - pt['ovr']))
    return worst


def season_end_check():
    """季末（g＝G）時 AA 改寫＝原值（逐位元）；中段 s*＝s_win 時也是原值。"""
    sys.path.insert(0, str(EXP))
    import aa_patch as AP
    rng = np.random.default_rng(0)
    n_p, d_p, n_c, d_c = (rng.uniform(1, 9, 50) for _ in range(4))
    n, d = n_p + n_c, d_p + d_c
    ev = rng.uniform(0, 30, 50)
    a = AP.rewrite(n, d, n_p, d_p, ev, 1230, 1230, 20.0, 'pure')
    b = AP.rewrite(n, d, n_p, d_p, ev, 1230, 1230, 20.0, 'max')
    c = AP.rewrite(n, d, n_p, d_p, ev, 146, 1230, float('inf'), 'pure')
    return bool((a == n).all() and (b == n).all() and (c == n).all())


def r033_check():
    """M 臂（A2-15-R）：最後一天 D<0 的人 MPG＋2 時 OVR 不降；A0 對照。"""
    out = {}
    for arm, anc in (('A0', ANC0), ('A2-15', ANC_A2)):
        bad = tot = 0
        for pid, pt in CACHE['r0'][LAST]['ovr'].items():
            if not pt or pt.get('predNew') is None or pt['predNew'] - R_REPL >= 0:
                continue
            D, m = pt['predNew'] - R_REPL, pt['MPGhat']
            tot += 1
            bad += omap(g_arm(D, m + 2, arm), anc) < omap(g_arm(D, m, arm), anc) - 1e-9
        out[arm] = {'negD': tot, 'ovr_drops_with_more_min': bad}
    return out


def player(name):
    return next((p for p, n in NAME.items() if n == name), None)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    res, series, lasts = {}, {}, {}
    for k in ARMS:
        res[k], series[k], lasts[k] = run_arm(k)
        print(k, {a: round(v, 4) if isinstance(v, float) else v for a, v in res[k].items()})
    base = res['A0']
    for k, r in res.items():
        r['R1'] = bool(r['B1'] >= base['B1'] + 0.15 and r['drop_rate'] <= 0.13)
        r['R2'] = bool(r['F_pm'] >= base['F_pm'] - 0.01)
    order = [k for k in ('MA', 'MAR', 'MR') if res[k]['R1'] and res[k]['R2']]
    if order:
        pick, capped = order[0], False
    else:
        r2 = [k for k in ARMS if k != 'A0' and res[k]['R2']]
        pick, capped = (min(r2, key=lambda k: res[k]['drop_rate']) if r2 else None), True
    # 只報：前 20 名重疊、最後一天 |Δ| 中位（對 A0）
    top = lambda L: [p for p, _ in sorted(L.items(), key=lambda x: -x[1])[:20]]
    t0 = top(lasts['A0'])
    side = {}
    for k in ARMS:
        common = [p for p in lasts[k] if p in lasts['A0']]
        side[k] = {'top20_overlap': len(set(top(lasts[k])) & set(t0)),
                   'last_absd_vs_A0_med': float(np.median([abs(lasts[k][p] - lasts['A0'][p]) for p in common])),
                   'top20': [(NAME.get(p, p), round(lasts[k][p], 1)) for p in top(lasts[k])]}
    # Yang 逐日與 11/7 那場屬性
    yang = player('Yang Hansen')
    ydoc = {}
    if yang:
        for k in ARMS:
            ydoc[k] = series[k].get(yang)
        attrs = {}
        for s in ('r0', 'ra', 'rap'):
            pts = dict((d, pt) for d, pt in HIST[s][yang]['pts'])
            if '2026-11-06' in pts and '2026-11-07' in pts:
                attrs[s] = {a: [pts['2026-11-06'].get(a), pts['2026-11-07'].get(a)] for a in ATTRS + ('predNew', 'MPGhat')}
        ydoc['attrs_1106_1107'] = attrs
        ydoc['games'] = [(d, round(bx[0], 1), bx[1]) for d, bx in ((d, box.get((yang, gid_of.get((yang, d))))) for d, _ in HIST['r0'][yang]['pts']) if bx]
    out = {'arms': res, 'pick': pick, 'score_capped_at_3': capped, 'side': side, 'yang': ydoc,
           'recon_max_abs_r0': recon_check(), 'season_end_identity': season_end_check(), 'r033': r033_check(),
           'mx': json.load(open(EXP / 'mx.json', encoding='utf-8'))['mx'], 'MA_minus_M_B1': res['MA']['B1'] - res['M']['B1']}
    print('pick', pick, 'capped', capped, 'recon', round(out['recon_max_abs_r0'], 4), 'season_end', out['season_end_identity'], 'r033', out['r033'])
    for k in ARMS:
        print(k, 'R1', res[k]['R1'], 'R2', res[k]['R2'], side[k]['top20_overlap'], round(side[k]['last_absd_vs_A0_med'], 2))
    json.dump(out, open(EXP / 'eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    json.dump(series, open(EXP / 'series.json', 'w', encoding='utf-8'), ensure_ascii=False)
