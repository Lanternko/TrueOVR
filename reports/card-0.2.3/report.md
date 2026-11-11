# card 0.2.3 建卡報告（本機打包，未 commit、未部署）

card 0.2.3 = card 0.2.2 + E-075（用人當能力證據：分鐘、出賽率、年齡、練兵隊；DNP 與輪休分開）。使用者已於 R-040 裁定採用，G5 已過。
`ranking.csv` 欄位與順序同 card 0.2.2（含 foulDisc、presDisplay），582 人。由 `build_card_023.py` 產生。

## 組成
- 取自 E-075 `reports/card-0.2.2+E073-usage-evidence/ranking.csv`（sha256 `01aab81a…2215`，依姓名）：`rank`、`ovr`、`mpg`、`gRepl`。
- 取自 card 0.2.2（依姓名，582 人全對上、無重名）：其餘所有欄，含能力值（long…stamina、heightInches、creation、pressure）、`pr`、`ovr36`、`foulDisc`、`presDisplay`。
- 列序 = E-075 名次。
- 欄名對應：E-075 的 `mpg` 欄等於其 `mpgAvail`（建卡時逐人斷言相同），是可出賽修正後的場均，與 card 0.2.2 的 `mpg` 不同者 341 人。名單頁「MPG」欄顯示的是 MIN／出賽場數（`build_card_viewer.py` 原本做法），不受此欄影響。E-075 的附加欄（Ap、playRate、mpgAvail、age、p、predNew、Ap072、ovr022、rank022）不進 card 檔，仍在 E-075 資料夾。
- 驗證：能力值欄、pr、ovr36、foulDisc、presDisplay 等 27 欄與 card 0.2.2 逐人逐欄相同；rank、ovr、mpg、gRepl 與 E-075 ranking.csv 逐人相同。與 card 0.2.2 不同的欄：rank 575 人、ovr 575 人、mpg 341 人、gRepl 582 人。
- `ranking.csv` sha256 `933797d84f6c411b57f3caadcf26a898c203858b4808cf97b461717a9c3ebc64`。

## 關卡（引用 E-075 results.json，role-audit 重算成立）
| 關卡 | 結果 | 數字 |
|---|---|---|
| c0 開關全關重現 card 0.2.2 | 過 | sha256 相同，ovr 最大差 0.0 |
| c1 npm test | 過 | exit 0，57 passed |
| c2 A/B 半 RAPM 每場 Δρ（對 card 0.2.2） | 過 | −0.0005，90% [−0.0186, +0.0159]，下界 > −0.02（不變差，不是變準） |
| c3 evaluate.mjs | 過 | 18/19，card 0.2.2 也是 18/19 |
| c4 回歸預測 vs p 的 ρ | **不過（只報告）** | +0.0160，90% [−0.0002, +0.0321]，下界差 0 僅 0.0002；判定語意版，使用者仍裁定採用 |
| R1（只報告） | — | Sandfort 53.6／Drummond 57.7／Sheppard 60.4 |
| R2 | 過 | F 組中位 51.7 < MIN≥1000 PR10 52.1 |
| R3 | 過 | 隊內 MIN–OVR Spearman 30 隊中位 0.7469 ≥ 0.6412 |
| R4 | 過 | MIN<100 PR90 57.8 < 組中位 63.5 |

只報告：對 2K27 每場 ρ（evaluate.mjs，n=575）card 0.2.2 0.6810 → 0.7401；對全量 RAPM ρ 0.8289 → 0.7747（樣本內，R-007 不算證據）；ρDef 0.5667 → 0.4901。
稽核：`reports/card-0.2.2+E073-usage-evidence/audit/audit.md`，浮點最大差 2.7e-15，582 列 OVR 差 0.0。

## 與 card 0.2.2 前 20 名進出
進入：Rudy Gobert（25→16）、Anthony Davis（26→18）、Pascal Siakam（35→20）；退出：Victor Wembanyama、Cade Cunningham、Herbert Jones。
card 0.2.3 前 20：1 Jokić 106.0、2 SGA 102.9、3 White 101.0、4 Durant 99.1、5 Dončić 99.0、6 Leonard 98.5、7 Embiid 94.4、8 Giannis 94.2、9 Markkanen 93.0、10 Curry 92.3、11 Butler 92.0、12 Wagner 92.0、13 Maxey 90.5、14 Holmgren 90.3、15 Murray 89.5、16 Gobert 89.3、17 Amen Thompson 89.3、18 Davis 89.3、19 Mitchell 89.2、20 Siakam 89.1。
全體 OVR 對 card 0.2.2 最大改動 17.9。
