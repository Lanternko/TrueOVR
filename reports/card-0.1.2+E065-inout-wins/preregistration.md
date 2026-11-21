# E-065 預註冊：OVR 對「四個平均隊友」定義的進出勝場測試

日期：2026-10-28　擬稿：lead（本 session）　狀態：凍結（sha256 見 preregistration.sha256）；凍結時 WinImp 與答案都還沒算

## 問題
R-025 定義 OVR＝「這名球員加四個聯盟平均隊友上場，能帶來多少比賽影響力」，R-026 單位是每場、含上場時間。
F-029 指出現行卡片 `pred = pred0 + defenseBonus + align`：pred0 是屬性 ridge，defenseBonus（RAPM pooledD）與 align（RAPM 對齊）是模擬之外的加項，最後再用 PR1/50/99 錨點映射、2K27 名次封頂。
使用者質疑：OVR 99 應該是「拿掉，原隊掉出季後賽；加入，球隊變爭冠」的強度。Derrick White（card 0.1.2 排第 6，99.0）與 Alex Caruso（第 9，98.9，pred0 −0.31、defenseBonus +3.86）看起來不到這個強度。

## 假設（先寫死）
- H1：在模擬器裡照 R-025 字面做的「每場勝場貢獻」（下稱 WinImp），對樣本外答案的 ρ 不低於 card 0.1.2 OVR。
- H2：defenseBonus 高估。card 0.1.2 前 60 名中 defenseBonus ≥ 1.0 的球員，OVR 名次比樣本外答案名次好（殘差 > 0）。

## 對象與版本
- 卡片：card 0.1.2＝`reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv`（sha256 d251824d…，E-064 c0 已確認可重現）。
- 人群：2025-26 MIN ≥ 500 且有卡的球員；主要結論看 card 0.1.2 前 60 名，另列全池。
- 模擬引擎：現行 `src/`（記錄 git HEAD）；seed 清單事先固定（每名球員 × 位置 × seed，team+seed 重抽，G3）。

## 量測
1. **WinImp（定義本身）**
   - 候選球員打他 2025-26 的場均分鐘，其餘四人與他不在場的時間都由聯盟平均 profile 補上（全聯盟依分鐘加權，不分位置；位置版另列副表，不作判準）。
   - 對照組：同樣分鐘換成平均 profile。
   - 輸出每場淨分差與換算勝率差 → 82 場勝場差。
   - 參考現有 `reports/ovr-v53-2025-26/worker.mjs` 的 `workloadTeam`；差別是基準改為全聯盟平均、不做位置中心化、單位每場（R-026）。
2. **樣本外答案**
   - 沿用 E-064 預註冊 §3.2（sha256 c86a2811…）：2025-26 依 int(gameId)%2 切半；A→B 答案＝RAPM_B pooledNet × MPG_B，B→A 反之。
   - RAPM：`reports/ovr-v58-holdout-2025-26/rapm-{A,B}.csv`；MPG：`reports/card-0.1.2+E064-pergame/mpg-{A,B}.csv`（只讀，等 E-064 lead 核對 verdict.json 後才讀）。
   - 人群：pooledPoss ≥ 2500 且 A、B 兩半各出賽 ≥ 5 場（與 E-064 相同）。
   - 注意：WinImp 用的屬性若來自全季，對分半答案仍是部分樣本內，要在報告中標明（R-007）。主比較是 WinImp 對 OVR 的「差」，兩邊同樣條件。
3. **示範（不作判準）**
   - BOS 2025-26 實際輪替拿掉 White（分鐘依現有輪替規則重分配），季模擬勝場差。
   - White 加入聯盟勝場中位數球隊，季模擬勝場差。
   - 同樣對 Luka、Wembanyama、Caruso 各做一次對照。

## 判準（凍結後不改）
- V1（H1）：ρ(WinImp, 答案) − ρ(OVR 0.1.2, 答案)，球員 bootstrap 2000 次，兩方向各算；90% 下界 > −0.02 視為「定義版不輸現行卡」，下界 > 0 視為「定義版較好」。
- V2（H2）：前 60 名中 defenseBonus ≥ 1.0 組的平均名次殘差（OVR 名次 − 答案名次，取負號使正值＝OVR 高估），bootstrap 90% 下界 > 0 → 確認高估。
- G1 `npm test` 先過；G2 報告記錄卡片 sha、RAPM 窗、資料 sha256、git HEAD、seed 清單。
- 任何一條沒過都照實報；不得看結果後換人群、換門檻、換 seed（L-026）。

## 執行
- 重度運算（每人多 seed 的 WinImp、季模擬）跑 5090。
- 輸出到本目錄：`winimp.csv`、`verdict.json`、`demo.md`、`report.md`。
- lead 收到後自己核對 verdict.json；memory 由 lead 寫（L-027）。

## 與其他工作的關係
- E-064（另一個 session）改的是 OVR 的單位與錨點；本測試量的是「定義本身」的勝場貢獻，可當 E-064 之後重建 OVR 的驗收目標。
- 兩邊共用 E-064 的分半答案檔，不改它的檔案。
