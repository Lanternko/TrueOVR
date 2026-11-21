"""E-273 重度部分（5090）：每個抽樣種子跑 T0／T1／T1tov（診斷：tovSkill 凍結在 0.2.9）／today（R-172 用：以「當天的 T」重算過去已完賽場次的預期）。
方法同 E-229b／E-246 pred_t：同一份陣容分鐘、5 個 net 取平均、N=2000 抽樣、rng=[seed, gid]（seed=229 即 E-246 原設定）。不讀任何比賽結果。
python -I -X utf8 run_t.py <seed> [--dates N]  → work/seed_<seed>.json
樹狀結構假設：本檔在 <ROOT>/reports/team-model-versions/，e229_live 在 <ROOT>/reports/E229-transformer-vs-m0-forward/（本機與 5090 同構）。"""
import json, os, sys, csv, shutil, collections, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np, torch
torch.set_num_threads(int(os.environ.get('NTHREADS', '3')))
import e229_live

SEED = int(sys.argv[1]); NDATES = int(sys.argv[sys.argv.index('--dates') + 1]) if '--dates' in sys.argv else None
LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
W = os.path.join(HERE, 'work')
games = json.load(open(os.path.join(W, 'games.json'))); rots = json.load(open(os.path.join(W, 'rots.json')))
TOV_OLD_FROM, TOV_OLD_SRC = '2026-10-31', '2026-10-30'


def tovold_tree():
    """診斷臂：從 0.2.12b（10-31 夾）起把 tovSkill 換回 0.2.9（10-30 夾）的值（舊夾沒有的人保留新值），其餘欄不動。"""
    out = os.path.join(W, 'live_tovold'); src = {r['playerId']: r['tovSkill'] for r in csv.DictReader(open(os.path.join(LIVE, TOV_OLD_SRC, 'ranking.csv'), encoding='utf-8'))}
    for f in sorted({g['folder'] for g in games}):
        if f < TOV_OLD_FROM:
            continue
        os.makedirs(os.path.join(out, f), exist_ok=True)
        shutil.copy(os.path.join(LIVE, f, 'meta.json'), os.path.join(out, f, 'meta.json'))
        R = list(csv.DictReader(open(os.path.join(LIVE, f, 'ranking.csv'), encoding='utf-8')))
        with open(os.path.join(out, f, 'ranking.csv'), 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(R[0].keys())); w.writeheader()
            for r in R:
                if r['playerId'] in src:
                    r['tovSkill'] = src[r['playerId']]
                w.writerow(r)
    return out


def ldir(root, f):
    p = os.path.join(root, f)
    return p if os.path.isdir(p) else os.path.join(LIVE, f)


def predict(C, rh, ra, gid):
    Rh, lh, rhk = C.prep(rh); Ra, la, rak = C.prep(ra)
    rng = np.random.default_rng([SEED, int(gid)])
    x = C.net100(C.draw(Rh, lh, rhk, rng, 2000), C.draw(Ra, la, rak, rng, 2000))
    return float((x.mean(1) * C.avg_poss / 100).mean())


class Runner:
    def __init__(self, blend, root):
        self.blend, self.root, self.C = blend, root, None

    def ctx(self, d, f, names):
        snap = os.path.join(HERE, 'snap', d)
        if self.C is None:
            self.C, info = e229_live.make_ctx(d, ldir(self.root, f), names, self.blend, snap)
        else:
            B, tab, info = e229_live.build(d, ldir(self.root, f), names, self.blend, snap)
            self.C.B = B; self.C.tab = tab
            self.C.med_h = float(np.median([x['heightInches'] for x in tab.values() if x.get('heightInches') is not None]))
        return self.C


byd = collections.defaultdict(list)
for g in games:
    byd[(g['date'], g['folder'])].append(g)
keys = sorted(byd)[:NDATES]
t0 = time.time(); out = {}
arms = {'T0': ((), LIVE), 'T1': (e229_live.TRACK_CLASSES, LIVE), 'T1tov': (e229_live.TRACK_CLASSES, tovold_tree())}
for arm, (blend, root) in arms.items():
    R = Runner(blend, root); res = {}
    for d, f in keys:
        gs = byd[(d, f)]
        names = {p: 1 for g in gs for s in ('home', 'away') for p, _ in g['rot_' + s]}
        C = R.ctx(d, f, names)
        for g in gs:
            res[g['gid']] = predict(C, g['rot_home'], g['rot_away'], g['gid'])
    out[arm] = res; print(SEED, arm, len(res), f'{time.time() - t0:.0f}s', flush=True)
# R-172：當天的 T（T1 特徵＋當天 live 夾）重算所有比賽日 < d 的已完賽場次
R = Runner(e229_live.TRACK_CLASSES, LIVE); today = {}
dates = {g['gid']: g['date'] for g in games}
for d, f in keys:
    past = [g for g in games if g['date'] < d]
    names = {p: 1 for g in games if g['date'] <= d for rot in rots[f][g['gid']] for p, _ in rot}
    C = R.ctx(d, f, names)
    today[d] = {g['gid']: predict(C, rots[f][g['gid']][0], rots[f][g['gid']][1], g['gid']) for g in past}
    print(SEED, 'today', d, len(past), f'{time.time() - t0:.0f}s', flush=True)
out['today'] = today
json.dump(out, open(os.path.join(W, f'seed_{SEED}.json' if NDATES is None else f'smoke_{SEED}.json'), 'w'))
print(SEED, 'DONE', f'{time.time() - t0:.0f}s', flush=True)
