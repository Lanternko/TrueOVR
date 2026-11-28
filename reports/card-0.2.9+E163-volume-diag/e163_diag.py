"""E-163 診斷（樣本內，不是證據）：card 0.2.9 的 OVR 相對 T6 目標的殘差 vs USG／TS。唯讀，輸出到本目錄。
python -I -B -X utf8 reports/card-0.2.9+E163-volume-diag/e163_diag.py"""
import csv, json, pickle, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
EI = ROOT / 'data/external-impact'
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
sys.path.insert(0, str(ROOT / 'reports/card-0.2.8+E157-next-epm-metric'))


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in s if c.isalnum())


def z(x):
    x = np.asarray(x, float)
    return (x - x.mean()) / x.std()


def names(s):
    m = {}
    for f in (EI / f'bpm/bpm_{s}.csv', EI / f'darko/darko_{s}.csv', EI / f'epm_self/epm_{s}.csv'):
        if f.exists():
            for r in csv.DictReader(open(f, encoding='utf-8-sig')):
                try:
                    m.setdefault(nm(r['name']), int(r['playerId']))
                except Exception:
                    pass
    return m


def ext(kind, s):
    p = {'bpm': ('bpm/bpm_%s.csv', 'obpm'), 'darko': ('darko/darko_%s.csv', 'o_dpm')}[kind]
    out = {}
    for r in csv.DictReader(open(EI / (p[0] % s), encoding='utf-8-sig')):
        try:
            out[int(r['playerId'])] = float(r[p[1]])
        except Exception:
            pass
    return out


def load_sal():
    import eval_v2 as V
    b = V._base()
    return {t: {p: v[0] for p, v in b[t]['raw']['sal'].items()} for t in SEAS}


def main():
    try:
        SAL = load_sal()
    except Exception as e:
        print('salary load failed', repr(e))
        SAL = None
    rows_all, log = [], {}
    for s in SEAS:
        T6 = pickle.load(open(ROOT / f'reports/E142-card-target/phase1-work/cands/T6-{s}.pkl', 'rb'))
        adv = pickle.load(open(E162 / f'work/adv-{s}.pkl', 'rb'))
        nid = names(s)
        ob, dk = ext('bpm', s), ext('darko', s)
        rk = list(csv.DictReader(open(E162 / f'ranking-K-{s}.csv', encoding='utf-8')))
        recs, miss = [], 0
        for r in rk:
            if float(r['MIN']) < 500:
                continue
            pid = nid.get(nm(r['name']))
            if pid is None or pid not in T6 or pid not in adv:
                miss += 1
                continue
            a = adv[pid]
            if a.get('usg_pct') is None or a.get('ts_pct') is None:
                miss += 1
                continue
            recs.append(dict(s=s, pid=pid, name=r['name'], ovr=float(r['ovr']), net=T6[pid][0], usg=a['usg_pct'], ts=a['ts_pct'],
                             per=a.get('per'), ob=ob.get(pid), dk=dk.get(pid), sal=(SAL[s].get(pid) if SAL else None), mp=float(r['MIN'])))
        zo, zn = z([x['ovr'] for x in recs]), z([x['net'] for x in recs])
        for x, a, b in zip(recs, zo, zn):
            x['r'] = a - b
        ro = (-np.array([x['ovr'] for x in recs])).argsort().argsort() + 1
        rn = (-np.array([x['net'] for x in recs])).argsort().argsort() + 1
        for x, a, b in zip(recs, ro, rn):
            x['rk_card'], x['rk_t6'] = int(a), int(b)
        log[s] = dict(n=len(recs), unmatched=miss, ranking_rows=len(rk))
        rows_all += recs
    print(json.dumps(log))
    out = {'log': log}

    def block(key):
        res = {}
        sp_u, sp_t, ols = [], [], []
        for s in SEAS:
            R = [x for x in rows_all if x['s'] == s and x.get(key) is not None]
            if len(R) < 50:
                continue
            r = z([x['ovr'] for x in R]) - z([x[key] for x in R])
            u, t = z([x['usg'] for x in R]), z([x['ts'] for x in R])
            su, st = spearmanr(r, u)[0], spearmanr(r, t)[0]
            X = np.column_stack([np.ones(len(R)), u, t])
            b = np.linalg.lstsq(X, r, rcond=None)[0]
            res[s] = dict(n=len(R), rho_usg=su, rho_ts=st, b_usg=b[1], b_ts=b[2])
            sp_u.append(su); sp_t.append(st); ols.append(b)
        res['mean'] = dict(rho_usg=float(np.mean(sp_u)), rho_ts=float(np.mean(sp_t)), b_usg=float(np.mean([o[1] for o in ols])), b_ts=float(np.mean([o[2] for o in ols])))
        return res
    out['T6'] = block('net')
    out['salary'] = block('sal') if any(x['sal'] is not None for x in rows_all) else None
    for s in SEAS:
        R = [x for x in rows_all if x['s'] == s]
        uq = np.quantile([x['usg'] for x in R], [.25, .5, .75])
        tq = np.quantile([x['ts'] for x in R], [1 / 3, 2 / 3])
        for x in R:
            x['uq'] = int(np.searchsorted(uq, x['usg'], side='right')) + 1
            x['tt'] = int(np.searchsorted(tq, x['ts'], side='right')) + 1
        S = [x for x in R if x['sal'] is not None]
        if len(S) > 50:
            rs = z([x['ovr'] for x in S]) - z([x['sal'] for x in S])
            for x, v in zip(S, rs):
                x['rs'] = float(v)
    cells, sc = {}, {}
    for u_ in (1, 2, 3, 4):
        for t_ in (1, 2, 3):
            R = [x for x in rows_all if x['uq'] == u_ and x['tt'] == t_]
            cells[f'U{u_}_T{t_}'] = dict(n=len(R), mean_r_T6=float(np.mean([x['r'] for x in R])))
            Rs = [x for x in R if 'rs' in x]
            sc[f'U{u_}_T{t_}'] = dict(n=len(Rs), mean_r_sal=float(np.mean([x['rs'] for x in Rs])) if Rs else None)
    out['cells_T6'] = cells
    out['cells_salary'] = sc
    R = [x for x in rows_all if x['s'] == '2025-26' and x['uq'] == 4 and x['tt'] == 2]
    R.sort(key=lambda x: x['r'])
    out['ex_cell_n'] = len(R)
    out['ex_2025_26'] = [dict(name=x['name'], card_rank=x['rk_card'], t6_rank=x['rk_t6'], usg=x['usg'], ts=x['ts'], r=round(x['r'], 2)) for x in R[:8]]
    ctl = {}
    for s in SEAS:
        R = [x for x in rows_all if x['s'] == s and x['ob'] is not None and x['dk'] is not None]
        d = z([x['ob'] for x in R]) - z([x['dk'] for x in R])
        ctl[s] = dict(n=len(R), rho_resid_vs_obpm_minus_darkoO=spearmanr([x['r'] for x in R], d)[0],
                      rho_usg_vs_obpm_minus_darkoO=spearmanr([x['usg'] for x in R], d)[0])
    out['control'] = ctl
    out['raw_corr'] = {}
    for s in SEAS:
        R = [x for x in rows_all if x['s'] == s]
        out['raw_corr'][s] = dict(card_usg=spearmanr([x['ovr'] for x in R], [x['usg'] for x in R])[0],
                                  t6_usg=spearmanr([x['net'] for x in R], [x['usg'] for x in R])[0])
    (HERE / 'e163_results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


main()
