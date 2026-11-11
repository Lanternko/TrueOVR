"""E-223 評估（預註冊後才對 2025-26 跑）。參數一律讀 work/train-fit-2425.json（凍結），這支程式不重擬合任何東西。
用法：python -I -X utf8 eval_oos.py <season> [--forward]      season＝2526（樣本外）；2425 只用來乾跑驗證程式（訓練季，不算證據）。
輸出 work/eval-<season>.json（含 forward 區塊時加 --forward）。"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json
import numpy as np
from fit_train import features, load_sims, brier
from e223_lib import *

key = sys.argv[1]; fwd = '--forward' in sys.argv
P = json.load(open(HERE / 'work/train-fit-2425.json'))
k1, a, b, r_tr = P['k1'], P['a'], P['b'], P['r']
MDE_B, MDE_W = 0.0100, 1.25            # 預註冊凍結：訓練季成對 bootstrap 90% 區間半寬（M1−M0）
zmap, zmiss, info = load_card(CARDS / SEASONS[key]['card'])
F = features(key, zmap, zmiss)
y = F['y']; n = len(y); home, away, ids = F['home'], F['away'], F['ids']
pred = {'B0': F['b0'] + H, 'M0': F['m0'] + H, 'M1': k1 * F['s'] + H, 'M2': a * F['m0'] + b * F['s'] + H}
pg = {k: brier(v, y) for k, v in pred.items()}
out = dict(season=key, n=n, params=dict(k1=k1, a=a, b=b, r=r_tr, MDE_B=MDE_B, MDE_W=MDE_W),
           brier={k: float(v[0].mean()) for k, v in pg.items()}, win_mae={k: wins_mae(v[1], y, home, away, ids) for k, v in pg.items()})
rng = np.random.default_rng(20261102); boots = [rng.integers(0, n, n) for _ in range(2000)]
def pair(x, z, metric):
    if metric == 'brier': v = np.array([pg[x][0][ix].mean() - pg[z][0][ix].mean() for ix in boots])
    else: v = np.array([wins_mae(pg[x][1], y, home, away, ids, ix) - wins_mae(pg[z][1], y, home, away, ids, ix) for ix in boots])
    return dict(diff=float(v.mean()), lo=float(np.percentile(v, 5)), hi=float(np.percentile(v, 95)))
out['pairs'] = {f'{x}-{z}': {m: pair(x, z, m) for m in ('brier', 'win')} for x, z in (('M1', 'M0'), ('M2', 'M0'), ('M1', 'B0'), ('M2', 'B0'), ('M0', 'B0'), ('M2', 'M1'))}
# 判定（預註冊）：硬條件＝候選對 M0 的 Brier／勝場 MAE 退步都 ≤ 2×MDE；B 線＝Brier ≤ M0 + MDE
out['verdict'] = {c: dict(hard_brier=out['brier'][c] - out['brier']['M0'] <= 2 * MDE_B, hard_win=out['win_mae'][c] - out['win_mae']['M0'] <= 2 * MDE_W,
                          B_line=out['brier'][c] - out['brier']['M0'] <= MDE_B) for c in ('M1', 'M2')}
# 逐隊預測勝場表
S = F['S']; W = {t: S['inp']['teams'][t]['W'] for t in ids}; name = {t: S['inp']['teams'][t]['abbr'] for t in ids}
pw = {k: {t: 0.0 for t in ids} for k in pg}
for k in pg:
    for i in range(n): pw[k][home[i]] += pg[k][1][i]; pw[k][away[i]] += 1 - pg[k][1][i]
out['teams'] = sorted([dict(abbr=name[t], W=W[t], **{k: float(pw[k][t]) for k in pg}) for t in ids], key=lambda r: -r['W'])
# ---------- A 線 ----------
af = HERE / f'work/sims-a{key}'
if af.exists():
    meta = json.load(open(HERE / f'work/aline-meta-{key}.json')); sims = load_sims_a = {}
    for f in glob.glob(str(af / 'o-*.json')):
        for rr in json.load(open(f))['res']: sims[rr['key']] = rr
    mu = lambda k: sims[k]['msum'] / sims[k]['n']
    for m in meta: m['d0'] = mu(m['snap'] * 10) - mu(m['snap'] * 10 + m['slot'])
    x = np.array([m['x'] for m in meta]); d0 = np.array([m['d0'] for m in meta]); snap = np.array([m['snap'] for m in meta])
    D = {'M0': d0, 'M1': k1 * x, 'M2': a * d0 + b * x}
    cid = np.unique(snap); idx = {c: np.where(snap == c)[0] for c in cid}
    arng = np.random.default_rng(20261102); ab = []
    for _ in range(2000):
        ii = np.concatenate([idx[c] for c in arng.choice(cid, len(cid))]); ab.append(ii)
    def corr(v, ii=None):
        ii = np.arange(len(x)) if ii is None else ii
        return float(np.corrcoef(v[ii], x[ii])[0, 1]) if np.std(v[ii]) > 0 else float('nan')
    hc = np.array([m['has_card'] for m in meta])
    out['aline'] = dict(n_removals=len(meta), n_snapshots=len(cid), sd_x=float(x.std()),
                        **{c: dict(r=corr(v), ci90=[float(np.nanpercentile([corr(v, ii) for ii in ab], 5)), float(np.nanpercentile([corr(v, ii) for ii in ab], 95))],
                                   r_card_only=float(np.corrcoef(v[hc], x[hc])[0, 1]) if np.std(v[hc]) > 0 else None,
                                   slope=float(np.polyfit(x, v, 1)[0]), mean=float(v.mean())) for c, v in D.items()},
                        d0_sd=float(d0.std()))
    dd = np.array([corr(D['M2'], ii) - corr(D['M0'], ii) for ii in ab])
    out['aline']['M2_minus_M0'] = dict(diff=corr(D['M2']) - corr(D['M0']), ci90=[float(np.nanpercentile(dd, 5)), float(np.nanpercentile(dd, 95))])
    out['aline']['met'] = bool(out['aline']['M2']['r'] >= 0.9 and out['aline']['M2_minus_M0']['ci90'][0] > 0)   # 預註冊 A 線成功：M2 的 r≥0.9 且比 M0 高（區間下界>0）
    # 例：每分鐘×OVR 變動最大的前 8 筆
    top = sorted(range(len(meta)), key=lambda j: -x[j])[:8]
    out['aline']['top_x'] = [dict(team=meta[j]['team'], nth=meta[j]['nth'], pid=meta[j]['pid'], minutes=meta[j]['minutes'], z=meta[j]['z'], x=float(x[j]), d0=float(d0[j])) for j in top]
# ---------- 2026-27 往前看 ----------
if fwd:
    FT = json.load(open(HERE / 'work/forward-team-ratings-2026-11-03.json', encoding='utf8'))
    lin = json.load(open(HERE / 'work/lineups-2425.json'))
    mm = np.array([[m, zmap.get(p, zmiss)] for r in lin.values() for p, m in r]); mz = float((mm[:, 0] * mm[:, 1]).sum() / mm[:, 0].sum())
    sz = float(np.sqrt((mm[:, 0] * (mm[:, 1] - mz) ** 2).sum() / mm[:, 0].sum()))
    ov = np.array([[q['min'], q['ovr']] for t in FT['teams'].values() for q in t['c']['rotation'] if q['ovr'] is not None])
    mo = float((ov[:, 0] * ov[:, 1]).sum() / ov[:, 0].sum()); so = float(np.sqrt((ov[:, 0] * (ov[:, 1] - mo) ** 2).sum() / ov[:, 0].sum()))
    zf = lambda o: zmiss if o is None else mz + (o - mo) / so * sz   # 無 OVR（補底卡球員）＝訓練季同一個 z_miss；把 live OVR 對到訓練季「輪替人群」的 z 尺度（只對人群均值與標準差，不看結果）
    sf = lambda rot: sum(q['min'] / 240.0 * (zf(q['ovr']) - r_tr) for q in rot)
    rows = []
    for t, v in FT['teams'].items():
        row = dict(abbr=v['abbr'], out=[q['name'] for q in v['injured'] if q['status'] in ('Out', 'Doubtful', 'Questionable', 'Day-To-Day', 'Suspension')])
        for ver in ('c', 'today'):
            n0 = v[ver]['net']; s1 = sf(v[ver]['rotation'])
            row[ver] = dict(M0=n0, M1=k1 * s1, M2=a * n0 + b * s1)
        rows.append(row)
    out['forward'] = dict(map=dict(train_mean_z=mz, train_sd_z=sz, live_mean=mo, live_sd=so), teams=rows,
                          n_today_gt_c={c: sum(r['today'][c] > r['c'][c] for r in rows) for c in ('M0', 'M1', 'M2')})
json.dump(out, open(HERE / f'work/eval-{key}{"-fwd" if fwd else ""}.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k not in ('teams', 'forward')}, indent=1, ensure_ascii=False))
if fwd: print(out['forward']['n_today_gt_c'], out['forward']['map'])
