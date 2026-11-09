"""E-299 部分 R：單場錨點顯示層，離線套在 E-296 同一把尺逐日歷史（A0 與 A2-15-R 兩種窗口 OVR）。"""
import sys, json, glob
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]; E296 = ROOT / 'reports/E296-neg-g-minutes'
sys.path.insert(0, str(E296)); from armlib import *
M = json.load(open(EXP / 'map.json')); A_, B_ = M['a'], M['b']
H = json.load(open(E296 / 'today/ovr-history.json', encoding='utf8'))['players']
pa = json.load(open(E296 / 'part_a.json', encoding='utf8'))
pg = json.load(open(ROOT / 'data/defense-seventh/2026-27/player-games.json', encoding='utf8'))['data']['resultSets'][0]
hd = pg['headers']; date_of = {}; gdate = {}
for r in pg['rowSet']:
    date_of[(str(r[hd.index('PLAYER_ID')]), r[hd.index('GAME_DATE')])] = r[hd.index('GAME_ID')]
    gdate[r[hd.index('GAME_ID')]] = r[hd.index('GAME_DATE')]
dates = sorted(set(gdate.values()))
played_by = {d: sum(1 for g, gd in gdate.items() if gd <= d) for d in dates}
def fade(d):
    n = max([v for k, v in played_by.items() if k <= d] or [0])
    return float(np.clip((1230 - n) / (0.2 * 1230), 0, 1))
box = {}
for f in glob.glob(str(ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08/games-box-*.json')):
    for gid, g in json.load(open(f, encoding='utf8'))['games'].items():
        for side in ('home', 'away'):
            if isinstance(g.get(side), list):
                for p in g[side]:
                    if p.get('rt') is not None and p.get('min'): box[(str(p['pid']), gid)] = (p['rt'], p['min'], p.get('pm') or 0)
BASES = {'A0': ('A0', dict(ANC0)), 'A2-15-R': ('A2-15', dict(ANC0, PR1=pa['A2-15-R']['PR1']))}
ARMS_R = [('cur', 0, 0), ('b0.3-h5', .3, 5), ('b0.3-h10', .3, 10), ('b0.5-h5', .5, 5), ('b0.5-h10', .5, 10)]
def wovr(pt, arm, a): return omap(g_arm(pt['predNew'] - R_REPL, pt['MPGhat'], arm), a) + (pt['mixBonus'] or 0)
res, series = {}, {}
for bk, (arm, anc) in BASES.items():
    for name, b0, h in ARMS_R:
        key = f'{bk}|{name}'
        X, Y, good, drop, absd = [], [], 0, 0, []
        Fx, Fpm, Frt = [], [], []
        last = {}; ser = {}
        for pid, hh in H.items():
            pts = [(d, pt) for d, pt in hh['pts'] if pt.get('predNew') is not None]
            games = []  # (date, s, min, rt, pm)
            disp = []
            for d, pt in pts:
                gid = date_of.get((pid, d)); bx = box.get((pid, gid)) if gid else None
                if bx: games.append((d, A_ + B_ * bx[0], bx[1], bx[0], bx[2]))
                W = wovr(pt, arm, anc)
                if b0 and games:
                    k = len(games) - 1
                    w = np.array([g[2] * 0.5 ** ((k - j) / h) for j, g in enumerate(games)])
                    Aa = float((w * np.array([g[1] for g in games])).sum() / w.sum()); n = w.sum() / 36
                    beta = b0 * n / (n + 5) * fade(d)
                    O = W + beta * (Aa - W)
                else: O = W
                disp.append((d, O, bx))
            ser[pid] = [(d, round(O, 2)) for d, O, _ in disp]
            hist = []
            for i, (d, O, bx) in enumerate(disp):
                if bx and i > 0:
                    dO = O - disp[i-1][1]; X.append(bx[0]); Y.append(dO); absd.append(abs(dO))
                    if hist and bx[1] >= 15 and bx[0] >= np.mean(hist) + 1:
                        good += 1; drop += dO < 0
                if bx:
                    hist.append(bx[0])
                    fut = [x for _, _, x in disp[i+1:] if x][:5]
                    if fut:
                        mn = sum(x[1] for x in fut)
                        Fx.append(O); Fpm.append(sum(x[2] for x in fut) / mn * 36); Frt.append(sum(x[0] * x[1] for x in fut) / mn)
            last[pid] = disp[-1][1] if disp else None
        res[key] = dict(B1=spearmanr(X, Y).correlation, n=len(X), good=good, drop=int(drop), drop_rate=drop / good,
                        absd_med=float(np.median(absd)), absd_max=float(np.max(absd)),
                        F_pm=spearmanr(Fx, Fpm).correlation, F_rt=spearmanr(Fx, Frt).correlation, nF=len(Fx))
        series[key] = ser
        print(key, {k: round(v, 4) if isinstance(v, float) else v for k, v in res[key].items()})
json.dump(res, open(EXP / 'part_r.json', 'w'), indent=1)
json.dump(series, open(EXP / 'part_r_series.json', 'w'))
