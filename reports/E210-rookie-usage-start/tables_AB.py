"""E-210 A／B 彙整 → AB-tables.json、AB-tables.md。"""
import csv, json, statistics as S, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
H = Path(__file__).resolve().parent
E9 = H.parent / 'E208-rookie-start-recheck'
GROUPS = [('1', 1, 1), ('2-3', 2, 3), ('4-10', 4, 10), ('11-30', 11, 30), ('31-60', 31, 60), ('落選', 61, 99)]


def grp(pick, kind='drafted'):
    if kind == 'undrafted':
        return '落選'
    for g, lo, hi in GROUPS[:-1]:
        if lo <= pick <= hi:
            return g
    return '落選'


def q(v, p):
    v = sorted(v)
    i = p * (len(v) - 1)
    j = int(i)
    return v[j] + (i - j) * (v[min(j + 1, len(v) - 1)] - v[j])


md = []
out = {}
# ---------- A
A = list(csv.DictReader(open(H / 'A-players.csv', encoding='utf-8')))
for r in A:
    for k in r:
        if k not in ('season', 'name', 'kind', 'pos'):
            r[k] = float(r[k])
    r['g'] = grp(int(r['pick']), r['kind'])
A9 = {(r['season'], int(float(r['playerId']))): r for r in csv.DictReader(open(E9 / 'A-players.csv', encoding='utf-8'))}
chk = [abs(r['B0_own_w20'] - float(A9[(r['season'], int(r['playerId']))]['win20C'])) for r in A if (r['season'], int(r['playerId'])) in A9]
chk2 = [abs(r['B0_own_end'] - float(A9[(r['season'], int(r['playerId']))]['seasonEndC'])) for r in A if (r['season'], int(r['playerId'])) in A9]
out['A_B0_vs_E209'] = {'n': len(chk), 'w20_mean_absdiff': S.fmean(chk), 'w20_max': max(chk), 'end_mean_absdiff': S.fmean(chk2), 'end_max': max(chk2)}


def a_tab(sub, arm):
    rows = []
    for g, *_ in GROUPS:
        xs = [r for r in sub if r['g'] == g]
        if not xs:
            continue
        cv = [r['curve'] for r in xs]
        o = {'g': g, 'n': len(xs), 'curve': S.median(cv)}
        for v in ('B0', 'U1'):
            for tag in ('w20', 'end'):
                vals = [r[f'{v}_{arm}_{tag}'] for r in xs]
                o[f'{v}_{tag}_med'] = S.median(vals)
                o[f'{v}_{tag}_p75'] = q(vals, .75)
                o[f'{v}_{tag}_above'] = sum(a > c for a, c in zip(vals, cv)) / len(xs)
        rows.append(o)
    return rows


def a_md(rows, title):
    md.append(f'\n**{title}**\n')
    md.append('| 順位組 | n | 曲線值 | 前20場 中位 B0 → U1 | 前20場 P75 B0 → U1 | 前20場 高於曲線 B0 → U1 | 季末 中位 B0 → U1 | 季末 高於曲線 B0 → U1 |\n|---|---|---|---|---|---|---|---|')
    for o in rows:
        md.append(f"| {o['g']} | {o['n']} | {o['curve']:.1f} | {o['B0_w20_med']:.1f} → {o['U1_w20_med']:.1f} | {o['B0_w20_p75']:.1f} → {o['U1_w20_p75']:.1f} | {o['B0_w20_above']:.0%} → {o['U1_w20_above']:.0%} | {o['B0_end_med']:.1f} → {o['U1_end_med']:.1f} | {o['B0_end_above']:.0%} → {o['U1_end_above']:.0%} |")


