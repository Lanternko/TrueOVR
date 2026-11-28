"""E-078：臂展和抄截、防守嚇阻力（照 preregistration.md；共用 E-077 的比對與檢定）。"""
import csv, json, os, sys, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'E077-wingspan'))
import analyze as A  # noqa: E402

ROOT = A.ROOT
RAPM = os.path.join(ROOT, 'reports', 'impact-rapm')
MIN_POSS = 2000


def combine_lookup():
    by = {}
    for n, yr, hh, rr, ww in A.build_combine()['rows']:
        k = A.norm(n)
        if k not in by or yr >= by[k][0]:
            by[k] = (yr, hh, rr, ww)
    return by


def attach(o, by):
    k = A.norm(o['name'])
    m = by.get(k) or by.get(A.ALIAS.get(k, ''))
    o['ape'] = m[3] - m[1] if m else np.nan
    o['reach'] = (m[2] - m[1]) if m and m[2] else np.nan


def stl_by_season():
    """(季, PLAYER_ID) → STL/36。"""
    out = {}
    d7 = os.path.join(ROOT, 'data', 'defense-seventh')
    for s in [f'{y}-{str(y + 1)[2:]}' for y in range(2014, 2025)]:
        g = os.path.join(d7, s, 'player-games.json')
        if not os.path.exists(g):
            continue
        agg = collections.defaultdict(lambda: [0.0, 0])
        for r in A.rs(g):
            m = A.mins(r['MIN'])
            if m > 0:
                agg[r['PLAYER_ID']][0] += m
                agg[r['PLAYER_ID']][1] += r['STL'] or 0
        for i, (mn, st) in agg.items():
            out[(s, i)] = st / mn * 36
    for r in A.rs(os.path.join(ROOT, 'data', 'benchmark-source', 'base.json')):
        if r['MIN']:
            out[('2025-26', r['PLAYER_ID'])] = r['STL'] / r['MIN'] * 36
    return out


def latest_bio():
    bio = {}
    d7 = os.path.join(ROOT, 'data', 'defense-seventh')
    paths = [os.path.join(d7, f'{y}-{str(y + 1)[2:]}', 'bio.json') for y in range(2014, 2025)]
    paths.append(os.path.join(ROOT, 'data', 'benchmark-source', 'bio.json'))
    for p in paths:
        if os.path.exists(p):
            for r in A.rs(p):
                if r['PLAYER_HEIGHT_INCHES'] and r['PLAYER_WEIGHT']:
                    bio[r['PLAYER_ID']] = r
    return bio


def rapm_rows(by):
    bio = latest_bio()
    rows = {}
    for r in csv.DictReader(open(os.path.join(RAPM, 'rapm.csv'), encoding='utf-8')):
        rows[int(r['playerId'])] = {'pooledD': float(r['pooledD']), 'possD': float(r['pooledPoss'])}
    ff = {int(r['playerId']): r for r in csv.DictReader(open(os.path.join(RAPM, 'four-factors.csv'), encoding='utf-8'))}
    obs = {'rapm': [], 'ff': []}
    for pid, b in bio.items():
        base = dict(pid=pid, name=b['PLAYER_NAME'], h=float(b['PLAYER_HEIGHT_INCHES']), w=float(b['PLAYER_WEIGHT']))
        attach(base, by)
        if pid in rows and rows[pid]['possD'] >= MIN_POSS:
            obs['rapm'].append(dict(base, pooledD=rows[pid]['pooledD']))
        if pid in ff and float(ff[pid]['defensePossessions']) >= MIN_POSS:
            o = dict(base)
            for k in ('rimShare', 'efg', 'fgaPerPoss', 'threeShare', 'ftRate', 'steal', 'tovNonSteal'):
                o[k] = float(ff[pid][k + '_defense'])
            obs['ff'].append(o)
    return obs


def main():
    by = combine_lookup()
    seas, _ = A.season_rows()
    stl = stl_by_season()
    for o in seas:
        attach(o, by)
        o['stl36'] = stl.get((o['season'], o['pid']), np.nan)
    rp = rapm_rows(by)
    out = dict(seed=A.SEED, nboot=A.NBOOT, min_poss=MIN_POSS, S={}, D={}, report={}, reach={})
    out['S']['stl36'] = A.run(seas, 'stl36')
    out['reach']['stl36'] = A.run(seas, 'stl36', expo='reach')
    out['D']['pooledD'] = A.run(rp['rapm'], 'pooledD')
    out['reach']['pooledD'] = A.run(rp['rapm'], 'pooledD', expo='reach')
    for k in ('rimShare', 'efg'):
        out['D'][k] = A.run(rp['ff'], k)
        out['reach'][k] = A.run(rp['ff'], k, expo='reach')
    for k in ('steal', 'tovNonSteal', 'fgaPerPoss', 'threeShare', 'ftRate'):
        out['report'][k] = A.run(rp['ff'], k)
    out['S_pass'] = out['S']['stl36']['dr2_ci'][0] > 0
    out['D_passed'] = [k for k, v in out['D'].items() if v['dr2_ci'][0] > 0]
    out['D_pass'] = len(out['D_passed']) >= 2
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, default=float)


if __name__ == '__main__':
    main()
