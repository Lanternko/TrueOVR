"""E-175 稽核 §3：SD 比、U 季末 OVR 一階近似（自己重寫）、第 0 天跳動 p90、drive 不對稱量化、近似誤差敏感度。
用法：python -I -X utf8 sec3_audit.py   （不 import 產出者的程式）"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac
import bt_audit as BA

HERE = Path(__file__).resolve().parent
R9A = ac.R / 'card-0.2.9a'
S = '2025-26'
db = ac.DB(); inp = ac.load_inputs(); bt = inp['bt']
V = ac.Chain(db, inp, 'V'); U = ac.Chain(db, inp, 'U')
names, pids = V.names, V.pids
res = {}

# ---------- 1. SD 比 ----------
mins_card = np.array([inp['rank_min'].get(n, 0) for n in names])
m5c = mins_card >= 500
sd = {}
for a in ac.ATTRS8:
    v, u = V.mapped[a], U.mapped[a]
    sd[a] = {'sdV': float(v.std()), 'sdU': float(u.std()), 'ratio': float(u.std() / v.std()), 'ratio_min500': float(u[m5c].std() / v[m5c].std()),
             'meanDiff': float((u - v).mean()), 'maxAbsDiff': float(np.abs(u - v).max()), 'maeUV': float(np.abs(u - v).mean())}
res['sd_ratio'] = sd
res['sd_all_in_band'] = all(0.9 <= x['ratio'] <= 1.1 for x in sd.values())
res['sd_n_min500'] = int(m5c.sum())
print('SD ratio', {a: round(x['ratio'], 3) for a, x in sd.items()}, 'inband', res['sd_all_in_band'])

# ---------- 2. OVR 一階近似（自己寫） ----------
rk = list(csv.DictReader(open(R9A / 'ranking.csv', encoding='utf-8')))
by = {}
for r in rk:
    by.setdefault(r['name'], []).append(r)
assert all(len(by[n]) == 1 for n in names)
row = [by[n][0] for n in names]
col = lambda k: np.array([float(r[k]) for r in row])
ovr, o36, p36, mn = col('ovr'), col('ovr36'), col('predictedPer36'), col('MIN')
sm = ac.jl(R9A / 'cards/K6/primary/summary.json')
val = {a: sm['valuePer10AttributePoints'][a]['per36'] for a in ac.ATTRS8}
se = {a: sm['valuePer10AttributePoints'][a]['bootstrapSE'] for a in ac.ATTRS8}
ux = np.unique(p36); uy = np.array([o36[p36 == x].mean() for x in ux])
sh_, sl_ = (uy[-1] - uy[-6]) / (ux[-1] - ux[-6]), (uy[5] - uy[0]) / (ux[5] - ux[0])


def f(x):
    x = np.asarray(x, float)
    return np.where(x > ux[-1], uy[-1] + sh_ * (x - ux[-1]), np.where(x < ux[0], uy[0] + sl_ * (x - ux[0]), np.interp(x, ux, uy)))


ratio = ovr / o36
res['proxy_selfcheck_maxabs'] = float(np.abs(f(p36) * ratio - ovr).max())
res['monotone_curve'] = bool(np.all(np.diff(uy) >= -1e-9))


def proxy(frm, to, base, vv=None, zero=None):
    vv = vv or val
    d = sum(vv[a] * (to[a] - frm[a]) / 10 for a in ac.ATTRS8)
    if zero is not None:
        d = np.where(zero, 0.0, d)
    return f(base + d) * ratio, d


def season_end_stats(ovrU, ovrV=ovr):
    rV, rU = rankdata(-ovrV, method='min'), rankdata(-ovrU, method='min')
    in100 = np.nonzero(rV <= 100)[0]
    t20V, t20U = set(np.nonzero(rV <= 20)[0]), set(np.nonzero(rU <= 20)[0])
    return {'absmean': float(np.abs(ovrU - ovrV).mean()), 'p90': float(np.percentile(np.abs(ovrU - ovrV), 90)), 'max': float(np.abs(ovrU - ovrV).max()),
            'top100_moved10': int((np.abs(rU[in100] - rV[in100]) >= 10).sum()), 'top100_n': int(len(in100)),
            'top20_out': sorted(names[i] for i in t20V - t20U), 'top20_in': sorted(names[i] for i in t20U - t20V),
            'spearman': float(spearmanr(ovrV, ovrU)[0]), 'rU': rU, 'rV': rV}


def strip(d):
    return {k: v for k, v in d.items() if k not in ('rU', 'rV')}


ovrU, dP = proxy(V.mapped, U.mapped, p36)
se_stat = season_end_stats(ovrU)
res['season_end'] = strip(se_stat)
rV, rU = se_stat['rV'], se_stat['rU']
res['season_end']['key_players'] = {k: {'rankV': int(rV[names.index(k)]), 'rankU': int(rU[names.index(k)])}
                                    for k in ('Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Anthony Davis', 'Joel Embiid')
                                    if k in names}
print('proxy selfcheck', res['proxy_selfcheck_maxabs'], 'season end', res['season_end'])

# ---------- 3. 第 0 天跳動 ----------
ac.SEASONS.append('2026-27'); S0 = '2026-27'; db.G[S0] = 1230
_e = np.zeros(0)
db.tab[S0] = {t: (_e.astype(int), _e.astype(int), _e, _e) for t in db.tab[S]}    # 2026-27 沒有任何資料（L-026）
by_pos = ac.positions(); posv0 = [ac.pos_of(by_pos, p, S0) for p in db.pids]
F = BA.fits_of(bt, {})
ix = V.ix
dz = V.dz


def day0(arm_u, scale=1.0):
    out = {}
    for a in ac.ATTRS8:
        if a == 'drive':
            rr = []
            for t in ('driveVol', 'driveEff'):
                fc, fb = F[t]
                fit = fb if arm_u else fc
                m = ac.causal_m(db, S0, 0, t, fit['prior'], posv0)
                rr.append((ac.rate_U(db, t, S0, 0, fit, m, scale) if arm_u else ac.rate_V(db, t, S0, 0, fit, m))[ix])
            sc = .5 * (36 * rr[0] - dz['mv']) / dz['sv'] + .5 * (rr[1] - dz['me']) / dz['se']
            out[a] = V.map['drive'](sc)
        else:
            fc, fb = F[a]
            fit = fb if arm_u else fc
            m = ac.causal_m(db, S0, 0, a, fit['prior'], posv0)
            r_ = (ac.rate_U(db, a, S0, 0, fit, m, scale) if arm_u else ac.rate_V(db, a, S0, 0, fit, m))[ix]
            if a == 'tovSkill':
                mp, sg, shf = V.map['tovSkill'], -1.0, 0.0
            elif a in ('mid', 'short'):
                mp, sg, shf = V.map[a], 1.0, V.shift[a]
            elif a in ('foulDraw', 'pass'):
                mp, sg, shf = V.map[a + 'Rate'], 1.0, 0.0
            else:
                mp, sg, shf = V.map[a], 1.0, 0.0
            out[a] = mp(sg * r_ + shf)
    return out


V0, U0 = day0(False), day0(True)
oV0, _ = proxy(V.mapped, V0, p36)
oU0, _ = proxy(U.mapped, U0, p36 + dP)
jV, jU = np.abs(oV0 - ovr), np.abs(oU0 - ovrU)
m5 = mn >= 500


def jump_stats(jv, ju):
    return {'V_p90': float(np.percentile(jv[m5], 90)), 'U_p90': float(np.percentile(ju[m5], 90)), 'V_med': float(np.median(jv[m5])), 'U_med': float(np.median(ju[m5])),
            'ratio_p90': float(np.percentile(ju[m5], 90) / np.percentile(jv[m5], 90)), 'V_p90_all': float(np.percentile(jv, 90)), 'U_p90_all': float(np.percentile(ju, 90))}


res['day0_jump'] = jump_stats(jV, jU)
res['day0_jump']['n_min500'] = int(m5.sum())
res['day0_attr_p90'] = {a: {'V': float(np.percentile(np.abs(V0[a] - V.mapped[a]), 90)), 'U': float(np.percentile(np.abs(U0[a] - U.mapped[a]), 90))} for a in ac.ATTRS8}
print('day0', res['day0_jump'])
print('day0 attr p90', {a: (round(x['V'], 2), round(x['U'], 2)) for a, x in res['day0_attr_p90'].items()})
# 窗口權重減半（window_weights 實際回傳值）
U0h = day0(True, 0.5)
Uh = ac.Chain(db, inp, 'U', 0.5)
ovrUh, dPh = proxy(V.mapped, Uh.mapped, p36)
oU0h, _ = proxy(Uh.mapped, U0h, p36 + dPh)
res['day0_jump_uscale0.5'] = jump_stats(jV, np.abs(oU0h - ovrUh))
res['season_end_uscale0.5'] = strip(season_end_stats(ovrUh))
print('day0 scale0.5', res['day0_jump_uscale0.5'])

# ---------- 4. 3(b) drive 不對稱：U 的 drive 只用 H1 場次 ----------
h1m = db.h1[S]
saved = {t: db.tab[S][t] for t in ('driveVol', 'driveEff')}
for t in saved:
    g, p, n, d = saved[t]
    m = h1m[g]
    db.tab[S][t] = (g[m], p[m], n[m], d[m])
try:
    Uh1 = ac.Chain(db, inp, 'U')
finally:
    db.tab[S].update(saved)
dd = Uh1.mapped['drive'] - V.mapped['drive']
res['drive_asym'] = {'sdV': float(V.mapped['drive'].std()), 'sdU_all': float(U.mapped['drive'].std()), 'sdU_h1only': float(Uh1.mapped['drive'].std()),
                     'ratio_all': float(U.mapped['drive'].std() / V.mapped['drive'].std()), 'ratio_h1only': float(Uh1.mapped['drive'].std() / V.mapped['drive'].std()),
                     'maeUV_all': float(np.abs(U.mapped['drive'] - V.mapped['drive']).mean()), 'maeUV_h1only': float(np.abs(dd).mean()),
                     'meanDiff_all': float((U.mapped['drive'] - V.mapped['drive']).mean()), 'meanDiff_h1only': float(dd.mean())}
ovrUa, _ = proxy(V.mapped, {**U.mapped, 'drive': Uh1.mapped['drive']}, p36)
res['drive_asym']['season_end_h1only'] = strip(season_end_stats(ovrUa))
res['drive_asym']['absOVR_change_vs_all'] = float(np.abs(ovrUa - ovrU).mean())
res['drive_asym']['maxOVR_change_vs_all'] = float(np.abs(ovrUa - ovrU).max())
print('drive asym', res['drive_asym'])

# ---------- 5. OVR 近似誤差敏感度 ----------
cap = sm['cap']
capped = set(cap['cappedNames'])
iscap = np.array([n in capped for n in names])
res['cap'] = {'cappedPlayers': cap['cappedPlayers'], 'allowedPlayers': cap['allowedPlayers'], 'n_capped_in_card582': int(iscap.sum()),
              'capped_in_top20V': int(iscap[rV <= 20].sum()), 'capped_in_top100V': int(iscap[rV <= 100].sum())}
ovrU_z, _ = proxy(V.mapped, U.mapped, p36, zero=iscap)           # 被封頂者不動（極端情境）
oU0_z, _ = proxy(U.mapped, U0, p36 + np.where(iscap, 0, dP), zero=iscap)
oV0_z, _ = proxy(V.mapped, V0, p36, zero=iscap)
res['cap']['season_end_cappedFrozen'] = strip(season_end_stats(ovrU_z))
res['cap']['day0_cappedFrozen'] = jump_stats(np.abs(oV0_z - ovr), np.abs(oU0_z - ovrU_z))
nc = m5 & ~iscap
res['cap']['day0_uncappedOnly_min500'] = {'n': int(nc.sum()), 'V_p90': float(np.percentile(jV[nc], 90)), 'U_p90': float(np.percentile(jU[nc], 90)),
                                          'ratio_p90': float(np.percentile(jU[nc], 90) / np.percentile(jV[nc], 90))}
print('cap', res['cap'])
rng = np.random.default_rng(20261101)
mc = []
for _ in range(300):
    vv = {a: val[a] + rng.normal() * se[a] for a in ac.ATTRS8}
    oU_, dP_ = proxy(V.mapped, U.mapped, p36, vv)
    oV0_, _ = proxy(V.mapped, V0, p36, vv)
    oU0_, _ = proxy(U.mapped, U0, p36 + dP_, vv)
    st = season_end_stats(oU_)
    mc.append((st['top100_moved10'], st['spearman'], np.percentile(np.abs(oU0_ - oU_)[m5], 90) / np.percentile(np.abs(oV0_ - ovr)[m5], 90), st['absmean']))
mc = np.array(mc)
pc = lambda x: [float(np.percentile(x, 5)), float(np.percentile(x, 95))]
res['coef_mc'] = {'B': 300, 'basis': 'valuePer10AttributePoints ± bootstrapSE 獨立常態', 'top100_moved10_90pct': pc(mc[:, 0]), 'spearman_90pct': pc(mc[:, 1]),
                  'day0_p90_ratio_UoverV_90pct': pc(mc[:, 2]), 'absmean_dOVR_90pct': pc(mc[:, 3])}
print('mc', res['coef_mc'])
(HERE / 'audit_sec3.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
