"""defense-update-speed 分析（預註冊 §4–§6 寫死）。讀 out/arms-<季>.json、out/sim-<季>-*.json、out/attrs-<季>.json.gz、out/desc-*.json，
寫 ../analysis.json。用法：python -I -X utf8 analyze.py"""
import glob, gzip, json, statistics as stt
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
SEASONS = ('2024-25', '2025-26')
ARMS = ('A0', 'A1', 'A2')
B, SEED = 5000, 20261102
MIN_REM = 500


def ci(x, lv):
    return [float(np.percentile(x, 50 - lv / 2)), float(np.percentile(x, 50 + lv / 2))]


def primary(season):
    A = json.load(open(OUT / f'arms-{season}.json', encoding='utf-8'))
    sim = {}
    for f in glob.glob(str(OUT / f'sim-{season}-*.json')):
        for o in json.load(open(f, encoding='utf-8'))['res']:
            sim[(o['team'], o['N'], o['arm'])] = 100 * o['pa'] / o['poa']
    teams = sorted({s['team'] for s in A['snaps']})
    act = {(s['team'], s['N']): s['drtgRem'] for s in A['snaps']}
    assert len(sim) == len(act) * len(ARMS), (len(sim), len(act))
    rel_a, rel_m = {}, {}
    for N in (10, 20):
        ma = stt.mean(act[(t, N)] for t in teams)
        for t in teams:
            rel_a[(t, N)] = act[(t, N)] - ma
        for arm in ARMS:
            mm = stt.mean(sim[(t, N, arm)] for t in teams)
            for t in teams:
                rel_m[(t, N, arm)] = sim[(t, N, arm)] - mm
    err = {arm: np.array([[abs(rel_m[(t, N, arm)] - rel_a[(t, N)]) for N in (10, 20)] for t in teams]) for arm in ARMS}   # [隊, N]
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(teams), size=(B, len(teams)))
    out = {'nTeams': len(teams), 'mae': {}, 'maeByN': {}, 'delta': {}, 'deltaByN': {}, 'corr': {}}
    for arm in ARMS:
        out['mae'][arm] = float(err[arm].mean())
        out['maeByN'][arm] = {str(N): float(err[arm][:, i].mean()) for i, N in enumerate((10, 20))}
        out['corr'][arm] = float(np.corrcoef([rel_m[(t, N, arm)] for t in teams for N in (10, 20)],
                                             [rel_a[(t, N)] for t in teams for N in (10, 20)])[0, 1])
    for arm in ('A1', 'A2'):
        d = err[arm] - err['A0']                       # [隊, N]
        boot = d[idx].mean(axis=(1, 2))
        out['delta'][arm] = {'point': float(d.mean()), 'ci90': ci(boot, 90), 'ci95': ci(boot, 95)}
        out['deltaByN'][arm] = {}
        for i, N in enumerate((10, 20)):
            bn = d[:, i][idx].mean(axis=1)
            out['deltaByN'][arm][str(N)] = {'point': float(d[:, i].mean()), 'ci90': ci(bn, 90)}
    out['perTeam'] = [dict(team=s['team'], abbr=s['abbr'], N=s['N'], D=s['D'], gRem=s['gRem'], actualRel=rel_a[(s['team'], s['N'])],
                           **{f'model{arm}': rel_m[(s['team'], s['N'], arm)] for arm in ARMS}) for s in A['snaps']]
    return out


def next_day(D):
    import datetime as dt
    return (dt.date.fromisoformat(D) + dt.timedelta(days=1)).isoformat()


