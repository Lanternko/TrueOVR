"""E-208 report.md 產生器：表格與數字全部由 *-tables.json 帶入，文字為手寫。"""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
H = Path(__file__).resolve().parent
J = lambda n: json.load(open(H / n, encoding='utf-8'))
A, BC, CT, AB, NS, G2, META = (J(n) for n in ('A-tables.json', 'BC-tables.json', 'C-tables.json', 'A-ablate.json', 'A-noskip.json', 'G2.json', 'BC-meta.json'))
p = lambda x: f'{x:.0%}'


def atab(t):
    s = ('| 順位組 | n | 曲線值 | **新·線上算法**（含 usage 層）中位 / P75 / 高於曲線 | 新·只資料（不含 usage 層）中位 / P75 / 高於曲線 | '
         'E-141 舊 ans0 中位 / P75 / 高於曲線 | 新(只資料)−舊 平均 | 新(線上)−舊 平均 | 季末(線上算法) 中位 |\n|---|---|---|---|---|---|---|---|---|\n')
    for g, v in t.items():
        s += (f"| {g} | {v['n']} | {v['curveMed']:.1f} | {v['newCMed']:.1f} / {v['newCP75']:.1f} / {p(v['newCAbove'])} | "
              f"{v['newMed']:.1f} / {v['newP75']:.1f} / {p(v['newAbove'])} | {v['oldMed']:.1f} / {v['oldP75']:.1f} / {p(v['oldAbove'])} | "
              f"{v['diffMean']:+.1f} | {v['diffC']:+.1f} | {v['endCMed']:.1f} |\n")
    return s


def btab(key):
    o = BC[key]
    s = ('| 第 1–6 場分鐘 | n | 第3場 | 第6場 | 第10場 | 第20場 | 季末 | 第6場→季末 留下比例（平均值比） | 斜率 | 相關 | 第6場與季末同號人數 |\n'
         '|---|---|---|---|---|---|---|---|---|---|---|\n')
    for g, v in o['groups'].items():
        if v['slope'] is None:
            s += f"| {g} | {v['n']} | {v['meanD3']:+.1f} | {v['meanD6']:+.1f} | {v['meanD10']:+.1f} | {v['meanD20']:+.1f} | {v['meanDend']:+.1f} | （n 太小） | | | {v['sameSign']}/{v['n']} |\n"
            continue
        r = f"{v['ratio']:.2f}" if v['ratio'] is not None and abs(v['ratio']) < 20 and abs(v['meanD6']) > 0.8 else '（分母≈0，無意義）'
        s += (f"| {g} | {v['n']} | {v['meanD3']:+.1f} | {v['meanD6']:+.1f} | {v['meanD10']:+.1f} | {v['meanD20']:+.1f} | {v['meanDend']:+.1f} | {r} | "
              f"{v['slope']:.2f} | {v['corr']:.2f} | {v['sameSign']}/{v['n']} |\n")
    s += f"| 全部 | {o['n']} | | {o['meanD6']:+.1f} | | | {o['meanDend']:+.1f} | | {o['slope']:.2f}（截距 {o['intercept']:+.1f}） | {o['corr']:.2f} | |\n"
    return s


ex = BC['examples']
exs = '| 球員 | 前6場分鐘 | 起點 | 第3場 | 第6場 | 第10場 | 第20場 | 季末 | （只資料）第6場 | （只資料）季末 |\n|---|---|---|---|---|---|---|---|---|---|\n'
for n, v in ex.items():
    exs += f"| {n} | {v['min6']:.0f} | {v['start']} | {v['ovr3']} | {v['ovr6']} | {v['ovr10']} | {v['ovr20']} | {v['ovrend']} | {v['raw6']} | {v['rawend']} |\n"
cs = CT['C90_summary']
crow = ('| 球員 | 順位 | 場數 | 線上公布 ΔOVR | 重播第6場 Δ（線上算法） | 重播第6場 Δ（只資料） | 在 B 同組(≥90 分)分布的百分位 | 估季末 Δ（B 迴歸） | 估季末 Δ（usage 層補滿＋資料部分×B 斜率） |\n'
        '|---|---|---|---|---|---|---|---|---|\n')
for x in sorted(CT['C90_ge6'], key=lambda x: -x['d6']):
    crow += (f"| {x['name']} | {int(x['pick'])} | {int(x['games'])} | {x['pubD']:+.1f} | {x['d6']:+.1f} | {x['raw_d6']:+.1f} | "
             f"{x['pctInB90']:.0%} | {x['estEnd_B']:+.1f} | {x['estEnd_layerSplit']:+.1f} |\n")
