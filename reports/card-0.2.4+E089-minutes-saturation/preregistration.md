# E-089 預註冊：卡片分鐘權重改成飽和曲線（R-043、R-047）

- 日期：2026-10-29。來源：R-043（分鐘要算、不能太重、邊際遞減），R-047（使用者選定飽和曲線，尺度 15）。
- 版本：`card 0.2.4+E089`（R-018）。基準：正式卡 card 0.2.4（R-044，`reports/card-0.2.4/ranking.csv`，sha256 af37ce25169c64b5e747afe066b42747c187b5d2ef20ffb3cc454e3ba95b7203）。
- git HEAD（寫本檔時）：d8715cb。角色：實作 role-card；判讀 lead；稽核 role-audit。本機可跑（bootstrap 2000 次，輕量）。
- 狀態：凍結（2026-10-29，使用者核可「你自己原地做」）。sha256 記在 `preregistration.sha256` 與 `memory/experiments.md` E-089。

## 0. 背景與假設

- card 0.2.4 的每場值 g = (pred − r) × mpg / 36，對分鐘是線性（`reports/card-0.2.3+E084-current-target/e084.py` 第 406、457 行）。違反 R-043。
  - 分鐘另外以 L = log(1 + mpg) 進用人回歸，當能力證據（R-040）。這部分**不動**。
- 這次是改價值定義，不是調參數。曲線和尺度由使用者在看任何結果前選定（R-047）：

  W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))，W(36) = 1。

  g_new = (pred − r) × W(mpg)

- 沒有可調參數：15 和 36 都寫死。替補水準 r、OVR 錨點 PR1／PR50／PR99、two_segment 都照原式從新的 g 分布重算。
- 預期（只是方向，不當判定）：低分鐘高效率的人（Caruso 型）上升；分鐘撐起名次的人（Dyson 型）下降；pred 低於替補水準的低分鐘球員，g 會比原本更負。
- 量尺衝突（R-043）：當季與四季量尺都是「RAPM × 另一半 MPG」，對分鐘線性，用它們評估遞減權重必然吃虧。所以本檔的主量尺改用**同一個價值定義**的答案：另一半 RAPM × W(另一半 MPG)。線性量尺只防大幅退步。

## 1. lead 已看過的（揭露）

- card 0.2.4 全部欄位，包括 Caruso（mpg 17.90，第 103 名）、Dyson Daniels（mpg 33.15，第 17 名）。
- card 0.2.4 的 mpg 分布：<10 分 187 人、10–15 72、15–20 70、20–25 70、25–30 96、≥30 87（共 582）。
- 只算過曲線本身在固定分鐘的值（5／10／…／36 分，和上述兩人的 mpg），沒有算過任何候選的 g、OVR、名次或量尺數字。
- E-084 全部數字（`results.json`、`evaluation.json`、`audit/audit.md`）。

## 2. 改動

- 複製 `reports/card-0.2.3+E084-current-target/e084.py` 為本目錄的 `e089.py`。
  - 目標固定 `season`（card 0.2.4 的設定）。
  - 加開關 `--minutes {linear,sat15}`，預設 `linear`。`linear` 必須和 card 0.2.4 完全相同。
- `sat15` 只改兩處，把 `mp / 36` 換成 `W(mp)`：
  - 半季評估的候選 g_c（原第 406 行）。
  - 卡片 `card_from()` 的 g（原第 457 行）。
  - W 用的分鐘和原式一樣（`sf['mp']`，也就是 ranking 的 mpg 欄）。
- 其他全部不動：用人回歸的特徵（含 L = log(1 + mpg)）、係數、人群、POOL_MIN、PR10 替補水準的算法、two_segment、年齡項、k、輸出欄位。
- 卡片組裝照 `reports/card-0.2.4/build_card_024.py` 的方式，衍生欄（rank、ovr、mpg、gRepl）取新值，其餘取 card 0.2.4。
- 單元檢查（寫進程式，跑時印出）：W(0) = 0、W(36) = 1、W(5) = 0.31175 ± 1e-5、W(20) = 0.80987 ± 1e-5。

