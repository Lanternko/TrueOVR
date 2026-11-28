# E-174 第 1–3 階段：停下，未開跑（blocked）

- 日期：2026-11-01，role-card。沒有寫任何腳本、沒有跑任何擬合或評估，沒有改任何既有檔案。凍結文件（預註冊、errata-1、design、stage0-data）一個位元沒動。
- 依任務規定「凍結文件有錯或做不到：停下，不要自行變通」，在讀完實作所需的來源碼（`live/rookie_defense.py` 的 `window_weights`／`veteran`、`v4/tools/season_attrs_v4.py` 的 `build_mapping`／`compute_attrs`、`card-0.2.9+E164-no-stamina/e164_build.py`、`calibrate_wing_t.py`、`stage1/run_t.py`）後停下。理由有兩類。

## 一、凍結文件沒有定義、需要 lead／使用者裁定的方法問題（不是我可以自己選的）

1. **百分位型屬性怎麼做窗口加權沒有定義。** long、mid、short、ft、tovSkill、pass、rebound、creation、drive、foulDraw 在現有程式裡是「某季的原始值 → 該季 pool（GP≥30 且 MPG≥20）內的百分位 → 屬性」（`build_mapping`、`compute_attrs`），pool 是每季各自凍結的。`window_weights`／`veteran` 只示範了 onBall／help 的作法（累計**量**可相加，再套 2025-26 凍結的映射）。
   - 命中率類（long／mid／short／ft）：窗口加權的是「命中數與出手數」再收縮，還是「各季屬性值」加權平均？
   - 百分位類：映射用哪一季的 pool？窗口合併量放進 2025-26 的 pool，還是放進該快照季自己的 pool？
   - 這三種選法的屬性分布寬度都不同，直接決定 U 和 S 的差，以及擬合係數的量尺（design §5 Q1 自己就說窗口值分布比單季窄）。預註冊 §6 又禁止事後調整，所以必須在跑之前定死。
2. **S 臂的定義有一個模糊處。** S＝「窗口只放當季」。但 S 在 2025-26 季末是否必須逐值等於 0.2.9a 官方值（任務要求的 sanity check），取決於上一點的映射選法；而 0.2.9a 官方值本身是「舊實驗預算的各季值」，不是由單一可重跑的程式產生，所以 S@2025-26 與官方值的差異無法保證可以歸因。

## 二、工程上，在不自行發明做法的前提下做不完

3. **pass／rebound、pressure、foulDraw、short（E2 折扣）、防守加成要各自逐季重建，且 2022-23、2023-24、2024-25 三季都要與 0.2.9a 算法位元級一致。** stage0 §2.1 已實測：用 `v4/cards` 路徑 pass 差 24.4、rebound 差 17.0、pressure 差 43.3，所以要改走 `build_prior_v4.py`、E-071 force→E-123 池百分位、E-070 foulDraw（新寫）、E-104 TL 逐場遞減。每一條都需要先驗證「在 2025-26 能重現 0.2.9a」（2025-26 的 pbp 不在 repo，只能比對有 pbp 的季對舊卡檔，驗證基準也不完整）。
4. **歷史原點管線的快取輸入是 L-091 污染的。** `run_t.py`／`build_card_t.py` 的 `hist(t, cand)` 從 `stage1/work/<t>/` 複製已快取輸入，`run_calib` 只接單一份 attr／def／tail／press csv（`--attrSource`、`--defSource`、`--tailSource`、`--pressureSource`）。要做 U／S 各四個快照共八份屬性檔，並確認快取中沒有任何一欄仍是 2025-26 現值（creation、foulDisc、tail、presDisplay 等），這是一個獨立的重建，不是參數替換。
5. **算量。** 2 個測試季各需 U、S 兩次完整三部件擬合＋Y0＋防守加成（外加 c0 重現），再加 K 臂與 bootstrap 2000 次、2025-26 每 10 天重播。依任務規定重運算必須走 5090；我在這個 session 內沒有把握在不跳步驟的情況下完成全部，而半套結果（例如只跑 S、或沿用現值補缺）正是 L-091／預註冊 §2 禁止的。

## 建議（要 lead 決定）

- 先請使用者／lead 補一份 **errata-2**，只定死第 1 點（命中率類與百分位類在窗口下的算式、使用哪一季的 pool／凍結映射、收縮用窗口加權後的量），並指定 S@2025-26 對 0.2.9a 的容許誤差。
- 把階段 1（`scripts/card_window.py`，輸出 U／S 在四個季末的屬性表＋meta＋與 0.2.9a 的差異清單）與階段 2–3（擬合、判定、§5 報告項）拆成兩個派工：階段 1 驗收通過後再跑階段 2–3，後者在 5090 上跑。
- 階段 1 本身是輕量（屬性重算，stage0 實測單季 17 秒），本機可做；擬合與 bootstrap 才需要 5090。

## 偏離凍結文件？

沒有。本檔是唯一新增的檔案。
