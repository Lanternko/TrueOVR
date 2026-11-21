"""E-142 稽核：獨立重算（不 import / 複製 phase1_eval.py、c0l_check.py）。
只照 preregistration.md + errata-1/2/3 文字重建。用法：
  python -I recompute.py --out OUT.json [--twok CSV] [--mode three|single] [--pctbase pop|eval] [--cands T0,T1,T4,T5,T6]
"""
import argparse, csv, datetime, glob, html, json, math, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

R = Path(__file__).resolve().parents[3]
E = R / 'reports/E142-card-target'
SRC = R / 'reports/salary-corr/source'
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
FOLDS = SEAS[:3]
NEXT = dict(zip(SEAS[:3], SEAS[1:]))
PAGES = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
PAGEF = dict(zip(PAGES, ['contracts2022', 'contracts2023', 'contracts2024', 'contracts2025', 'bref2526', 'bref']))
TXF = ['tx2021', 'tx2022', 'tx2023', 'tx2024', 'tx2025', 'tx2026']
ED = dict(zip(SEAS, ['2K24', '2K25', '2K26', '2K27']))
YW = {1: 1.0, 2: 1.0, 3: 0.7, 4: 0.5}   # 5+ -> 0.3
WB = dict(sal=0.4, k2=0.3, rapm=0.15)
TOL = dict(sal=0.02, k2=0.02, rapm=0.05)


def nm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n)
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def pg_file(s):
    return R / ('data/season-source/player-games.json' if s == '2025-26' else f'data/defense-seventh/{s}/player-games.json')


def rs0(p):
    d = json.loads(Path(p).read_text(encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(d['headers'], r)) for r in d['rowSet']]


def population(s):
    mins, gp, name, tg = defaultdict(float), defaultdict(int), {}, defaultdict(lambda: defaultdict(int))
    for r in rs0(pg_file(s)):
        if r['MIN']:
            p = r['PLAYER_ID']; mins[p] += r['MIN']; gp[p] += 1; name[p] = r['PLAYER_NAME']; tg[p][r['TEAM_ABBREVIATION']] += 1
    pop = {p: dict(name=name[p], team=max(tg[p], key=tg[p].get), min=m) for p, m in mins.items() if m >= 500}
    return pop, {p: mins[p] / gp[p] for p in mins}


def W(m):
    return (1 - math.exp(-m / 15)) / (1 - math.exp(-36 / 15))


FIX = {'BRK': 'BKN', 'PHO': 'PHX', 'CHO': 'CHA'}


def contracts(pg):
    txt = (SRC / (PAGEF[pg] + '.html')).read_text(encoding='utf-8')
    out = defaultdict(list)
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', txt, re.S):
        m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row)
        if not m:
            continue

        def val(k):
            x = re.search(r'data-stat="%s"[^>]*>\$?([\d,]+)' % k, row)
            return int(x.group(1).replace(',', '')) if x else None
        if val('y1') is None:
            continue
        t = re.search(r'data-stat="team_id"[^>]*>(?:<a[^>]*>)?([A-Z]{3})', row)
        sched = []
        for i in range(1, 7):
            v = val('y%d' % i)
            if v is None:
                break
            sched.append(v)
        out[nm(m.group(1))].append((FIX.get(t.group(1), t.group(1)) if t else None, sched))
    return out


def same(prev, cur):
    if len(prev) < 2:
        return False
    n = min(len(prev) - 1, len(cur))
    return all(abs(prev[i + 1] - cur[i]) <= 0.01 * cur[i] + 1 for i in range(n))


def txev():
    ev = defaultdict(list)
    for f in TXF:
        txt = (SRC / (f + '.html')).read_text(encoding='utf-8')
        for d, body in re.findall(r'<li[^>]*>\s*<span>([^<]+)</span>(.*?)</li>', txt, re.S):
            mo = re.match(r'([A-Za-z]+) (\d+), (\d{4})', d)
            if not mo:
                continue
            dt = datetime.datetime.strptime(' '.join(mo.groups()), '%B %d %Y').date()
            for p in re.findall(r'<p>(.*?)</p>', body, re.S):
                t = html.unescape(re.sub('<[^>]+>', '', p))
                m = re.search(r'signed (.+?) to (?:a|an) (multi-year contract|contract extension)\.$', t)
                if m:
                    for n in re.split(r', and |, | and ', m.group(1)):
                        ev[nm(n)].append((dt, 'ext' if 'extension' in m.group(2) else 'fa'))
    return ev


def drafts():
    out = {}
    for f in glob.glob(str(R / 'data/**/bio.json'), recursive=True):
        try:
            d = json.loads(Path(f).read_text(encoding='utf-8'))['data']['resultSets'][0]
        except Exception:
            continue
        h = {k: i for i, k in enumerate(d['headers'])}
        if 'DRAFT_YEAR' in h:
            for r in d['rowSet']:
                out[r[h['PLAYER_ID']]] = (r[h['DRAFT_YEAR']], r[h['DRAFT_ROUND']])
    return out


