# card 0.2.10c（E-187 KAU：修 Jalen Williams 偏高，F-125）

- 2026-11-01 上線（R-122，使用者選 KAU）。基底 card 0.2.10a（R-121）。版號跳過 b：`reports/card-0.2.10b/` 是另一個 session 的 E-188（OVR 頂端錨，未上線）；E-188 若要上線，改在本卡上重跑。
- 改法：用 0.2.10a 的修正後 T6（L-102）重擬合全部係數，傳球改全位置共用斜率（E-180 臂 A，`--dropInteract pass`）；屬性 tail-U.csv、用人層流程同 0.2.10a。建法與重現見 `reports/card-0.2.10a+E187-rebase/`（臂 KAU），本目錄 ranking.csv＝該臂 `work/KAU-2025-26/out/ranking.csv` 原檔。
- 版號：字母小版（R-064 影響小）：MIN≥500 前 20 名換 1 人（Scottie Barnes 出、Austin Reaves 進）、前 100 名移動 ≥10 名 18 人；evaluate.mjs 未跑（同 0.2.10a，無 2025-26 evaluation.json）。注意：係數不再凍結 0.2.9a。
- JW：MIN≥500 第 9→12（MIN≥900 8.5→10.5），OVR 87.3→87.0；前 25 名分段殘差 −1.50→−1.22（L-100）。
- 樣本內（R-007）；三原點樣本外沿用 E-187 KA（0.2.10 底，C 幾乎不變）。真樣本外：2026-27 季末本季 RAPM 複查 JW（F-125）。
- 網站：`build_card_viewer.py` 指本卡；`season_nav.off_def` 加 card_path（正式卡頁用本卡係數，新賽季頁仍用 0.2.10）。新賽季頁未改接（R-121：由 0.2.12 帶上；0.2.12 若要含本改動需改以 0.2.10b 為底）。npm test 52/52＋engine OK。

| 檔 | sha256 |
|---|---|
| ranking.csv | e46315bded816662b842460903104794f369d371e14f22df459d35eddc23158b |
| three-value.csv（同 0.2.10a） | 1176f259beb1c6a59cadbf066a4eab3b6c4a306a10a2d44d30b9720f4f4e225f |
| rapm-T6.csv（同 0.2.10a） | 514ba5e0a14fee5f5e700032bea613486fac68eed6d2073a0b12e21296bc6bb8 |