lay = CT['layerB']
RV = BC['C_replay_vs_pub']
S1, S2 = A['slopes']['all'], A['slopes']['D1-D3']
g90 = BC['B_raw']['groups']['>=90']
supp = '、'.join(f"{x['name']}(第{x['pick']}順位，身高{x['height']}吋)" for x in META['B_supplement'])

txt = f'''# E-208 新秀起點曲線 R-096 在 inseason／card 0.2.12b 管線下複查（量測，不改任何線上檔）

> **樣本內聲明（R-007、L-026）**：A、B 的人群和答案都是已經看過的歷史季；沒有擬合新曲線參數，只描述中位數／P75 對順位的關係。結論不得當樣本外證據。
> 本報告是 role-card 量測，不寫 rulings；findings 由 lead 決定。

## 0. 結論

1. **曲線比實際陡很多**：T(順位)=73−5.9·ln(順位)；實際前 20 場視窗 OVR（線上算法）對 ln(順位) 的斜率約 {S1['win20C']:.2f}（全 246 人）／{S2['win20C']:.2f}（資料最完整的 D1–D3），舊 E-141 是 {S1['old_ans0']:.2f}。線上算法下：狀元、2–3 順位實際中位數低於曲線，4–10 順位貼著曲線，11 順位以後（含落選）高過曲線 3～13 分。
2. **線上算法（含 usage 層）才是線上對新秀實際會算出的值**：2026 屆 42 人用本量測的重播對線上公布 OVR，平均只差 {RV['meanC']:+.1f}、相關 {RV['corrC']:.2f}；拿掉 usage 層平均差 {RV['meanRaw']:+.1f}、相關 {RV['corrRaw']:.2f}（§1.2）。
3. **B 的關鍵發現**：2025-26 屆「只資料」的第 6 場加分平均是 {BC['B_raw']['meanD6']:+.1f}（≥90 分鐘組 {g90['meanD6']:+.1f}），不是 +7.5；線上 ΔOVR 的正值大半來自 usage 層（平均 第3場 {lay['3']:+.1f}、第6場 {lay['6']:+.1f}、第10場 {lay['10']:+.1f}、季末 {lay['end']:+.1f}），它在滿 10 場前機械式爬升。所以「第 6 場加分留到季末幾成」要分兩段看（§2）。
4. **C**：2026 屆 14 位 ≥90 分鐘（線上公布平均 {CT['pub']['mean90']:+.1f}）換成 B 的重播口徑（只有 11 人滿 6 場），資料部分平均 {cs['meanRawD6']:+.1f}（B 同組 {cs['B90_meanRawD6']:+.1f}）；線上 Δ 在滿 10 場後預期再往上約 4 點（usage 層補滿），資料部分約留七成。估季末約 {cs['meanEstEnd_B']:+.1f}～{cs['meanEstEnd_split']:+.1f}（§3）。**B 只有一屆、≥90 分鐘 20 人，個人層級相關約 0.3，估計很粗。**

## 1. A：E-141 真新秀（Y2/Y3/Y5/Y6/D1/D2/D3，共 246 人）

做法：每人用 R-096 起點（形狀沿用 E-116，δ 用 build_2k_start.solve 重解到 T(順位)，落選＝第 61 順位），取自己的前 20 場視窗卡（現行 m26_window_cards），走現行 `eval_rookie`（arm=own，w=1，即「自己的視窗 OVR」，跟 E-141 的 ans0 同概念）；「線上算法」再接 chain_rookie 的 usage 層。季末＝自己全部出賽場數的視窗，同樣算法。母體與順位組沿用 E-141 rookie-players.csv，組別：1、2–3、4–10、11–30、31–60、落選。「高於曲線」＝該人 OVR > 自己順位的曲線值。逐人資料見 A-players.csv。

### 1.1 全部 246 人

{atab(A['all'])}
### 1.2 兩套「新」差在哪

兩套用的是**同一份視窗卡、同一個起點**，唯一差別是最後有沒有接線上的 usage 層（chain_rookie：`pn = p + min(N/10,1)·(full − p)`，full 是用 MPGhat 與 pred 回歸出的用人層）：

- **新·只資料** ＝ E-141 舊 ans0 的同一口徑（視窗屬性進 OVR 公式，不含用人層），所以只有它能跟舊表逐人比較。
- **新·線上算法** ＝ 線上對一個已出賽 ≥10 場的新秀實際會算出的值（usage 層滿）。證據：2026 屆 42 人，重播(含 usage 層)對線上公布 OVR 平均差 {RV['meanC']:+.1f}、相關 {RV['corrC']:.2f}；不含 usage 層平均差 {RV['meanRaw']:+.1f}、相關 {RV['corrRaw']:.2f}。**回答「新秀會算出什麼」請看線上算法欄**，回答「跟 E-141 比有沒有變」請看只資料欄。
- 兩套差距（例：4–10 順位中位 {A['all']['4-10']['newMed']:.1f} 對 {A['all']['4-10']['newCMed']:.1f}；11–30 高於曲線 {p(A['all']['11-30']['newAbove'])} 對 {p(A['all']['11-30']['newCAbove'])}）就是 usage 層：246 人平均 +{A['overall']['diffMeanC']-A['overall']['diffMean']:.1f}（B 的 2025-26 屆實算 第20場 {lay['20']:+.1f}、季末 {lay['end']:+.1f}）。**不是補值造成的**，是線上模型多的一層。
- 兩套都不是線上的完整值：線上還有 onBall／help 追蹤防守、gravity、tov 持球版、pressure／drive 本季值與防守加成，重播都沒有（§1.4）。**重播沒有比線上更準，只是少了這些項。**
- 注意 A 的欄位用 arm=own（w=1，不收縮），線上用 e116 收縮臂；兩者在 20 場時的差距本報告沒有單獨量，未驗證。

### 1.3 只看 D1–D3（有 creationJ 的三屆，n=93）

{atab(A['D1-D3'])}
### 1.4 補值／缺值逐項清單（不能做的事不靜默換法）

| 項目 | 受影響 | 做法 |
|---|---|---|
| creation（逐場 creationJ 計數） | Y2/Y3/Y5/Y6 共 148 人（逐場計數檔只有 2022-23 起） | 視窗樣本門檻設無限大＝creation 維持起點 x0。D1–D3 有計數，用現行 creation_map。消融：D1–D3 也遮掉 creation，前20場 OVR（只資料）平均 {AB['D1']['meanMaskedMinusWith']:+.1f}／{AB['D2']['meanMaskedMinusWith']:+.1f}／{AB['D3']['meanMaskedMinusWith']:+.1f}（D1/D2/D3；線上算法 {AB['D1']['meanMaskedMinusWithC']:+.1f}／{AB['D2']['meanMaskedMinusWithC']:+.1f}／{AB['D3']['meanMaskedMinusWithC']:+.1f}），即遮掉約低 2 分 |
| onBall／help（追蹤防守） | 全部 246 人 | 歷史季沒有逐場追蹤防守，維持起點 x0 |
| gravity | 全部 246 人 | 維持 ROOKIE_G0（線上本季 0 場的值） |
| drive／tovSkill／pressure | 全部 246 人 | 線上 eval_rookie 的 SKIP 本來就不用視窗值更新這三項，維持起點 x0（tovSkill 持球時間版歷史季也沒資料） |
| 防守加成 | 全部 246 人 | 設 0（def-L-live 是現行最終擬合，拿來算歷史季會洩漏） |
| usage 層 | 全部 | 現行係數（b8_ydL=0，不受 team_badness 影響），n_games＝視窗場數 |
| 版本代入 | 全部 | 起點、OVR 公式、anchor、r_repl 都用現行最終版（pw='S*'），不是當年的版本 |
| 母體 | D3 | E-141 的 D3 缺 7 人（bio 檔沒有），B 補上（§2） |

### 1.5 新(只資料)對 E-141 舊 ans0 差多少、為什麼（含狀元 −11）

- 狀元 n=6（Ayton、Edwards、Cunningham、Wembanyama、Risacher、Flagg），新−舊平均 {A['all']['1']['diffMean']:+.1f}，2–3 順位 n=14 為 {A['all']['2-3']['diffMean']:+.1f}，整體 {A['overall']['diffMean']:+.1f}。n 很小，單人影響大（Edwards 23 對 59、Lonzo Ball 30 對 56、Cunningham 41 對 62、Jalen Green 36 對 58）。
- **補值造成的部分很小**：(a) 無 creationJ 的 Y 屆遮掉 creation 約 −2；(b) 現行 SKIP 不更新 drive／tovSkill／pressure，舊答案有更新 drive／tovSkill：把 SKIP 拿掉後「新−舊」的變化是 狀元 {NS['1']['noSkip-new']:+.1f}、2–3 順位 {NS['2-3']['noSkip-new']:+.1f}、4–10 {NS['4-10']['noSkip-new']:+.1f}、整體 {NS['ALL']['noSkip-new']:+.1f}，方向不一致（A-noskip.json），不是主因。
- **剩下的主要部分我無法拆開**：拿掉 SKIP 後仍差 狀元 {NS['1']['noSkip-old']:+.1f}、2–3 順位 {NS['2-3']['noSkip-old']:+.1f}。舊答案的環境檔案（pool-027、當年先驗卡）已搬到 _retired 或重擬合，沒辦法在舊環境重算同一批人；已知的版本差有 OVR 公式多了 gravity／onBall／help 等新係數、anchor／r_repl 重取、視窗卡屬性映射改版。**哪一項是主因，原因不確定**。
- Y 屆比 D 屆更低（只資料欄，Y2/Y3/Y5/Y6 新−舊平均 −5～−8，D1/D2/D3 為 +4.0、−1.4、+1.4）：遮 creation 只解釋約 2 分；其餘（歷史年代資料口徑；E-116 形狀曲線以 2017–2021 新秀擬合，Y 屆為樣本內形狀）不能拆開，原因不確定。

### 1.6 描述性斜率（不是擬合，R-096 曲線不變）

每多一個 ln(順位) 單位的 OVR 變化（逐人 OLS，落選以 61 代入，246 人）：曲線 −5.9；E-141 舊 ans0 {S1['old_ans0']:.2f}；新·只資料 {S1['win20']:.2f}；新·線上 {S1['win20C']:.2f}；季末(只資料) {S1['seasonEnd']:.2f}。D1–D3：舊 {S2['old_ans0']:.2f}、新·只資料 {S2['win20']:.2f}、新·線上 {S2['win20C']:.2f}、季末 {S2['seasonEnd']:.2f}。

## 2. B：2025-26 屆重播（D3，n={BC['B_ovr']['n']}）

人群＝E-141 的 D3 33 人 + 補 7 人（E-141 的 bio 沒有他們：{supp}；順位、身高取自 data/benchmark-source/bio.json，其餘條件同 E-141：季總分鐘≥500、出賽≥30 場）。Knueppel 因此在內。每人用 R-096 起點，取自己第 3/6/10/20 場與季末的視窗，走線上的 e116 收縮臂＋usage 層（防守加成 0、無追蹤防守）。ΔOVR＝該時點 OVR − 起點。逐人資料見 B-players.csv。

### 2.1 線上算法（含 usage 層）

{btab('B_ovr')}
usage 層平均貢獻：第3場 {lay['3']:+.1f}、第6場 {lay['6']:+.1f}、第10場 {lay['10']:+.1f}、第20場 {lay['20']:+.1f}、季末 {lay['end']:+.1f}。它在 10 場內機械爬升，所以「留下比例」大於 1 不是球員表現變好，而是這層還沒爬完。

### 2.2 只資料（不含 usage 層）

{btab('B_raw')}
- 資料部分第6場加分到季末只留下一部分：全體斜率 {BC['B_raw']['slope']:.2f}、相關僅 {BC['B_raw']['corr']:.2f}；≥90 分鐘組斜率 {g90['slope']:.2f}、相關 {g90['corr']:.2f}，第6場與季末同號只有 {g90['sameSign']}/{g90['n']} 人。<30、30–90 組平均比值分母接近 0，不要看。
- 2025-26 屆 ≥90 分鐘組第6場「只資料」平均 {g90['meanD6']:+.1f}、季末 {g90['meanDend']:+.1f}：這一屆沒有像今年 +7.5 那樣的資料面大幅加分。

### 2.3 例子（線上算法）

{exs}
Flagg 第3場 +3.7、第6場 −2.2，之後回到起點上下（季末 +0.1）；Harper 一路 +4～+8；Edgecombe 第3場 +7.7 後逐步掉到起點以下（季末 −3.5，「只資料」季末 −13.4）；Knueppel 前 6 場略低於起點（第6場 −2.2），季末 +18.1，是「前期沒加分、後期大幅追上」的相反例子。第6場加分最多的四人：Coward +14.2、Kalkbrenner +13.4、Clayton +11.3、Clifford +9.4；Coward、Kalkbrenner 季末仍在高位（80.6、82.0），Clayton、Clifford 季末回到起點附近（59.1 對 55.9、54.0 對 54.2）。

## 3. C：2026 屆（線上資料截止 2026-10-31，42 人）

線上公布的 ΔOVR＝rookies-detail.json 的 ovr − lastOVR；≥90 分鐘（ranking.csv 的 MIN26）共 {CT['pub']['n90']} 人平均 {CT['pub']['mean90']:+.1f}（其餘 {CT['pub']['nOther']} 人平均 {CT['pub']['meanOther']:+.1f}），Lendeborg +22.9、Flemings +15.2，與派工資料吻合。重播口徑（跟 B 同一程式、只取前 6 場、無追蹤防守與防守加成），逐人見 C-players.csv，≥90 分鐘且滿 6 場者：

{crow}
- ≥90 分鐘且滿 6 場 {cs['n']} 人：線上平均 {cs['meanPubD']:+.1f}、重播第6場（線上算法）{cs['meanD6']:+.1f}（B 同組 {cs['B90_meanD6']:+.1f}）、重播第6場（只資料）{cs['meanRawD6']:+.1f}（B 同組 {cs['B90_meanRawD6']:+.1f}）。
- **估計**：用 B 全體線性關係（季末 Δ ≈ {BC['B_ovr']['intercept']:+.1f} + {BC['B_ovr']['slope']:.2f}×第6場 Δ）平均約 {cs['meanEstEnd_B']:+.1f}；用「usage 層補滿 + 資料部分×B 斜率 {BC['B_raw']['slope']:.2f}」約 {cs['meanEstEnd_split']:+.1f}。B 同組實際季末平均是 {cs['B90_meanDend']:+.1f}。今年同組資料面起步比 2025-26 屆高約 4 點，加上 usage 層還沒補滿，**預期線上 Δ 還會再往上而不是回吐**；Lendeborg、Boozer、Flemings 在 B 同組分布的最前面（百分位 ≥90%），Sharp、Peterson（重播第6場為負）在最後面。
- 重播沒有的東西（追蹤防守、gravity、tov 持球版、pressure／drive 本季值、防守加成）會讓個人 Δ 與重播差很多（Peterson 線上 +9.5 對重播 −4.2、Mara 線上 −0.5 對重播 +6.5），所以個人預測不可靠，只有組平均可看。

## 4. 限制

- B 只有一屆（n={BC['B_ovr']['n']}，≥90 分鐘 {g90['n']} 人），個人層級相關 0.2–0.4，留下比例／斜率誤差很大。
- A 的欄位用 arm=own，B、C 用 e116 收縮臂。
- 全部重播在「少了追蹤防守、gravity、tov 持球、防守加成」的受限管線下；D3 季末(只資料)對 card-0.2.12b 的 2025-26 排名（有卡者 n=32）平均低 5.5、相關 0.63，符合缺防守層的方向。
- Y 屆無 creationJ，見 §1.4。

## 5. 版本與可重現（G2）

- **量測用的程式狀態**：git HEAD `{G2['gitHead']}` 的 inseason／card **0.2.12b**。共用工作樹裡另一個 session 正在進行 0.2.12c 換版（run_c4_live.py、run_c4_live_rookie.py、tov_live.py、window8.py 有未提交改動，0212tov 檔已 rename 進 _retired），本量測**沒有用工作樹的那些版本**：e208_lib.py 以 `git show HEAD:<檔>` 載入這四個檔（run_c4_live.py 的 load_ns 讀取也改走 HEAD 版），0212tov 檔因被搬走，只做唯讀的路徑轉向到 `_retired/`。沒有用 `git worktree`／`git stash`，因為資料目錄與凍結檔不在 git 裡，乾淨副本讀不到。驗證：釘住 HEAD 之後重跑 A，A-players.csv 與釘住前逐位元相同（cmp 無差異）。
- 沒有改任何 src/、live/、CURRENT.json、R-096 曲線、build_2k_start.py 常數；沒有呼叫 build_2k_start.main()。
- 子程序只有 `git show`／`git rev-parse`，皆帶 CREATE_NO_WINDOW。
- sha256：
'''
for k, v in G2.items():
    if k in ('gitHead', 'pinnedFromHead'):
        continue
    txt += f'  - {k}：`{v}`\n'
txt += '''
## 6. 檔案

e208_lib.py（共用）、run_A.py／A_tables.py／run_A_ablate.py／run_A_noskip.py、run_BC.py／BC_tables.py／C_tables.py、g2.py、make_report.py；輸出 A-players.csv、A-tables.json、A-ablate.json、A-noskip.json、B-players.csv、C-players.csv、BC-tables.json、C-tables.json、BC-meta.json、G2.json。
'''
(H / 'report.md').write_text(txt, encoding='utf-8')
print(len(txt))
