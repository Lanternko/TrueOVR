# 總評
**2/5 主目標達成 但是有副作用**

（預註冊 `preregistration.md`，凍結 sha256 344f860a…263c；基準 B6 = card 0.2.6 原樣重建；不 commit、不發布。）

**這次目標**
把你選的 UL 防守加成（防守越好加越多、近期加權的防守）搬到正式卡 card 0.2.6 上，確認整體排名沒變差，而且 Wagner 仍排在 Wembanyama 後面。

**進步了什麼**
- Wembanyama #3 → **#2**，防守加成從 0 變 3.34，OVR 101.7 → 103.7。
- Wagner 維持 #7，排在 Wemby 後面 5 名，R-061 成立。他的加成 1.20 → 2.07，但大部分被 RAPM 名次上限切掉，名次沒動。
- 防守好的人往上：
  - Derrick White #8 → #4
  - Kawhi #6 → #5、Chet #9 → #8
  - Jimmy Butler #18 → #15、Mobley #25 → #22、Caruso #36 → #32
  - Queta #23 → #13，進前 20
- 樣本外一致性三項都過門檻，其中兩項的區間整個在 0 以上，跟 RAPM 對得更好一點。
- `npm test` 57 項全過。組卡流程完整重現了 card 0.2.6 和 E-106 的結果，位元完全相同。

**退步了什麼**
- **19 道門檻掉到 18/19**：「16 個長人至少 14 個不輸 2K」只剩 13 個。card 0.2.6 原本是 15 個。
  - Embiid #17 → #24，2K 參考 17.5。
  - Koloko #354 → #442：近期防守資料不夠，加成 1.47 整個沒了。
  - Anthony Davis #38 → #40，參考 32，原本就沒過。
- 進攻型、防守普通的人往下：
  - Luka #4 → **#9**、Jokić #2 → #3
  - Durant #21 → #27、Embiid 掉出前 20
  - Cade #12 → #14、Herbert Jones #13 → #16
  - Curry #32 → #34、Edwards #35 → #38、LeBron #67 → #73
- 和 2K 稍遠一點：相關 0.737 → 0.736，名次差平均 78.1 → 78.5。
- OVR 頂端被壓縮：頂端的人大多拿到加成，99 分位的錨點跟著往上。SGA 107.3 → 104.0，541 人的 OVR 數字變了。名次照排，但名單頁上的分數會跟現在不一樣。
- 我事前預期 Wagner 會升到 #3–#5，這點沒發生：0.2.6 的 Wagner 本來就已經頂到 RAPM 名次上限。

**直觀證據**

| 球員 | 2K27 | RAPM 淨值 | RAPM 防守 | 0.2.6 | UL6 | 加成 0.2.6 → UL6 |
|---|---|---|---|---|---|---|
| SGA | 2 | 2 | 23 | 1 | 1 | 0 → 2.21 |
| **Wembanyama** | 2 | 5 | 1 | 3 | **2** | 0 → 3.34 |
| Jokić | 2 | 1 | 76 | 2 | 3 | 0 → 0.68 |
| Derrick White | 70.5 | 6 | 4 | 8 | 4 | 1.96 → 2.99 |
| Kawhi | 11.5 | 4 | 59 | 6 | 5 | 0 → 1.32 |
| Giannis | 5 | 3 | 52 | 5 | 6 | 0 → 0.80 |
| **Wagner** | 47.5 | 7 | 6 | 7 | **7** | 1.20 → 2.07 |
| Chet | 38 | 8 | 10 | 9 | 8 | 0 → 2.23 |
| **Luka** | 5 | 17 | 246 | 4 | **9** | 0 → 0.05 |
| Cade | 8 | 58 | 160 | 12 | 14 | 0 → 0.63 |
| Butler | 47.5 | 12 | 78 | 18 | 15 | 0 → 1.84 |
| **Embiid** | 17.5 | 10 | 11 | 17 | **24** | 0.80 → 0.69 |
| Durant | 11.5 | 39 | 176 | 21 | 27 | 0 → 0.04 |
| Curry | 11.5 | 27 | 423 | 32 | 34 | 0 → 0 |
| Tatum | 11.5 | 44 | 161 | 33 | 33 | 0.07 → 0.10 |

（RAPM 名次是四季合併、回合數 ≥ 5000 的人裡排；2K 同分取平均名次。完整名單在 `ranking.csv`。）

- 前 20 名只換了 2 人：Queta、Ryan Rollins 進，Knueppel、Embiid 出。
- 名次移動 ≥ 10 名的有 82 人，前 300 名裡 48 人。

