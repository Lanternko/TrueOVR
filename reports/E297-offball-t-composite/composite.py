"""E-297 第三階段（本機、只讀 5090 拉回的 results/）：三組無球合併權重 W-eq／W-imp／W-dist 的描述性評估。
母體 2025-26 ≥1000 分鐘（value-ALL.json 的 pids）。12 欄 z＝季內 ≥200 分鐘全聯盟尺；缺值（SpeedDistance／CatchShoot 沒資料）記 z=0。
  python -I -X utf8 composite.py
"""
import csv, json, os, re, sys, unicodedata
import numpy as np
from scipy.optimize import nnls
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OB = ['cut36', 'cutPPP', 'offScr36', 'handoff36', 'spotup36', 'roll36', 'putback36', 'trans36', 'distOff36', 'speedOff', 'cs3a36', 'cs3pct']
NAMED_OFF = ['Derrick White', 'Klay Thompson', 'Aaron Gordon', 'Buddy Hield', 'Duncan Robinson', 'Sam Hauser', 'Josh Hart', 'Mikal Bridges',
             'Jarrett Allen', 'Rudy Gobert', 'Dereck Lively II']
NAMED_ON = ['Luka Dončić', 'Trae Young', 'Shai Gilgeous-Alexander', 'James Harden']
POS = ['PG', 'SG', 'SF', 'PF', 'C']


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def zs(season):
    rows = list(csv.DictReader(open(os.path.join(HERE, 'data', f'offball-{season}.csv'), encoding='utf-8')))
    Z = {r['pid']: np.zeros(len(OB)) for r in rows}; miss = {r['pid']: 0 for r in rows}
    for j, c in enumerate(OB):
        v = np.array([float(r[c]) for r in rows if r[c] != ''])
        mu, sd = v.mean(), v.std()
        for r in rows:
            if r[c] == '':
                miss[r['pid']] += 1
            else:
                Z[r['pid']][j] = (float(r[c]) - mu) / sd
    return Z, miss


