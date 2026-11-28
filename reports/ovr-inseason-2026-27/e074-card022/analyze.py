"""E-074 比對：out-020（inseason 0.2.0c 重現）vs out-022（inseason 0.2.1）。輸出 compare.md、compare.json。
用法：CARD_MODE=022 python -I reports/ovr-inseason-2026-27/e074-card022/analyze.py"""
import csv, json, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import run_c4_live as L  # noqa: E402

def rd(p):
    return {int(r['playerId']): r for r in csv.DictReader(p.open(encoding='utf-8'))}
def rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r
def spearman(a, b):
    ra, rb = rank(a), rank(b); ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return num / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5

o20, o22 = rd(HERE / 'out-020/ranking.csv'), rd(HERE / 'out-022/ranking.csv')
assert set(o20) == set(o22)
out = {'n020': len(o20), 'n022': len(o22)}
md = []
# (c2) 先驗 OVR vs card 0.2.2 每場 OVR
card = {r['name']: float(r['ovr']) for r in csv.DictReader((ROOT / 'reports/card-0.2.2/ranking.csv').open(encoding='utf-8'))}
names = [r['name'] for r in o22.values() if r['name'] in card]
out['spearman_lastOVR_vs_card022'] = spearman([float(next(r for r in o22.values() if r['name'] == n)['lastOVR']) for n in names], [card[n] for n in names])
out['spearman_n'] = len(names)
out['finite022'] = all(float(r['ovr']) == float(r['ovr']) and abs(float(r['ovr'])) < 1e9 for r in o22.values())
# 另算 prior 卡全部 582 人（不限已出賽）：lastOVR 只輸出已出賽者，所以只能用 362 人
# 1) 前 20
def top(o, k=20):
    return [r for r in sorted(o.values(), key=lambda r: -float(r['ovr']))[:k]]
t20, t22 = top(o20), top(o22)
n20, n22 = {r['name']: r for r in t20}, {r['name']: r for r in t22}
md.append('## 1. 前 20 名變化（0.2.0c → 0.2.1）\n')
md.append('進榜：' + '、'.join(f"{n}（{n22[n]['ovr']}，原 #{next(r for r in o20.values() if r['name']==n)['rank']} {next(r for r in o20.values() if r['name']==n)['ovr']}）" for n in n22 if n not in n20) + '\n')
md.append('出榜：' + '、'.join(f"{n}（原 {n20[n]['ovr']}，現 #{next(r for r in o22.values() if r['name']==n)['rank']} {next(r for r in o22.values() if r['name']==n)['ovr']}）" for n in n20 if n not in n22) + '\n')
out['top20_in'] = [n for n in n22 if n not in n20]; out['top20_out'] = [n for n in n20 if n not in n22]
# 2) OVR 變動
d = {p: float(o22[p]['ovr']) - float(o20[p]['ovr']) for p in o22}
out['absdelta_median'] = statistics.median(abs(v) for v in d.values()); out['absdelta_max'] = max(abs(v) for v in d.values())
vp = json.loads((ROOT / 'reports/card-0.2.2/cards/P1/primary/summary.json').read_text(encoding='utf-8'))['valuePer10AttributePoints']
A = [a for a in vp]
md.append(f"\n## 2. OVR 變動\n\n|ΔOVR| 中位數 {out['absdelta_median']:.2f}、最大 {out['absdelta_max']:.2f}（{len(d)} 人）。主要屬性＝(Δ屬性×valuePer10AttributePoints/10) 絕對值最大者（線性近似，不含位置交互作用與 MPG 映射）。\n")
rows = []
for p in sorted(d, key=lambda p: -abs(d[p]))[:10]:
    ch = sorted(((float(o22[p][a]) - float(o20[p][a])) * vp[a]['per36'] / 10, a, float(o20[p][a]), float(o22[p][a])) for a in A)
    ch = sorted(ch, key=lambda t: -abs(t[0]))[:3]
    rows.append(f"| {o22[p]['name']} | {o20[p]['ovr']} | {o22[p]['ovr']} | {d[p]:+.1f} | " + '；'.join(f"{a} {x:.1f}→{y:.1f}" for _, a, x, y in ch) + ' |')
md.append('| 球員 | 0.2.0c | 0.2.1 | Δ | 主要屬性（前 3，x0＋C4 後） |\n|---|---|---|---|---|\n' + '\n'.join(rows))
# 3) foulDraw 新舊公式（同一視窗、同一 usage 前的觀測值 y）
sd26, mp = L.setup()
w26, _ = L.F.windows_of(L.PRIOR, L.ALL_N)
fz_rows = []
for p, o in o22.items():
    rec = w26.get(p)
    if rec is None or L.IC.sample_of(rec, 'drive') < L.SA.SEASON_MIN_SAMPLE['drive']:
        continue
    smp = rec['sample']
    fz_rows.append((abs(L.foul_draw_y(rec) - rec['drive']), o['name'], smp['fta'] / smp['min'] * 36, smp['fta'] / smp['fga'], rec['drive'], L.foul_draw_y(rec), int(o['N']), smp['fga']))
fz_rows.sort(reverse=True)
out['foulDrawY_n'] = len(fz_rows)
out['foulDrawY_medianAbsDiff'] = statistics.median(r[0] for r in fz_rows)
md.append(f"\n\n## 3. foulDraw 新舊公式（視窗觀測值 y，未收縮；達最小樣本 FGA≥50 的 {len(fz_rows)} 人，|新−舊| 中位數 {out['foulDrawY_medianAbsDiff']:.1f}）\n")
md.append('| 球員 | N | FGA | FTA/36 | FTA/FGA | 舊 y（FTA/FGA 百分位） | 新 y（E-070） |\n|---|---|---|---|---|---|---|\n' + '\n'.join(
    f"| {r[1]} | {r[6]} | {r[7]:.0f} | {r[2]:.2f} | {r[3]:.3f} | {r[4]:.1f} | {r[5]:.1f} |" for r in fz_rows[:5]))
sga = [r for r in fz_rows if r[1].startswith('Shai')]
(HERE / 'compare.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(HERE / 'compare.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1)); print('\n'.join(md))
