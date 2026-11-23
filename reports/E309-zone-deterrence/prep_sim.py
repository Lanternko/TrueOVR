"""E-309 (b)：把 sim 窗（2025-26＋2026-27）的 rimDet／threeDet（百分點）換成 v45 細區出手選擇模型的防守者 logit。
聯盟基準用 v45 choice-fit 2025-26 的截距：L＝σ(three)、σp＝σ(paintGivenTwo)、禁區佔比 S＝(1−L)σp。
  dL＝−threeDet/100 → dℓ3＝dL／(L(1−L))
  dS＝−rimDet/100   → dℓp＝(dS＋σp·dL)／((1−L)σp(1−σp))
只換 three 與 paintGivenTwo；raGivenPaint、cornerGivenThree 不動。置中（分鐘加權、維持聯盟平均）在 JS 端做。
  python -I -X utf8 prep_sim.py   （DATA_ROOT 預設主 checkout）→ data/sim-choice.json"""
import csv, json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('DATA_ROOT', 'D:/Projects/CODING/basketball-autochess')
sig = lambda x: 1 / (1 + np.exp(-x))
c = json.load(open(os.path.join(ROOT, 'reports/player-impact-v45/choice-fit.json')))['seasons']
c = next(s for s in c if s['season'] == '2025-26'); m = {z['name']: z for z in c['models']}
L, sp = sig(m['three']['intercept']), sig(m['paintGivenTwo']['intercept'])
out = {}
for r in csv.DictReader(open(os.path.join(HERE, 'data/rimdet-sim.csv'), encoding='utf-8')):
    dL, dS = -float(r['threeDet']) / 100, -float(r['rimDet']) / 100
    out[r['pid']] = {'three': dL / (L * (1 - L)), 'paintGivenTwo': (dS + sp * dL) / ((1 - L) * sp * (1 - sp))}
json.dump({'base': {'L': L, 'sigmaPaint': sp, 'S': (1 - L) * sp}, 'players': out}, open(os.path.join(HERE, 'data/sim-choice.json'), 'w'), indent=0)
print('base', L, sp, (1 - L) * sp, 'players', len(out))
w = out.get('1641705'); print('Wemby', w)
