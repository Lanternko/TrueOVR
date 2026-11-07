"""賽中 RAPM 窗 R_N（v5/pathA/preregistration-rapm-inseason.md §2）。

三段：
  plan   （本機）每個起點、每個 N 的季權重與目標季可放進的比賽（兩隊各自前 N 場內），
         寫 v5/pathA/rapm-inseason/plan.json，並列出要帶去 5090 的 stint 檔。
  fit    （5090）讀 plan.json 與 stint，呼叫 reports/impact-rapm/rapm.py 的 observations / fit_rapm；
         淡出季的 points 與 possessions 同乘 m（y 不變、權重 ×m）。輸出 rapm-<起點>-N<n>.csv、pipe-*.csv。
  check  （本機）R1：R_0 對預測窗、R_82 對答案窗，逐球員 |net| 差 ≤ 0.01。
"""
import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
N_LIST = [0, 3, 5, 10, 20, 82]
TOL = 0.01


def seasons_of(tag):
    a, b = tag.split('_') if '_' in tag else (tag, tag)
    y0, y1 = int(a[:4]), int(b[:4])
    return [f'{y}-{(y + 1) % 100:02d}' for y in range(y0, y1 + 1)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------- plan（本機）
def stint_source(root, season):
    if season == '2025-26':
        return root / 'reports/defense-b1/stints.jsonl'
    if season == '2021-22':
        return root / 'reports/ovr-inseason-2026-27/v3/data/derived-2021-22/stints/stints.jsonl'
    return root / f'reports/defense-seventh/{season}/stints/stints.jsonl'


def plan():
    sys.path.insert(0, str(HERE))
    import pathA_common as PA
    from pathA_common import base as C
    import inseason_common as IC
    PA.install()
    root = C.ROOT
    out = {'starts': {}, 'stints': {}}
    for s in PA.ORDER:
        ch = PA.CHAIN_U[s]
        if not ch.get('buildable', True):
            continue
        t = ch['target']
        P = seasons_of(ch['pred'])
        Q = seasons_of('2022-23_2025-26') if ch['ans'] == 'formal-card-H1-m0' else seasons_of(ch['ans'])
        extra = [q for q in Q if q not in P and q != t]
        rec = {'target': t, 'P': P, 'Q': Q, 'predTag': ch['pred'], 'ansTag': ch['ans']}
        if extra:
            rec['stopped'] = f'Q 有不在 P 的非目標季 {extra}'
            out['starts'][s] = rec
            continue
        sd = C.load_target_season(t)
        idx = IC.team_game_index(sd)
        per_team = {}
        for (tid, gid), i in idx.items():
            per_team[tid] = max(per_team.get(tid, 0), i)
        G = statistics.median(per_team.values()) if t == '2019-20' else PA.G_SEASON[t]
        games = {}
        for (tid, gid), i in idx.items():
            g = games.setdefault(str(gid), [])
            g.append(i)
        rec['G'] = G
        rec['windows'] = {}
        for N in N_LIST:
            f = min(N / G, 1.0)
            w = {q: (1.0 if q in Q else 1.0 - f) for q in P}
            if N == 0:
                tg = []
            elif N == 82:
                tg = sorted(games)
            else:
                tg = sorted(g for g, ix in games.items() if len(ix) == 2 and max(ix) <= N)
            rec['windows'][str(N)] = {'f': f, 'seasonWeight': w, 'targetGames': tg}
        out['starts'][s] = rec
    need = sorted({q for r in out['starts'].values() for q in r['P'] + [r['target']]})
    for q in need:
        p = stint_source(root, q)
        out['stints'][q] = {'path': p.relative_to(root).as_posix(), 'sha256': sha(p)}
    dst = PA.PATHA / 'rapm-inseason'
    dst.mkdir(parents=True, exist_ok=True)
    (dst / 'plan.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for s, r in out['starts'].items():
        print(s, r.get('stopped') or {N: len(v['targetGames']) for N, v in r['windows'].items()}, r.get('G'))


# ---------------------------------------------------------------- fit（5090）
def weighted(obs, w, keep_target, target):
    for o in obs:
        season, gid, op, dp, pts, poss, ot, dt = o
        if season == target:
            if gid not in keep_target:
                continue
            m = 1.0
        else:
            m = w[season]
            if m <= 0:
                continue
        yield season, gid, op, dp, pts * m, poss * m, ot, dt


def fit(bundle, only=None):
    sys.path.insert(0, str(bundle / 'reports/impact-rapm'))
    import rapm
    pl = json.loads((bundle / 'reports/ovr-inseason-2026-27/v5/pathA/rapm-inseason/plan.json').read_text(encoding='utf-8'))
    out = bundle / 'reports/ovr-inseason-2026-27/v5/pathA/rapm-inseason'
    cache = {}

    def season_obs(q):
        if q not in cache:
            src = bundle / pl['stints'][q]['path']
            cache[q] = [tuple(o[:1]) + (str(o[1]),) + o[2:]
                        for o in rapm.observations([q], lambda _s: open(src, encoding='utf-8'))]
        return cache[q]

    man = {}
    for s, r in pl['starts'].items():
        if 'stopped' in r or (only and s not in only):
            continue
        for N, win in r['windows'].items():
            t0 = time.time()
            keep = set(win['targetGames'])
            obs = []
            for q in r['P']:
                obs.extend(weighted(season_obs(q), win['seasonWeight'], keep, r['target']))
            if keep:
                obs.extend(weighted(season_obs(r['target']), win['seasonWeight'], keep, r['target']))
            players = sorted({p for o in obs for p in o[2] + o[3]})
            res, info = rapm.fit_rapm(obs, players)
            tag = f'{s}-N{N}'
            with open(out / f'rapm-{tag}.csv', 'w', encoding='utf-8', newline='') as fh:
                w = csv.writer(fh)
                w.writerow(['playerId', 'net', 'O', 'D', 'poss'])
                for p in sorted(res, key=lambda p: -res[p]['net']):
                    v = res[p]
                    w.writerow([p, round(v['net'], 3), round(v['O'], 3), round(v['D'], 3), round(v['poss'])])
            man[tag] = {'observations': len(obs), 'players': len(players), 'lambda': info['lambda'],
                        'cv': info['cvWeightedMSE'], 'targetGames': len(keep),
                        'targetPoss': round(sum(o[5] for o in obs if o[0] == r['target']), 1),
                        'seasonWeight': win['seasonWeight'], 'seconds': round(time.time() - t0, 1)}
            print(tag, len(obs), len(players), info['lambda'], f'{time.time() - t0:.0f}s', flush=True)
            (out / f'manifest-fit{"-" + "-".join(only) if only else ""}.json').write_text(
                json.dumps(man, indent=1), encoding='utf-8')


# ---------------------------------------------------------------- check（本機）
def read_net(p):
    out = {}
    for r in csv.DictReader(open(p, encoding='utf-8')):
        out[int(r['playerId'])] = float(r.get('pooledNet') or r['net'])
    return out


def to_pipe(src, dst, names):
    with open(dst, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss',
                    'lastSeasonNet', 'lastSeasonO', 'lastSeasonD', 'lastSeasonPoss'])
        for r in csv.DictReader(open(src, encoding='utf-8')):
            w.writerow([r['playerId'], names.get(int(r['playerId']), ''), r['net'], r['O'], r['D'], r['poss'],
                        0, 0, 0, 0])


def check():
    sys.path.insert(0, str(HERE))
    import pathA_common as PA
    from pathA_common import base as C
    PA.install()
    d = PA.PATHA / 'rapm-inseason'
    pl = json.loads((d / 'plan.json').read_text(encoding='utf-8'))
    rep = {}
    for s, r in pl['starts'].items():
        if 'stopped' in r:
            rep[s] = {'stopped': r['stopped']}
            continue
        ref0 = read_net(C.rapm_path(r['predTag']))
        ans = (C.ROOT / 'reports/impact-rapm/rapm.csv' if r['ansTag'] == 'formal-card-H1-m0'
               else C.rapm_path(r['ansTag']))
        ref82 = read_net(ans)
        rec = {}
        for N, ref, src in (('0', ref0, C.rapm_path(r['predTag'])), ('82', ref82, ans)):
            got = read_net(d / f'rapm-{s}-N{N}.csv')
            common = set(got) & set(ref)
            rec[N] = {'ref': Path(src).relative_to(C.ROOT).as_posix(), 'onlyNew': len(set(got) - set(ref)),
                      'onlyRef': len(set(ref) - set(got)),
                      'maxAbsNetDiff': max(abs(got[p] - ref[p]) for p in common) if common else None}
            rec[N]['pass'] = (rec[N]['onlyNew'] == 0 and rec[N]['onlyRef'] == 0
                              and rec[N]['maxAbsNetDiff'] is not None and rec[N]['maxAbsNetDiff'] <= TOL)
        rec['pass'] = rec['0']['pass'] and rec['82']['pass']
        rep[s] = rec
        names = {}
        for p in (C.rapm_path(r['predTag']), ans):
            for row in csv.DictReader(open(p, encoding='utf-8')):
                names.setdefault(int(row['playerId']), row.get('name', ''))
        for N in r['windows']:
            to_pipe(d / f'rapm-{s}-N{N}.csv', d / f'pipe-{s}-N{N}.csv', names)
        print(s, rec['0']['maxAbsNetDiff'], rec['0']['onlyNew'], rec['0']['onlyRef'], '|',
              rec['82']['maxAbsNetDiff'], rec['82']['onlyNew'], rec['82']['onlyRef'], 'pass' if rec['pass'] else 'FAIL')
    (d / 'r1-check.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['plan', 'fit', 'check'])
    ap.add_argument('--bundle', type=Path)
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    if a.mode == 'plan':
        plan()
    elif a.mode == 'fit':
        fit(a.bundle, a.only)
    else:
        check()
