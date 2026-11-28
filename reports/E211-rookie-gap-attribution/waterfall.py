"""用法：python -I waterfall.py <out.md> label1=path1.csv:col label2=path2.csv:col ...（依時間順序）
每步：六組平均／中位數、相對上一步的變化；狀元、2–3 順位逐人例子。
組別：#1、2–3、4–10、11–30、31–60、undrafted（kind 非 drafted 或 pick>60）。"""
import sys, csv, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
GR = ['#1', '2-3', '4-10', '11-30', '31-60', 'undr']


def grp(r):
    p = int(r['pick'])
    if r['kind'] != 'drafted' or p > 60:
        return 'undr'
    return '#1' if p == 1 else '2-3' if p <= 3 else '4-10' if p <= 10 else '11-30' if p <= 30 else '31-60'


def load(spec):
    lab, rest = spec.split('=', 1)
    path, col = rest.rsplit(':', 1)
    d = {(r['season'], r['playerId']): r for r in csv.DictReader(open(path, encoding='utf-8'))}
    return lab, {k: float(v[col]) for k, v in d.items()}, d


specs = [load(s) for s in sys.argv[2:]]
base = specs[0][2]
keys = [k for k in base if all(k in s[1] for s in specs)]
g = {k: grp(base[k]) for k in keys}
out = ['| 步驟 | ' + ' | '.join(GR) + ' | 全體 |', '|---|' + '---|' * (len(GR) + 1)]
prev = None
for lab, v, _ in specs:
    mean = {x: st.mean(v[k] for k in keys if g[k] == x) for x in GR}
    med = {x: st.median(v[k] for k in keys if g[k] == x) for x in GR}
    allm, allmed = st.mean(v[k] for k in keys), st.median(v[k] for k in keys)
    out.append(f'| {lab}（平均） | ' + ' | '.join(f'{mean[x]:.2f}' for x in GR) + f' | {allm:.2f} |')
    out.append(f'| 〃（中位數） | ' + ' | '.join(f'{med[x]:.2f}' for x in GR) + f' | {allmed:.2f} |')
    if prev:
        out.append(f'| **本步變化（平均）** | ' + ' | '.join(f'{mean[x]-prev[x]:+.2f}' for x in GR) + f' | {allm-prev["all"]:+.2f} |')
    prev = dict(mean, all=allm)
out.append('')
n = {x: sum(1 for k in keys if g[k] == x) for x in GR}
out.append('人數：' + '、'.join(f'{x}={n[x]}' for x in GR) + f'（共 {len(keys)}）')
out.append('')
names = ['Anthony Edwards', 'Lonzo Ball', 'Cade Cunningham', 'Zion Williamson', 'Paolo Banchero', 'Victor Wembanyama', 'Jabari Smith Jr.', 'Chet Holmgren']
out.append('| 球員 | 順位 | ' + ' | '.join(s[0] for s in specs) + ' |')
out.append('|---|---|' + '---|' * len(specs))
for k in keys:
    nm = base[k]['name']
    if nm in names or (int(base[k]['pick']) == 1 and nm not in names):
        out.append(f'| {nm} | {base[k]["pick"]} | ' + ' | '.join(f'{s[1][k]:.1f}' for s in specs) + ' |')
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('\n'.join(out))
