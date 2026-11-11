"""E-301 兩格無球（prereg.md 凍結後只跑一次）。純本機、純 Python。
  python -I -X utf8 reports/E301-offball-two-cells/run.py
"""
import csv, json, os, re, unicodedata
import numpy as np
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
E297 = os.path.join(ROOT, 'reports', 'E297-offball-t-composite'); RAW = os.path.join(ROOT, 'reports', 'E239-tracking-full', 'data')
E227D = os.path.join(ROOT, 'reports', 'E227-lineup-transformer-r2', 'data')
OB = ['cut36', 'cutPPP', 'offScr36', 'handoff36', 'spotup36', 'roll36', 'putback36', 'trans36', 'distOff36', 'speedOff', 'cs3a36', 'cs3pct']
WEQ = {c: (0.5 if c in ('cutPPP', 'cs3pct') else 1.0) for c in OB}
V = {'SHOOT': {'spotup36': 1, 'offScr36': 1, 'handoff36': 1, 'cs3pct': 0.5},
     'CUTROLL': {'cut36': 1, 'roll36': 1, 'putback36': 1, 'trans36': 1, 'cutPPP': 0.5}}
PT = {'SHOOT': ['Spotup', 'OffScreen', 'Handoff'], 'CUTROLL': ['Cut', 'PRRollman', 'OffRebound', 'Transition']}
NAMED = {'SHOOT': ['Klay Thompson', 'Buddy Hield', 'Duncan Robinson', 'Sam Hauser', 'Derrick White'],
         'CUTROLL': ['Aaron Gordon', 'Jarrett Allen', 'Rudy Gobert', 'Dereck Lively II', 'Josh Hart'],
         'ONBALL': ['Luka Dončić', 'Trae Young', 'Shai Gilgeous-Alexander', 'James Harden']}
K_PPP, K_CS = 30.0, 50.0


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def table(name):
    d = json.load(open(os.path.join(RAW, f'{name}.json'), encoding='utf-8')); out = {}
    for r in d['rowSet']:
        r = dict(zip(d['headers'], r)); p = str(r['PLAYER_ID'])
        if p in out:
            for k in ('POSS', 'PTS'):
                out[p][k] = (out[p][k] or 0) + (r[k] or 0)
        else:
            out[p] = r
    return out


def season(s):
    """回傳 {pid: {'min', z 欄…, 'P_SHOOT', 'P_CUTROLL'}}，母體 ≥200 分鐘。"""
    rows = [r for r in csv.DictReader(open(os.path.join(E297, 'data', f'offball-{s}.csv'), encoding='utf-8')) if r['cut36'] != '']
    out = {r['pid']: {'min': float(r['minutes'])} for r in rows}
    for c in OB:
        v = np.array([float(r[c]) for r in rows if r[c] != '']); mu, sd = v.mean(), v.std()
        for r in rows:
            out[r['pid']][c] = (float(r[c]) - mu) / sd if r[c] != '' else 0.0
    for cell, pts in PT.items():
        for p in out:
            out[p]['P_' + cell] = 0.0
        for t in pts:
            tb = table(f'syn-{t}-{s}'); lg = sum(r['PTS'] for r in tb.values()) / sum(r['POSS'] for r in tb.values())
            for p, o in out.items():
                r = tb.get(p)
                if r:
                    ppp = (r['PTS'] + K_PPP * lg) / (r['POSS'] + K_PPP); o['P_' + cell] += 36 * r['POSS'] * (ppp - lg) / o['min']
    cs = table(f'pt-CatchShoot-{s}')
    lg = sum(r['CATCH_SHOOT_FG3M'] or 0 for r in cs.values()) / sum(r['CATCH_SHOOT_FG3A'] or 0 for r in cs.values())
    for p, o in out.items():
        r = cs.get(p)
        if r and r['CATCH_SHOOT_FG3A']:
            a = r['CATCH_SHOOT_FG3A']; pct = (r['CATCH_SHOOT_FG3M'] + K_CS * lg) / (a + K_CS)
            o['P_SHOOT'] += 36 * 3 * a * (pct - lg) / o['min']   # CatchShoot FG3A 是全季總數
    return out


def zcol(D, f):
    v = np.array([f(o) for o in D.values()]); mu, sd = v.mean(), v.std()
    return {p: (f(o) - mu) / sd for p, o in D.items()}


def scores(D):
    """各臂各格分數（季內 ≥200 分鐘尺）。"""
    S = {}
    for cell, w in V.items():
        S[('V', cell)] = zcol(D, lambda o, w=w: sum(o[c] * x for c, x in w.items()) / sum(w.values()))
        S[('P', cell)] = zcol(D, lambda o, cell=cell: o['P_' + cell])
        S[('VP', cell)] = {p: 0.5 * (S[('V', cell)][p] + S[('P', cell)][p]) for p in D}
    S[('W-eq', 'ONE')] = zcol(D, lambda o: sum(o[c] * x for c, x in WEQ.items()) / sum(WEQ.values()))
    return S