md.append('## A 歷屆真新秀（E-141 母體）')
sets = {'全部246人': A, 'D1–D3（93人）': [r for r in A if r['season'] in ('D1', 'D2', 'D3')]}
for nm, sub in sets.items():
    for arm, lab in (('own', 'arm=own（E-209 的「線上算法」欄，w=1）'), ('e116', 'arm=e116（線上的收縮臂）')):
        rows = a_tab(sub, arm)
        out[f'A_{nm}_{arm}'] = rows
        a_md(rows, f'{nm}／{lab}')
        d20 = [r[f'U1_{arm}_w20'] - r[f'B0_{arm}_w20'] for r in sub]
        de = [r[f'U1_{arm}_end'] - r[f'B0_{arm}_end'] for r in sub]
        md.append(f"\n逐人 U1−B0：前20場 平均 {S.fmean(d20):+.2f}（最小 {min(d20):+.1f}、最大 {max(d20):+.1f}），季末 平均 {S.fmean(de):+.2f}（最小 {min(de):+.1f}、最大 {max(de):+.1f}）")
# ---------- B
B = list(csv.DictReader(open(H / 'B-players.csv', encoding='utf-8')))
for r in B:
    for k in r:
        if k not in ('name', 'pos'):
            r[k] = float(r[k])
    r['g'] = grp(int(r['pick']), 'undrafted' if r['pick'] >= 61 else 'drafted')
B9 = {int(float(r['playerId'])): r for r in csv.DictReader(open(E9 / 'B-players.csv', encoding='utf-8'))}
c6 = [abs(r['B0_6'] - float(B9[int(r['playerId'])]['ovr6'])) for r in B if int(r['playerId']) in B9]
cE = [abs(r['B0_end'] - float(B9[int(r['playerId'])]['ovrend'])) for r in B if int(r['playerId']) in B9]
out['B_B0_vs_E209'] = {'n': len(c6), 'ovr6_mean_absdiff': S.fmean(c6), 'ovr6_max': max(c6), 'end_mean_absdiff': S.fmean(cE), 'end_max': max(cE)}
NS = (0, 3, 6, 10, 20, 'end')


def mean_d(rows, v, N):
    return S.fmean(r[f'{v}_{N}'] - r[f'{v}_0'] for r in rows)


md.append('\n## B 2025-26 屆重播（40 人，arm=e116＝線上算法）')
md.append('\n### 平均 Δ（相對各自的第 0 場；兩版第 0 場都＝曲線值）\n')
md.append('| 組 | n | 版本 | ' + ' | '.join(f'第{N}場' if N != 'end' else '季末' for N in NS[1:]) + ' |\n|---|---|---|' + '---|' * (len(NS) - 1))
bt = {}
for lab, rows in (('全部', B), ('前6場≥90分鐘', [r for r in B if r['min6'] >= 90]), ('前6場30–90分鐘', [r for r in B if 30 <= r['min6'] < 90]), ('前6場<30分鐘', [r for r in B if r['min6'] < 30])):
    for v in ('B0', 'U1'):
        vals = [mean_d(rows, v, N) for N in NS[1:]]
        bt[f'{lab}_{v}'] = vals
        md.append(f'| {lab} | {len(rows)} | {v} | ' + ' | '.join(f'{x:+.1f}' for x in vals) + ' |')
out['B_meanD'] = bt
md.append('\n### 平均 Δ 逐場曲線（全部 40 人）\n')
cols = list(range(1, 21)) + [30, 'end']
md.append('| 版本 | ' + ' | '.join(str(N) if N != 'end' else '季末' for N in cols) + ' |\n|---|' + '---|' * len(cols))
for v in ('B0', 'U1'):
    md.append(f'| {v} | ' + ' | '.join(f'{mean_d(B, v, N):+.1f}' for N in cols) + ' |')
