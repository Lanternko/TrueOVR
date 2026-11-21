"""role-audit：card 0.2.14-cand 獨立重算（不 import build_cand.py／e290_eval.py／e288 鏈）。
名字對應自己做（NFKD 去重音、小寫、去標點），資料只讀 0.2.13a 卡、stats-2025-26.csv、hustle-2025-26.json。
用法（repo root）：python -I -B -X utf8 reports/audit-0.2.14-cand/recompute.py"""
import csv, json, unicodedata, re, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LAM = 0.5

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())

card = list(csv.DictReader(open(ROOT / 'reports/card-0.2.13a/ranking.csv', encoding='utf-8')))
cand = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.14-cand/ranking.csv', encoding='utf-8'))}
st = {}
for r in csv.DictReader(open(ROOT / 'reports/E227-lineup-transformer-r2/data/stats-2025-26.csv', encoding='utf-8')):
    st.setdefault(norm(r['name']), []).append(r)
js = json.loads((ROOT / 'data/tracking-cells/2025-26/hustle-2025-26.json').read_text(encoding='utf-8'))
H = {}
for row in js['rowSet']:
    r = dict(zip(js['headers'], row)); H.setdefault(norm(r['PLAYER_NAME']), []).append(r)

def f(x):
    return float(x) if x not in ('', None) else np.nan

N = len(card)
names = [r['name'] for r in card]
pos = np.array([r['pos'] for r in card]); MIN = np.array([float(r['MIN']) for r in card])
ovr = np.array([float(r['ovr']) for r in card]); reb = np.array([float(r['rebound']) for r in card])
ob = np.full(N, np.nan); db = np.full(N, np.nan); con = np.full(N, np.nan); hmin = np.zeros(N)
uniq = np.zeros(N, bool)
for i, nm in enumerate(names):
    s = st.get(norm(nm)) or []
    if len(s) == 1:
        uniq[i] = True; ob[i] = f(s[0]['orebPct']); db[i] = f(s[0]['drebPct'])
    h = H.get(norm(nm)) or []
    if len(h) == 1:
        hmin[i] = h[0]['MIN'] or 0
        if hmin[i] >= 200:
            con[i] = (h[0]['CONTESTED_SHOTS_2PT'] or 0) / hmin[i] * 36

pop = (MIN >= 500) & uniq
print('eval pop n =', pop.sum(), ' (build_cand 說 379)')
sd = ovr[pop].std()
ref = np.sqrt((pos[pop] == 'C').mean())
print(f'sd(ovr, pop, ddof0)={sd:.4f}  sd(全 582)={ovr.std():.4f}  P_ref={ref:.6f}')

def z(v, m):
    k = m & np.isfinite(v); mu, s = v[k].mean(), v[k].std()
    out = (v - mu) / s
    return np.where(np.isfinite(out), out, 0.0)

rebc = np.clip((z(reb, pop) + z(ob, pop) + z(db, pop)) / 3, 0, 1.5)
conr = np.clip(z(con, pop), 0, 1.5)
rms = lambda v: np.sqrt((v[pop] ** 2).mean())
Preb = rebc * ref / rms(rebc); Pcon = conr * ref / rms(conr)
mix = .5 * Preb + .5 * Pcon
Pmix = mix * ref / rms(mix)
bonus = LAM * sd * Pmix
new = np.round(ovr + bonus, 1)
print(f'scales REBc={ref/rms(rebc):.6f} CON={ref/rms(conr):.6f} MIX={ref/rms(mix):.6f}')

cb = np.array([float(cand[n]['mixBonus']) for n in names]); co = np.array([float(cand[n]['ovr']) for n in names])
d = np.abs(bonus - cb); do = np.abs(new - co)
print(f'mixBonus |diff| max={d.max():.4f}  >0.05: {(d>0.05).sum()}  ;  ovr |diff|>0.05: {(do>0.05).sum()}')
bad = np.where(d > 0.05)[0]
rows = []
for i in bad:
    rows.append((names[i], pos[i], MIN[i], round(bonus[i], 3), cb[i], bool(pop[i]), bool(uniq[i])))
for r in sorted(rows, key=lambda r: -abs(r[3] - r[4]))[:40]:
    print('  diff', r)
# 非母體（MIN<500）拿到的加分
lo = ~pop
print('非母體人數', lo.sum(), '其中 cand 有加分(>0)', (cb[lo] > 0).sum(), '; cand 加分=0 的 MIN>=200 人', ((cb == 0) & (MIN >= 200)).sum())
order = np.argsort(-cb)
print('cand 加分最高 15：')
for i in order[:15]:
    print(f'  {names[i]:25s} {pos[i]} MIN={MIN[i]:.0f} cand={cb[i]:.2f} mine={bonus[i]:.2f} oreb%={ob[i]} dreb%={db[i]} con36={con[i]:.2f}' if np.isfinite(con[i]) else f'  {names[i]:25s} {pos[i]} MIN={MIN[i]:.0f} cand={cb[i]:.2f} mine={bonus[i]:.2f} oreb%={ob[i]} con=NA')
print('MIN<1000 加分 >=4：')
for i in order:
    if MIN[i] < 1000 and cb[i] >= 4:
        print(f'  {names[i]:25s} {pos[i]} MIN={MIN[i]:.0f} cand={cb[i]:.2f} rank {card[i]["rank"]}->{cand[names[i]]["rank"]}')
np.savez(OUT / 'recompute.npz', names=np.array(names), bonus=bonus, cb=cb, pop=pop, MIN=MIN, pos=pos)