def r2(X, y):
    X = np.column_stack([np.ones(len(y)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    return 1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def fit(pop, S, arm, ovr, tgts):
    cells = ['ONE'] if arm == 'W-eq' else ['SHOOT', 'CUTROLL']; out = {}
    for t, y in tgts.items():
        k = [i for i, p in enumerate(pop) if not np.isnan(y[i]) and not np.isnan(ovr[i])]
        yy = y[k]; X0 = ovr[k, None]; X1 = np.column_stack([X0] + [np.array([S[(arm, c)][pop[i]] for i in k]) for c in cells])
        out[t] = {'dR2': round(float(r2(X1, yy) - r2(X0, yy)), 4), 'n': len(k)}
    out['mean'] = round(float(np.mean([out[t]['dR2'] for t in tgts])), 4)
    return out


def main():
    D25, D24 = season('2025-26'), season('2024-25'); S25, S24 = scores(D25), scores(D24)
    VA = json.load(open(os.path.join(E297, 'results', 'value-ALL.json'), encoding='utf-8'))
    VM = json.load(open(os.path.join(E297, 'results', 'value-ALL#mask.json'), encoding='utf-8'))
    dT = {p: a - b for p, a, b in zip(VA['pids'], VA['off'], VM['off'])}
    pop25 = [p for p in VA['pids'] if p in D25]; name25 = dict(zip(VA['pids'], VA['names']))
    pl24 = {r['pid']: r['name'] for r in csv.DictReader(open(os.path.join(E227D, 'players-2024-25.csv'), encoding='utf-8'))}
    pop24 = sorted(p for p, o in D24.items() if o['min'] >= 1000 and p in pl24)
    # 外部
    def bpm(s):
        return {r['playerId']: float(r['obpm']) for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', 'bpm', f'bpm_{s}.csv'), encoding='utf-8'))}
    k27 = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'ovr-v55-2k27-compare', '2k27_ratings.csv'), encoding='utf-8-sig')):
        if r['overall2k']:
            k27.setdefault(nm(r['name']), float(r['overall2k']))
    k26 = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'ovr-v55-2k27-compare', '2k_yearly_ovr.csv'), encoding='utf-8-sig')):
        if r['2K26']:
            k26.setdefault(nm(r['name']), float(r['2K26']))
    c25 = {nm(r['name']): float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'card-0.2.14a', 'ranking.csv'), encoding='utf-8'))}
    c24 = {nm(r['name']): float(r['ovr']) for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'E290-reb-bonus-0213a', 'stage', 'ranking-S-2024-25.csv'), encoding='utf-8'))}
    b25, b24 = bpm('2025-26'), bpm('2024-25')
    T25 = {'OBPM': np.array([b25.get(p, np.nan) for p in pop25]), '2K': np.array([k27.get(nm(name25[p]), np.nan) for p in pop25])}
    T24 = {'OBPM': np.array([b24.get(p, np.nan) for p in pop24]), '2K': np.array([k26.get(nm(pl24[p]), np.nan) for p in pop24])}
    O25 = np.array([c25.get(nm(name25[p]), np.nan) for p in pop25]); O24 = np.array([c24.get(nm(pl24[p]), np.nan) for p in pop24])
    out = {'N25': len(pop25), 'N24': len(pop24), 'arms': {}}
    for arm in ('V', 'P', 'VP', 'W-eq'):
        cells = ['ONE'] if arm == 'W-eq' else ['SHOOT', 'CUTROLL']; o = {'cells': {}}
        for c in cells:
            s = S25[(arm, c)]; both = [p for p in pop25 if p in D24]
            e = {'yoy': round(float(np.corrcoef([s[p] for p in both], [S24[(arm, c)][p] for p in both])[0, 1]), 3), 'nYoy': len(both),
                 'rhoDT': round(float(spearmanr([s[p] for p in pop25], [dT[p] for p in pop25])[0]), 3)}
            v = np.array([s[p] for p in pop25]); pct = {p: float((v < s[p]).mean() * 100) for p in pop25}
            idx = {nm(name25[p]): p for p in pop25}
            e['named'] = {g: {n: (round(pct[idx[nm(n)]], 1) if nm(n) in idx else None) for n in L} for g, L in NAMED.items()}
            if c in ('SHOOT', 'CUTROLL'):
                got = [x for x in e['named'][c].values() if x is not None]
                e['C2'] = {'hit': sum(x >= 70 for x in got), 'n': len(got), 'pass': bool(got) and sum(x >= 70 for x in got) >= 0.75 * len(got)}
            order = sorted(pop25, key=lambda p: -s[p])
            e['top10'] = [f'{name25[p]} {pct[p]:.0f}' for p in order[:10]]
            o['cells'][c] = e
        o['fit25'] = fit(pop25, S25, arm, O25, T25); o['fit24'] = fit(pop24, S24, arm, O24, T24)
        if arm != 'W-eq':
            o['cellCorr25'] = round(float(np.corrcoef([S25[(arm, 'SHOOT')][p] for p in pop25], [S25[(arm, 'CUTROLL')][p] for p in pop25])[0, 1]), 3)
        out['arms'][arm] = o
    weq24 = out['arms']['W-eq']['fit24']['mean']
    for arm in ('V', 'P', 'VP'):
        o = out['arms'][arm]
        o['C1'] = all(o['cells'][c]['yoy'] >= 0.60 for c in o['cells'])
        o['C2'] = all(o['cells'][c]['C2']['pass'] for c in o['cells'])
        o['C3'] = o['fit24']['mean'] > 0 and o['fit24']['mean'] >= weq24
        o['pass'] = o['C1'] and o['C2'] and o['C3']
    ok = [a for a in ('V', 'P', 'VP') if out['arms'][a]['pass']]
    out['recommended'] = max(ok, key=lambda a: (out['arms'][a]['fit24']['mean'], a == 'V')) if ok else None
    # 輸出建議臂（或 VP）的 2025-26 兩格分數
    arm = out['recommended'] or 'VP'
    with open(os.path.join(HERE, f'cells-2025-26-{arm}.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['pid', 'name', 'SHOOT', 'CUTROLL'])
        for p in pop25:
            w.writerow([p, name25[p], round(S25[(arm, 'SHOOT')][p], 4), round(S25[(arm, 'CUTROLL')][p], 4)])
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
