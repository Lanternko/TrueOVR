"""0.2.10i 步驟 2：drive_D 的單季池值（E-101 合併池用），照 card-0.2.5+E101-crossera/work/pool_data.py v61_season 的 drive 段逐行複製，
只把 V61 history/pbp-drive-{季}.csv.gz 換成 E-190 work/history/pbp-drive-{OLD|D}-{季}.csv.gz（歷史目標的前三季也一起換）。
c0：OLD 的 2022-23～2024-25 要逐人等於 E-101 pool/raw-{季}.json attrs.drive（＝E-125 pool-P50，已驗相同），
    OLD 的 2025-26 池值（GP41≥15 且 MPG41≥20）排序後要等於 E-090 work/a0-raw.json drive.pool。
輸出 work/pool-drive-D.json：{季: {pid: score}}（2022-23～2025-26，D 類）與 c0 結果。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/drive_pool_D.py"""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = ROOT / 'reports'
V61 = R / 'ovr-v61-shrink-history-2025-26'
E190H = R / 'card-0.2.10c+E190-creation-jumper/work/history'
E101 = R / 'card-0.2.5+E101-crossera'
E090 = R / 'card-0.2.4+E090-onball-tail'
sys.path.insert(0, str(V61))
import engine as E  # noqa: E402
import build_attrs as B  # noqa: E402

TAG = {'v': None}
_orig = E.read_gz_csv


def read_gz_csv(path):
    p = Path(path)
    if p.name.startswith('pbp-drive-') and TAG['v']:
        p = E190H / p.name.replace('pbp-drive-', f'pbp-drive-{TAG["v"]}-')
    return _orig(p)


E.read_gz_csv = read_gz_csv
prod = json.load(open(V61 / 'backtest.json', encoding='utf-8'))['production']
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']


def season_min_gp(s, half1=False):
    mins, gp = defaultdict(float), defaultdict(int)
    for r in E.load_pergame(s):
        if half1 and r['half'] != '1':
            continue
        m = float(r['MIN'])
        pid = int(r['playerId'])
        mins[pid] += m
        gp[pid] += m > 0
    return mins, gp


def run(tag):
    TAG['v'] = tag
    cache = {s: E.season_halves(s) for s in E.DRIVE_SEASONS}
    pos_by = E.positions()

    def shrunk(attr, s, pids, fit, n, d, pos):
        ds = E.Dataset(attr, s, cache, pos_by, ids=pids)
        league_rate = n.sum() / d.sum()
        pn, pd_ = defaultdict(float), defaultdict(float)
        for i, p in enumerate(pids):
            pn[pos[p]] += n[i]; pd_[pos[p]] += d[i]
        m = np.full(len(pids), league_rate) if fit['prior'] == 'league' else np.array([pn[pos[p]] / pd_[pos[p]] for p in pids])
        return B.shrink(n, d, m, B.Hist(ds.hn, ds.hd), 'c', fit)

    out, pools = {}, {}
    for s in SEAS:
        mins, gp = season_min_gp(s)
        pids = sorted(p for p in mins if mins[p] > 0)
        pos = {p: E.pos_lookup(pos_by, p, s) for p in pids}
        dv, de = cache[s]['driveVol'], cache[s]['driveEff']
        z4 = [0.0] * 4
        mins41 = np.array([dv.get(p, z4)[1] for p in pids], float)
        nv = np.array([dv.get(p, z4)[0] for p in pids], float)
        pts = np.array([de.get(p, z4)[0] for p in pids], float)
        nW = np.array([de.get(p, z4)[1] for p in pids], float)
        _, gp41 = season_min_gp(s, half1=True)
        g = np.array([gp41.get(p, 0) for p in pids], float)
        inpool = (g >= B.POOL41[0]) & (mins41 / np.where(g > 0, g, 1) >= B.POOL41[1])
        comp = prod['drive']['components']
        rv = 36 * shrunk('driveVol', s, pids, comp['driveVol']['c'], nv, mins41, pos)
        re_ = shrunk('driveEff', s, pids, comp['driveEff']['c'], pts, nW, pos)
        sc = .5 * (rv - rv[inpool].mean()) / rv[inpool].std() + .5 * (re_ - re_[inpool].mean()) / re_[inpool].std()
        out[s] = {str(p): float(sc[i]) for i, p in enumerate(pids) if mins41[i] > 0}
        pools[s] = sorted(float(sc[i]) for i in range(len(pids)) if inpool[i])
    return out, pools


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    old, old_pool = run('OLD')
    c0 = {}
    for s in SEAS[:3]:
        ref = json.load(open(E101 / 'pool' / f'raw-{s}.json', encoding='utf-8'))['attrs']['drive']
        diff = [abs(old[s][k] - v) for k, v in ref.items() if k in old[s]]
        c0[s] = {'n_ref': len(ref), 'n_got': len(old[s]), 'n_common': len(diff), 'max_abs': max(diff), 'keys_equal': set(ref) == set(old[s])}
    a0 = sorted(json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))['drive']['pool'])
    c0['2025-26-pool'] = {'n_ref': len(a0), 'n_got': len(old_pool['2025-26']),
                          'max_abs': max(abs(a - b) for a, b in zip(a0, old_pool['2025-26'])) if len(a0) == len(old_pool['2025-26']) else None}
    c0['pass'] = all(c0[s]['keys_equal'] and c0[s]['max_abs'] < 1e-9 for s in SEAS[:3]) and c0['2025-26-pool']['max_abs'] is not None and c0['2025-26-pool']['max_abs'] < 1e-9
    new, new_pool = run('D')
    res = {'c0': c0, 'D': new, 'D_pool2526': new_pool['2025-26'], 'n_D': {s: len(new[s]) for s in SEAS}}
    (HERE / 'work/pool-drive-D.json').write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(c0, ensure_ascii=False, indent=1), res['n_D'])


if __name__ == '__main__':
    main()
