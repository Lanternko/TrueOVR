# E-128 預註冊：新賽季 OVR 跟上 card 0.2.7b（E-111 的接續）

狀態：草稿（2026-10-30）。凍結後不改；sha256 存在 `preregistration.sha256`。

## 0. 這份是什麼

- 繼承 `reports/ovr-inseason-2026-27/e111-card027/preregistration.md`（凍結 sha256 f20f34a4…739e）以及它的 errata-1（sha256 1d243371…0c90，RAPM 名次同分照卡片產生器排），下稱「E-111 預註冊」。本檔只列改動的地方，沒寫到的照 E-111 預註冊。E-111 預註冊本身繼承 E-107 新賽季版。
- 基準卡從 card 0.2.7 改成 **card 0.2.7b**：0.2.7 加上 E-125（pass 看量也看率），再加上 E-123（3PT、RIM、PRES 頂端不封 99；R-072、R-078）。
  - 卡片在 `reports/card-0.2.7b/`。
  - `ranking.csv` 的 sha256 要等於 `summary.json` 的 `ranking_csv_sha256`（361bcac6…5e81105）。用程式比對這兩個值，不寫死字串。
- 版號照 R-050：採用後是 inseason 0.2.7b。
- lead 已經看過的東西，所以這次不算盲測：
  - E-111 的全部結果，包括回測 (1)(2)；
  - E-123、E-125 的全部結果；
  - card 0.2.7b 的全部欄位；
  - 子代理對現行 inseason 鏈的盤點（哪些屬性逐場更新、哪些凍結、各處的 99 封頂在哪裡）。
- 本實驗的改動都是 card 0.2.7b 本身逼出來的機械調整，沒有新的自由參數。門檻全部沿用 E-111。

## 1. 對 E-111 預註冊 §1 的修改

所有改動都放在新開關 `CARD_MODE='027b'` 後面。`'027'` 分支要保持原樣，因為 (c0) 要拿它比對。

1. **先驗 x0**：
   - 來源改成 card 0.2.7b 的未四捨五入值。屬性欄和 0.2.7 不同的只有 pass（E-125）、help、pressure（E-123）。其他欄沿用 E-111 的來源。開工時先核對這點，跟預期不同就停下回報。
   - 未四捨五入檔的位置：
     - pass 取 `reports/card-0.2.7+E125-pass-volume/`；
     - help、pressure、presDisplay 取 `reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/`；
     - threeValue 取 `reports/card-0.2.7b/three-value.csv`。
     - 實作者要寫明實際用的檔名和 sha256。
   - 產出 `live/build_prior_027b.py` 和 `live/prior-2025-26-card027b.json`。
2. **pass 逐場更新改用 E-125 公式**：
   - 公式是 `0.5·zs(AST/36，E-055 (c) 收縮) + 0.5·zs(AST%)`。常數照 `astvol-fit.json`（k=5.657、λ=0.5、kh=8、位置先驗）。
   - **zs 的選法**：賽中視窗用 2025-26 凍結的平均和 SD，同 E-111 §1.5 foulDraw 的作法。合併池用各季自己的 zs，同卡片端。
   - 四季合併池 `pool-027.json` 改建成 `pool-027b.json`。只有 pass 欄改變，r90、r99、S 照 E-101 重算。其他 8 項屬性的池要和 pool-027 逐位元相同。
   - `tools/season_attrs.py`、`build_pool_027.py` 現在只看 AST%，要加 027b 分支，不改 027 分支。
3. **help（RIM）用 E-123 的尾巴**：
   - `live/rookie_defense.py` 的新秀路徑和老將四季窗口路徑目前都是反查 CURVE_DEF_RIM 再夾在 40–99。027b 改成照 E-123 的 help 換算：
     - curve 型；
     - 頂端 a99 = 0.095，S = 0.050102；
     - 底端 SD_pool = 0.031933；
     - 用 E-101 的頂端和底端公式。這些參數取自 `tail-summary.json`，凍結使用，不重擬合。
   - 上限 150、下限 25 是公式本身的漸近值，不另外截斷。
   - 實作必須重用 `e123.py` 的 help 函式（import 或逐行複製並註明出處），不另寫一份。
4. **pressure、presDisplay**：
   - 賽中照舊凍結，凍結值改成 card 0.2.7b 的值。這兩欄可以超過 99，Thybulle 的 pressure 是 127.0。
   - foulDisc 照舊取先驗。
5. **threeValue（3PT，只顯示，不進 OVR）**：
   - 拿掉 `three_value_columns` 的 99 封頂。
   - 頂端照 E-123 T 用 E-101 頂端公式，r90、r99、S 凍結取自 `tail-summary.json`，S = 0.232510。
   - 底端維持 40，因為 E-123 的 h1 沒過。
   - 先驗從 card-0.2.7b 的 `three-value.csv` 讀。
