"""E-285 名次比較（本機，讀 results/value.json）：兩臂淨／防守換人值名次、Spearman、指名球員、變動最大者 → rank-summary.json、ranking.csv。"""
import csv, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
NAMED = ['Kevin Durant', 'Stephen Curry', 'Victor Wembanyama', 'Rudy Gobert', 'Anthony Davis', 'Bam Adebayo', 'Jarrett Allen',
         'Isaiah Hartenstein', 'Alex Caruso', 'Amen Thompson', 'Trae Young', 'Brook Lopez', 'Herbert Jones', 'Jaren Jackson Jr.',
         'Nikola Jokić', 'Karl-Anthony Towns']
A0, A1 = 'R2-stats', 'R2-statsX'


def rank(v):
    v = np.asarray(v); return (-v).argsort().argsort() + 1


def sp(a, b):
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def main():
    d = json.load(open(os.path.join(HERE, 'results', 'value.json'), encoding='utf-8'))
    nm = d['names']; n = len(nm); out = {'n': n, 'spearman': {}, 'top20': {}, 'named': {}, 'movers': {}}
    R = {}
    for k in ('net', 'def', 'off'):
        out['spearman'][k] = round(sp(d['arms'][A0][k], d['arms'][A1][k]), 4)
        for a in (A0, A1):
            R[(a, k)] = rank(d['arms'][a][k])
        for a in (A0, A1):
            o = np.argsort(R[(a, k)])[:20]
            out['top20'][f'{a}:{k}'] = [(nm[i], round(d['arms'][a][k][i], 2)) for i in o]
        diff = R[(A1, k)] - R[(A0, k)]
        o = np.argsort(diff)
        out['movers'][k] = {'up': [(nm[i], int(R[(A0, k)][i]), int(R[(A1, k)][i])) for i in o[:10]],
                            'down': [(nm[i], int(R[(A0, k)][i]), int(R[(A1, k)][i])) for i in o[::-1][:10]],
                            'meanAbsShift': round(float(np.abs(diff).mean()), 1)}
    for s in NAMED:
        if s in nm:
            i = nm.index(s)
            out['named'][s] = {k: (int(R[(A0, k)][i]), int(R[(A1, k)][i])) for k in ('net', 'def')}
    with open(os.path.join(HERE, 'ranking.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['name', 'pos', 'min'] + [f'{a}:{k}{x}' for a in (A0, A1) for k in ('net', 'off', 'def') for x in ('', '_rank')])
        for i in np.argsort(R[(A1, 'net')]):
            w.writerow([nm[i], 'PG SG SF PF C'.split()[d['modal'][i]], d['min'][i]] + [v for a in (A0, A1) for k in ('net', 'off', 'def') for v in (round(d['arms'][a][k][i], 3), int(R[(a, k)][i]))])
    json.dump(out, open(os.path.join(HERE, 'rank-summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
