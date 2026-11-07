# E-107 預註冊：把 UL 防守加成搬到正式卡 card 0.2.6 上

- 日期：2026-10-30。
- 來源：使用者 2026-10-30 回「b UL」（R-061）：
  - 防守加成選 UL。
  - R-058 放寬：Wagner 只要不贏 Wembanyama。
  - lead 說明「UL 是在 card 0.2.5 基準上跑的，正式卡已是 0.2.6，要重做才能定版」後，使用者回「先寫預註冊」。
- 版本：`card 0.2.6+E107`（R-018）。卡片層基準 B6 = 正式卡 card 0.2.6（`reports/card-0.2.6/ranking.csv`，sha256 a0a81ecb…6c91）。
- git HEAD（寫本檔時）：22073d9。
- 角色：實作 role-card（執行者照派工路由決定）；判讀 lead；稽核 role-audit。
- 狀態：**凍結**（2026-10-30，使用者「凍結開跑」；sha256 在 `preregistration.sha256`）。凍結後才准跑任何 UL6 卡。

## 0. 背景與假設

### card 0.2.6 的防守加成
- 卡片 = card 0.2.5 的公式，加上 E-101 改過的能力值（`--tailSource attributes-e101.csv`）。
- 防守加成仍是 card 0.2.5 的 taper：
  - 屬性分百分位 ≥ 96 的人，加成歸 0。
  - 防守值 D 是四季等權的 pooledD。
- 在 0.2.6 裡：Wembanyama #3、Wagner #7、Cade #12、Curry #32、SGA #1。

### UL 的做法（E-106）
- 加成 = max(0, centeredD)，不打折。
- D 改用 E-104 的逐場線性遞減版（`def-L-*.csv`），回合門檻乘 1/2。
- RAPM 名次封頂（H1）、align、gamma 都不動。

### 本實驗
- 只把 UL 這兩個開關加到 card 0.2.6 的組卡流程上，其他一字不改。

### 假設
- H1：UL6 對 B6，名次整體一致性（m1–m3）不明顯變差。
- H2：Wembanyama 分數與名次上升，而且 Wagner 仍排在 Wembanyama 後面（R-061）。

### lead 事前預期（寫在看結果之前）
- 照 E-106 的經驗，預期以下幾點：
  - Wembanyama 升到 #1–#2。
  - Wagner 也往上，落在 #3–#5 附近。
  - Cade 大致不動（RAPM 名次封頂，F-049）。
  - Curry、Luka、Durant 往下。
  - 頂端 OVR 壓縮。
- 前 20 名很可能換掉超過 3 人（R-019：要重跑 G4，見 §3）。

## 1. lead 已看過的（揭露）
- card 0.2.5、E-094、E-101（含 0.2.6 名次）、E-104、E-106 全部結果，包括 E-106 UL 的名次與 Δρ。
- 使用者是看過 E-106 結果才選 UL（L-026）。所以本實驗的 m1–m3 不是盲測：資料季、RAPM 分半和 E-106 相同。
- **沒有算過** card 0.2.6 能力值配 UL 的任何 pred、名次或 Δρ。

## 2. 做法

### 2.1 程式（新目錄 `reports/card-0.2.6+E107-defense-UL/`）
- `calibrate-wing.py`：
  - 由 `reports/card-0.2.5+E106-defense-bonus-monotone/calibrate-wing.py` 複製。
  - 從 `reports/card-0.2.5+E101-crossera/calibrate-wing.py` 原樣搬入 E-090 的 `--tailSource`：`TAIL_SOURCE`、`TAIL_ATTRS`、`attach_tail()`、`load()` 最後的呼叫、argv 解析。
  - 其餘一字不改。diff 存成 `diff-calibrate.txt`，對兩個來源各一份。
- `run_cards.py`：
  - 由 E-106 的 `run_cards.py` 複製。
  - COMMON／P1／PART 一字不改，兩組都加 `--tailSource reports/card-0.2.5+E101-crossera/attributes-e101.csv`。
- `e107.py`：
  - 由 E-106 的 `e106.py` 複製，組卡 pipeline 與 m1–m3 照舊唯讀匯入 `reports/card-0.2.5+E094-defense-ceiling/e094.py`（`set_card_dir`、`pipeline(BASE_OPTS, pools, 'season')`、`e089_eval`）。
  - 基準換成 B6，r1 換成 r1'（§3），只報告的具名名單加上 2K27、RAPM 名次欄。
- `evaluate.mjs`：由 E-106 的複製，候選換成 E107-B6、E107-UL6。

### 2.2 組別（各 primary／fitA／fitB 三張卡）
| 組 | 能力值 | 防守 D | 打折 |
|---|---|---|---|
| `B6`（基準） | E-101（`--tailSource`） | 四季等權 pooledD | taper（card 0.2.6 原樣） |
| `UL6` | E-101（`--tailSource`） | E-104 `def-L-<part>.csv`，`--defPossFactor 0.5` | none |

