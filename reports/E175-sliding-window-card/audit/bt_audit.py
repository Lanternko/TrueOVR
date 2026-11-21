"""E-175 稽核：獨立重算 §2 主判定。用法：python -I -X utf8 bt_audit.py"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac

B, SEED = 2000, 20261101
CUTS = [('0', 0.0), ('10%', 0.10), ('25%', 0.25), ('46.7%', 574 / 1230), ('75%', 0.75)]


def fits_of(bt, opts):
    f = {}
    for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short'):
        fc, fb = dict(bt['production'][a]['fit']), dict(bt['attrs'][a]['fit']['b'])
        if opts.get('league_midshort') and a in ('mid', 'short'):
            fc['prior'] = fb['prior'] = 'league'
        f[a] = (fc, fb)
    for k in ('driveVol', 'driveEff'):
        c = bt['production']['drive']['components'][k]
        f[k] = (dict(c['c']), dict(c['b']))
    return f


def run(db, ch, inp, S, opts=None):
    opts = opts or {}
    bt = inp['bt']
    F = fits_of(bt, opts)
    scale = opts.get('uscale', 1.0)
    by = ac.positions()
    posv = [ac.pos_of(by, p, S) for p in db.pids]
    G = db.G[S]
    rec = {}

    def arms(t, g, fc, fb):
        mv = ac.causal_m(db, S, g, t, fc['prior'], posv)
        mu = ac.causal_m(db, S, g, t, fb['prior'], posv)
        return ac.rate_V(db, t, S, g, fc, mv), ac.rate_U(db, t, S, g, fb, mu, scale)

    for cn, frac in CUTS:
        g = int(round(frac * G))
        for a in ac.ATTRS8:
            if a == 'drive':
                vn, vd = db.agg(S, 'driveVol', g)
                en, ed = db.agg(S, 'driveEff', g)
                sel = np.nonzero((vd >= ac.MIN_D2['driveVol']) & (ed >= ac.MIN_D2['driveEff']))[0]
                z = ch.dz
                score = lambda rv, re_: .5 * (36 * rv - z['mv']) / z['sv'] + .5 * (re_ - z['me']) / z['se']
                tr = ch.map['drive'](score(vn[sel] / vd[sel], en[sel] / ed[sel]))
                Vv, Uv = arms('driveVol', g, *F['driveVol'])
                Ve, Ue = arms('driveEff', g, *F['driveEff'])
                pv, pu = ch.map['drive'](score(Vv[sel], Ve[sel])), ch.map['drive'](score(Uv[sel], Ue[sel]))
            else:
                n, d = db.agg(S, a, g)
                sel = np.nonzero(d >= ac.MIN_D2[a])[0]
                Vr, Ur = arms(a, g, *F[a])
                if a in ('foulDraw', 'pass') and opts.get('composite'):
                    vt = 'vol' if a == 'foulDraw' else 'astvol'
                    vfit = inp['volfit'] if a == 'foulDraw' else inp['astfit']
                    fU = {'k': vfit['k'], 'prior': vfit['prior']}
                    Vx, Ux = arms(vt, g, vfit, fU)
                    nx, dx = db.agg(S, vt, g)
                    sel = sel[dx[sel] > 0]
                    w1, w2 = (.75, .25) if a == 'foulDraw' else (.5, .5)
                    (m1, s1), (m2, s2) = ch.zp[vt], ch.zp[a]
                    comb = lambda xv, xr: w1 * (xv - m1) / s1 + w2 * (xr - m2) / s2
                    mp = ch.map[a + 'Comp']
                    tr = mp(comb(nx[sel] / dx[sel], n[sel] / d[sel]))
                    pv = mp(comb(Vx[sel], Vr[sel]))
                    pu = mp(comb(Ux[sel], Ur[sel]))
                else:
                    if a == 'tovSkill':
                        mp, sg, sh = ch.map['tovSkill'], -1.0, 0.0
                    elif a in ('mid', 'short'):
                        mp, sg, sh = ch.map[a], 1.0, ch.shift[a]
                    elif a in ('foulDraw', 'pass'):
                        mp, sg, sh = ch.map[a + 'Rate'], 1.0, 0.0
                    else:
                        mp, sg, sh = ch.map[a], 1.0, 0.0
                    tr = mp(sg * n[sel] / d[sel] + sh)
                    pv = mp(sg * Vr[sel] + sh)
                    pu = mp(sg * Ur[sel] + sh)
            rec[(cn, a)] = {'idx': sel, 'eV': np.abs(pv - tr), 'eU': np.abs(pu - tr), 'g': g}
    return rec


def summarize(rec):
    cuts = [c for c, _ in CUTS]
    used = sorted({int(i) for r in rec.values() for i in r['idx']})
    pos = {p: j for j, p in enumerate(used)}
    rng = np.random.default_rng(SEED)
    cnt = rng.multinomial(len(used), np.full(len(used), 1 / len(used)), size=B).astype(float)
    st = {}
    for k, r in rec.items():
        c = cnt[:, [pos[int(i)] for i in r['idx']]]
        st[k] = (c @ r['eU'], c @ r['eV'])
    pc = lambda x: [float(np.percentile(x, 5)), float(np.percentile(x, 95))]
    out = {'cells': {}, 'cut': {}, 'pooledAttr': {}}
    Rb = {}
    for c in cuts:
        for a in ac.ATTRS8:
            r = rec[(c, a)]
            Rb[(c, a)] = st[(c, a)][0] / st[(c, a)][1]
            out['cells'][f'{c}|{a}'] = {'n': len(r['idx']), 'maeU': float(r['eU'].mean()), 'maeV': float(r['eV'].mean()),
                                        'R': float(r['eU'].mean() / r['eV'].mean())}
        out['cut'][c] = {'Rbar': float(np.mean([out['cells'][f'{c}|{a}']['R'] for a in ac.ATTRS8])),
                         'ci90': pc(np.mean([Rb[(c, a)] for a in ac.ATTRS8], axis=0))}
    pb = []
    for a in ac.ATTRS8:
        eu = sum(rec[(c, a)]['eU'].sum() for c in cuts)
        ev = sum(rec[(c, a)]['eV'].sum() for c in cuts)
        n = sum(len(rec[(c, a)]['idx']) for c in cuts)
        bb = sum(st[(c, a)][0] for c in cuts) / sum(st[(c, a)][1] for c in cuts)
        pb.append(bb)
        out['pooledAttr'][a] = {'n': n, 'maeU': float(eu / n), 'maeV': float(ev / n), 'R': float(eu / ev), 'ci90': pc(bb)}
    pbar = np.mean(pb, axis=0)
    out['pooled'] = {'Rbar': float(np.mean([out['pooledAttr'][a]['R'] for a in ac.ATTRS8])), 'ci90': pc(pbar), 'upper95': float(np.percentile(pbar, 95))}
    okc = all(out['cut'][c]['Rbar'] <= 1.02 for c in cuts)
    bad = [a for a in ac.ATTRS8 if out['pooledAttr'][a]['R'] > 1.05]
    adopt = okc and not bad
    out['verdict'] = {'everyCutRbar<=1.02': okc, 'attrR>1.05': bad, 'adopt': adopt, 'upper95<1': out['pooled']['upper95'] < 1,
                      'label': 'MINOR' if adopt and out['pooled']['upper95'] < 1 else 'PATCH' if adopt else 'FAIL-adopt'}
    return out


def brief(tag, o):
    print(tag, o['verdict']['label'], 'cuts', {c: round(x['Rbar'], 4) for c, x in o['cut'].items()}, 'pooled', round(o['pooled']['Rbar'], 4),
          [round(x, 4) for x in o['pooled']['ci90']], 'up95', round(o['pooled']['upper95'], 4))
    print('    attrR', {a: round(x['R'], 3) for a, x in o['pooledAttr'].items()}, 'bad', o['verdict']['attrR>1.05'])


if __name__ == '__main__':
    t0 = time.time()
    db = ac.DB()
    inp = ac.load_inputs()
    ch = ac.Chain(db, inp, 'V')
    res = {}
    variants = [('main', {}), ('league_midshort', {'league_midshort': True}), ('uscale0.5', {'uscale': 0.5}), ('composite', {'composite': True})]
    for S in ('2025-26', '2024-25'):
        for nm, o in variants:
            if S == '2024-25' and nm != 'main':
                continue
            rec = run(db, ch, inp, S, o)
            res[f'{S}|{nm}'] = summarize(rec)
            brief(f'{S}|{nm}', res[f'{S}|{nm}'])
            if nm == 'main' and S == '2025-26':
                np.savez_compressed(Path(__file__).with_name('audit_errors_main.npz'),
                                    **{f'{c}|{a}|{k}': r[k] for (c, a), r in rec.items() for k in ('idx', 'eU', 'eV')})
    Path(__file__).with_name('audit_bt.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('sec', round(time.time() - t0, 1))
