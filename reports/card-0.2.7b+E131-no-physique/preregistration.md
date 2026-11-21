# E-131 預註冊：卡片 OVR 迴歸拿掉 physique（體格）

- 日期：2026-10-30。來源：使用者問 PHYS 有什麼效果、要不要放網站；lead 回報卡片 0.2.7a 係數（physique +0.231／10 分，SE 0.102；heightInches −0.752／10 吋，SE 0.518）與 2025-26 相關（體重～pooled RAPM r = +0.18，同身高下的體重 r = +0.11）；使用者認為體格和影響力沒有實質關係，選「連 OVR 也拿掉 physique」（選項 2）。
- 版本：`card 0.2.7b+E131`（R-018）。基準：正式卡 card 0.2.7b（R-078，`reports/card-0.2.7b/ranking.csv`，sha256 361bcac61075dec1150c3b89b406ecd62dcaf4fdb5d738ccff68a0634de81105）。
- git HEAD（寫本檔時）：404659f。角色：實作 role-card；判讀 lead；稽核 role-audit。本機可跑（同 E-125）。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」）。sha256 記在 `preregistration.sha256` 與 `memory/experiments.md` E-131。凍結後第一步：K0 的 c0 過了才准跑 K1。

## 0. 背景與假設

### 現況
- physique＝(身高吋＋體重磅/10) 的聯盟百分位，換成 40–99（`scripts/build_season_league.js:84,120`），沒有任何比賽數據。
- 卡片 OVR 迴歸的設計矩陣 `ATTRS` 含 physique 與 heightInches（`reports/card-0.2.7+E123-tail-3pt-rim-pres/calibrate-wing.py:58`）；`e094.py`（用人回歸、防守加成）不讀 physique。
- card 0.2.7b 的建法：`reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/run_cards.py`（arm e123a）＋ `rebase-027a/e123a.py`（唯讀匯入 E-094 `e094.py`）。

### 改動（候選只有一個）
- `calibrate-wing.py` 加一個選項 `--dropAttr physique`（預設不帶＝逐位元不變）：只把 physique 從 OVR 迴歸的 `ATTRS` 拿掉。
- 不動：heightInches 留在迴歸裡；physique 仍留在 `TAIL_ATTRS` 與卡片欄位（顯示用，網站拿掉另外處理）；form／ridge 照原本的 CV 選法重選（程序不變，結果若和基準不同要報告）；其他屬性、用人回歸、防守加成、錨點算法一字不改。
- 模擬引擎（`src/` 的 physEdge、reboundContest）不動，不在本實驗範圍。

### 假設
- H1（沒弄壞）：拿掉 physique 後，樣本外排序一致性（m1–m3）不明顯變差。
- 不設任何球員名次目標。

### lead 事前預期（看結果前寫）
- heightInches 係數往正的方向移（吸收 physique 裡身高的那部分）。
- 同身高偏壯的長人（Zion、Adebayo、Randle、Steven Adams 類）OVR 小降；偏瘦的長人與後衛小升。
- physique 權重排第 7、和位置與 rebound／help 重疊，預期 m1 點估計小幅為負但在門檻內。

## 1. lead 已看過的（揭露）
- card 0.2.7a 與 0.2.7b 全部欄位；card 0.2.7a primary 的 16 項 `valuePer10AttributePoints`（含 physique、heightInches）與 form／ridge（position-interactions、1.0）。
- 2025-26 bio × pooled RAPM（pooledPoss ≥ 3000，448 人）：體重、身高、同身高下體重對 net／O／D 的相關與分位置相關。
- **沒看過**任何拿掉 physique 後的係數、OVR、名次或 Δρ。
- 不是盲測：方向由使用者看過係數與相關之後選（L-026），沒有自由參數。m1–m3 只證明「沒變差」。版號在採用時照 R-064 判定（影響小＝字母小版本 card 0.2.7c，否則 PATCH card 0.2.8）。

## 2. 做法

### 2.1 程式（新目錄 `reports/card-0.2.7b+E131-no-physique/`）
- `calibrate-wing.py`：由 `reports/card-0.2.7+E123-tail-3pt-rim-pres/calibrate-wing.py` 複製，只加 `--dropAttr <name>`（可重複；在 `main()` 解析旗標後、建設計矩陣前把它從 `ATTRS` 移除）。diff 存 `diff-calibrate.txt`。
- `run_cards.py`：由 `rebase-027a/run_cards.py` 複製，只跑 arm e123a 的 tail／def 輸入（唯讀沿用 `rebase-027a/work/tail-e123a.csv` 與 E-123 `work/def-new.csv`，不重新 merge），呼叫本目錄的 calibrate-wing.py；組別 `K0`（不帶 dropAttr）、`K1`（`--dropAttr physique`），各產 `cards/{K0,K1}/{primary,fitA,fitB}`。
- `e131.py`：由 `rebase-027a/e123a.py` 改寫，唯讀匯入 `e094.py`；pipeline 與 presDisplay 覆寫照 e123a 原樣；pools 照 e123a 的建法；m1–m3 用 K1 對 K0，候選和基準共用同一組抽樣。
- `evaluate.mjs`：由 `rebase-027a/evaluate.mjs` 複製，候選換成 K0、K1。
- 子程序帶 `creationflags=subprocess.CREATE_NO_WINDOW`。

