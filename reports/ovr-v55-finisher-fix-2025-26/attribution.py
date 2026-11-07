"""python reports/ovr-v55-finisher-fix-2025-26/attribution.py [mode]  -> attribution.json

三個診斷，用來誠實解釋 A4 與追問條件為什麼只有「組別層」成立、個別球員層不穩：

1. boardNoise：同一顆種子在 v54 與 <mode> 之間的 per-36 差，除以兩塊板自己的蒙地卡羅
   標準誤（shrink.board 回傳的 mc）。B1 會改變機率，隨機流就跟著分岔，所以兩塊板的
   per-36 差包含「完整」的 MC 雜訊，不是成對比較。|z| < 2 表示該球員的個別名次變化
   在這個樣本數下無法與雜訊區分。
2. cardDecomposition：卡片層的 simulatedPer36（迴歸目標＝模擬板）與 predictedPer36
   （迴歸預測＝真正決定 OVR 的量）分開列出。目標上升但預測下降，代表名次變化來自
   「屬性被重新定價」而不是「模擬值變差」。
3. coefficientShift：每 10 點屬性的 per-36 價值在 v53 / v54 / <mode> 的變化，附
   bootstrapSE。這是檢驗 2k27-compare §6.3（卡片把吃餅長人的 drive/help/onBall/long
   定價過高）有沒有被這個修正壓下去的直接證據。
"""
import csv, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import shrink as S  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else 'B12'
OUT = Path(__file__).parent
CARD = OUT / 'card'
NAMES = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza',
         'Neemias Queta', 'Rudy Gobert', 'Jalen Smith',
         'Charles Bassey', 'Jaxson Hayes', 'Jordan Walsh', 'Josh Minott', 'Robert Williams III',
         'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Luka Dončić', 'Trae Young', 'Victor Wembanyama']

boards = {}
for v in ['v54', MODE]:
    pl = S.load(v)
    x, mc = S.board(pl, set(range(8)))
    boards[v] = (pl, x, mc)
pl = boards['v54'][0]
idx = {p['name']: i for i, p in enumerate(pl)}
dx = boards[MODE][1] - boards['v54'][1]
se = np.sqrt(boards['v54'][2] + boards[MODE][2])
noise = {n: {'sourceMinutes': round(pl[idx[n]]['W']), 'v54Per36': round(float(boards['v54'][1][idx[n]]), 3),
             'per36': round(float(boards[MODE][1][idx[n]]), 3), 'delta': round(float(dx[idx[n]]), 3),
             'seOfDelta': round(float(se[idx[n]]), 3), 'z': round(float(dx[idx[n]] / se[idx[n]]), 2)}
         for n in NAMES if n in idx}
league = {'medianAbsDelta': round(float(np.median(np.abs(dx))), 3), 'medianSeOfDelta': round(float(np.median(se)), 3),
          'shareAbsZunder2': round(float((np.abs(dx / se) < 2).mean()), 3)}

rd = lambda v: {r['name']: r for r in csv.DictReader(open(CARD / v / 'ranking.csv', encoding='utf-8-sig'))}
cards = {v: rd(v) for v in ['v53', 'v54', MODE] if (CARD / v / 'ranking.csv').exists()}
vers = list(cards)
decomp = {}
for n in NAMES:
    if all(n in cards[v] for v in vers):
        decomp[n] = {v: {k: float(cards[v][n][k]) for k in ['rank', 'ovr', 'simulatedPer36', 'predictedPer36']} for v in vers}

summ = {v: json.loads((CARD / v / 'summary.json').read_text(encoding='utf-8')) for v in vers}
coef = {k: {v: round(summ[v]['valuePer10AttributePoints'][k]['per36'], 3) for v in vers}
        for k in summ[vers[0]]['valuePer10AttributePoints']}
for k in coef:
    coef[k]['deltaVsV53'] = round(coef[k][MODE] - coef[k]['v53'], 3)
    coef[k]['bootstrapSE'] = round(summ[MODE]['valuePer10AttributePoints'][k]['bootstrapSE'], 3)

out = {'mode': MODE, 'boardNoise': {'players': noise, 'league': league},
       'cardDecomposition': decomp, 'coefficientShift': coef}
(OUT / 'attribution.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({'league': league,
                  'karlo': noise.get('Karlo Matković'),
                  'jalenSmith': noise.get('Jalen Smith'),
                  'coefKeys': {k: coef[k]['deltaVsV53'] for k in ['long', 'help', 'pass', 'rebound', 'creation']}},
                 ensure_ascii=False, indent=1))