- UL6 的開關 = B6 的參數再加 `--bonusShape none --defWindow season --defRapm reports/card-0.2.5+E104-defense-pergame-decay/def-L-<part>.csv --defPossFactor 0.5`。
- 不加第三組。

## 3. 判定

### 硬條件（沒過就停下回報，不自己修）
| 代號 | 內容 | 門檻 |
|---|---|---|
| c0a | `B6` 的 P1 三張卡和 `reports/card-0.2.5+E101-crossera/cards/e101/P1/{primary,fitA,fitB}` 比對：`pred.csv`、`ranking.csv`、`pergame-main.csv`、`pergame-repl.csv`、`pergame-summary.json` | 逐位元相同；summary.json 內容相同 |
| c0b | `B6` 經 e094 pipeline 輸出的 ranking | 和 `reports/card-0.2.6/ranking.csv` 逐位元相同（sha256 a0a81ecb…6c91） |
| c0c | 本目錄 calibrate-wing 不帶 `--tailSource`，用 E-106 UL primary 的參數重跑 | 和 E-106 `cards/UL/primary` 逐位元相同（合併沒弄壞 E-106 的路徑） |
| c1 | `npm test` | 全過 |
| u1 | 同 E-106：UL6 三張卡各抽 10 人，RAPM 封頂前的加成 = 門檻內 max(0, centeredD)，門檻外為 0 | 差 < 1e-9 |
| f2 | 同 E-106：UL6 讀 def-L csv | 差 < 1e-9 |

- c0b 沒過（c0a 過）代表 e094 pipeline 和 E-101 chain 組最後名次的方式有差。這時停下，寫 errata 給使用者，不自己改 pipeline。

### 對 B6（照 R-042 權衡，不機械否決）
- (m1)–(m3) 同 E-106：
  - Δρ_{N_W} 下界 > −0.02
  - Δρ_{Q_W} 下界 > −0.05
  - Δρ_{N_lin} 下界 > −0.05
- (r1') R-061：primary 卡 Wagner 名次要低於 Wembanyama。沒過照實記錄差幾名，交使用者；不因此調參數再試。
- evaluate.mjs 19 道門檻（含前十長人）照跑，只報告。card 0.2.6 是 19/19。

### G4 與版號（R-019）
- 前 20 名對 card 0.2.6 換掉超過 3 人時，m1–m3 就當作 G4 重跑：A／B 分半樣本外。
- 依 §1，UL 是看過同一批資料後選的，m1–m3 變好也不算盲測證據。所以採用時版號一律 PATCH（card 0.2.7），除非使用者另有裁定。
- 新賽季先驗（inseason 0.2.5a）不跟著改；要跟上另走 inseason 實驗（R-050）。

### 只報告
- 具名球員名次與 OVR（B6 → UL6），並列 2K27 名次、四季 RAPM 淨值名次、防守名次：
  - Wembanyama、SGA、Jokić、Luka、Giannis、Kawhi、Chet、Wagner、Cade、Derrick White
  - Curry、Durant、Embiid、Caruso、Butler、Herbert Jones、Tatum、LeBron、Gobert、Davis、Brunson、Edwards、Mobley
- 前 20 名換了誰（進／出）。名次移動 ≥ 10 名的人數與名單（全部、前 300 名）。
- 屬性分前 4%、加成 > 0 的人與加成值。被 RAPM 名次封頂切到的人數。
- OVR 錨點 p1／p50／p99 變化。對 2K27 的 ρ、名次差平均、差最大 10 人。

### 選不選
- 使用者在 G5 決定採用（發 card 0.2.7）或不採用。採用的不能稱盲測通過（L-026）。

## 4. 不准做的事
- 不改這些：centeredD 公式（0.75、位置平均）、回合門檻、RAPM 名次封頂、align、gamma、E-101 能力值、def-L csv。
- 不加第三組。
- 不動以下目錄，跑前跑後做 sha256 唯讀核對（同 E-106）：
  - `reports/impact-rapm/`
  - `reports/card-0.2.6/`
  - 本目錄以外所有 `reports/card-0.2.5*`（含 E-094、E-101、E-104、E-106）
- 不發布名單頁、不 commit。採用後由使用者說了才做。
- 計算量輕（E-106 每張卡約 1 秒），本機跑；所有子程序帶 `CREATE_NO_WINDOW`。

## 5. 回報
- CLAUDE.md 六段；區間、閘門代號放第 6 段之後。
- 寫 `report.md`、`phase2.json`、`ranking.csv`（B6、UL6 並列，含 2K27、RAPM 名次欄）。
- 收工更新：
  - `memory/experiments.md` 的 E-107
  - `memory/handoff.md` 自己那行
  - 新事實寫 F
