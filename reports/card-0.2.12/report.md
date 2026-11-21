# 總評

**4/5 大致達成 有部分退步**

主目標達成：long、creation、threeValue、MPG 四項已改成四季滑動窗口，card 0.2.12 與 inseason 0.2.12 都在 card 0.2.10a 的底上完成，自我檢查逐位元通過、`npm test` 全過。扣一分是因為三分價值（只影響顯示）的離散度縮小，且 MPG 窗口有一個已知限制（見「退步」）。

**這次目標**

把 long（三分）、creation（自主創造）、threeValue（3PT 欄）、預測 MPG 四項換成近四季滑動窗口（近季權重高），係數、OVR 錨、r_repl、k 全凍結（= 0.2.9a），底是 card 0.2.10a（R-121）。

**進步了什麼**

- 底換對了：0.2.12 建在 0.2.10a 上（Jokić、Wembanyama 的 T6 已補回）。把新窗口全關掉後，同一條鏈重建出的排名和 0.2.10a 逐位元相同；新賽季端關窗口也和 0.2.10 的輸出逐位元相同。
- `frozen.json`（係數、錨、r_repl）和 0.2.10、0.2.10a 的逐位元相同，沒有被動到。
- 整體很穩：379 名有排名的人，名次相關 0.992（Spearman）；前 20 名沒人進出；前 100 名移動 ≥10 名的 15 人、前 300 名 121 人。
- 例子（逐人原因沒有一一拆，只報結果）：Tyus Jones 的 long 50.0 → 76.5（355 → 317 名）、Sabonis 119 → 76 名、Javon Small 106 → 58 名。
- 長人前十：Jokić 3 → 2、Wembanyama 2 → 3、Giannis 4 → 5、Tatum 8 → 8、Jalen Williams 9 → 9、Embiid 20 → 16（Mobley、Barnes、Holmgren 各退 1–3 名，Porziņģis 進前十）。
- 預測 MPG 的窗口長度只用 2024-25 選：窗口 1 季最準（誤差 3.86，2 季 4.04、3 季 4.21、4 季 4.34）；2025-26 只報告，也是 1 季最準（4.09 / 4.33 / 4.52 / 4.66），方向一致。
- 新賽季（2026-10-31 資料，484 人）：把「0.2.10 → 0.2.10a」和「0.2.10a → 0.2.12 窗口」分開看：
  - 0.2.10 → 0.2.10a（只換底，窗口關）：149 人 OVR 有變，前 20 名 1 人換、前 100 名 3 人換；主要是 SGA 118.6 → 103.6、Kawhi 4 → 6 名、Jokić 6 → 3 名、Wembanyama OVR 下修 6.7（都來自 0.2.10a 本身的 T6 修正，不是窗口）。
  - 0.2.10a → 0.2.12（只開窗口）：433 人 OVR 有變、最大 11.3（都是出賽少的新秀／板凳，如 Mashack、Cody Williams、Saraf）；前 20 名 1 人換、前 100 名 7 人換；前 100 名移動 ≥10 名的 30 人。
  - 例子：Mike Conley 339 → 275 名、Tyus Jones 431 → 318 名、Dorian Finney-Smith 351 → 285 名往上；Enrique Freeman 409 → 457 名、Isaiah Collier 407 → 451 名往下。

**退步了什麼**

- threeValue（只影響顯示）的離散度縮小：標準差變成 0.89 倍（17.6 → 15.6），與 0.2.10a 的相關 0.85；少數人抬得很多（Jović 40 → 75、Lonzo Ball 42 → 77、De'Andre Hunter 50 → 84），原因沒有逐一拆。
- long 離散度也略縮（標準差 0.97 倍）；Giannis 的 long 64 → 44、Ausar Thompson 58 → 33 降得明顯。
- Franz Wagner 21 → 41 名、Alperen Sengun 77 → 99 名、Hartenstein 33 → 53 名等人掉了 20 名左右；少數球員一次掉很多名是這版的代價。
- 新賽季端的限制：「上季 OVR 基準」(lastOVR) 用開季第 0 天的窗口 MPG，所以季中 OVR 變化量（dOVR）主要來自比賽，但窗口 MPG 隨賽季更新的部分仍會進 OVR。正式卡檢查（lastOVR 對正式卡）最大差從 0.0 變成 0.1（四捨五入層級）。
- 按 R-109 的數字（前 20 名無進出、前 100 名 15 人 ≤25）其實夠格當字母版，但派工指定版號 0.2.12，這次照指定；要不要改成字母版由你決定。

**直觀證據**

| 球員 | 0.2.10a | 0.2.12 | 說明 |
|---|---|---|---|
| Tyus Jones | 355 名 | 317 名 | long 50 → 76 |
| Domantas Sabonis | 119 名 | 76 名 | |
| Javon Small | 106 名 | 58 名 | |
| Franz Wagner | 21 名 | 41 名 | |
| Alperen Sengun | 77 名 | 99 名 | |
| Embiid | 20 名 | 16 名 | |
| Jokić | 3 名 (100.6) | 2 名 (101.3) | |
| Wembanyama | 2 名 (100.9) | 3 名 (99.5) | |

SD 比（0.2.12 / 0.2.10a）：long 0.97、creation 0.99、OVR 1.02、threeValue 0.89。OVR 差：平均 +0.20、標準差 2.03、最大 9.0。

**要你決定的事**

1. 採用與否：按 R-118 直接上線，但因第 4 點先不動正式卡指標、不發佈到 gh-pages（本機頁面已建，3PT、CRT 都有值、無 NaN）。
2. 版號：照派工用 0.2.12；若要按 R-109 改字母版（0.2.10c 之類，併進 0.2.10 那格）告訴我，我改 PATCH_NOTES 與檔名。
3. threeValue 離散度縮小（0.89 倍）要不要處理：選項 A 照現狀（只影響顯示）；選項 B 另開實驗把窗口收縮常數 K 改小（要預註冊，不在這次凍結範圍內）。
4. **底又換了**：做到最後發現 R-122（你選 KAU）把正式卡定為 card 0.2.10b，而我這版建在 0.2.10a 上。所以我**沒有 commit** 會改正式卡指標的三個共用檔（`status_snapshot.py` 的 OFFICIAL_CARD、`season_nav.py` 的更新說明／提示卡、`build_card_viewer.py`；這三個檔另一個 session 的 0.2.10b 修改還沒提交），改法存成 patch：`reports/card-0.2.12/work/patches/*.patch`。選項 A：0.2.12 重建在 0.2.10b 上（鏈條已自動化，輸入換成 0.2.10b 的 T6 與三張部件卡再跑一次，再套 patch）；選項 B：維持建在 0.2.10a 上、2025-26 正式頁維持 0.2.10b，只讓新賽季頁用 0.2.12。我建議 A。

---

查證附註（不放進回覆）：
- 版本鏈：card 0.2.11 是另一個 session 先佔用並改名 0.2.10a；我保留 0.2.12 這個名字（派工指定）。
- 輸入：`reports/card-0.2.10a/{rapm-T6.csv, cards/K6/*, work/t6/fixed/*, frozen.json}`；frozen.json sha256 前綴 b069064574f2dc1a，三版相同。
- 自我檢查：`work/Sf`（卡端）、`work/inseason-0210a-nowin-1031`（新賽季端，0.2.10a 底、窗口關）。
- 比較腳本：`cmp_final.py`、`cmp_inseason.py`；數字存 `cmp_final.json`。
