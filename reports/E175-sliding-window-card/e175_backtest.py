"""E-175 §2 主判定：U（R-076 滑動窗口）對 V（按季分塊，V61 方法 c）預測 t 以後的比率，屬性量尺 MAE。
預註冊：reports/E175-sliding-window-card/preregistration.md（sha256 15ba2d7d…，不改）。參數只讀 backtest.json，不重擬合。
用法：python -I -X utf8 reports/E175-sliding-window-card/e175_backtest.py [--sens]   輸出 backtest-result.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e175_lib as L
import e175_card as C

B, SEED = 2000, 20261101
CUTS = [('0', 0.0), ('10%', 0.10), ('25%', 0.25), ('46.7%', L.H1_FRACTION), ('75%', 0.75)]
ATTRS8 = C.ATTRS8
SENS = '--sens' in sys.argv  # mid／short 先驗改聯盟（0.2.9a 實際，E-101 改動一）：只報告，不進判定


def build_fits(bt, sens):
    """每個屬性 → {'V': 方法 c 的 fit, 'U': 方法 b 的 fit}（backtest.json 原值）。drive 回傳兩個分量。"""
    fits = {}
    for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short'):
        fc, fb = dict(bt['production'][a]['fit']), dict(bt['attrs'][a]['fit']['b'])
        assert bt['production'][a]['selected'] == 'c'
        if sens and a in ('mid', 'short'):
            fc['prior'] = fb['prior'] = 'league'
        fits[a] = {'V': fc, 'U': fb}
    comp = bt['production']['drive']['components']
    for key in ('driveVol', 'driveEff'):
        fits[key] = {'V': dict(comp[key]['c']), 'U': dict(comp[key]['b'])}
    return fits


def arm_rate(D, tab, arm, fit, S, g, posv):
    m = L.causal_prior(D, tab, S, g, fit['prior'], posv)
    return L.v_rate(D, tab, S, g, fit, m) if arm == 'V' else L.u_rate(D, tab, S, g, fit, m)


def run_season(D, ch, bt, S, sens):
    fits = build_fits(bt, sens)
    by = L.positions_by()
    posv = np.array([L.pos_lookup(by, p, S) for p in D.pids])
    G = D.G[S]
    mp = ch['mappers']
    zr = ch['info']['driveZ']
    sh = {a: ch['info'][a + 'Shift']['shift'] for a in ('mid', 'short')}
    tabname = {'ft': 'ft', 'foulDraw': 'foulDraw', 'tovSkill': 'tovSkill', 'pass': 'pass', 'rebound': 'rebound', 'mid': 'mid', 'short': 'short'}
    mapper = {'ft': mp['ft'], 'foulDraw': mp['foulDrawRate'], 'tovSkill': mp['tovSkill'], 'pass': mp['passRate'], 'rebound': mp['rebound'],
              'mid': mp['mid'], 'short': mp['short'], 'drive': mp['drive']}
    rec = {}   # (cut, attr) -> dict(idx, eU, eV, ...)
    for cname, frac in CUTS:
        g = int(round(frac * G))
        for a in ATTRS8:
            if a == 'drive':
                dv_n, dv_d = D.tab[S]['driveVol'].agg(g, 10 ** 9)
                de_n, de_d = D.tab[S]['driveEff'].agg(g, 10 ** 9)
                sel = np.nonzero((dv_d >= L.MIN_D2['driveVol']) & (de_d >= L.MIN_D2['driveEff']))[0]

                def score(rv, re_):
                    return .5 * (36 * rv - zr['mv']) / zr['sv'] + .5 * (re_ - zr['me']) / zr['se']
                truth = mapper[a](score(dv_n[sel] / dv_d[sel], de_n[sel] / de_d[sel]))
                out = {}
                for arm in ('V', 'U'):
                    rv = arm_rate(D, 'driveVol', arm, fits['driveVol'][arm], S, g, posv)
                    re_ = arm_rate(D, 'driveEff', arm, fits['driveEff'][arm], S, g, posv)
                    out[arm] = mapper[a](score(rv[sel], re_[sel]))
            else:
                n, d = D.tab[S][tabname[a]].agg(g, 10 ** 9)
                sel = np.nonzero(d >= L.MIN_D2[a])[0]
                sgn, shift = (-1.0, 0.0) if a == 'tovSkill' else (1.0, sh.get(a, 0.0))
                truth = mapper[a](sgn * (n[sel] / d[sel]) + shift)
                out = {}
                for arm in ('V', 'U'):
                    r = arm_rate(D, tabname[a], arm, fits[a][arm], S, g, posv)
                    out[arm] = mapper[a](sgn * r[sel] + shift)
            rec[(cname, a)] = {'idx': sel, 'eV': np.abs(out['V'] - truth), 'eU': np.abs(out['U'] - truth), 'g': g}
    return rec, fits


def bootstrap(rec, nP_all):
    """球員層 bootstrap（所有屬性、所有切點共用同一組重抽，球員跨屬性相關）。回傳每格與合併的 R 區間。"""
    used = sorted({int(i) for r in rec.values() for i in r['idx']})
    pos = {p: j for j, p in enumerate(used)}
    nU = len(used)
    rng = np.random.default_rng(SEED)
    cnt = rng.multinomial(nU, np.full(nU, 1.0 / nU), size=B).astype(float)   # B × nU
    stat = {}   # (cut, attr) -> (sumU[B], sumV[B], den[B])
    for k, r in rec.items():
        cols = np.array([pos[int(i)] for i in r['idx']])
        c = cnt[:, cols]
        stat[k] = (c @ r['eU'], c @ r['eV'], c.sum(1))
    return stat


def pct(x):
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]


def summarize(rec, stat):
    cuts = [c for c, _ in CUTS]
    res = {'cells': {}, 'cut': {}, 'pooledAttr': {}, 'pooled': {}}
    Rb = {}
    for c in cuts:
        for a in ATTRS8:
            r = rec[(c, a)]
            su, sv, den = stat[(c, a)]
            Rb[(c, a)] = su / sv
            res['cells'][f'{c}|{a}'] = {'n': int(len(r['idx'])), 'g': r['g'], 'maeU': float(r['eU'].mean()), 'maeV': float(r['eV'].mean()),
                                        'R': float(r['eU'].mean() / r['eV'].mean()), 'R_ci90': pct(Rb[(c, a)]),
                                        'maeU_ci90': pct(su / den), 'maeV_ci90': pct(sv / den)}
        rbar = np.mean([res['cells'][f'{c}|{a}']['R'] for a in ATTRS8])
        rbar_b = np.mean([Rb[(c, a)] for a in ATTRS8], axis=0)
        res['cut'][c] = {'Rbar': float(rbar), 'Rbar_ci90': pct(rbar_b)}
    pb = []
    for a in ATTRS8:
        eu = sum(rec[(c, a)]['eU'].sum() for c in cuts)
        ev = sum(rec[(c, a)]['eV'].sum() for c in cuts)
        n = sum(len(rec[(c, a)]['idx']) for c in cuts)
        bu = sum(stat[(c, a)][0] for c in cuts)
        bv = sum(stat[(c, a)][1] for c in cuts)
        pb.append(bu / bv)
        res['pooledAttr'][a] = {'n': int(n), 'maeU': float(eu / n), 'maeV': float(ev / n), 'R': float(eu / ev), 'R_ci90': pct(bu / bv)}
    pbar = np.mean(pb, axis=0)
    res['pooled'] = {'Rbar': float(np.mean([res['pooledAttr'][a]['R'] for a in ATTRS8])), 'Rbar_ci90': pct(pbar),
                     'Rbar_upper95': float(np.percentile(pbar, 95))}
    ok_cut = all(res['cut'][c]['Rbar'] <= 1.02 for c in cuts)
    bad_attr = [a for a in ATTRS8 if res['pooledAttr'][a]['R'] > 1.05]
    adopt = ok_cut and not bad_attr
    minor = adopt and res['pooled']['Rbar_upper95'] < 1.0
    res['verdict'] = {'everyCutRbar<=1.02': bool(ok_cut), 'attrsPooledR>1.05': bad_attr, 'adopt': bool(adopt), 'pooledRbarUpper95<1': bool(res['pooled']['Rbar_upper95'] < 1.0),
                      'label': 'MINOR (card 0.3.0)' if minor else 'PATCH (card 0.2.10)' if adopt else '不過 adopt'}
    return res


def main():
    t0 = time.time()
    D = L.Data()
    inp = C.load_inputs()
    ch = C.card_chain(D, inp)
    out = {'meta': {'seed': SEED, 'B': B, 'cuts': dict(CUTS), 'sens_midshort_league_prior': SENS, 'games': dict(D.G)}}
    for S in ('2025-26', '2024-25'):
        rec, fits = run_season(D, ch, inp['bt'], S, SENS)
        stat = bootstrap(rec, D.NP)
        out[S] = summarize(rec, stat)
        out[S]['fits'] = fits
        v = out[S]['verdict']
        print(S, 'verdict', v['label'], '| per-cut Rbar', {c: round(x['Rbar'], 4) for c, x in out[S]['cut'].items()},
              '| pooled Rbar', round(out[S]['pooled']['Rbar'], 4), [round(x, 4) for x in out[S]['pooled']['Rbar_ci90']])
        print('   pooled R by attr', {a: round(x['R'], 3) for a, x in out[S]['pooledAttr'].items()}, '| bad', v['attrsPooledR>1.05'])
        if S == '2025-26':
            np.savez_compressed(Path(__file__).with_name('backtest-errors-sens.npz' if SENS else 'backtest-errors.npz'),
                                **{f'{c}|{a}|{k}': (r[k] if k != 'idx' else r['idx']) for (c, a), r in rec.items() for k in ('idx', 'eU', 'eV')})
    out['seconds'] = time.time() - t0
    Path(__file__).with_name('backtest-result-sens.json' if SENS else 'backtest-result.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('done', round(out['seconds'], 1), 's')


if __name__ == '__main__':
    main()