## 3. 評估

- 程式與定義沿用 E-084 的 `evaluate` 段（E-081 的定義），候選和基準共用同一組抽樣：
  - 基準：`e089.py --minutes linear` 的半季 g_c（等於 card 0.2.4）。
  - 候選：`e089.py --minutes sat15` 的半季 g_c。
  - 人群 E-075 `pools[dn]`；球員 bootstrap 2000 次，seed 1，master 聯集；兩方向平均。
- 四個答案（另一半）：
  - N_W：rapm1 net × W(mpg_ev)。**主量尺**，和新定義一致。
  - Q_W：pooledNet × W(mpg_ev)。
  - N_lin：rapm1 net × mpg_ev（E-084 的答案 N）。
  - Q_lin：pooledNet × mpg_ev（E-084 的答案 Q）。
- Δρ_X = ρ_X(候選) − ρ_X(基準)，報點估計與 90% 區間。

## 4. 判定

硬條件只放「有修到」和「沒弄壞」（R-042）。門檻在看結果前定死。

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | `--minutes linear` 重現 | `ranking.csv` sha256 = af37ce25…7203（或共同欄位最大差 < 1e-9）。不過就停下修程式，不看任何誤差數字 |
| (c1) | G1 | `npm test` 過 |
| (u) | 單元檢查 | §2 的四個 W 值全對 |
| (m1) | 新定義下樣本外不變差 | Δρ_{N_W} 的 90% 區間下界 > −0.02 |
| (m2) | 線性當季量尺沒有大幅退步 | Δρ_{N_lin} 的 90% 區間下界 > −0.05 |
| (m3) | 四季量尺沒有大幅退步 | Δρ_{Q_W} 的 90% 區間下界 > −0.05 |

- 全過：記為「通過」，交 role-audit 重算，再交使用者 G5。版號由使用者定（R-019）。
- (c0)、(c1)、(u) 任一沒過：停下修程式。
- (m1)–(m3) 沒過：照 R-042 權衡，記錄是哪一條、差多少，交使用者裁定，lead 不自己改門檻或曲線。
- 不准看過結果後改曲線、尺度、分鐘定義、人群、門檻（L-026）。

## 5. 只報告

- Δρ_{Q_lin}；evaluate 19 閘的結果（carusoGate 和 big14of16 特別列出；參考名次是 max(2K27, 四季合併 RAPM)，對新定義只報告，R-042）。
- Caruso、Dyson Daniels 的 OVR、名次、mpg，和 card 0.2.4 並排。
- 前 20 名；OVR 變動最大的 20 人（上升、下降各列）。
- mpg 分組（<10、10–15、15–20、20–25、25–30、≥30）的 OVR 中位數和人數，和 card 0.2.4 比。
- mpg < 10 的人進前 150 名的人數，和 card 0.2.4 比。
- MIN ≥ 1000 球員中 ρ(mpg, OVR) 與 ρ(pred, OVR)，和 card 0.2.4 比。
- 新的替補水準 r 與錨點 PR1／PR50／PR99。

## 6. 不准

- 唯讀，用 sha256 檢查（L-037）：
  - `reports/card-0.2.4/`
  - `reports/card-0.2.3+E084-current-target/`
  - `reports/card-0.2.3+E081-age-residual/`
  - `reports/card-0.2.2+E073-usage-evidence/`
  - `reports/card-0.2.3/`
  - `reports/impact-rapm/`
  - `data/`
- 新程式和新輸出只放 `reports/card-0.2.4+E089-minutes-saturation/`，附上和 `e084.py` 的 diff。
- 不改模擬（`src/`）、屬性、賽中 OVR（R-028；賽中先驗仍是 card 0.2.2）。
- 不碰 memory/、live/、gh-pages、狀態板。
- 不部署、不 commit、不 push。
- 子程序帶 `creationflags=subprocess.CREATE_NO_WINDOW`。
