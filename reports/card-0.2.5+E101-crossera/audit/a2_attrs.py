"""稽核 3：自己組合併池（short、ft、pass），算 r90、r99、SD_pool、S，與 2025-26 頂端 3 人屬性值，對 attributes-e101.csv。
池門檻（GP、MIN）自己從 V61 pergame 算；2025-26 的 MIN 用 benchmark base.json。各季原始值取自 pool/raw-<季>.json（另抽查對 E-090 h1-pairs）。
不 import 產出者或 V61 程式。"""
import json, sys, csv, gzip, math, re
from pathlib import Path
from collections import defaultdict
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
E090 = ROOT/'reports/card-0.2.4+E090-onball-tail'
HIST = ROOT/'reports/ovr-v61-shrink-history-2025-26/history'
PAST = ['2022-23', '2023-24', '2024-25']
raw = json.load(open(E090/'work/a0-raw.json', encoding='utf-8'))
p101 = json.load(open(OUT/'a0-e101.json', encoding='utf-8'))['p']
seas = {s: json.load(open(OUT/'pool'/f'raw-{s}.json', encoding='utf-8')) for s in PAST}
card = {int(r['playerId']): r for r in csv.DictReader(open(OUT/'attributes-e101.csv', encoding='utf-8'))}
pids = sorted(card)

def pergame(s):
    mins, gp = defaultdict(float), defaultdict(int)
    with gzip.open(HIST/f'pergame-{s}.csv.gz', 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            m = float(r['MIN']); p = int(r['playerId'])
            mins[p] += m; gp[p] += (m > 0)
    return mins, gp
pg = {s: pergame(s) for s in PAST}

d = json.load(open(ROOT/'data/benchmark-source/base.json', encoding='utf-8'))
rs = d['data']['resultSets']; rs = rs[0] if isinstance(rs, list) else rs
H = rs['headers']; base = {int(r[H.index('PLAYER_ID')]): float(r[H.index('MIN')]) for r in rs['rowSet']}
pool500_26 = [p for p in pids if base.get(p, 0) >= 500]

def pct(x, arr):
    a = np.asarray(arr)
    return 100*((a < x).sum() + 0.5*(a == x).sum())/len(a)

def anchors(vals):
    s = np.sort(np.asarray(vals, float))
    pc = np.array([pct(v, s) for v in s])
    r90 = s[pc >= 90].min(); r99 = s[pc >= 99].min()
    sd = float(np.std(s)); gap = (r99 - r90)/1.044
    return dict(n=len(s), r90=float(r90), r99=float(r99), SD=sd, gap=gap, ratio=gap/sd, S=max(gap, sd), insurance=sd > gap)

txt = (ROOT/'src/constants.js').read_text(encoding='utf-8')
def curve(name):
    body = re.search(rf'export const {name} = \[(.*?)\];', txt, re.S).group(1)
    return [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]
def attr_at(curv, x):  # curve(attr)->rate, return rate at attr x
    for (x0, y0), (x1, y1) in zip(curv, curv[1:]):
        if x0 <= x <= x1: return y0 + (x - x0)/(x1 - x0)*(y1 - y0)

res = {}
# ---------- 命中率型 short、ft
for a, cname in (('short', 'CURVE_SHORT'), ('ft', 'CURVE_FT')):
    pmap = p101[a] if a == 'short' else raw[a]['p']
    vals = [pmap[str(p)] for p in pool500_26]
    per = {'2025-26': len(vals)}
    for s in PAST:
        mins, _ = pg[s]
        v = [x for k, x in seas[s]['attrs'][a].items() if mins.get(int(k), 0) >= 500]
        per[s] = len(v); vals += v
    an = anchors(vals); an['perSeason'] = per
    a99 = attr_at(curve(cname), 99); sc = 1.96*an['S']
    top = []
    for p in pids:
        pp = pmap[str(p)]
        if pp > a99:
            v = 99 + 51*(1 - math.exp(-(pp - a99)/sc))/(1 - math.exp(-(1 - a99)/sc))
            if a == 'short':
                v = max(40.0, min(150.0, 70 + (v - 70)*raw['short']['discount'][str(p)]))
            top.append((v, card[p]['name'], float(card[p][a])))
    top.sort(reverse=True)
    an['a99'] = a99
    an['top3'] = [{'name': n, 'mine': round(v, 3), 'producer': round(c, 3), 'diff': round(v - c, 4)} for v, n, c in top[:3]]
    res[a] = an
# ---------- 百分位型 pass（GP>=30 且 MPG>=20）
e = raw['pass']
vals = list(e['pool']); per = {'2025-26': len(vals)}
for s in PAST:
    mins, gp = pg[s]
    v = [x for k, x in seas[s]['attrs']['pass'].items() if gp.get(int(k), 0) >= 30 and mins[int(k)]/gp[int(k)] >= 20]
    per[s] = len(v); vals += v
an = anchors(vals); an['perSeason'] = per
top = []
for p in pids:
    if str(p) not in e['r']: continue
    x = e['r'][str(p)]
    if pct(x, vals) >= 99:
        v = 99 + 51*(1 - math.exp(-(x - an['r99'])/(1.96*an['S'])))
        top.append((v, card[p]['name'], float(card[p]['pass'])))
top.sort(reverse=True)
an['top3'] = [{'name': n, 'mine': round(v, 3), 'producer': round(c, 3), 'diff': round(v - c, 4)} for v, n, c in top[:3]]
res['pass'] = an
# ---------- 生產者 tail-summary 對照
ts = json.load(open(OUT/'tail-summary.json', encoding='utf-8'))['e101']
for a in res:
    t = ts[a]
    res[a]['producer'] = {k: t.get(k) for k in ('r90', 'r99', 'SD_pool', 'gapScale', 'ratio', 'S', 'insuranceActive', 'poolN', 'poolPerSeason')}
# ---------- 抽查各季原始值：pool/raw 對 E-090 h1-pairs（pass、ft）
ref = json.load(open(E090/'work/h1-pairs.json', encoding='utf-8'))
chk = {}
for a in ('pass', 'ft'):
    n = bad = 0
    for r in ref[a]:
        for ss, key in ((r['pair'][:7], 'prev'), (r['pair'][-7:], 'next')):
            if ss in seas:
                n += 1; bad += seas[ss]['attrs'][a].get(str(r['pid'])) != r[key]
    chk[a] = {'checked': n, 'mismatch': bad}
res['rawVsE090pairs'] = chk
# ---------- ft 原始值合理性：過去季池內收縮 p 對原始 FTM/FTA 的相關
def ftraw(s):
    m, a_ = defaultdict(float), defaultdict(float)
    with gzip.open(HIST/f'pergame-{s}.csv.gz', 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            p = int(r['playerId']); m[p] += float(r['FTM']); a_[p] += float(r['FTA'])
    return m, a_
fm, fa = ftraw('2023-24')
xs = [(seas['2023-24']['attrs']['ft'][str(p)], fm[p]/fa[p]) for p in fa if fa[p] >= 200 and str(p) in seas['2023-24']['attrs']['ft']]
res['ftSanity2023-24'] = {'n_FTA>=200': len(xs), 'corr_shrunk_vs_raw': float(np.corrcoef(*zip(*xs))[0, 1]),
                          'maxAbsDiff': float(max(abs(a_ - b) for a_, b in xs))}
(Path(__file__).parent/'a2_attrs.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