**要你決定的事**
1. UL 要不要進正式卡？
   - (a) 採用，發 **card 0.2.7**（PATCH，不算盲測）：Wemby #2、防守型球員上升；代價是 18/19、Luka #9、Embiid #24、OVR 頂端壓縮。發名單頁要你另外說。
   - (b) 不採用，維持 card 0.2.6。
   - (c) 先查 Embiid 和 Koloko 為什麼掉（近期防守資料少、回合門檻），再決定。
2. 如果選 (a)：另一個 session 正在把新賽季頁對齊 0.2.6（inseason E-107）。0.2.7 上線後新賽季頁也要再跟一次（R-050）。

---

## 細節

### 硬條件（全過）
- c0a 過：B6 的 P1 三張卡（primary／fitA／fitB）和 E-101 的卡逐位元相同，比了 pred、ranking、pergame-main、pergame-repl、pergame-summary 五個檔，summary.json 內容也相同。
- c0b 過：B6 經 e094 pipeline 的 ranking sha256 = a0a81ecb…6c91，和 `reports/card-0.2.6/ranking.csv` 相同。
- c0c 過：本目錄 calibrate-wing 不帶 `--tailSource`、用 E-106 UL 參數，和 E-106 `cards/UL/primary` 逐位元相同。
- c1：`npm test` 57 passed、0 failed。
- u1、f2 過：三張卡各抽 10 人，差 < 1e-9。

### 對 B6（R-042 權衡）
| | 點估計 | 90% 區間 | 門檻 |
|---|---|---|---|
| m1 Δρ_N_W | +0.0059 | [+0.0009, +0.0111] | 下界 > −0.02 ✓ |
| m2 Δρ_Q_W | +0.0016 | [−0.0026, +0.0059] | 下界 > −0.05 ✓ |
| m3 Δρ_N_lin | +0.0063 | [+0.0011, +0.0116] | 下界 > −0.05 ✓ |
| r1' | Wagner 7、Wemby 2 | | Wagner > Wemby ✓ |

- R-019：前 20 名換 2 人（≤ 3），不強制重跑 G4；m1–m3 本身就是 A／B 分半的樣本外。依 L-026，UL 是看過 E-106 結果才選的，這不算盲測證據。
- evaluate.mjs：
  - card 0.2.6 與 B6：19/19，ρ2K 0.7371、ρRAPM 0.7802。
  - UL6：18/19，ρ2K 0.7359、ρRAPM 0.7793、ρDef 0.5369 → 0.5322。
  - 沒過的是 big14of16，13/16：Embiid 24（參考 17.5）、Koloko 442（參考 428）、Davis 40（參考 32）。
  - wingGuard 13/14 仍過，Ajay Mitchell 85 對參考 81。
  - 前十長人：Wembanyama、Jokić、Giannis、Chet、Markkanen，和 0.2.6 是同五人。
- OVR 錨點（per-game g）：PR1 −0.813 → −0.831、PR50 1.243 → 1.252、PR99 3.511 → 4.120。

### 只報告
- 屬性分前 4% 拿到加成的人（UL6 primary，封頂前）：Wembanyama 3.34、Chet 2.23、SGA 2.20、Butler 1.84、Kawhi 1.32、Mobley 1.11、Paul George 1.06、Scottie Barnes 0.96、Giannis 0.80、Jokić 0.68、Cade 0.63、Davis 0.43、Luka 0.05、Durant 0.04。
- 加成為正的人：B6 180、UL6 214。被 RAPM 名次封頂切到的人：B6 112、UL6 118，Wagner、Cade 在 UL6 都被切到。
- 和 2K 名次差最大的 10 人兩版幾乎相同（Keyonte George 484、Isaiah Collier 444…），都是新秀或低分鐘的人，跟這次的改動無關。

### lead 事前預期對照
- Wemby #1–#2：對（#2）。
- Wagner #3–#5：錯，他維持 #7。
- Cade 大致不動：對（#12 → #14）。
- Curry、Luka、Durant 往下：對。
- 頂端壓縮：對。
- 前 20 名換超過 3 人：錯，只換 2 人。

### 唯讀核對
- impact-rapm、E079、card-0.2.6、本目錄以外的 card-0.2.5*：跑前跑後 822 檔 sha256 全部相同，沒有新增也沒有消失。

### 檔案
- `phase2.json`、`ranking.csv`（B6、UL6 並列，含 2K27、RAPM 淨值、防守名次）、`cards/{B6,UL6,c0c}/`、`work/{B6,UL6}/ranking.csv`、`evaluation.json`、`evaluate.log`、`npm-test.log`、`diff-calibrate.txt`、`ro_before.json`、`ro_after.json`。
- 編號：另一個 session 同日也用了 E-107（新賽季頁對齊 0.2.6，`reports/ovr-inseason-2026-27/e107-card026/`）。本條先寫、預註冊已用此號凍結，不改號；引用時寫「E-107 防守 UL」。
