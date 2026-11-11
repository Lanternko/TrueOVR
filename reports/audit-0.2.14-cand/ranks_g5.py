"""role-audit：名次副作用與 G5（2K27、EPM 名次相關），比較 0.2.13a、候選卡、以及「全 582 人都套加分」的變體。
用法（repo root，先跑 recompute.py）：python -I -B -X utf8 reports/audit-0.2.14-cand/ranks_g5.py"""
import csv, unicodedata, re
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
ROOT = Path(__file__).resolve().parents[2]; OUT = Path(__file__).resolve().parent
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s); return ' '.join(s.split())
z = np.load(OUT / 'recompute.npz', allow_pickle=True)
names = list(z['names']); pos = z['pos']; MIN = z['MIN']; pop = z['pop']; full_bonus = z['bonus']; cb = z['cb']
card = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.13a/ranking.csv', encoding='utf-8'))}
o0 = np.array([float(card[n]['ovr']) for n in names]); r0 = np.array([int(card[n]['rank']) for n in names])
# 重建自己的候選：母體內套加分（= cand 實際行為），檢查與 cand 一致
mine_pop = np.where(cb != 0, full_bonus, 0.0)  # 名單差異已在 recompute 報告
var = {'0.2.13a': o0, 'cand': np.round(o0 + cb, 1), 'full582': np.round(o0 + full_bonus, 1)}
def ranks(o):  # 同分依原名次
    idx = sorted(range(len(o)), key=lambda i: (-o[i], r0[i])); r = np.empty(len(o), int); r[idx] = np.arange(1, len(o) + 1); return r
R = {k: ranks(v) for k, v in var.items()}
cand_rank = {r['name']: int(r['rank']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.14-cand/ranking.csv', encoding='utf-8'))}
print('cand rank 重排一致：', all(R['cand'][i] == cand_rank[n] for i, n in enumerate(names)))
for k in ('cand', 'full582'):
    print(f'\n== {k} 前十：', [(names[i], pos[i], int(r0[i])) for i in np.argsort(R[k])[:10]])
    drops = [(names[i], int(r0[i]), int(R[k][i])) for i in range(len(names)) if r0[i] <= 30 and R[k][i] - r0[i] > 10]
    d10 = [(names[i], int(r0[i]), int(R[k][i])) for i in range(len(names)) if r0[i] <= 30 and R[k][i] - r0[i] >= 10]
    print('前30 掉>10：', drops, '；掉>=10：', d10)
b = var['cand'] - o0
print('\n各位置平均加分（全卡／MIN>=500）')
for p in ('PG', 'SG', 'SF', 'PF', 'C'):
    m = pos == p; q = m & (MIN >= 500)
    print(f'  {p}: {b[m].mean():.2f} / {b[q].mean():.2f}  max {b[m].max():.2f}')
cap = b.max(); print('加分上限', round(cap, 3), '達上限人數', int((b > cap - 0.01).sum()), [names[i] for i in np.where(b > cap - 0.01)[0]])
# 外部對照
tw = {norm(r['name']): float(r['overall2k']) for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8-sig')) if r['overall2k']}
ep = {norm(r['name']): (float(r['net']), float(r['poss2627'])) for r in csv.DictReader(open(ROOT / 'reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8'))}
print('\nG5 名次相關（Spearman）')
for lab, mask in (('全員 MIN>=500', MIN >= 500), ('C+PF MIN>=500', (MIN >= 500) & np.isin(pos, ['PF', 'C'])), ('前100(0.2.13a)', r0 <= 100)):
    for src, D, extra in (('2K27', tw, None), ('EPM net poss>=200', ep, 200)):
        idx = [i for i in range(len(names)) if mask[i] and norm(names[i]) in D and (extra is None or D[norm(names[i])][1] >= extra)]
        y = [D[norm(names[i])] if extra is None else D[norm(names[i])][0] for i in idx]
        s = ' '.join(f"{k}={spearmanr([var[k][i] for i in idx], y)[0]:.4f}" for k in var)
        print(f'  {lab:16s} {src:18s} n={len(idx):3d} {s}')
show = ['Victor Wembanyama', 'Nikola Jokić', 'Shai Gilgeous-Alexander', 'Chet Holmgren', 'Evan Mobley', 'Anthony Davis', 'Anthony Edwards', 'Kevin Durant',
        'Rudy Gobert', 'Jarrett Allen', 'Ivica Zubac', 'Jalen Duren', 'Alperen Sengun', 'Karl-Anthony Towns', 'Joel Embiid', 'Devin Booker', 'Tyrese Maxey', 'Paul Reed', 'Trayce Jackson-Davis', 'Zach Edey', 'Ariel Hukporti']
print('\n代表球員：名字 | pos | MIN | 0.2.13a | cand | full582 | 加分 | 2K27 | EPM net(poss)')
for n in show:
    if n not in names: continue
    i = names.index(n); e = ep.get(norm(n))
    print(f'  {n} | {pos[i]} | {MIN[i]:.0f} | {r0[i]} | {R["cand"][i]} | {R["full582"][i]} | {b[i]:+.2f} | {tw.get(norm(n), "—")} | {e if e else "—"}')
# EPM 名次（poss>=200 的人群內）
