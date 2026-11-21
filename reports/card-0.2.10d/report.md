# 總評

**4/5 大致達成 有部分退步**

主目標達成：long、creation、threeValue（3PT 欄）、預測 MPG 四項改成四季滑動窗口，疊在正式卡 card 0.2.10c（E-187 KAU）上，版號 card／inseason 0.2.10d。自我檢查逐位元通過、`npm test` 全過。扣一分：窗口把 0.2.10c 修掉的 Jalen Williams 偏高又帶回來了（12 → 9 名），Franz Wagner 一次掉 21 名。

**這次目標**

在 card 0.2.10c 上把 long、creation、threeValue、預測 MPG 換成近四季滑動窗口（近季權重高），係數、OVR 錨、r_repl 照 KAU 流程重擬合；2025-26 頁與新賽季頁同一條管線、同一個版號。

**進步了什麼**

- 底沒有換錯：把窗口全關，同一條鏈重建出的排名和 0.2.10c 逐位元相同；新賽季端關窗口也能獨立存成一份（0.2.10c 底、無窗口）。
- 整體很穩：379 名有排名的人（MIN ≥ 500），名次相關 0.991；前 20 名只換 1 人（Desmond Bane 進、Austin Reaves 出）、前 100 名移動 ≥10 名的只有 13 人；照 R-109 屬字母版（≤2、≤25），所以併進 0.2.10 那格、不另開新格。
- 三分被低估或高估的人往合理處修：Domantas Sabonis 138 → 75 名、Javon Small 117 → 60 名、Tyus Jones 343 → 308 名（long 50.0 → 76.5）、Mike Conley 320 → 279 名。
- 長人前十：Jokić 2 → 2、Wembanyama 3 → 3、Giannis 4 → 5、Tatum 8 → 8、Jalen Williams 12 → 9、Holmgren 14 → 14、Embiid 19 → 15、Mobley 16 → 18、Davis 23 → 22、Porziņģis 39 → 23 進前十（Barnes 26 → 出前十）。
- 新賽季（2026-10-31 資料，484 人）：前 20 名人員和 0.2.12 完全相同（0 人進出）；前 100 名換 7 人、移動 ≥10 名 23 人。

**退步了什麼**

- **窗口吃掉了 0.2.10c 的 Jalen Williams 修正**：0.2.10c 把 JW 從第 9 名壓到第 12 名（OVR 87.0），加上窗口後又回第 9 名（OVR 90.7）。原因是他的 long 從 55.8 變 70.7（窗口抓進前幾季較高的三分命中）；創造 92.5 沒變。新賽季端 JW 也是 10 → 9 名（88.8 → 92.1）。這是資料帶來的，不是 bug，但等於 R-122 要修的那個人又被抬回去；Jokić、Wembanyama 的 T6 修正則還在（Jokić 2 名、Wembanyama 3 名，沒被抵銷）。
- Franz Wagner 21 → 42 名（OVR 84.1 → 81.3）：long 64.2 → 48.4，預測 MPG 30.0 → 24.6。Alperen Sengun 91 → 96 名、Giannis long 64 → 44（排名 4 → 5）也是同類。
- OVR 整體往上移：平均 +1.4（最大 +11.3），SGA 106.6 → 109.9、Jokić 103.7 → 107.0；新賽季端 SGA 到 110.0（頂在上限）。前 20 名順序沒變，但絕對值變高，和 0.2.10c 的 OVR 數字不能直接比。
- 新賽季端，窗口對 0.2.10c 底的影響比對 0.2.10a 底大：關窗口時 0.2.10c 底和 0.2.10d 之間 474 人 OVR 有變、前 100 名移動 ≥10 名 33 人（超過 R-109 字母版的 25，但那條只管 2025-26 卡）；0.2.12 → 0.2.10d 直接比則是 23 人。
- threeValue（只影響顯示）離散度仍比窗口前小（0.2.12 起就是 0.89 倍），這次沒處理。
- MPG 窗口只進 OVR 的用人層（g、錨、ranking 的 mpg 欄），不改用人回歸的設計矩陣，這個限制沒變。

**直觀證據**

2025-26 卡（MIN ≥ 500）：

