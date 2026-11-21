"""E-289 M1/M2：線上 T 換人值，把球員自己的護框／籃板／對照特徵設成聯盟平均，看掉多少（credit），再看 OVR 少算哪組。
用法（repo root）：python -I -B -X utf8 reports/E289-rim-vs-reb-T/e289_t.py [live_dir]"""
import csv, datetime as dt, hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'reports/E229-transformer-vs-m0-forward'))
sys.path.insert(0, str(ROOT / 'reports/E228-transformer-team-rating'))
sys.path.insert(0, str(ROOT / 'reports/E227-lineup-transformer-r2'))
sys.path.insert(0, str(ROOT / 'scripts'))
N_DRAWS, SEED, BSEED, B = 3000, 20261108, 20261289, 2000
GROUPS = {'RIM': ['help', 'blk36', 'cont2pt36'],
          'REB': ['rebound', 'oreb36', 'dreb36', 'orebPct', 'drebPct', 'boxoutO36', 'boxoutD36'],
          'CTRL': ['screenAst36'],
          'REB_O': ['oreb36', 'orebPct', 'boxoutO36'],
          'REB_D': ['dreb36', 'drebPct', 'boxoutD36', 'rebound']}
SHOW = ['Rudy Gobert', 'Jarrett Allen', 'Isaiah Hartenstein', 'Myles Turner', 'Ivica Zubac', 'Jakob Poeltl', 'Steven Adams',
        'Evan Mobley', 'Bam Adebayo', 'Nikola Jokić', 'Victor Wembanyama', 'Domantas Sabonis', 'Alperen Sengun', 'Chet Holmgren',
        'Walker Kessler', 'Daniel Gafford', 'Dereck Lively II', 'Mitchell Robinson', 'Clint Capela', 'Nic Claxton']


def pct(v):
    import numpy as np
    return (np.argsort(np.argsort(v)) + 0.5) / len(v)


