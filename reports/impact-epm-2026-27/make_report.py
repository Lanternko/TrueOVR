"""產生 report.md 的 sanity 表（python -I reports/impact-epm-2026-27/make_report.py）。"""
import csv, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
rows = list(csv.DictReader(open(HERE / 'epm-live.csv', encoding='utf-8')))
S = json.loads((HERE / 'epm-live-summary.json').read_text(encoding='utf-8'))
f = lambda x: float(x) if x != '' else None
last = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm-prior.csv', encoding='utf-8'))}
def rank(v):
    o = np.argsort(v); r = np.empty(len(v)); r[o] = np.arange(len(v)); return r
def sp(a, b): return float(np.corrcoef(rank(np.array(a)), rank(np.array(b)))[0, 1])
vets = [r for r in rows if r['careerO'] != '' and int(r['playerId']) in last]
out = ['# 2026-27 自製 EPM 式影響力 sanity 檢查', '',
       f"資料截至 {S['dataCutoff']}；{S['players']} 人（其中 {S['rookiesNoCareer']} 人沒有生涯 RAPM）。單位：每 100 回合，net = O + D。", '',
       '## 1. 老將 net 對 2025-26 單季 RAPM net 的 Spearman', '']
for lo in (0, 100, 200):
    v = [r for r in vets if float(r['poss2627']) >= lo]
    out.append(f"- 當季回合 ≥ {lo}：n={len(v)}，Spearman {sp([float(r['net']) for r in v], [float(last[int(r['playerId'])]['lastSeasonNet']) for r in v]):.3f}")
out += ['', '## 2. 前 15 與後 10（當季回合 ≥ 100 者；全體最低多為只打幾回合的人，見第 4 節）', '', '| 名次 | 球員 | O | D | net | 當季回合 | 生涯 net |', '|---|---|---|---|---|---|---|']
big = [r for r in rows if float(r['poss2627']) >= 100]
cn = lambda r: '' if r['careerO'] == '' else f"{f(r['careerO']) + f(r['careerD']):+.1f}"
for i, r in enumerate(big[:15]): out.append(f"| {i+1} | {r['name']} | {r['O']} | {r['D']} | {r['net']} | {float(r['poss2627']):.0f} | {cn(r)} |")
out.append('| … | | | | | | |')
for i, r in enumerate(big[-10:]): out.append(f"| {len(big)-9+i} | {r['name']} | {r['O']} | {r['D']} | {r['net']} | {float(r['poss2627']):.0f} | {cn(r)} |")
out += ['', '## 3. 新秀前 10（無生涯 RAPM；box 先驗＝角色先驗收縮後）', '', '| 球員 | net | box O | box D | box net | 當季回合 |', '|---|---|---|---|---|---|']
roo = sorted([r for r in rows if r['careerO'] == ''], key=lambda r: -float(r['net']))
for r in roo[:10]: out.append(f"| {r['name']} | {r['net']} | {r['boxO']} | {r['boxD']} | {f(r['boxO'])+f(r['boxD']):+.2f} | {float(r['poss2627']):.0f} |")
out += ['', '## 4. 當季回合最少的 10 人（應貼近先驗）', '', '| 球員 | 當季回合 | 先驗 net | 輸出 net | 差 | 有生涯 |', '|---|---|---|---|---|---|']
for r in sorted(rows, key=lambda r: float(r['poss2627']))[:10]:
    pn = f(r['priorO']) + f(r['priorD'])
    out.append(f"| {r['name']} | {float(r['poss2627']):.1f} | {pn:+.2f} | {r['net']} | {float(r['net'])-pn:+.2f} | {'是' if r['careerO'] != '' else '否（角色先驗）'} |")
lowd = [abs(float(r['net']) - (f(r['priorO']) + f(r['priorD']))) for r in rows if float(r['poss2627']) < 30]
hi = [abs(float(r['net']) - (f(r['priorO']) + f(r['priorD']))) for r in rows if float(r['poss2627']) >= 200]
out += ['', f"輸出與先驗的平均絕對差：當季回合 <30（n={len(lowd)}）{np.mean(lowd):.2f}；≥200（n={len(hi)}）{np.mean(hi):.2f}。", '',
        '## 5. λ 與 CV（rapm.py 的 5 折，依場次分折，加權 MSE）', '', f"選中 λ = {S['lambda']}", '', '| λ | CV 加權 MSE |', '|---|---|']
for k, v in S['cvWeightedMSE'].items(): out.append(f"| {k} | {v:.3f} |")
out += ['', '## 6. 參數與揭露', '', f"- c（生涯噪音）：O {S['cCareerNoise']['O']['c']:.0f}、D {S['cCareerNoise']['D']['c']:.0f}（n={S['cCareerNoise']['O']['players']}）",
        f"- box 模型誤差變異：O {S['boxModelErrorVar']['O']:.2f}、D {S['boxModelErrorVar']['D']:.2f}", f"- 輸入補值統計：{S['inputsNotes']}"] + [f'- {d}' for d in S['disclosure']]
(HERE / 'report.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
