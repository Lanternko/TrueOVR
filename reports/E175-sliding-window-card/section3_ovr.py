"""E-175 §3 OVR 層（只報告）。8 項 SD 比全落在 [0.9,1.1] → 沿用 0.2.9a 係數，不重擬合。
OVR 是「一階近似」，不是重跑整條建卡管線：U 與 V 的 8 項屬性差 × 0.2.9a 第一層「每 10 點能力值的每 36 分」(cards/K6/primary/summary.json valuePer10AttributePoints)
→ predictedPer36 的增量 → 沿 0.2.9a ranking.csv 的單調曲線 predictedPer36→ovr36（Spearman 1.0）換成 ovr36 → 乘該人 ovr/ovr36 比。位置交互項、RAPM 封頂 (H1 cap)、用人層重擬合都不重跑。
用法：python -I -X utf8 reports/E175-sliding-window-card/section3_ovr.py   （cwd＝repo 根目錄）
"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr, rankdata
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(H))
import e175_lib as L, e175_card as C, e175_backtest as BT

D = L.Data(); inp = C.load_inputs(); bt = inp['bt']
V = C.card_chain(D, inp, 'V'); U = C.card_chain(D, inp, 'U')
pids, names = V['pids'], V['names']
ix = np.array([D.pidx[p] for p in pids])
rk = list(csv.DictReader(open(ROOT / 'reports/card-0.2.9a/ranking.csv', encoding='utf-8')))
byname = {}
for r in rk:
    byname.setdefault(r['name'], []).append(r)
assert all(len(byname[n]) == 1 for n in names)
row = [byname[n][0] for n in names]
ovr = np.array([float(r['ovr']) for r in row]); o36 = np.array([float(r['ovr36']) for r in row]); p36 = np.array([float(r['predictedPer36']) for r in row])
mn = np.array([float(r['MIN']) for r in row]); pos = [r['pos'] for r in row]
val = json.load(open(ROOT / 'reports/card-0.2.9a/cards/K6/primary/summary.json', encoding='utf-8'))['valuePer10AttributePoints']
# 單調曲線 predictedPer36 → ovr36（ranking.csv 的 582 點；重複的 x 取平均）
ux = np.unique(p36); uy = np.array([o36[p36 == x].mean() for x in ux])
assert np.all(np.diff(uy) >= -1e-9), 'ovr36 對 predictedPer36 不單調'
slope_hi = (uy[-1] - uy[-6]) / (ux[-1] - ux[-6]); slope_lo = (uy[5] - uy[0]) / (ux[5] - ux[0])


def f(x):
    x = np.asarray(x, float)
    y = np.interp(x, ux, uy)
    return np.where(x > ux[-1], uy[-1] + slope_hi * (x - ux[-1]), np.where(x < ux[0], uy[0] + slope_lo * (x - ux[0]), y))


ratio = ovr / o36


def proxy_ovr(attrs_from, attrs_to, base=None):
    d = sum(val[a]['per36'] * (attrs_to[a] - attrs_from[a]) / 10 for a in C.ATTRS8)
    return f((p36 if base is None else base) + d) * ratio, d


chk = f(p36) * ratio
res = {'method': '一階近似（見檔頭）', 'proxyCheck_maxAbsErr_vs_ranking': float(np.abs(chk - ovr).max())}
print('proxy self-check max|err|', res['proxyCheck_maxAbsErr_vs_ranking'])

# ---------- 2025-26 季末 U 對 V ----------
ovrU, dP = proxy_ovr(V['mapped'], U['mapped'])
rV = rankdata(-ovr, method='min'); rU = rankdata(-ovrU, method='min')
order = np.argsort(rV, kind='stable')
topV = set(np.nonzero(rV <= 20)[0]); topU = set(np.nonzero(rU <= 20)[0])
in100 = np.nonzero(rV <= 100)[0]
res['season_end'] = {
    'n': len(pids), 'dOVR_mean': float((ovrU - ovr).mean()), 'dOVR_absmean': float(np.abs(ovrU - ovr).mean()), 'dOVR_p90abs': float(np.percentile(np.abs(ovrU - ovr), 90)), 'dOVR_maxabs': float(np.abs(ovrU - ovr).max()),
    'top20_out': [names[i] for i in sorted(topV - topU, key=lambda i: rV[i])], 'top20_in': [names[i] for i in sorted(topU - topV, key=lambda i: rU[i])],
    'top100_moved>=10': int((np.abs(rU[in100] - rV[in100]) >= 10).sum()), 'top100_n': int(len(in100)),
    'top300_moved>=10': int((np.abs(rU[rV <= 300] - rV[rV <= 300]) >= 10).sum()),
    'rank_spearman_UV': float(spearmanr(ovr, ovrU)[0])}
key = ['Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić']
res['season_end']['key_players'] = {k: {'ovrV': float(ovr[names.index(k)]), 'rankV': int(rV[names.index(k)]), 'ovrU': round(float(ovrU[names.index(k)]), 1), 'rankU': int(rU[names.index(k)])} for k in key if k in names}
big = [i for i in order if pos[i] in ('C', 'PF')][:10]
res['season_end']['bigs_top10'] = [{'name': names[i], 'pos': pos[i], 'rankV': int(rV[i]), 'rankU': int(rU[i]), 'ovrV': float(ovr[i]), 'ovrU': round(float(ovrU[i]), 1)} for i in big]
mv = np.argsort(-np.abs(rU - rV))
res['season_end']['biggest_rank_moves_min500'] = [{'name': names[i], 'rankV': int(rV[i]), 'rankU': int(rU[i]), 'MIN': float(mn[i])} for i in mv if mn[i] >= 500][:6]

# 薪水／2K Spearman（2025-26，MIN>=500，同 E-164 稽核口徑；只報告，同季不算樣本外）
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))
import eval_v2 as EV
P = EV.P
base = EV._base()['2025-26']
YW = {1: 1.0, 2: 1.0, 3: 0.7, 4: 0.5}


def wsp(x, y, w):
    a, b = rankdata(x), rankdata(y)
    w = np.asarray(w, float); w = w / w.sum()
    ca, cb = a - (w * a).sum(), b - (w * b).sum()
    return (w * ca * cb).sum() / np.sqrt((w * ca * ca).sum() * (w * cb * cb).sum())


byn = {}
for p, i in base['pop'].items():
    byn.setdefault(P.norm(i['name']), []).append(p)


def omap(vals):
    m = {}
    for i, n in enumerate(names):
        if mn[i] < 500:
            continue
        ids = byn.get(P.norm(n)) or []
        if len(ids) == 1:
            m[ids[0]] = float(vals[i])
    return m


sp = {}
for arm, vals in (('V', ovr), ('U', ovrU)):
    M = omap(vals); d = {}
    for k in ('sal', 'twok'):
        have = [p for p in M if p in base['raw'][k]]
        oo = np.array([M[p] for p in have])
        d[k] = float(wsp(oo, [base['raw'][k][p][0] for p in have], [YW.get(base['raw'][k][p][1], 0.3) for p in have])) if k == 'sal' else float(spearmanr(oo, [base['raw'][k][p] for p in have])[0])
        d['n_' + k] = len(have)
    sp[arm] = d
res['season_end']['spearman_2025-26'] = sp
print(json.dumps(res['season_end'], ensure_ascii=False, indent=1)[:3000])

# ---------- 換季跳動：季末 → 2026-27 開季第 0 天（只用 2025-26 以前的資料） ----------
L.SEASONS.append('2026-27'); D.G['2026-27'] = 1230; D.tab['2026-27'] = {a: L.Tab([], [], [], [], D.NP) for a in D.tab['2025-26']}
S0 = '2026-27'
by = L.positions_by()
posv = np.array([L.pos_lookup(by, p, S0) for p in D.pids])
fits = BT.build_fits(bt, False)
mp = V['mappers']; zr = V['info']['driveZ']; sh = {a: V['info'][a + 'Shift']['shift'] for a in ('mid', 'short')}
mapper = {'ft': mp['ft'], 'foulDraw': mp['foulDrawRate'], 'tovSkill': mp['tovSkill'], 'pass': mp['passRate'], 'rebound': mp['rebound'], 'mid': mp['mid'], 'short': mp['short'], 'drive': mp['drive']}


def day0(arm):
    out = {}
    for a in C.ATTRS8:
        if a == 'drive':
            rv = BT.arm_rate(D, 'driveVol', arm, fits['driveVol'][arm], S0, 0, posv)[ix]
            re_ = BT.arm_rate(D, 'driveEff', arm, fits['driveEff'][arm], S0, 0, posv)[ix]
            out[a] = mapper[a](.5 * (36 * rv - zr['mv']) / zr['sv'] + .5 * (re_ - zr['me']) / zr['se'])
        else:
            r = BT.arm_rate(D, a, arm, fits[a][arm], S0, 0, posv)[ix]
            sgn, shift = (-1.0, 0.0) if a == 'tovSkill' else (1.0, sh.get(a, 0.0))
            out[a] = mapper[a](sgn * r + shift)
    return out


V0, U0 = day0('V'), day0('U')
oV0, _ = proxy_ovr(V['mapped'], V0)
oU0, _ = proxy_ovr(U['mapped'], U0, base=p36 + dP)
# 注意：V0／U0 用回測口徑（全人群先驗、drive 沒資料者走先驗不是 70），季末 V／U 用卡片口徑；兩臂同樣處理
jV, jU = np.abs(oV0 - ovr), np.abs(oU0 - ovrU)
m5 = mn >= 500
res['day0_jump'] = {'V_p90abs_all': float(np.percentile(jV, 90)), 'U_p90abs_all': float(np.percentile(jU, 90)),
                    'V_p90abs_min500': float(np.percentile(jV[m5], 90)), 'U_p90abs_min500': float(np.percentile(jU[m5], 90)), 'n_all': len(pids), 'n_min500': int(m5.sum()),
                    'V_median_min500': float(np.median(jV[m5])), 'U_median_min500': float(np.median(jU[m5])),
                    'ratio_p90_min500_UoverV': float(np.percentile(jU[m5], 90) / np.percentile(jV[m5], 90)),
                    'attr_p90abs_dAttr': {a: {'V': float(np.percentile(np.abs(V0[a] - V['mapped'][a]), 90)), 'U': float(np.percentile(np.abs(U0[a] - U['mapped'][a]), 90))} for a in C.ATTRS8}}
print(json.dumps(res['day0_jump'], ensure_ascii=False, indent=1))
res['coefficients'] = '沿用 0.2.9a（8 項 SD 比全落在 [0.9,1.1]，見 section3-attrs.json）'
(H / 'section3-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
with open(H / 'section3-ranking-U-proxy.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['name', 'pos', 'MIN', 'ovrV', 'rankV', 'ovrU_proxy', 'rankU_proxy', 'dPred36'])
    for i in order:
        w.writerow([names[i], pos[i], mn[i], ovr[i], rV[i], round(float(ovrU[i]), 2), rU[i], round(float(dP[i]), 4)])