def secondary(season):
    A = json.load(open(OUT / f'arms-{season}.json', encoding='utf-8'))
    X = json.load(gzip.open(OUT / f'attrs-{season}.json.gz', 'rt', encoding='utf-8'))
    vets = set(X['vets'])
    res = {}
    for N in (10, 20):
        ds = sorted(s['D'] for s in A['snaps'] if s['N'] == N)
        D = ds[len(ds) // 2]                             # 該季第 N 場快照日的中位數（預註冊 §5）
        tgt = X['tgt'][D]
        # 預註冊 §5「D 之後出場 ≥ 500 分鐘」：advanced 表（PerMode=Totals）的 MIN 實為每場平均，總分鐘＝MIN×GP（2026-11-02 跑後發現，只修實作、門檻不變）
        adv = json.load(open(HERE.parent / 'data/cut' / season / f'from-{next_day(D)}-advanced.json', encoding='utf-8'))['data']['resultSets'][0]
        I = adv['headers'].index
        mtot = {str(r[I('PLAYER_ID')]): r[I('MIN')] * r[I('GP')] for r in adv['rowSet']}
        for p in tgt:
            tgt[p]['minRem'] = mtot.get(p, 0)
        r = {'D': D}
        for a in ('onBall', 'help'):
            pids = [p for p in tgt if int(p) in vets and tgt[p].get('minRem', 0) >= MIN_REM and a in tgt[p]
                    and all(a in X['win'][D][arm].get(p, {}) for arm in ARMS)]
            e = {arm: np.array([abs(X['win'][D][arm][p][a] - tgt[p][a]) for p in pids]) for arm in ARMS}
            rng = np.random.default_rng(SEED)
            idx = rng.integers(0, len(pids), size=(B, len(pids)))
            r[a] = {'n': len(pids), 'mae': {arm: float(e[arm].mean()) for arm in ARMS}}
            for arm in ('A1', 'A2'):
                d = e[arm] - e['A0']
                r[a][f'delta{arm}'] = {'point': float(d.mean()), 'ci90': ci(d[idx].mean(axis=1), 90)}
        res[str(N)] = r
    return res


def descriptive():
    desc = json.load(open(OUT / 'desc-2026-27.json', encoding='utf-8'))
    out = {'c': desc['c'], 'curWeight': {arm: desc['arms'][arm]['weights'].get('2026-27') for arm in ARMS}, 'phiPlayers': {}, 'drtg': {}}
    for arm in ARMS:
        for p, v in desc['arms'][arm]['phi'].items():
            out['phiPlayers'].setdefault(v['name'], {})[arm] = {k: v.get(k) for k in ('onBall', 'help')}
        fs = glob.glob(str(OUT / f'desc-sim-{arm}-*.json'))
        if not fs:
            continue
        r = {}
        for f in fs:
            for o in json.load(open(f, encoding='utf-8'))['res']:
                r[str(o['team'])] = 100 * o['pa'] / o['poa']
        m = stt.mean(r.values())
        out['drtg'][arm] = {'PHI': r.get('1610612755', float('nan')) - m, 'rank': 1 + sorted(r.values()).index(r['1610612755'])}
    return out


if __name__ == '__main__':
    res = {'primary': {s: primary(s) for s in SEASONS}, 'secondary': {s: secondary(s) for s in SEASONS}, 'descriptive': descriptive()}
    p25, p26 = res['primary']['2024-25']['delta'], res['primary']['2025-26']['delta']
    # 預註冊 §4：臂 k 通過＝2024-25 ΔMAE 的 95% CI（兩臂 Bonferroni，對應單臂 90%）上界 < 0，且 2025-26 點估計 < 0
    res['H1'] = {arm: {'pass2425': p25[arm]['ci95'][1] < 0, 'sameDir2526': p26[arm]['point'] < 0,
                       'pass': p25[arm]['ci95'][1] < 0 and p26[arm]['point'] < 0} for arm in ('A1', 'A2')}
    res['H1']['any'] = any(res['H1'][a]['pass'] for a in ('A1', 'A2'))
    json.dump(res, open(HERE.parent / 'analysis.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'H1': res['H1'], 'mae': {s: res['primary'][s]['mae'] for s in SEASONS},
                      'delta': {s: res['primary'][s]['delta'] for s in SEASONS}}, indent=1))
