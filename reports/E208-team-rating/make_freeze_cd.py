# (c)/(d) version of make_freeze.py; usage: python -I -X utf8 make_freeze_cd.py c|d
# builds forward-2026-27-frozen-<X>.json from results/ratingfwd-F-*.json and results/pairsfwd-F-*.json
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, hashlib, os
X = sys.argv[1]; assert X in ('c', 'd')
from common import *
fi = json.load(open(os.path.join(HERE, f'forward-inputs-{X}.json'), encoding='utf8'))
rt = rating(load(f'ratingfwd-{X}')); pr = {(o['h'], o['a']): mean(o['m']) for o in load(f'pairsfwd-{X}')}
ids = sorted(rt); assert len(ids) == 30 and len(pr) == 870
mo = mean([rt[i]['ortg'] for i in ids]); md = mean([rt[i]['drtg'] for i in ids])
out = {}
for t in ids:
    pw = []
    for o in ids:
        if o == t: continue
        ph = Phi((pr[(t, o)] + H) / SIGMA); pa = 1 - Phi((pr[(o, t)] + H) / SIGMA)
        pw.append(0.5 * (ph + pa))
    p_avgopp = mean(pw); W, L = fi['sofar'][t]; gp = W + L
    out[t] = dict(name=fi['teams'][t]['name'], ortg=rt[t]['ortg'], drtg=rt[t]['drtg'], net=rt[t]['net'],
        ortg_centered=rt[t]['ortg'] - mo, drtg_centered=rt[t]['drtg'] - md,
        win_prob_vs_average_neutral=Phi(rt[t]['margin'] / SIGMA),
        win_prob_vs_average_home_away=0.5 * (Phi((rt[t]['margin'] + H) / SIGMA) + Phi((rt[t]['margin'] - H) / SIGMA)),
        win_prob_vs_average_opponent_pool=p_avgopp, W_sofar=W, L_sofar=L, games_remaining=82 - gp,
        predicted_wins_final=W + (82 - gp) * p_avgopp)
meta = dict(spec=f'E-208 forward freeze ({X})', engine='sim 0.1.4', abilities=fi['version'], card=fi['card'], dataCutoff=fi['dataCutoff'],
    home_points=H, sigma=SIGMA, seeds_rating=200, seeds_pairs=40,
    note='no full 2026-27 schedule in repo: predicted_wins_final = W_sofar + games_remaining * mean win prob vs the other 29 teams (home/away averaged)',
    minutes=('(c) team previous-10-game actual minutes average, top 10 normalized to 240 cap 48' if X == 'c' else '(d) top 10 by ability proxy with 36/34/32/30/28/24/20/16/12/8 template and 2G+1C starter rule; rules in preregistration-2024-25.md'), input_sha256=fi['sources'])
pm = {f'{h}|{a}': v for (h, a), v in pr.items()}
fz = dict(meta=meta, teams=out, pair_mean_margin_home_minus_away=pm)
p = os.path.join(HERE, f'forward-2026-27-frozen-{X}.json')
s = json.dumps(fz, ensure_ascii=False, indent=1, sort_keys=True)
open(p, 'w', encoding='utf8', newline='\n').write(s)
h = hashlib.sha256(s.encode('utf8')).hexdigest()
open(os.path.join(HERE, f'forward-2026-27-frozen-{X}.sha256'), 'w').write(h + f'  forward-2026-27-frozen-{X}.json\n')
print(h)
for t in sorted(ids, key=lambda t: -out[t]['net']): print(out[t]['name'], round(out[t]['net'], 1), round(out[t]['predicted_wins_final'], 1))
