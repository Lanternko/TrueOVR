import json,hashlib,os
D=os.path.dirname(os.path.abspath(__file__))+'/'
a=json.load(open(D+'analysis.json'))
m=a['metrics'];d=a['diffs']
f=lambda x:f"{x:.4f}"
rows="\n".join(f"| {k} | {f(v['brier'])} | {f(v['logloss'])} | {v['hit']:.3f} | {v['margin_mae']:.2f} | {v['win_total_mae']:.2f} |" for k,v in m.items())
def dl(k):
    return f"- {k}: "+"；".join(f"{mm} {d[k][mm]['diff']:+.4f} [{d[k][mm]['ci90'][0]:+.4f}, {d[k][mm]['ci90'][1]:+.4f}]" for mm in('brier','win_total_mae'))
dls="\n".join(dl(k) for k in d)
def c(v,k):
    return f"{v[k]['mae_centered_vs_estimator']:.2f} / {v[k]['corr_estimator']:.2f}" if k in v else "-"
rr="\n".join(f"| {k} | {c(v,'ortg')} | {c(v,'drtg')} | {c(v,'net')} |" for k,v in a['ratings'].items())
tb="\n".join(f"| {r['abbr']} | {r['actual']} | {r['P_a']:.1f} | {r['P_b']:.1f} | {r['B0']:.1f} |" for r in sorted(a['teams'],key=lambda r:-r['actual']))
files=['inputs.json','forward-inputs.json','pprime-day0.json','lib.mjs','run.mjs','analyze.py','forward-2026-27-frozen.json']
hs="\n".join(f"  - {n}: `{hashlib.sha256(open(D+n,'rb').read()).hexdigest()}`" for n in files)
open(D+'report.md','w',encoding='utf8').write(f"""# E-208 球隊評分 v0（無傷病）報告

**限定語：P′ 是「部分污染，只當參考，不單獨當證據」；I 是樣本內（R-007）。真正的樣本外是 2026-27 前瞻凍結（本次不評）。**

預註冊 commit 7eec8cb（回測前），內容與 sha256 見 `preregistration.md`／`preregistration.sha256`。跑完沒有改任何設定。

## 結果（2025-26，1230 場；H=2.5、σ=12.0 寫死）
| 版本 | Brier | log loss | 命中率 | 分差 MAE | 勝場 MAE |
|---|---|---|---|---|---|
{rows}

(a)＝實際名單與分鐘（等於完美傷病資訊）；(b)＝季前預期分鐘。差值（bootstrap 2000 次以場重抽，90% CI）：
{dls}

**主判定：P′(a) Brier 比 B0 小，CI 不含 0，通過（部分污染，只當參考，不單獨當證據）。次要：勝場 MAE P′(a) 4.17 < B0 10.89，通過。**
(a) 用了事後實際名單與分鐘，不是真預測；(b) 才是無傷病資訊的公平比較，P′(b) 也贏 B0。B0 本身很差（2025-26 洗牌大，B0 與 B-coin 的 Brier 差 CI 含 0）。

## ORtg／DRtg／Net（球隊對平均隊 S=200；置中 MAE / Pearson r，對逐場估計式 actual2526）
| 版本 | ORtg | DRtg | Net |
|---|---|---|---|
{rr}

估計式與官方 advanced-teams 不同（pace 約 +1.2、ORtg 約 -0.8），故以置中 MAE 為主；對官方數值見 analysis.json。

## 預測勝場 vs 實際
| 隊 | 實際 | P′(a) | P′(b) | B0 |
|---|---|---|---|---|
{tb}

## 洩漏稽核與 P′ 欄位表
見 `preregistration.md` 第 3、4 節。`prior-2025-26-card0212-tov.json`（現名 prior-2025-26-card0212c.json）是 **2025-26 季末**狀態，對 2025-26 回測是污染的，沒有使用。CURRENT.json＝card 0.2.12b／inseason 0.2.12b，prior、usage、coefficients、anchors 沒有重抓。2024-25 乾淨對照不做（L-091）。

## G2／G3
- 引擎 sim 0.1.4；卡片 card 0.2.12b；E-175 窗口。輸入 sha256 預註冊時與結束時一致（`sha256sum -c preregistration.sha256` 全 OK）：
{hs}
- G3：P 與 I 同場同 seed（key＝場序號），只差 profile；5090 與本機逐位元相同（rating:pre 抽查）。

## 偏離 spec
1. P′ 只重算 7 項引擎可見屬性（drive、ft、mid、pass、rebound、short、tovSkill），用差值法；long、creation、MPG 沒重算（foulDraw 非引擎欄位）。
2. profile 為引擎 x.players，非官方卡。3. 10 人 budget 輪替，非 workloadRotation。4. 前瞻沒有逐場賽程（只有已賽 88 場），輸出為已有勝敗＋剩餘場次×對其餘 29 隊平均勝率，另附 30×30 對戰表。5. (b) 名單用各隊前 10 場，含少量交易洩漏。6. 乾淨 2024-25 對照不做。

## 前瞻凍結
`forward-2026-27-frozen.json`（sha256 `58e6c4744275f175f249704d0a43f0325c6dc434aaaeab489a5210fcd979d552`），資料截止 2026-10-31。之後每週對真實賽果。

## 抓到的錯
5090 舊副本與本機程式不同，模擬結果悄悄不一樣；改用本機工作樹 tar 位元組同步並逐位元交叉比對。`git archive` 會套 CRLF 轉換，不能用來同步。見 L-114。
""")
