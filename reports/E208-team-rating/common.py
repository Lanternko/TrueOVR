import json, glob, math, os
H = 2.5      # fixed home-advantage points (pre-registered, not tuned)
SIGMA = 12.0 # fixed margin spread for margin->win prob (pre-registered)
HERE = os.path.dirname(os.path.abspath(__file__))
def Phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def load(tag):
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, 'results', tag + '-*.json'))):
        out += json.load(open(f, encoding='utf8'))['res']
    return out
def mean(a): return sum(a) / len(a)
def rating(res):
    r = {}
    for o in res:
        ortg = 100 * o['pf'] / o['pof']; drtg = 100 * o['pa'] / o['poa']
        r[o['id']] = dict(ortg=ortg, drtg=drtg, net=ortg - drtg, margin=mean(o['m']), n=len(o['m']))
    return r
