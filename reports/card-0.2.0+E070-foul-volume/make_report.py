"""E-070 組 verdict.json 與 report.md。python -I -X utf8 make_report.py"""
import json
from pathlib import Path
D = Path(__file__).parent
L = lambda n: json.loads((D / n).read_text(encoding='utf-8'))
c2 = L('c2.json'); it = L('report-items.json'); vf = L('vol-fit.json')
s = vf['shrinkCheck2025_26']
p5 = c2['possScale0.5']; p1 = c2['possScale1.0']
v = {'experiment': 'E-070', 'preregistrationSha256': 'c3fe3cd7a049a6a33fb9cb892e1ccf77e77eb6bafb1033e7e539e6f5cc04c817',
     'c0': {'pass': True, 'detail': 'w_vol=0 重建的 ranking.csv 與 reports/card-0.2.0/ranking.csv 逐位元相同（cmp）'},
     'c1': {'pass': True, 'detail': 'npm test exit 0；57 passed, 0 failed'},
     'c2': {'pass': c2['c2']['pass'], 'metric': 'repl（card 0.2.0 每場 OVR）', 'delta': c2['c2']['delta'], 'ci90': c2['c2']['ci90'], 'threshold': '下界 > -0.02',
            'n': p5['n'], 'unionN': p5['unionN'], 'byDirection': p5['repl']['byDirection'],
            'game': {k: p5['game'][k] for k in ('delta', 'ci90')}, 'ovr36': {k: p5['ovr36'][k] for k in ('delta', 'ci90')},
            'sensitivityPossScale1.0_repl': {k: p1['repl'][k] for k in ('delta', 'ci90', 'pass')}},
     'c3': {'pass': True, 'detail': 'evaluate.mjs 通過數 card 0.2.0 18/19，E070 18/19（>=）；未過者同為 allFourStayTop10、strictFourBigsTop10', 'card020': '18/19', 'E070': '18/19'},
     'reportOnly': {'foulDrawCoefPer10': it['foulDrawCoef'], 'rho2k': it['rho2k'], 'ovrChange': it['ovrChange']},
     'shrinkageCheck2025_26': s,
     'cardSide': '通過（c0-c3 全過），交使用者決定採用；本 session 未改 memory、未 commit'}
v['allPass'] = all(v[k]['pass'] for k in ('c0', 'c1', 'c2', 'c3'))
(D / 'verdict.json').write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding='utf-8')
f = lambda x: f'{x:.4f}'
R = []
R.append(f"""# E-070 foulDraw 量化（report）

預註冊：`preregistration.md`（sha256 `c3fe3cd7a049a6a33fb9cb892e1ccf77e77eb6bafb1033e7e539e6f5cc04c817`，未改）。FD = 池內百分位(0.75·z(收縮後 FTA/36) + 0.25·z(收縮後 FTA/FGA))。池 = 252 人（GP>=30、MPG>=20、皆在 582 卡內）。

## 結論
c0-c3 全過。卡片端判定：**通過**，交使用者決定是否採用（不自動採用、未 commit、未動 memory/）。

| 關卡 | 內容 | 數值 | 結果 |
|---|---|---|---|
| c0 | w_vol=0 重現 card 0.2.0 | ranking.csv 逐位元相同 | 過 |
| c1 | npm test | exit 0，57 passed, 0 failed | 過 |
| c2 | RAPM 分半 ρ(候選)-ρ(card 0.2.0)，repl 每場 OVR | Δ={f(c2['c2']['delta'])}，90% CI [{f(c2['c2']['ci90'][0])}, {f(c2['c2']['ci90'][1])}]，下界 > -0.02 | 過 |
| c3 | evaluate.mjs 通過數 >= card 0.2.0 | 18/19 對 18/19 | 過 |

c2 細節（possScale 0.5 為主；人群 A→B {p5['n']['AB']} 人、B→A {p5['n']['BA']} 人、聯集 {p5['unionN']}；bootstrap 2000、seed 1、球員配對）：

| 變體 | Δ（兩方向平均） | 90% CI | A→B | B→A |
|---|---|---|---|---|""")
for k, n in (('repl', 'repl（主）'), ('game', 'game'), ('ovr36', '每 36')):
    x = p5[k]
    R.append(f"| {n} | {f(x['delta'])} | [{f(x['ci90'][0])}, {f(x['ci90'][1])}] | {f(x['byDirection']['AB'])} | {f(x['byDirection']['BA'])} |")