def salary_terms(t, pop, C, DR, EV):
    ti = PAGES.index(t)
    out, st = {}, defaultdict(int)
    for pid, info in pop.items():
        k = nm(info['name'])
        dy, rd = DR.get(pid, (None, None))
        try:
            D = int(dy)
        except Exception:
            D = None
        if D is not None and str(rd) == '1' and 0 <= int(t[:4]) - D <= 3:
            st['rookie'] += 1
            continue
        rows = C[t].get(k, [])
        if not rows:
            st['norow'] += 1
            continue
        if len(rows) == 1:
            row = rows[0]
        else:
            sm = [r for r in rows if r[0] == info['team']]
            row = sm[0] if sm else max(rows, key=lambda r: r[1][0])
        cur, j = row[1], ti
        cens = False
        while True:
            if j == 0:
                cens = True
                break
            hit = next((c for c in C[PAGES[j - 1]].get(k, []) if same(c[1], cur)), None)
            if hit is None:
                break
            cur, j = hit[1], j - 1
        if not cens:
            yr = ti - j + 1
        else:
            evs = [e for e in EV.get(k, []) if e[0].year >= 2020]
            if not evs:
                st['undated'] += 1
                continue
            yr = ti + 1
            fa = [e for e in evs if e[1] == 'fa']
            if fa:
                d = fa[-1][0]
                ss = d.year if d.month >= 7 else d.year - 1
                if ss <= 2021:
                    yr = int(t[:4]) - ss + 1
            st['tx'] += 1
        out[pid] = (row[1][0], max(1, yr))
    return out, dict(st)