md.append('| U1−B0 | ' + ' | '.join(f'{mean_d(B, "U1", N) - mean_d(B, "B0", N):+.1f}' for N in cols) + ' |')
out['B_curve'] = {v: [mean_d(B, v, N) for N in cols] for v in ('B0', 'U1')}
md.append('\n### 單場跳動（第 N−1 場→第 N 場，N=1..20，OVR 變化的絕對值）\n')
md.append('| 版本 | 每人「最大單場跳動」平均 | 全員最大單場跳動 | 前 6 場平均單場 | 第 7–20 場平均單場 | 跳動≥5 的次數（共 800 步） |\n|---|---|---|---|---|---|')
jump = {}
for v in ('B0', 'U1'):
    mx, early, late, big = [], [], [], 0
    top = (0, '')
    for r in B:
        steps = [abs(r[f'{v}_{N}'] - r[f'{v}_{N - 1}']) for N in range(1, 21)]
        mx.append(max(steps))
        early += steps[:6]
        late += steps[6:]
        big += sum(s >= 5 for s in steps)
        if max(steps) > top[0]:
            top = (max(steps), r['name'])
    jump[v] = {'meanMax': S.fmean(mx), 'top': top, 'early': S.fmean(early), 'late': S.fmean(late), 'big': big}
    md.append(f"| {v} | {S.fmean(mx):.1f} | {top[0]:.1f}（{top[1]}） | {S.fmean(early):.2f} | {S.fmean(late):.2f} | {big} |")
out['B_jump'] = jump
md.append('\n### 依順位分組（2025-26 屆，n 小）\n')
md.append('| 順位組 | n | 曲線值 | 季末 平均 B0 → U1 | 季末 中位 B0 → U1 | 前20場−起點 平均 B0 → U1 | 季末−起點 平均 B0 → U1 |\n|---|---|---|---|---|---|---|')
bg = {}
for g, *_ in GROUPS:
    xs = [r for r in B if r['g'] == g]
    if not xs:
        continue
    o = {'n': len(xs), 'curve': S.fmean(r['curve'] for r in xs)}
    for v in ('B0', 'U1'):
        o[f'{v}_end_mean'] = S.fmean(r[f'{v}_end'] for r in xs)
        o[f'{v}_end_med'] = S.median(r[f'{v}_end'] for r in xs)
        o[f'{v}_dEnd'] = mean_d(xs, v, 'end')
        o[f'{v}_d20'] = mean_d(xs, v, 20)
    bg[g] = o
    md.append(f"| {g} | {len(xs)} | {o['curve']:.1f} | {o['B0_end_mean']:.1f} → {o['U1_end_mean']:.1f} | {o['B0_end_med']:.1f} → {o['U1_end_med']:.1f} | {o['B0_d20']:+.1f} → {o['U1_d20']:+.1f} | {o['B0_dEnd']:+.1f} → {o['U1_dEnd']:+.1f} |")
out['B_groups'] = bg
md.append('\n### 個人例子\n')
md.append('| 球員 | 順位 | 版本 | 第0場 | 第3場 | 第6場 | 第10場 | 第20場 | 季末 |\n|---|---|---|---|---|---|---|---|---|')
for nm in ('Cooper Flagg', 'Dylan Harper', 'Kon Knueppel', 'VJ Edgecombe', 'Ace Bailey'):
    rr = [r for r in B if r['name'] == nm]
    if not rr:
        continue
    r = rr[0]
    for v in ('B0', 'U1'):
        md.append(f"| {nm} | {int(r['pick'])} | {v} | " + ' | '.join(f"{r[f'{v}_{N}']:.1f}" for N in NS) + ' |')
# 排名變動：季末 OVR 排序（40 人）
for v in ('B0', 'U1'):
    out[f'B_end_rank_{v}'] = [r['name'] for r in sorted(B, key=lambda r: -r[f'{v}_end'])[:10]]
json.dump(out, open(H / 'AB-tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
(H / 'AB-tables.md').write_text('\n'.join(md), encoding='utf-8')
print('\n'.join(md))
print(json.dumps({k: out[k] for k in ('A_B0_vs_E209', 'B_B0_vs_E209')}))
