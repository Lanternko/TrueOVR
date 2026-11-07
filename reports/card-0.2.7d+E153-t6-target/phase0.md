# E-153 第 0 階段（2026-11-01）

## 結論：停在 §3 停止規則，B12 那一半沒有明確的 T6 對應，等 lead 決定

## c0 / c0h 驗證（通過）
| 項目 | 結果 |
|---|---|
| c0：K0 2025-26 ranking vs `reports/card-0.2.7d/ranking.csv` | sha 同為 696a8ac7b235acf51cdb5634fa9896a6905fec81adb96166b6995b9015c20649，逐位元相同 |
| c0 底（連續 d 關閉）= 0.2.7c | sha 99466f36…1655，與 0.2.7c 相同 |
| c0h 2022-23 | out/K0/ranking.csv 3e7d08ec…2b67a 與 E-142 T0 相同 |
| c0h 2023-24 | 5c03c2e1…f479 與 E-142 T0 相同 |
| c0h 2024-25 | 4940c59d…1cc85 與 E-142 T0 相同 |
驅動程式：`e153_build.py`（包 E142 build_card_t；cont=1 時 scope_feats 的 d 換成連續 d）。

## 2025-26 建卡讀到的「影響力目標」輸入
| 輸入 | 位置 | 內容 | E-142 c0 是否換 |
|---|---|---|---|
| B12 目標表 | `reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv`（primary／fitA／fitB 各 part 都讀，calibrate_wing_t.py TARGET） | 欄位 name, position, healthy_minutes, centered_contribution, standard_error；模型推得、已置中的每 36 分貢獻，附標準誤；與 RAPM 以 alpha 0.5 組合 | 沒換 |
| RAPM 半（primary） | `reports/impact-rapm/rapm.csv` pooledNet/O/D | 目標組合＋align／封頂的 RAPM 參照 | 沒換 |
| RAPM 半（fitA／fitB） | `--rapm` CSV | 同上，各自分半 | 換（swap_rapm） |
| usage 層 rapm1 | e094_t 管線的季 RAPM | scope_feats 擬合 | 沒換 |
E-142 的 2025-26 實際只換 fitA／fitB 的 RAPM 半；歷史原點 alpha=1、y=0，沒有 B12，所以歷史原點是整個換掉。

## 為什麼停
1. B12 表是「模型推得的每 36 分置中貢獻＋標準誤」，T6 是 DARKO／BPM 的 z 平均轉回每百回合。單位、置中方式、標準誤（T6 沒有）都沒有現成對應。
2. 「整個換掉」在 2025-26 還含 primary RAPM 半、align／封頂參照、usage 層 rapm1，E-142 都沒做過，預註冊沒說怎麼處理。
3. B12 與 RAPM 的 50/50 組合，換成 T6 後是變成 100% T6（等同歷史原點 alpha=1），還是 T6 取代 RAPM 但保留 B12，預註冊沒定。
這些選擇會改變結果，故依 §3 不自行決定。

## 需要 lead 決定
- (a) 2025-26 目標＝100% T6（比照歷史原點 alpha=1、y=0，B12 整張不用）？
- (b) 還是把 B12 重標度後與 T6 各半（需定義轉換與標準誤）？
- (c) primary RAPM 參照、align／封頂、usage 層 rapm1 是否也換成 T6？
未建 K0h 以外任何換目標的卡；K6 未建。

## errata-1 補記（2026-11-01）
K6 的 primary／fitA／fitB 三個 --rapm 輸入在 2025-26 與三個歷史原點換法相同；清單與 sha 見 `report.md`「核對」一節。