| 球員 | 0.2.10c | 0.2.10d | 說明 |
|---|---|---|---|
| Jalen Williams | 12 名（87.0） | 9 名（90.7） | long 55.8 → 70.7，JW 修正被吃回 |
| Jokić | 2 名（103.7） | 2 名（107.0） | |
| Wembanyama | 3 名（101.5） | 3 名（102.0） | |
| SGA | 1 名（106.6） | 1 名（109.9） | |
| Anthony Edwards | 10 名（87.6） | 10 名（89.1） | |
| Franz Wagner | 21 名（84.1） | 42 名（81.3） | long 64 → 48、MPG 30 → 25 |
| Alperen Sengun | 91 名（75.5） | 96 名（75.5） | |
| Domantas Sabonis | 138 名（72.9） | 75 名（77.1） | long 51 → 72 |
| Tyus Jones | 343 名 | 308 名 | long 50 → 76.5 |

新賽季（2026-10-31，484 人），排名（OVR）：

| 球員 | 0.2.12 | 0.2.10c 底、關窗口 | 0.2.10d |
|---|---|---|---|
| Jalen Williams | 9（91.6） | 10（88.8） | 9（92.1） |
| Jokić | 2（101.3） | 2（103.5） | 2（107.0） |
| Wembanyama | 3（100.0） | 3（102.6） | 3（102.5） |
| SGA | 1（104.4） | 1（106.4） | 1（110.0） |
| Edwards | 16（86.0） | 12（87.6） | 12（88.6） |
| Franz Wagner | 32（81.4） | 20（84.4） | 34（82.4） |
| Sengun | 83（75.7） | 77（76.3） | 74（76.7） |

新賽季「0.2.12 → 0.2.10d」怎麼拆（OVR 平均變化、前 20 名進出、前 100 名移動 ≥10 名人數）：

- 只換底（0.2.10a → 0.2.10c，窗口都關）：−0.36、0 人、24 人。主要是新秀與板凳球員下修（Trevon Brazile −9.7、Emanuel Sharp −9.1）。
- 只開窗口（在 0.2.10c 底上）：+1.11、1 人（Franz Wagner 出、Kevin Durant 進）、33 人。
- 兩者合併，也就是 0.2.12 → 0.2.10d：+0.88、0 人、23 人（最大 6.4：Kingston Flemings、Jahmai Mashack、Jokić +5.7）。

前 20 名（新賽季 0.2.10d）：SGA、Jokić、Wembanyama、Dončić、Giannis、Kawhi、Mitchell、Tatum、Jalen Williams、Ty Jerome、Butler、Edwards、Murray、Curry、Holmgren、Maxey、Durant、Embiid、Cunningham、Mobley。

**要你決定的事**

1. 採用與否：按 R-111／R-118 直接上線（兩頁同一條管線，約基奇 T6 修正和窗口一起發布）；若不接受 JW 又回第 9 名，要回到 0.2.10c 只要把 CURRENT.json 指回 0.2.10c 的檔（關窗口的輸出已獨立存好）。
2. JW 要不要另處理：選項 A 照現狀（他的三分近季確實較高，窗口是資料）；選項 B 另開實驗，把窗口的 long 收縮得更重（要預註冊，不在這次凍結範圍）。我建議 A，先觀察賽季中是否仍偏高。
3. Franz Wagner 的預測 MPG 30 → 25 與 long 64 → 48 是否合理（傷病／角色變動），要不要抽查。
4. threeValue 離散度（0.89 倍）沿用，要不要另開實驗調收縮常數。

---

查證附註（不放進回覆）：
- 輸入：`reports/card-0.2.12/{tail-U.csv, mpg-c82.csv, three-value.csv, mpg-L-selection.json}`、`reports/card-0.2.10c/{rapm-T6.csv, ranking.csv}`；流程同 `reports/card-0.2.10a+E187-rebase/build.py`（複製，附 E185_* 環境旋鈕）。
- 自我檢查（0.2.10a 的 tail-U、原 MPG、原 threeValue 重建 0.2.10c）：ranking sha256 e46315bded816662b842460903104794f369d371e14f22df459d35eddc23158b，與 card-0.2.10c 相同，見 `results.json`。
- 新賽季端關窗口：`WIN10=0 python run_c4_live_rookie.py _base10c_nowin`，用 `work-selfcheck` 的 0.2.10c 重建檔。
- 比較腳本：`cmp_final.py`、`cmp_inseason.py`；數字存 `cmp_final.json`、`cmp_inseason.json`。
- 為了讓賽季端吃 KAU 卡（拿掉傳球位置交互項），`reports/ovr-inseason-2026-27/tools/ovr_pipeline.py` 的設計矩陣改由係數個數判斷是否少 4 欄；舊 summary 行為不變。