x = p1['repl']
R.append(f"""
敏感度 possScale 1.0（repl）：Δ={f(x['delta'])}，CI [{f(x['ci90'][0])}, {f(x['ci90'][1])}]，也過。差異全在 ±0.003 內，等同「不變差、也沒變好」。

c3 補充：未過的兩條（allFourStayTop10、strictFourBigsTop10）在兩張卡相同；ρ2K {f(it['rho2k']['card0.2.0']['perGame'])}→{f(it['rho2k']['E070']['perGame'])}、ρRAPM（樣本內，僅參考，R-007）0.8139→0.8136、ρDef 0.5572→0.5551。

## 收縮檢查（2025-26，method (c) 的 FTA/36，k=8、λ=0.35、kh=4、位置先驗）
擬合季 2015-16..2024-25，訓練 n={vf['trainN']}。2025-26 預測下半季的 MAE（n={s['n']}）：收縮後 {s['shrunk']:.4f}，k=0（不收縮）{s['k0']:.4f}，只用上半季 {s['firstHalfOnly']:.4f}。收縮比不收縮低 {(1 - s['shrunk'] / s['k0']) * 100:.1f}%，比只用上半季低 {(1 - s['shrunk'] / s['firstHalfOnly']) * 100:.1f}%，收縮有效。

## 只報告項目
### foulDraw 在 calibrate 的係數（每 10 點，per36）
| | 係數 | bootstrap SE |
|---|---|---|
| card 0.2.0 | {it['foulDrawCoef']['card0.2.0']['per36']:.4f} | {it['foulDrawCoef']['card0.2.0']['bootstrapSE']:.4f} |
| E-070 | {it['foulDrawCoef']['E070']['per36']:.4f} | {it['foulDrawCoef']['E070']['bootstrapSE']:.4f} |

係數幾乎沒動（+0.006，遠小於 SE）。

### 2K27 ρ（n={it['rho2k']['n']}）
| | 每場 | 每 36 |
|---|---|---|
| card 0.2.0 | {f(it['rho2k']['card0.2.0']['perGame'])} | {f(it['rho2k']['card0.2.0']['per36'])} |
| E-070 | {f(it['rho2k']['E070']['perGame'])} | {f(it['rho2k']['E070']['per36'])} |

### OVR 變動總覽
582 人平均絕對變動 {it['ovrChange']['meanAbs']:.2f}、最大 {it['ovrChange']['max']:.1f}、>1 分 {it['ovrChange']['n_gt1']} 人、>3 分 0 人；新舊 OVR 的 Spearman {it['ovrChange']['spearmanOldNewOvr']:.4f}。

### 前 20 名 OVR（舊→新）
| 名次 | 舊 | 新 |
|---|---|---|""")
for r in it['top20']:
    R.append(f"| {r['rank']} | {r['old'][0]} {r['old'][1]} | {r['new'][0]} {r['new'][1]} |")
R.append("""
前 20 名人選只差在第 20 名：舊 OG Anunoby 88.2、新 Stephen Curry 88.4。前十人選相同，只有 Kawhi／Markkanen 互換（5/6）。

### 變動最大的 15 人
| 球員 | 位 | MIN | FD 舊→新 | OVR 舊→新 | Δ | 名次 舊→新 |
|---|---|---|---|---|---|---|""")
for r in it['movers']:
    R.append(f"| {r['name']} | {r['pos']} | {r['MIN']} | {r['fdOld']}→{r['fdNew']} | {r['ovrOld']}→{r['ovrNew']} | {r['dOvr']:+} | {r['rankOld']}→{r['rankNew']} |")
R.append("""
### foulDraw 前 20（582 卡，新）
（99.0 有多人並列，名次為排序順序，非嚴格）

| 名次 | 球員 | FD 新 | FD 舊 | 舊名次 | MIN |
|---|---|---|---|---|---|""")
for r in it['topFD']:
    R.append(f"| {r['rank']} | {r['name']} | {r['fd']} | {r['fdOld']} | {r['oldFdRank']} | {r['MIN']} |")
R.append("""
### G5 抽查（13 人）
| 球員 | 位 | MIN | FD 舊→新 | FD 名次 舊→新 | OVR 舊→新 | OVR 名次 舊→新 |
|---|---|---|---|---|---|---|""")
for r in it['g5']:
    R.append(f"| {r['name']} | {r['pos']} | {r['MIN']} | {r['fdOld']}→{r['fdNew']} | {r['fdRankOld']}→{r['fdRankNew']} | {r['ovrOld']}→{r['ovrNew']} | {r['rankOld']}→{r['rankNew']} |")
R.append("""
讀法：Luka（30→4）、SGA（21→5）、Embiid（13→2）、Brunson（179→52）的罰球製造升到應有位置；Gobert（3→40）、Adams（8→62）、Powell（4→26）、Plumlee（5→59）被拉下，仍在上段。OVR 影響都在 ±0.3 內，名次幾乎不動（Gobert 27→27、Luka 3→3）。原因是 foulDraw 在 calibrate 的係數小（約 0.11／10 點），FD 大改對 OVR 影響有限。

## 偏離預註冊
1. z 分數用 ddof=0（母體標準差），預註冊未寫明；池 = 252 人，皆在 582 卡內（attrs-check.json）。屬實作細節，在看任何結果前決定。
2. w_vol=0 的屬性檔保留 V61 原始 `new_foulDraw` 字串（重算會因讀 6 位小數的 CSV 差 4.98e-7，只影響捨入）；因此 c0 逐位元相同。w=0.75 版 FTA/FGA 項的 rate 同樣從 V61 CSV 的 6 位小數讀取。
3. c2 的答案與人群沿用 E-064 `evaluate_e064.py`（含 mpg-A/B 檔）；主指標取 repl 變體，因為 card 0.2.0 的每場 OVR 用 g_r。game／每 36 變體另列，結論相同。
4. 擬合半卡（fitA/fitB）用 possScale 0.5（與 E-064 輸出比對差 0.0）；possScale 1.0 只當敏感度。
5. `cards-w0/c0-switch-off` 是 `cards-w0/primary` 的重複跑（留存，不影響結果）。
6. `evaluate.mjs` 為 E060 版複本，只改 CANDIDATES 與輸出路徑；門檻與函式未改。
7. 沒有調過任何參數；未動 automations，故未跑 audit.ps1。

## 檔案
`e070_vol.py`、`run_cards.py`、`build_card.py`、`evaluate_e070.py`、`evaluate.mjs`、`report_items.py`、`make_report.py`；`vol-fit.json`、`attrs-check.json`、`c2.json`、`evaluation.json`、`report-items.json`、`verdict.json`、`inputs-sha256.json`、`npm-test.log`、`npm-test.exit`；`primary/ranking.csv`、`primary/summary.json`；`attributes-w0/`、`attributes-w075/`、`cards-w0/`、`cards-w075/`。
""")
(D / 'report.md').write_text('\n'.join(R), encoding='utf-8')
print(v['allPass'], v['c2']['ci90'])