def pct(d):
    ks = list(d)
    if len(ks) < 2:
        return {k: 0.5 for k in ks}
    r = rankdata([d[k] for k in ks])
    return {k: (x - 1) / (len(ks) - 1) for k, x in zip(ks, r)}


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def wsp(x, y, w):
    a, b, w = rankdata(x), rankdata(y), np.asarray(w, float)
    w = w / w.sum()
    ma, mb = (w * a).sum(), (w * b).sum()
    return float((w * (a - ma) * (b - mb)).sum() / math.sqrt((w * (a - ma) ** 2).sum() * (w * (b - mb) ** 2).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--twok', default=str(R / 'data/external-impact/2k/2k-merged-e142.csv'))
    ap.add_argument('--mode', default='three')
    ap.add_argument('--pctbase', default='pop')
    ap.add_argument('--cands', default='T0,T1,T4,T5,T6')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    CANDS = a.cands.split(',')
    C = {p: contracts(p) for p in PAGES}
    DR, EV = drafts(), txev()
    K2 = {}
    for r in csv.DictReader(open(a.twok, encoding='utf-8-sig')):
        K2.setdefault(nm(r['name']), r)
    pops, mpg = {}, {}
    for s in SEAS:
        pops[s], mpg[s] = population(s)
    D, diag = {}, {}
    for t in SEAS:
        pop = pops[t]
        sal, st = salary_terms(t, pop, C, DR, EV)
        ps = pct({p: v[0] for p, v in sal.items()})
        T = {'sal': {p: (ps[p], WB['sal'] * YW.get(sal[p][1], 0.3)) for p in sal}}
        k2 = {}
        for p, i in pop.items():
            r = K2.get(nm(i['name']))
            if r and (r.get(ED[t]) or '').strip():
                try:
                    k2[p] = float(r[ED[t]])
                except ValueError:
                    pass
        pk = pct(k2)
        T['k2'] = {p: (pk[p], WB['k2']) for p in k2}
        rv = {}
        if t in NEXT:
            n = NEXT[t]
            d = json.loads((R / f'reports/card-0.2.7+E126-tank-next-season/rapm-{n}.json').read_text(encoding='utf-8'))
            rv = {int(p): v['net'] * W(mpg[n][int(p)]) for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mpg[n]}
        pr = pct(rv)
        T['rapm'] = {p: (pr[p], WB['rapm']) for p in rv}
        ref = {}
        for p in pop:
            num = den = 0.0
            for k in T:
                if p in T[k]:
                    v, w = T[k][p]
                    num += w * v
                    den += w
            if den > 0:
                ref[p] = num / den
        n2 = defaultdict(list)
        for p, i in pop.items():
            n2[nm(i['name'])].append(p)
        ov = {}
        for c in CANDS:
            f = E / 'phase1-work' / c / ('c0/ranking.csv' if t == '2025-26' else f'{t}/out/K0/ranking.csv')
            m = {}
            for r in csv.DictReader(open(f, encoding='utf-8-sig')):
                if float(r['MIN']) < 500:
                    continue
                ids = n2.get(nm(r['name'])) or []
                if len(ids) != 1:
                    continue
                m[ids[0]] = float(r['ovr'])
            ov[c] = m
        ids = sorted(p for p in set.intersection(*[set(ov[c]) for c in CANDS]) if p in ref)
        if a.pctbase == 'eval':
            ev = set(ids)
            T2 = {}
            x = pct({p: sal[p][0] for p in sal if p in ev})
            T2['sal'] = {p: (x[p], WB['sal'] * YW.get(sal[p][1], 0.3)) for p in x}
            x = pct({p: k2[p] for p in k2 if p in ev})
            T2['k2'] = {p: (x[p], WB['k2']) for p in x}
            x = pct({p: rv[p] for p in rv if p in ev})
            T2['rapm'] = {p: (x[p], WB['rapm']) for p in x}
            ref = {}
            for p in ids:
                num = den = 0.0
                for k in T2:
                    if p in T2[k]:
                        v, w = T2[k][p]
                        num += w * v
                        den += w
                if den > 0:
                    ref[p] = num / den
            ids = [p for p in ids if p in ref]
        D[t] = dict(ids=ids, ovr={c: np.array([ov[c][p] for p in ids]) for c in CANDS}, ref=np.array([ref[p] for p in ids]),
                    raw=dict(sal=sal, k2=k2, rapm=rv))
        diag[t] = dict(pop=len(pop), n=len(ids), salStats=st, avail={k: sum(1 for p in ids if p in D[t]['raw'][k]) for k in D[t]['raw']},
                       yearDist={y: sum(1 for p in ids if p in sal and sal[p][1] == y) for y in range(1, 8)})

    def met(t, c, idx=None):
        d = D[t]
        idx = np.arange(len(d['ids'])) if idx is None else idx
        o, rf = d['ovr'][c][idx], d['ref'][idx]
        out = dict(n=int(len(idx)), C=sp(o, rf))
        for k in ('sal', 'k2', 'rapm'):
            have = [i for i in idx if d['ids'][i] in d['raw'][k]]
            out['n_' + k] = len(have)
            if len(have) < 10:
                out[k] = None
                continue
            oo = d['ovr'][c][have]
            if k == 'sal':
                out[k] = wsp(oo, [d['raw'][k][d['ids'][i]][0] for i in have], [YW.get(d['raw'][k][d['ids'][i]][1], 0.3) for i in have])
            else:
                out[k] = sp(oo, [d['raw'][k][d['ids'][i]] for i in have])
        return out
    PS = {t: {c: met(t, c) for c in CANDS} for t in SEAS}

    def pick(seasons):
        cc = {c: sum(PS[t][c]['n'] * PS[t][c]['C'] for t in seasons) / sum(PS[t][c]['n'] for t in seasons) for c in CANDS if c != 'T0'}
        return sorted(cc, key=lambda c: (-cc[c], c))[0], cc
    if a.mode == 'three':
        tests = FOLDS
        folds = {}
        for t in FOLDS:
            tr = [s for s in FOLDS if s != t]
            ts, cc = pick(tr)
            folds[t] = dict(train=tr, Tstar=ts, trainC=cc)
    else:
        ts, cc = pick(['2022-23'])
        tests = ['2023-24', '2024-25']
        folds = {t: dict(train=['2022-23'], Tstar=ts, trainC=cc) for t in tests}
    final = pick(FOLDS)

    def pd(key):
        num = den = 0.0
        for t in tests:
            x, b = PS[t][folds[t]['Tstar']], PS[t]['T0']
            if x.get(key) is None or b.get(key) is None:
                continue
            nn = x['n'] if key == 'C' else x['n_' + key]
            num += nn * (x[key] - b[key])
            den += nn
        return num / den
    od = {k: pd(k) for k in ('C', 'sal', 'k2', 'rapm')}
    rng = np.random.default_rng(20261031)
    allids = sorted(set().union(*[D[t]['ids'] for t in tests]))
    pos = {t: {p: i for i, p in enumerate(D[t]['ids'])} for t in tests}
    dif = np.empty(2000)
    for b in range(2000):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = den = 0.0
        for t in tests:
            sel = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat([pos[t][allids[j]] for j in sel], [mult[j] for j in sel])
            d = D[t]
            num += len(idx) * (sp(d['ovr'][folds[t]['Tstar']][idx], d['ref'][idx]) - sp(d['ovr']['T0'][idx], d['ref'][idx]))
            den += len(idx)
        dif[b] = num / den
    lo, hi = float(np.percentile(dif, 5)), float(np.percentile(dif, 95))
    j = [lo > 0, od['sal'] >= -TOL['sal'], od['k2'] >= -TOL['k2'], od['rapm'] >= -TOL['rapm']]
    res = dict(args=vars(a), per_season=PS, folds=folds, final=dict(Tstar=final[0], C=final[1]), oof=od, lower90=lo, upper90=hi, judge=j,
               verdict='adopt' if all(j) else ('side_effect' if j[0] else 'no_improvement'), diag=diag)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(a.out, res['verdict'], {k: round(v, 4) for k, v in od.items()}, round(lo, 4), {t: folds[t]['Tstar'] for t in tests})


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
