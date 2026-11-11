"""E-296 B1／B2：全聯盟逐場 rt 與該場打完 ΔOVR（同一把尺逐日重算，hist_rows.py 輸出）。各 A 臂離線重算 OVR。
只用本季相鄰兩個出賽點的差（略過每人第一場，避免開季先驗用的是舊臂）。"""
import sys, json, glob
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP)); from armlib import *
H = json.load(open(EXP / 'today/ovr-history.json', encoding='utf8'))['players']
pa = json.load(open(EXP / 'part_a.json', encoding='utf8'))
pg = json.load(open(ROOT / 'data/defense-seventh/2026-27/player-games.json', encoding='utf8'))['data']['resultSets'][0]
hd = pg['headers']; date_of = {}
for r in pg['rowSet']: date_of[(str(r[hd.index('PLAYER_ID')]), r[hd.index('GAME_DATE')])] = r[hd.index('GAME_ID')]
rt = {}
for f in glob.glob(str(ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08/games-box-*.json')):
    for gid, g in json.load(open(f, encoding='utf8'))['games'].items():
        for side in ('home', 'away'):
            if isinstance(g.get(side), list):
                for p in g[side]:
                    if p.get('rt') is not None: rt[(str(p['pid']), gid)] = (p['rt'], p['min'])
def ovr_of(pt, arm, a):
    return omap(g_arm(pt['predNew'] - R_REPL, pt['MPGhat'], arm), a) + (pt['mixBonus'] or 0)
res = {}
for arm in ARMS:
    for ak in ('F', 'R'):
        if arm == 'A0' and ak == 'R': continue
        key = f'{arm}-{ak}'; a = dict(ANC0); a['PR1'] = pa[key]['PR1']
        X, Y, good, good_drop, comp = [], [], 0, 0, []
        for pid, h in H.items():
            pts = h['pts']; hist_rt = []
            for i, (d, pt) in enumerate(pts):
                gid = date_of.get((pid, d)); r = rt.get((pid, gid)) if gid else None
                if i > 0 and r and pt.get('predNew') is not None and pts[i-1][1].get('predNew') is not None:
                    prev = pts[i-1][1]
                    dO = ovr_of(pt, arm, a) - ovr_of(prev, arm, a)
                    X.append(r[0]); Y.append(dO)
                    if hist_rt and r[1] >= 15 and r[0] >= np.mean(hist_rt) + 1:
                        good += 1
                        if dO < 0:
                            good_drop += 1
                            Dp, Dn = prev['predNew'] - R_REPL, pt['predNew'] - R_REPL
                            gm = g_arm(Dp, pt['MPGhat'], arm) - g_arm(Dp, prev['MPGhat'], arm)
                            gp = g_arm(Dn, pt['MPGhat'], arm) - g_arm(Dp, pt['MPGhat'], arm)
                            comp.append((gm, gp, Dp < 0))
                if r: hist_rt.append(r[0])
        comp = np.array(comp, float) if comp else np.zeros((0, 3))
        res[key] = dict(B1_rho=spearmanr(X, Y).correlation, n=len(X), B2_good=good, B2_drop=good_drop, B2_rate=good_drop / max(good, 1),
                        B2_drop_minuteNeg=int((comp[:, 0] < 0).sum()) if len(comp) else 0,
                        B2_drop_per36Neg=int((comp[:, 1] < 0).sum()) if len(comp) else 0,
                        B2_drop_Dneg=int(comp[:, 2].sum()) if len(comp) else 0)
        print(key, {k: round(v, 4) if isinstance(v, float) else v for k, v in res[key].items()})
json.dump(res, open(EXP / 'part_b.json', 'w', encoding='utf8'), indent=1)