### 2.2 凍結後第一步
- 先只跑 K0，c0 過了才准跑 K1。c0 沒過就停下回報，不自己修。

## 3. 判定

### 硬條件（沒過就停下回報）
| 代號 | 內容 | 門檻 |
|---|---|---|
| c0 | K0 輸出的 ranking.csv | 和 `reports/card-0.2.7b/ranking.csv` 逐位元相同（sha256 361bcac6…1105） |
| c1 | `npm test` | 全過 |
| u1 | K1 的 ranking | 屬性欄（含 physique）和 K0 逐位元相同；只有 OVR 相關欄（ovr、predictedPer36、pred0、rank 等）可以變 |

### 對 K0（照 R-042 權衡，不機械否決）
- 門檻同 E-107／E-125：
  - (m1) Δρ_{N_W} 90% 區間下界 > −0.02
  - (m2) Δρ_{Q_W} 90% 區間下界 > −0.05
  - (m3) Δρ_{N_lin} 90% 區間下界 > −0.05
- 沒過：照實記錄是哪一條、差多少，交使用者；不准因此改人群、門檻、拿掉 heightInches 或其他屬性再試。

### G4（R-019）
- 前 20 名對 card 0.2.7b 換掉超過 3 人時，m1–m3 就當作 G4 重跑（A／B 分半樣本外，fitA／fitB）。

### 只報告
- K0 → K1 的 16→15 項 `valuePer10AttributePoints`（特別是 heightInches、rebound、help）與 form／ridge 有沒有變。
- evaluate.mjs 19 道門檻（card 0.2.7b 為 18/19）；2K27 ρ；前十長人（R-002 名單）。
- 具名球員 OVR 與名次（K0 → K1），並列身高、體重、physique：
  - Zion Williamson、Bam Adebayo、Julius Randle、Steven Adams、Jusuf Nurkić、Giannis Antetokounmpo、Joel Embiid、Nikola Jokić、Victor Wembanyama、Chet Holmgren、Evan Mobley、Jarrett Allen、Ivica Zubac、Shai Gilgeous-Alexander、Tyrese Maxey、Trae Young、Herbert Jones、Luguentz Dort
- OVR 前 20 名換了誰；OVR 名次移動 ≥ 10 名的人數與名單（MIN ≥ 1000）；依 physique 五等分的平均 OVR 變化；OVR 錨點 PR1／PR50／PR99。

### 選不選
- 使用者在 G5 決定採用或不採用。採用的不能稱盲測通過（L-026）。
- 採用時一併：名單頁 2025-26 拿掉 PHYS 欄（使用者原始要求）；新賽季頁要跟上另走 inseason 實驗（R-050）；模擬端 physique 另案。

## 4. 不准做的事
- 只動 physique 這一項：不拿掉 heightInches、不改其他屬性、不改 form／ridge 選法、人群、用人回歸、防守加成、tail、錨點算法。
- 不加第二個候選（例如同時拿掉身高、或只降權重）。要做另寫預註冊。
- 跑前跑後 sha256 唯讀核對（L-037）：
  - `reports/card-0.2.7b/`、`reports/card-0.2.7a/`、`reports/card-0.2.7/`
  - `reports/card-0.2.7+E123-tail-3pt-rim-pres/`（含 rebase-027a）
  - `reports/card-0.2.7+E125-pass-volume/`
  - `reports/card-0.2.5+E094-defense-ceiling/`
  - `reports/impact-rapm/`、`data/`
- 不碰 `reports/ovr-inseason-2026-27/`（E-128、E-129、E-130 執行中）。
- 不改 `src/`、live/、名單頁、狀態板、memory/（memory 由 lead 收工寫）。不部署、不 commit、不 push。

## 5. 回報
- CLAUDE.md 六段（`# 總評` 開頭）；Δρ、區間、閘門代號只寫在報告檔。
- 報告正文寫成 `report.txt`（L-055），附 `results.json`、`ranking.csv`（K0、K1 並列）、`diff-calibrate.txt`、唯讀核對 json。
- lead 寫 `report.md` 前，從 results.json 重算關鍵數字（L-065）。
