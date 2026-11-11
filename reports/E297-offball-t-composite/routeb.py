"""E-297 第二階段契合度（路線 B，prereg 第 43、47 行）：每臂換人值對 BPM／OBPM／2K27 的 Spearman 減 base，以球員 bootstrap 2000 次報 90% 區間。
  python -I -X utf8 routeb.py
"""
import csv, json, os, re, unicodedata
import numpy as np
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); R = os.path.join(HERE, 'results')


def nm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def main():
    ev = json.load(open(os.path.join(R, 'eval.json'), encoding='utf-8')); arms = ev['arms']
    V = {a: json.load(open(os.path.join(R, f'value-{a}.json'), encoding='utf-8')) for a in arms}
    pids, names = V['base']['pids'], V['base']['names']
    bpm = {r['playerId']: r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'external-impact', 'bpm', 'bpm_2025-26.csv'), encoding='utf-8'))}
    k2 = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'reports', 'ovr-v55-2k27-compare', '2k27_ratings.csv'), encoding='utf-8-sig')):
        if r['overall2k']:
            k2.setdefault(nm(r['name']), float(r['overall2k']))
    refs = {'net~BPM': ('net', [float(bpm[p]['bpm']) if p in bpm else None for p in pids]),
            'off~OBPM': ('off', [float(bpm[p]['obpm']) if p in bpm else None for p in pids]),
            'net~2K27': ('net', [k2.get(nm(n)) for n in names])}
    rng = np.random.default_rng(297); out = {}
    idx = {k: np.array([i for i, y in enumerate(v[1]) if y is not None]) for k, v in refs.items()}
    boots = {k: [rng.integers(0, len(ix), len(ix)) for _ in range(2000)] for k, ix in idx.items()}
    for a in arms:
        assert V[a]['pids'] == pids
        o = {}
        for k, (fld, ys) in refs.items():
            ix = idx[k]; y = np.array([ys[i] for i in ix]); x = np.array(V[a][fld])[ix]; xb = np.array(V['base'][fld])[ix]
            r = spearmanr(x, y)[0]; o[k] = {'rho': round(float(r), 4), 'n': len(ix)}
            if a != 'base':
                bs = [spearmanr(x[b], y[b])[0] - spearmanr(xb[b], y[b])[0] for b in boots[k]]
                o[k]['d'] = round(float(r - spearmanr(xb, y)[0]), 4); o[k]['ci90'] = [round(float(q), 4) for q in np.percentile(bs, [5, 95])]
        if a != 'base':
            ds = [o[k]['d'] for k in refs]; dm = ev['test']['arm'][a]['dNet']['point']
            o['meanD'] = round(float(np.mean(ds)), 4)
            o['routeB'] = bool(np.mean(ds) >= 0.01 and min(ds) >= -0.01 and dm <= 2.0)
        out[a] = o
    json.dump(out, open(os.path.join(R, 'routeb.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for a, o in out.items():
        print(a, {k: (v['rho'], v.get('d')) for k, v in o.items() if isinstance(v, dict)}, o.get('meanD'), o.get('routeB'))


if __name__ == '__main__':
    main()
