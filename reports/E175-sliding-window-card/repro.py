"""E-175 步驟 1：V 臂重現 0.2.9a 的 8 項屬性（2025-26 季末）。通過條件：|差| ≤ 0.1 的人 ≥ 99%（對 reports/card-0.2.9a/ranking.csv，四捨五入到 0.1）。
另外對全精度檔（0.2.7+E125 attributes-P50.csv、tail-e123a.csv）報最大差，並對 E-090 a0-raw.json 的收縮比率逐位比對。
用法：python -I -X utf8 reports/E175-sliding-window-card/repro.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e175_lib as L
import e175_card as C

D = L.Data()
inp = C.load_inputs()
ch = C.card_chain(D, inp)
pids, names = ch['pids'], ch['names']
res = {'inputs': {}, 'attrs': {}}

# ---- 目標 1：0.2.9a ranking.csv（四捨五入 0.1）----
rk = list(csv.DictReader(open(L.R / 'card-0.2.9a/ranking.csv', encoding='utf-8')))
dup = {}
for r in rk:
    dup.setdefault(r['name'], []).append(r)
cardrows = {}
for p, nm in zip(pids, names):
    rows = dup.get(nm)
    if rows and len(rows) == 1:
        cardrows[p] = rows[0]
# ---- 目標 2：全精度（tail-e123a.csv；E125 P50）----
full = {int(r['playerId']): r for r in csv.DictReader(open(L.R / 'card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv', encoding='utf-8'))}
p50 = {int(r['playerId']): r for r in csv.DictReader(open(L.E125 / 'attributes-P50.csv', encoding='utf-8'))}
idx = {p: i for i, p in enumerate(pids)}
tot_ok = tot_n = 0
allrows = []
for a in C.ATTRS8:
    mine = ch['mapped'][a]
    d1 = [(abs(mine[idx[p]] - float(r[a])), p) for p, r in cardrows.items()]
    d2 = [abs(mine[idx[p]] - float(full[p][a])) for p in pids if p in full]
    d3 = [abs(mine[idx[p]] - float(p50[p][a])) for p in pids if p in p50]
    ok = sum(x <= 0.1 + 1e-9 for x, _ in d1)
    tot_ok += ok
    tot_n += len(d1)
    top = sorted(d1, reverse=True)[:5]
    res['attrs'][a] = {'nVsRanking': len(d1), 'within0.1': ok, 'share': ok / len(d1), 'maxDiffRanking': max(x for x, _ in d1),
                       'nFull': len(d2), 'maxDiffFull(tail-e123a)': max(d2), 'meanDiffFull': float(np.mean(d2)),
                       'maxDiffP50': max(d3), 'worst5': [(names[idx[p]], round(x, 4)) for x, p in top]}
    print(f"{a:9s} n={len(d1)} within0.1={ok} ({ok / len(d1):.4f}) maxRank={max(x for x, _ in d1):.4f} maxFull={max(d2):.6f} maxP50={max(d3):.6f}")
# 球員層：8 項全部 ≤ 0.1
pl_ok = pl_n = 0
for p, r in cardrows.items():
    pl_n += 1
    pl_ok += all(abs(ch['mapped'][a][idx[p]] - float(r[a])) <= 0.1 + 1e-9 for a in C.ATTRS8)
res['pooled'] = {'attrValuesWithin0.1': tot_ok, 'attrValuesN': tot_n, 'share': tot_ok / tot_n, 'playersAll8Within0.1': pl_ok, 'playersN': pl_n, 'playerShare': pl_ok / pl_n,
                 'cardPlayers': len(pids), 'matchedByUniqueName': len(cardrows)}
print(res['pooled'])

# ---- 比率層對 E-090 a0-raw.json（逐位）----
raw = L.jload(L.E090 / 'work/a0-raw.json')
rl = {}
for a in ('tovSkill', 'rebound'):
    ref = raw[a]['r']
    rl[a] = max(abs(-ch['rn'][a][idx[int(k)]] - v) for k, v in ref.items()) if a == 'tovSkill' else max(abs(ch['rn'][a][idx[int(k)]] - v) for k, v in ref.items())
for a in ('ft', 'mid', 'short'):
    ref = raw[a]['p']
    rl[a] = max(abs(ch['rn'][a][idx[int(k)]] - v) for k, v in ref.items())
res['rateLevelMaxDiffVsE090a0raw'] = {**rl, 'note': 'mid／short 的 a0-raw 是 V61 位置先驗＋V61 分區，0.2.9a 改用 E-101 分區＋聯盟先驗，所以這兩項預期不為 0；ft、tovSkill、rebound 應為 0'}
print('rate-level vs a0-raw', rl)
res['info'] = ch['info']
res['inpool'] = ch['inpool']
Path(__file__).with_name('repro-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