def r2(X, y):
    X = np.column_stack([np.ones(len(y)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    return 1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def main():
    R = os.path.join(HERE, 'results')
    VA = json.load(open(os.path.join(R, 'value-ALL.json'), encoding='utf-8'))
    VM = json.load(open(os.path.join(R, 'value-ALL#mask.json'), encoding='utf-8'))
    assert VA['pids'] == VM['pids']
    pids, names, modal = VA['pids'], VA['names'], VA['modal']
    dT = np.array(VA['off']) - np.array(VM['off'])
    Z25, miss25 = zs('2025-26'); Z24, _ = zs('2024-25')
    keep = [i for i, p in enumerate(pids) if p in Z25]
    pids = [pids[i] for i in keep]; names = [names[i] for i in keep]; modal = [modal[i] for i in keep]; dT = dT[keep]
    Zm = np.stack([Z25[p] for p in pids]); N = len(pids)

    # 三組權重
    ev = json.load(open(os.path.join(R, 'eval.json'), encoding='utf-8'))
    imp = ev['fold0']['importance']['ALL']
    W = {'W-eq': np.array([0.5 if c in ('cutPPP', 'cs3pct') else 1.0 for c in OB]),
         'W-imp': np.array([max(imp[c], 0.0) for c in OB])}
    w, _ = nnls(Zm - Zm.mean(0), dT - dT.mean()); W['W-dist'] = w
    for k in list(W):
        if W[k].sum() <= 0:
            W[k] = None
        else:
            W[k] = W[k] / W[k].sum()

    # 外部參照
    card = {nm(r['name']): float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.14a', 'ranking.csv'), encoding='utf-8'))}
    bpm = {r['playerId']: float(r['obpm']) for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', 'bpm', 'bpm_2025-26.csv'), encoding='utf-8'))}
    k2 = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'ovr-v55-2k27-compare', '2k27_ratings.csv'), encoding='utf-8-sig')):
        if r['overall2k']:
            k2.setdefault(nm(r['name']), float(r['overall2k']))
    ovr = np.array([card.get(nm(n), np.nan) for n in names])
    tgt = {'OBPM': np.array([bpm.get(p, np.nan) for p in pids]), '2K27': np.array([k2.get(nm(n), np.nan) for n in names])}

    out = {'N': N, 'missingAnyCol': int(sum(1 for p in pids if miss25[p])), 'weights': {}, 'eval': {}, 'perCol': {}}
    for j, c in enumerate(OB):
        o = {'rhoDT': round(float(spearmanr(Zm[:, j], dT)[0]), 3)}
        for t, y in tgt.items():
            m = ~np.isnan(y); o['rho' + t] = round(float(spearmanr(Zm[m, j], y[m])[0]), 3)
        out['perCol'][c] = o
    comp = {}
    for k, w in W.items():
        if w is None:
            out['weights'][k] = None; continue
        out['weights'][k] = {c: round(float(x), 4) for c, x in zip(OB, w)}
        s = Zm @ w; comp[k] = s; e = {'rhoDT': round(float(spearmanr(s, dT)[0]), 3)}
        dr = []
        for t, y in tgt.items():
            m = ~np.isnan(y) & ~np.isnan(ovr)
            d = r2(np.column_stack([ovr[m], s[m]]), y[m]) - r2(ovr[m, None], y[m]); dr.append(d)
            e['dR2_' + t] = round(float(d), 4); e['n_' + t] = int(m.sum())
            e['rho' + t] = round(float(spearmanr(s[m], y[m])[0]), 3)
        e['dR2_mean'] = round(float(np.mean(dr)), 4)
        both = [i for i, p in enumerate(pids) if p in Z24]
        e['yoy'] = round(float(np.corrcoef(s[both], np.array([Z24[pids[i]] @ w for i in both]))[0, 1]), 3); e['nYoy'] = len(both)
        e['yoyOK'] = e['yoy'] >= 0.60
        out['eval'][k] = e
    ok = {k: e for k, e in out['eval'].items() if e['yoyOK']}
    best = max(ok, key=lambda k: (round(ok[k]['dR2_mean'], 4), k == 'W-eq')) if ok else None
    out['recommended'] = best
    if best:
        s = comp[best]; pct = {p: float((s < s[i]).mean() * 100) for i, p in enumerate(pids)}
        idx = {nm(n): i for i, n in enumerate(names)}
        out['named'] = {}
        for grp, L in (('offball', NAMED_OFF), ('onball', NAMED_ON)):
            out['named'][grp] = {}
            for n in L:
                i = idx.get(nm(n))
                out['named'][grp][n] = None if i is None else {'pct': round(pct[pids[i]], 1), 'pos': POS[modal[i]],
                                                                 'pctByComp': {k: round(float((comp[k] < comp[k][i]).mean() * 100), 1) for k in comp}}
        out['posMeanPct'] = {POS[q]: round(float(np.mean([pct[pids[i]] for i in range(N) if modal[i] == q])), 1) for q in range(5)}
        order = np.argsort(-s)
        out['top15'] = [{'name': names[i], 'pos': POS[modal[i]], 'pct': round(pct[pids[i]], 1)} for i in order[:15]]
        out['bottom5'] = [{'name': names[i], 'pos': POS[modal[i]], 'pct': round(pct[pids[i]], 1)} for i in order[-5:]]
        with open(os.path.join(R, 'offball-composite-2025-26.csv'), 'w', encoding='utf-8', newline='') as f:
            wr = csv.writer(f); wr.writerow(['pid', 'name', 'pos', 'composite', 'pct', 'dTOff'] + list(comp))
            for i in order:
                wr.writerow([pids[i], names[i], POS[modal[i]], round(float(s[i]), 4), round(pct[pids[i]], 1), round(float(dT[i]), 3)] + [round(float(comp[k][i]), 4) for k in comp])
    json.dump(out, open(os.path.join(R, 'composite.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('N', 'weights', 'eval', 'recommended')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
