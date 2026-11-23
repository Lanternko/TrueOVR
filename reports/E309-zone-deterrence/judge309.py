"""E-309 (b) 判定（prereg.md 凍結）：j2／j2c／j3 同 E-166 judge 算法，B＝E-166 checkpoint-k／rr-k，Z＝本實驗 checkpoint-Z／rr-Z。
另報解析換算淨值（每壓低 1 個百分點對手禁區佔比＝每 100 回合少幾分）。cwd＝主 checkout。
  python -I -X utf8 <本檔> [Z 結果目錄，預設本目錄 results/sim]"""
import csv, json, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ZD = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'results' / 'sim'
D, E = 'reports/sim-0.1.2+E166-ft-defense/', 'reports/E140-foul-on-recal/'
G = json.load(open(D + 'frozen-groups.json', encoding='utf-8'))
RP = {r['name']: r for r in csv.DictReader(open('reports/sim-0.1.0+E085-physedge/rapm-2022-25.csv', encoding='utf-8')) if r['name']}
POS = {r['name']: r['pos'] for r in csv.DictReader(open('reports/sim-0.1.0+E076-physique-dedup/winimp-dedup.csv', encoding='utf-8-sig'))}
SHOW = ['Victor Wembanyama', 'Nikola Jokić', 'Neemias Queta', 'Rudy Gobert', 'Draymond Green', 'Jarrett Allen', 'Evan Mobley', 'Walker Kessler']


def ck(f):
    X, M, P = {}, {}, {}
    for l in open(f, encoding='utf-8'):
        if l.strip():
            r = json.loads(l)['avg']; d = np.array(r['draws'], float)
            X[r['name']] = float((d[:, 4] - d[:, 5]).mean()); M[r['name']] = r['minutes']; P[r['name']] = r['playerId']
    return X, M, P


rk = lambda v: (-v).argsort().argsort() + 1


def j2(f, grp=None):
    X, M, _ = ck(f); N = [n for n in G['population'] if grp is None or POS.get(n) in grp]
    assert all(n in X for n in N), 'population missing'
    x = np.array([X[n] for n in N]); m = np.array([M[n] for n in N])
    ans = np.array([float(RP[n]['pooledO']) + float(RP[n]['pooledD']) for n in N]) * m / 48 * 2
    return float(spearmanr(x, ans)[0]), dict(zip(N, rk(x))), dict(zip(N, rk(ans))), X, len(N)


def rr(f):
    return [r for l in open(f, encoding='utf-8') if l.strip() for r in json.loads(l)['records']]


S1 = list(range(20261028, 20261060))


