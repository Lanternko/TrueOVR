# card／inseason 0.2.10 卡住：需要 lead 裁定「OVR 係數」政策

日期 2026-11-01。尚未建立任何其他檔案、未修改任何既有檔案、未跑任何會寫檔的指令。

## 問題
派工 spec 同時寫了「OVR 係數沿用 0.2.9a」和「整條管線重跑（位置交互、RAPM 封頂、用人層、防守加成）」。
讀碼後這兩句在現有程式裡不能同時照字面成立：

- card 0.2.9a 的 `build_card_029a.py` 只是拷貝 E-164 S 臂的輸出，不是建構器。
- 真正產卡的是 `reports/card-0.2.9+E164-no-stamina/calibrate_wing_t.py`，每次執行都用「當次輸入的屬性」重擬合 ridge（含 position-interactions 設計矩陣、標準化均值／SD、H1 封頂、align δ=0.25、百分位錨點 PR1/PR50/PR99）。它沒有「套用凍結係數」模式。
- 因此「整條管線重跑」＝用 U 版屬性檔（`--attrSource`、`--tailSource`）再跑一次 calibrate，係數會隨屬性分布重新擬合，並不等於 0.2.9a 的係數。

## 選項
A. 重擬合（同方法、同超參數、同目標 T6）：用 U 版屬性餵 `calibrate_wing_t.py` 三張部件卡（primary／fitA／fitB，帶 `--dropAttr physique --dropAttr stamina`、H1、γ=1、δ=0.25、capMargin 0、bonusShape none、defWindow season、defPossFactor 0.5），再跑 E-162 用人層。優點：不用新寫模型程式，完全沿用既有流程與 G 關卡；缺點：係數不是 0.2.9a 的，「只換屬性來源」的歸因會混進係數變動（E-175 一階代理用的是凍結係數，所以跟代理的差異會有一部分來自重擬合）。
B. 凍結係數：複製 calibrate 腳本，新增「讀 0.2.9a 部件卡 summary.json 的 formula（intercept、attributeMean、attributeSD、coefficientsOnStandardized）直接套 U 屬性」的路徑，再跑位置交互、封頂、用人層。優點：真正只換屬性，符合 E-175 代理的假設；缺點：要新寫程式；還要裁定錨點（PR1/PR50/PR99、封頂的 allowed 值、用人層 r_repl／映射錨）是凍結 2025-26 舊值還是用 U 屬性重算（spec 只說「映射池與錨點凍結在 2025-26 池」，指的是屬性映射，沒說 OVR 百分位錨點）。

我的建議：B，且錨點與 r_repl 一併凍結用 0.2.9a 值（讓「只換 8 項屬性」可歸因）。但這是設計判斷，依 spec 不自行決定。

## 需要 lead 回答
1. A 或 B？
2. 若 B：OVR 百分位錨點（PR1/PR50/PR99）、H1 封頂參照、用人層 r_repl 與兩段映射錨，凍結 0.2.9a 值，還是用 U 屬性重算？
3. 賽中 0.2.10：沿用同一政策（inseason 讀的是 card-0.2.10 的 summary 係數）？

## 已確認、不影響上述裁定的事實
- 8 項屬性的 U 臂程式已在 `reports/E175-sliding-window-card/e175_card.py`（`card_chain(D, inp, 'U')`），E-175 重現對 0.2.9a V 臂 4656 格 |差|≤0.1 為 100%，可直接重用產出 U 屬性（含 foulDraw／pass 組合、mid／short PBP 平移、drive）。
- 需要改的版本常數在 `live/run_c4_live.py`：L42 CARD_MODE、L56 VERSION、L57 CARD_VERSION、L64–69 的 prior／CARD_DIR 等路徑、L79 USAGE_FILE；`daily_inseason_update.probe_base_version` 以 regex 讀 VERSION。
- 尚未讀：`test/live_current_gate.py`、`season_nav.py`、`daily_inseason_update.py`、`build_card_viewer.py`、`enrich_roster_viewer.py`、`status_snapshot.py`、`run_c4_live_rookie.py`。

2026-11-01 lead 裁定：B＋全凍結，見 build 說明
