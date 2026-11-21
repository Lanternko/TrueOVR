"""E-228 缺陣敏感度（只報告）：沿用 E-223 A 線的 snapshot 與輪替（aline-jobs／aline-meta，只含陣容，無比賽結果）。
每個 snapshot（隊、第 n 場的今日陣容）逐一拿掉輪替內一人後，T 的 ΔNet＝(原輪替 − 移除後輪替) 打「聯盟平均對手」的淨值差（換算成每場邊際）。
對手：從該季全部 lineups 的隊伍輪替隨機抽一隊（固定 rng），再按分鐘抽 5 人；所有輪替共用同一批對手（共同隨機數）。
報 ΔNet 與 x（Σ(min/240)·z 前後差）的 Pearson r（snapshot 為單位 cluster bootstrap 2000 次、rng 20261102），與同一批 M0 的 r 並列。
  python -I -X utf8 aline_t.py --key 2425 --weights T2425 --prior 2023-24 --out aline-2425.json"""
import argparse, glob, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t_lib import *

ap = argparse.ArgumentParser()
ap.add_argument('--key', required=True); ap.add_argument('--weights', required=True); ap.add_argument('--prior', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--draws', type=int, default=1000); ap.add_argument('--threads', type=int, default=6); ap.add_argument('--dev', default='cpu'); ap.add_argument('--limit', type=int, default=0)
a = ap.parse_args(); torch.set_num_threads(a.threads)
C = Ctx(a.weights, a.prior, a.dev); N = a.draws
jobs = json.load(open(os.path.join(E223, f'aline-jobs-{a.key}.json')))['jobs']; meta = json.load(open(os.path.join(E223, f'aline-meta-{a.key}.json')))
lin = json.load(open(os.path.join(E223, f'lineups-{a.key}.json'), encoding='utf-8'))
rng0 = np.random.default_rng([228, 7]); keys = sorted(lin); pool = [keys[j] for j in rng0.choice(len(keys), 400, replace=False)]
pp = [C.prep(lin[k]) for k in pool]
opp = np.concatenate([C.draw(*pp[rng0.integers(len(pool))], rng0, 1) for _ in range(N)], 0)       # [N,5,2F]：每個 draw 一個隨機隊的 5 人
net = {}; t0 = time.time()
jl = jobs if not a.limit else [j for j in jobs if j['key'] < a.limit * 10]
for j in jl:
    R, lm, rk = C.prep(j['roster']); rng = np.random.default_rng([228, j['seedKey'], 1])
    net[j['key']] = C.net100(C.draw(R, lm, rk, rng, N), opp).mean(1) * C.avg_poss / 100   # [5 seed]
    if j['key'] % 200 == 0: print(j['key'], round(time.time() - t0), 's', flush=True)
sims = {}
for f in glob.glob(os.path.join(E223, f'sims-a{a.key}', 'o-*.json')):
    for r in json.load(open(f))['res']: sims[r['key']] = r['msum'] / r['n']
rows = []
for m in meta:
    b, r = m['snap'] * 10, m['snap'] * 10 + m['slot']
    if b in net and r in net:
        rows.append(dict(snap=m['snap'], x=m['x'], dT=(net[b] - net[r]).tolist(), dM0=(sims[b] - sims[r]) if b in sims and r in sims else None))
x = np.array([r['x'] for r in rows]); T5 = np.array([r['dT'] for r in rows]); dT = T5.mean(1); sn = np.array([r['snap'] for r in rows])
ok = np.array([r['dM0'] is not None for r in rows]); dM = np.array([r['dM0'] if r['dM0'] is not None else np.nan for r in rows])
corr = lambda u, v: float(np.corrcoef(u, v)[0, 1])
rng = np.random.default_rng(20261102); us = np.unique(sn); ix = {s: np.where(sn == s)[0] for s in us}; bs = []
for _ in range(2000):
    sel = np.concatenate([ix[s] for s in rng.choice(us, len(us))]); o = sel[ok[sel]]
    bs.append((corr(dT[sel], x[sel]), corr(dM[o], x[o]), corr(dT[o], x[o]) - corr(dM[o], x[o])))
bs = np.array(bs); q = lambda c: [float(np.percentile(bs[:, c], 5)), float(np.percentile(bs[:, c], 95))]
sl = float(np.polyfit(x, dT, 1)[0])
res = dict(key=a.key, weights=a.weights, prior=a.prior, draws=N, n_removals=len(rows), n_snap=len(us), n_with_M0=int(ok.sum()),
           r_T=corr(dT, x), r_T_ci90=q(0), r_M0=corr(dM[ok], x[ok]), r_M0_ci90=q(1), r_T_minus_M0_same_rows=corr(dT[ok], x[ok]) - corr(dM[ok], x[ok]), diff_ci90=q(2),
           slope_T_margin_per_x=sl, dT_sd=float(dT.std()), x_sd=float(x.std()), sd_across_seeds_dT=float(T5.std(1, ddof=1).mean()))
json.dump(res, open(os.path.join(HERE, a.out), 'w'), indent=1); print(json.dumps(res, indent=1))