def mae(rec):
    ids = [t['id'] for t in json.load(open(E + 'team-ids.json', encoding='utf-8'))]
    rs = json.load(open('data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets'][0]; ix = {h: i for i, h in enumerate(rs['headers'])}
    col = lambda k: {str(r[ix['TEAM_ID']]): float(r[ix[k]]) for r in rs['rowSet']}; pace, net = col('PACE'), col('NET_RATING')
    act = np.array([net[str(i)] * pace[str(i)] / 100 for i in ids])
    assert sorted({r['seed'] for r in rec}) == S1 and len(rec) == len(S1) * 435
    Mx, Nx = np.zeros((32, 30)), np.zeros((32, 30))
    for r in rec:
        s = S1.index(r['seed']); d = r['ptsA'] - r['ptsB']; Mx[s, r['a']] += d; Nx[s, r['a']] += 1; Mx[s, r['b']] -= d; Nx[s, r['b']] += 1
    return float(np.abs((Mx / Nx).mean(0) - act).mean())


def league(rec):
    poss = sum(r['possA'] + r['possB'] for r in rec)
    return {'rimAttPer100': 100 * sum(r['rimAttA'] + r['rimAttB'] for r in rec) / poss,
            'rimFgPct': sum(r['rimMadeA'] + r['rimMadeB'] for r in rec) / sum(r['rimAttA'] + r['rimAttB'] for r in rec),
            'ptsPer100': 100 * sum(r['ptsA'] + r['ptsB'] for r in rec) / poss, 'possPerTeamGame': poss / (2 * len(rec))}


def analytic():
    """2025-26 stints：各區每球得分、每 100 回合 FGA；threeDet 對 rimDet 的 fga 加權斜率＝被擋出禁区的出手幾成變三分。"""
    t = dict.fromkeys(('fga', 'shortA', 'shortM', 'midA', 'midM', 'longA', 'longM', 'poss'), 0)
    for line in open('reports/defense-b1/stints.jsonl', encoding='utf-8'):
        st = json.loads(line)
        for de in st['teams']:
            o = de['opponent']
            for k in ('fga', 'shortA', 'shortM', 'midA', 'midM', 'longA', 'longM'):
                t[k] += o.get(k, 0)
            t['poss'] += de['defensivePossessions']
    pps = {'rim': 2 * t['shortM'] / t['shortA'], 'mid': 2 * t['midM'] / t['midA'], 'three': 3 * t['longM'] / t['longA']}
    fga100 = 100 * t['fga'] / t['poss']
    rd = [r for r in csv.DictReader(open(HERE / 'data' / 'rimdet-sim.csv', encoding='utf-8')) if float(r['fgaW']) >= 2500]
    x = np.array([float(r['rimDet']) for r in rd]); y = np.array([float(r['threeDet']) for r in rd]); w = np.array([float(r['fgaW']) for r in rd])
    xm, ym = np.average(x, weights=w), np.average(y, weights=w)
    slope = float(np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)); f3 = min(max(-slope, 0.0), 1.0)
    per_pp = fga100 * 0.01 * (pps['rim'] - (f3 * pps['three'] + (1 - f3) * pps['mid']))
    names = {r['playerId']: r['name'] for r in csv.DictReader(open('reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8'))}
    allr = {r['pid']: float(r['rimDet']) for r in csv.DictReader(open(HERE / 'data' / 'rimdet-sim.csv', encoding='utf-8'))}
    ex = {names[p]: (round(v, 2), round(v * per_pp, 2)) for p, v in allr.items() if names.get(p) in SHOW}
    return {'pps': {k: round(v, 4) for k, v in pps.items()}, 'fgaPer100': round(fga100, 2), 'slopeThreeOnRim': round(slope, 3), 'toThree': round(f3, 3),
            'ptsPer100PerPP': round(per_pp, 4), 'examples_rimDet_pts100': ex}


def main():
    out = {'analytic': analytic()}
    print(json.dumps(out['analytic'], ensure_ascii=False))
    zc, zr = ZD / 'checkpoint-Z.jsonl', ZD / 'rr-Z.jsonl'
    if not (zc.exists() and zr.exists()):
        print('Z 結果還沒到：只算解析換算'); return
    bj, bs, ba, bx, n = j2(D + 'checkpoint-k.jsonl'); zj, zs, za, zx, _ = j2(str(zc))
    bjc, _, _, _, nc = j2(D + 'checkpoint-k.jsonl', ('PF', 'C')); zjc, _, _, _, _ = j2(str(zc), ('PF', 'C'))
    rb, rz = rr(D + 'rr-k.jsonl'), rr(str(zr)); mb, mz = mae(rb), mae(rz)
    lb, lz = league(rb), league(rz)
    out['j2'] = {'base': bj, 'new': zj, 'delta': zj - bj, 'n': n}
    out['j2c'] = {'base': bjc, 'new': zjc, 'delta': zjc - bjc, 'n': nc}
    out['j3'] = {'base': mb, 'new': mz, 'delta': mz - mb}
    out['league'] = {'base': lb, 'new': lz, 'rimAttRelChange': lz['rimAttPer100'] / lb['rimAttPer100'] - 1}
    out['pass'] = bool(out['j2']['delta'] >= -0.01 and out['j3']['delta'] <= 0.1 and (out['j2']['delta'] >= 0.005 or out['j2c']['delta'] >= 0.02))
    out['players'] = {m: {'pos': POS.get(m), 'ans': int(ba[m]), 'base': int(bs[m]), 'new': int(zs[m]), 'xBase': round(bx[m], 3), 'xNew': round(zx[m], 3)}
                      for m in SHOW if m in bs}
    ch = sorted(G['population'], key=lambda m: zx[m] - bx[m])
    out['biggestMoves'] = {'down': [(m, round(zx[m] - bx[m], 3)) for m in ch[:8]], 'up': [(m, round(zx[m] - bx[m], 3)) for m in ch[-8:][::-1]]}
    (HERE / 'results').mkdir(exist_ok=True)
    json.dump(out, open(HERE / 'results' / 'judge.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: out[k] for k in ('j2', 'j2c', 'j3', 'league', 'pass', 'players', 'biggestMoves')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    main()
