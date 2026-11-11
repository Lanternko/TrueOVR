"""E-179 評估：預註冊 preregistration.md（凍結 sha 見 preregistration.sha256）。
卡片＝0.2.9a 底歷史原點（E-164 ranking-S）三季；答案＝E-126 下季 RAPM（net×W、O×W）。前鋒 F＝SF/PF、後衛 G＝PG/SG，各自算 Spearman(屬性, 殘差)。
用法（repo root）：python -I -B -X utf8 reports/E179-forward-pass-vs-rapm/e179_eval.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
sys.path.insert(0, str(E142))
s = importlib.util.spec_from_file_location('pe', E142 / 'phase1_eval.py'); P = importlib.util.module_from_spec(s); s.loader.exec_module(P)
sys.path.insert(0, str(ROOT / 'scripts'))
import season_nav as SN
SEASONS = ['2022-23', '2023-24', '2024-25']
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
SEED, B = 20261101, 2000
JUDGE = ['pass', 'creation']
REPORT = ['drive', 'tovSkill', 'foulDraw']
GROUPS = {'F': {'SF', 'PF'}, 'G': {'PG', 'SG'}, 'C': {'C'}}
EXAMPLES = ['Jalen Williams', 'Jalen Johnson']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(x):
    return rankdata(x) / len(x)


def sp(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1]) if len(x) > 2 else np.nan


def off_scores(card):
    """season_nav.off_def 的做法套在該季卡片內：依位置把 pred0 回歸到 OD_ALL，取進攻段；回 {name: OFF}、pred0 誤差 > 0.02 的比例。"""
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        X = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = np.array([np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL])
    out, bad = {}, 0
    for r in q:
        b = coef[r['pos']]
        x = np.array([float(r[a]) for a in SN.OD_ALL])
        bad += abs(b[0] + b[1:] @ x - float(r['pred0'])) > 0.02
        out[r['name']] = float((b[1:] * (x - mu))[:len(SN.OD_OFF)].sum())
    return out, bad / len(q)


def season_data(t, rec):
    f = E164 / f'ranking-S-{t}.csv'
    card = list(csv.DictReader(open(f, encoding='utf-8-sig')))
    off, badfrac = off_scores(card)
    pop, _ = P.pop_of(t)
    _, mp_next = P.pop_of(NEXT[t])
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    m = {}
    for r in card:
        if float(r['MIN']) < 500:
            continue
        ids = n2.get(P.norm(r['name'])) or []
        if len(ids) == 1:
            m[ids[0]] = r
    d = json.loads((E126 / f'rapm-{NEXT[t]}.json').read_text(encoding='utf-8'))
    assert d['season'] == NEXT[t]
    rv = {int(p): v for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp_next}
    ids = sorted(p for p in m if p in rv)
    rows = [m[p] for p in ids]
    W = np.array([P.wfun(mp_next[p]) for p in ids])
    out = {'ids': ids, 'names': [r['name'] for r in rows], 'pos': np.array([r['pos'] for r in rows]),
           'ovr': np.array([float(r['ovr']) for r in rows]), 'off': np.array([off[r['name']] for r in rows]),
           'net': np.array([rv[p]['net'] for p in ids]) * W, 'O': np.array([rv[p]['O'] for p in ids]) * W}
    for a in JUDGE + REPORT:
        out[a] = np.array([float(r[a]) for r in rows])
    nF, nG = int(np.isin(out['pos'], list(GROUPS['F'])).sum()), int(np.isin(out['pos'], list(GROUPS['G'])).sum())
    out['checks'] = {'c0': sha(f) == rec[f'S-{t}'], 'sha': sha(f), 'n': len(ids), 'nF': nF, 'nG': nG,
                     'c1': len(ids) >= 150 and nF >= 50 and nG >= 50, 'off_bad_frac': badfrac, 'c2': badfrac <= 0.05}
    return out


def stats(d, idx):
    e_net = pct(d['net'][idx]) - pct(d['ovr'][idx])
    e_O = pct(d['O'][idx]) - pct(d['off'][idx])
    pos = d['pos'][idx]
    o = {}
    for a in JUDGE + REPORT:
        x = d[a][idx]
        for tag, e in (('net', e_net), ('O', e_O)):
            for g, ps in GROUPS.items():
                k = np.isin(pos, list(ps))
                o[f'S_{g}_{a}_{tag}'] = sp(x[k], e[k])
            o[f'D_{a}_{tag}'] = o[f'S_F_{a}_{tag}'] - o[f'S_G_{a}_{tag}']
    return o


def main():
    rec = json.loads((E164 / 'results.json').read_text(encoding='utf-8'))['sha256']
    data = {t: season_data(t, rec) for t in SEASONS}
    checks = {t: data[t]['checks'] for t in SEASONS}
    pre_ok = all(c['c0'] and c['c1'] and c['c2'] for c in checks.values())
    res = {'prereg_sha256': sha(HERE / 'preregistration.md'),
           'prereg_sha256_ok': sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(),
           'seed': SEED, 'draws': B, 'checks': checks, 'preconditions_pass': pre_ok}
    if not (pre_ok and res['prereg_sha256_ok']):
        res['verdict'] = 'stopped_at_preconditions'
        (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
        print(json.dumps(checks, ensure_ascii=False, default=float))
        return
    ns = {t: len(data[t]['ids']) for t in SEASONS}
    wts = {t: ns[t] / sum(ns.values()) for t in SEASONS}
    per = {t: stats(data[t], np.arange(ns[t])) for t in SEASONS}
    keys = list(per[SEASONS[0]])

    def pooled(st):
        return {k: float(sum(wts[t] * st[t][k] for t in SEASONS)) for k in keys}
    point = pooled(per)
    rng = np.random.default_rng(SEED)
    draws = {k: [] for k in keys}
    for _ in range(B):
        st = {t: stats(data[t], rng.integers(0, ns[t], ns[t])) for t in SEASONS}
        for k, v in pooled(st).items():
            draws[k].append(v)
    ci = {k: [float(np.nanpercentile(v, 5)), float(np.nanpercentile(v, 95))] for k, v in draws.items()}
    verdict = {}
    for a in JUDGE:
        sF, dd = ci[f'S_F_{a}_net'], ci[f'D_{a}_net']
        verdict[a] = ('forward_overrated' if sF[1] < 0 and dd[1] < 0 else
                      'overrated_all_positions' if sF[1] < 0 else 'no_bias')
    ex, fw = [], []
    for t in SEASONS:
        d = data[t]
        e_net = pct(d['net']) - pct(d['ovr'])
        e_O = pct(d['O']) - pct(d['off'])
        for i, nm in enumerate(d['names']):
            row = {'season': t, 'name': nm, 'pos': str(d['pos'][i]), 'pass': float(d['pass'][i]), 'creation': float(d['creation'][i]),
                   'ovrPct': float(pct(d['ovr'])[i]), 'netPct': float(pct(d['net'])[i]), 'offPct': float(pct(d['off'])[i]),
                   'OPct': float(pct(d['O'])[i]), 'e_net': float(e_net[i]), 'e_O': float(e_O[i])}
            if nm in EXAMPLES:
                ex.append(row)
            if row['pos'] in GROUPS['F']:
                fw.append(row)
    res.update({'n': ns, 'per_season': per, 'pooled': point, 'ci90': ci, 'verdict': verdict,
                'examples': ex, 'top10_forward_pass': sorted(fw, key=lambda r: -r['pass'])[:10]})
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print('verdict', verdict)
    for k in keys:
        print(f'{k:24s} {point[k]:+.3f} [{ci[k][0]:+.3f}, {ci[k][1]:+.3f}]  ' + ' '.join(f'{t}:{per[t][k]:+.3f}' for t in SEASONS))
    print('n', ns, {t: (checks[t]['nF'], checks[t]['nG'], round(checks[t]['off_bad_frac'], 3)) for t in SEASONS})


if __name__ == '__main__':
    main()