def main(ldir: Path):
    import numpy as np, torch
    import e229_live
    from e227_common import ATTRS, STATS
    from e227_model import predict
    import season_nav as sn
    torch.set_num_threads(4)
    pre = HERE / 'preregistration.md'
    assert hashlib.sha256(pre.read_bytes()).hexdigest() == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'
    cols = ATTRS + STATS; F = len(cols)
    idx = {g: [cols.index(c) for c in cs] for g, cs in GROUPS.items()}
    t0 = time.time()
    meta = json.loads((ldir / 'meta.json').read_text(encoding='utf-8'))
    today = (dt.date.fromisoformat(meta['dataCutoff']) + dt.timedelta(days=1)).isoformat()
    rows = list(csv.DictReader(open(ldir / 'ranking.csv', encoding='utf-8')))
    info = {r['playerId']: r for r in rows}
    C, _ = e229_live.make_ctx(today, str(ldir))
    pool = sn.mpg_pool({r['playerId']: float(r['MIN26'] or 0) / int(r['N']) for r in rows if int(r['N'])})
    pool = sorted(p for p in pool if p in C.B and p in info)
    rng = np.random.default_rng(SEED)
    draws = [list(rng.choice(pool, 10, replace=False)) for _ in range(N_DRAWS)]
    V = {p: C.vec(p) for p in pool}
    order = lambda l: sorted(l, key=C.hkey)
    pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    N = N_DRAWS
    A = np.stack([np.stack([V[p] for p in order(d[4:9])]) for d in draws])

    def value(x, vx):
        W = dict(V); W[x] = vx
        Ao = A.copy()
        for i, d in enumerate(draws):
            if x in d[4:9]:
                Ao[i] = np.stack([W[p] for p in order([d[9] if q == x else q for q in d[4:9]])])
        H = [[d[9] if q == x else q for q in d[:4]] for d in draws]
        Hs = np.stack([np.stack([W[p] for p in order(m + [x])]) for m in H])
        X = torch.from_numpy(np.concatenate([np.concatenate([Hs, Ao], 1), np.concatenate([Ao, Hs], 1)], 0))
        T = [X, pos.expand(2 * N, -1), side.expand(2 * N, -1)]
        o_, d_ = [], []
        for m in C.nets:
            o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy() * 100
            o_.append(0.5 * (o[:N, 0] + o[N:, 1])); d_.append(0.5 * (o[:N, 1] + o[N:, 0]))
        return float(np.mean(o_)), float(np.mean(d_))

    out = {}
    for k, x in enumerate(pool):
        r = {}
        own, opp = value(x, V[x]); r['full'] = [own, opp]
        for g, ii in idx.items():
            v = V[x].copy(); v[ii] = 0.0          # 值設聯盟平均，遮罩不動
            r[g] = list(value(x, v))
        out[x] = r
        if k % 20 == 0:
            print(f'{k}/{len(pool)} {time.time() - t0:.0f}s', flush=True)
    net = lambda a: a[0] - a[1]
    ids = pool
    nf = np.array([net(out[p]['full']) for p in ids])
    cr = {g: np.array([net(out[p]['full']) - net(out[p][g]) for p in ids]) for g in GROUPS}
    crd = {g: np.array([out[p][g][1] - out[p]['full'][1] for p in ids]) for g in GROUPS}   # 防守端：設平均後對手多得幾分
    ovr = np.array([float(info[p]['ovr']) for p in ids])
    posv = np.array([info[p]['pos'] for p in ids])
    gap = pct(nf) - pct(ovr)
    res = {'prereg_sha256': (HERE / 'preregistration.sha256').read_text().strip(), 'live_dir': str(ldir.relative_to(ROOT)),
           'dataCutoff': meta['dataCutoff'], 'n_pool': len(ids), 'seconds': round(time.time() - t0, 1)}
    res['credit_by_pos'] = {pv: {g: float(cr[g][posv == pv].mean()) for g in GROUPS} | {'n': int((posv == pv).sum()), 'net': float(nf[posv == pv].mean()), 'gap': float(gap[posv == pv].mean())}
                            for pv in ('PG', 'SG', 'SF', 'PF', 'C')}
    res['credit_def_by_pos'] = {pv: {g: float(crd[g][posv == pv].mean()) for g in GROUPS} for pv in ('PG', 'SG', 'SF', 'PF', 'C')}
    # M2：gap ~ z(cRIM)+z(cREB)+z(cCTRL)+位置
    z = lambda v: (v - v.mean()) / v.std()
    Xd = np.column_stack([np.ones(len(ids)), z(cr['RIM']), z(cr['REB']), z(cr['CTRL'])] + [(posv == pv).astype(float) for pv in ('SG', 'SF', 'PF', 'C')])
    beta = lambda I: np.linalg.lstsq(Xd[I], gap[I], rcond=None)[0]
    b0 = beta(np.arange(len(ids)))
    brng = np.random.default_rng(BSEED)
    bs = np.array([beta(brng.integers(0, len(ids), len(ids))) for _ in range(B)])
    ci = lambda v: [float(np.percentile(v, 5)), float(np.percentile(v, 95))]
    res['M2'] = {'beta_RIM': float(b0[1]), 'ci_RIM': ci(bs[:, 1]), 'beta_REB': float(b0[2]), 'ci_REB': ci(bs[:, 2]),
                 'beta_CTRL': float(b0[3]), 'ci_CTRL': ci(bs[:, 3]), 'diff_RIM_REB': float(b0[1] - b0[2]), 'ci_diff': ci(bs[:, 1] - bs[:, 2])}
    # 只有 PF/C 子集（報告）
    m = np.isin(posv, ['PF', 'C'])
    Xb = np.column_stack([np.ones(m.sum()), z(cr['RIM'][m]), z(cr['REB'][m]), z(cr['CTRL'][m]), (posv[m] == 'C').astype(float)])
    res['M2_bigs'] = dict(zip(['c', 'RIM', 'REB', 'CTRL', 'isC'], map(float, np.linalg.lstsq(Xb, gap[m], rcond=None)[0])))
    rk_t = (-nf).argsort().argsort() + 1; rk_o = (-ovr).argsort().argsort() + 1
    nm = {p: info[p]['name'] for p in ids}
    res['players'] = {nm[p]: {'pos': info[p]['pos'], 'rankT': int(rk_t[i]), 'rankOVR': int(rk_o[i]), 'net': round(float(nf[i]), 2),
                              **{g: round(float(cr[g][i]), 2) for g in GROUPS}} for i, p in enumerate(ids)}
    res['raw'] = out
    (HERE / 't_results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('credit_by_pos', 'credit_def_by_pos', 'M2', 'M2_bigs')}, ensure_ascii=False, indent=1))
    for s in SHOW:
        if s in res['players']:
            print(s, res['players'][s])


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-07')