6. **OVR 層**：
   - 屬性迴歸、用人層、r_repl、錨點、UL 防守加成都照產生 card 0.2.7b 的那條鏈（`rebase-027a/` 的 e123a 卡；錨點是 PR1 −0.8234、PR50 1.2758、PR99 4.1150）。
   - 用人層檔：`live/build_usage_027b.py` 產出 `live/usage-2025-26-card027b.json`。
   - onBall 和 help 照 R-075、R-076 的 wrapper 逐場更新；防守加成照現行每日重擬（`defense_bonus.py`）。
7. **版號**：027b 模式下：
   - `VERSION = 'inseason 0.2.7b'`；
   - `CARD_VERSION = 'card 0.2.7b'`；
   - `FORMAL_RANKING = reports/card-0.2.7b/ranking.csv`。
   - 採用時才改預設值，同 E-111 §1.6。
8. **回測**：
   - 用 `e128-card027b/backtest_e128.py`，規則同 E-111 §1.7，文中的「027」一律讀成「027b」。
   - 歷史季的答案卡和先驗卡，pass 用 E-125 公式套該季資料。
   - help、pressure 照 E-111 的歷史卡作法：歷史卡的 onBall、help 固定 70（E-111 D15），pressure 也沿用 E-111。所以 E-123 的尾巴在回測裡只透過 2025-26 先驗起作用。
   - threeValue 不進 OVR，回測不用它。

## 2. 對 E-111 預註冊 §2 判定表的修改

| 代號 | 條件 |
|---|---|
| (c0) | 不變，但改比 027：`CARD_MODE='027'` 的輸出要和線上現行 inseason 0.2.7 的快照逐位元相同 |
| (c1) | `npm test` 全過 |
| (u) | 不變，對照的池改成 pool-027b。另加一條：pass 以外的 8 項池和 pool-027 差 0 |
| (z) | 不變 |
| (L1) | N=0 要重現 **card 0.2.7b**：<br>• ref 換算的 OVR 對 card 0.2.7b `ranking.csv` 的 ovr，卡內每人 \|差\| ≤ 0.1；<br>• 錨點、r_repl、UL 防守加成差 0（容許浮點誤差 1e-9）；<br>• pass、help、pressure、presDisplay 每人 \|差\| ≤ 0.05 |
| (h) 新增 | `rookie_defense.py` 用 2025-26 原始表重算的 help，對 card 0.2.7b 的 help 每人 \|差\| ≤ 0.05，包括 4 個 > 99 的人（Stewart、Holmgren、Wembanyama、Kalkbrenner）。onBall 照 E-111 也要逐人吻合 |
| (t) 新增 | N=0 的 threeValue 對 card-0.2.7b 的 `three-value.csv` 的 `tv_main`，每人 \|差\| ≤ 0.05。剛好 99 的要是 0 人 |
| (s) | 同 E-111。更新的屬性不變，還是那 9 項；x0 改成 0.2.7b |
| (1) | RG1-027b 對 027b 答案卡，要過 v5 §2 的 V1∧V2。基準是 RA-027b，門檻不改 |
| (2) | 8 格每格都要 MAE(RG1-027b) − MAE(RG1-sat15) ≤ +0.05。基準仍是 E-095 的 `predictions-sat15.csv` |

- 採用規則同 E-111 §4。前置關卡是 (c0)(c1)(u)(z)(L1)(h)(t)(s)，任何一項沒過就停下回報，不看 (1)(2)。

## 3. 只報告（不影響判定）

- 同 E-111 §3。
- 線上 027b 對 027 的名次變動：前 20 名的進出、\|ΔOVR\| 的中位數和最大值。
- 指定球員的名次和值：
  - OVR 名次：Mobley、Ausar Thompson、Anunoby、Giannis、Trae Young、Wembanyama、Wagner。
  - 3PT：Curry；RIM：Stewart；PRES：Thybulle。
- 新賽季裡 > 99、剛好 99、> 140 的人數，四欄分開列：pass、help、pressure／presDisplay、threeValue。
- R-064 影響檢查（rank 欄）：
  - 前 20 名換了幾人；
  - 前 300 名裡移動 ≥ 10 名的有幾人。

## 4. 不准

- 同 E-111 §4。
- 不改 `src/`。
- 不改 `CARD_MODE='027'` 和 `'025'` 分支的輸出。
- 不在看過 (1)(2) 之後改池、尾巴參數或門檻。
- 不重擬合 E-123、E-125 的常數。
- 不改網站或 gh-pages。上線由 lead 在使用者採用後處理。

## 5. 上線時的連帶修改（採用才做）

- 看 `season_nav.py` 的 0.2.7 那格：
  - 目前已經標了 `('card','inseason')`，而且列出 0.2.7a 和 0.2.7b 兩行。採用後就名實相符，不用改。
  - 不採用的話，要改成新賽季只對到 0.2.7，在下一次 commit 修正。
- `daily_inseason_update.py` 的 RUN_LIVE 切到 027b。先跑 `--dry-run` 核對，再正式發佈。
