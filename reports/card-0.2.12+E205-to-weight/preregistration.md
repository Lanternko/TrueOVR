# E-205 預註冊：TO 的持球時間權重 0.5 → 0.25

- 日期：2026-11-02。使用者看 0.2.12 後：「AR 好像因為新的 TO 公式衝太前面了」→ lead 給三個方向 → 使用者「持球權重降低」（R-141）。
- 基準 K12：線上 card 0.2.12（`reports/card-0.2.12-tov/ranking.csv`，sha256 29ca32eb…＝E-202 KT）；建法＝E-202 KT 臂（`reports/card-0.2.10j+E202-to-possession/`）。
- 狀態：**已凍結**（2026-11-02）；sha256 見 `preregistration.sha256`（以 git HEAD 版 LF 計），之後不改，有錯寫 errata 給使用者核可。

## 0. 已揭露（lead 看過）
- 0.2.12 的 tovSkill＝0.5·z(−r)＋0.5·z(v)（r＝每持球分鐘失誤，方法 c 收縮；v＝持球分鐘/36）。
- E-202 結果：TO 對 2K27 Ball Handle ρ 0.08→0.79；F-143 19→0；tovSkill 與 creation 相關 0.72、與 pass 0.78、VIF 5.4（K0 1.5）；每 10 點 TO 約 2.3 OVR；OVR 對 EPM ρ 0.793→0.769。
- 池內（252 人）：Reaves r 第 15、v 第 13，TO 58→97，卡片 26→12（2K27 總評第 24）；Kevin Porter Jr. TO 47→97，32→17（2K 第 145）；Luka r 第 65、v 第 7；Cade r 42／v 2；Brunson r 2／v 1。
- lead 沒看過 0.25 權重下的 TO、係數、OVR 或名次。

## 1. 改動（只一個主臂）
| 臂 | 內容 |
|---|---|
| K12 | 線上 card 0.2.12（c0 先逐位元重現 ranking.csv） |
| **KW** | 只把合成權重改成 raw＝**0.75**·z(−r)＋**0.25**·z(v)，其他全同 K12；**全部係數重擬合**（R-115，同 E-202 流程、不設下限） |

- 0.25 是 0.5 與 0（純比率）的中點，事前定死、只跑這一臂，不掃描、不看完再換（L-026）。
- r、v、收縮、z 的池、0–99 轉換、topMissing 規則、其他 16 項與 gravity、用人層、OVR 映射全照 K12。

## 2. 判定
人群同 E-202（2025-26 MIN≥500）；bootstrap 球員層 2000 次，seed 20261102。phase0（只用 K12）先寫檔、commit，之後才跑 KW。

硬條件：
- **A（機制：重複計分降低）**：tovSkill 對其他能力值的 VIF ≤ 3.0（K12 5.4）。
- **保住 E-202**：tovSkill 對 2K27 Ball Handle Spearman KW − 0.0798（0.2.11 值）≥ 0.0879（E-202 的 MDE）。
- **沒弄壞**：c0 逐位元重現 K12；`npm test` 過；全體 OVR 對 2025-26 RAPM Spearman KW − K12 ≥ −2h（h＝phase0 用 K12 算的 90% 半寬）。

B（不擋採用）：F-143 TO 前 30 名中持球/36 低於池中位數的人數 ≤ 10。

只報告：
- tovSkill 與 creation、pass、gravity 相關；每 10 點 OVR 係數與 SE。
- 全體 OVR 對 2K27 OVR、EPM、薪水 ρ（K0＝0.2.11、K12、KW 三欄）；RAPM 分半兩半方向。
- 前 100 名移動 ≥10 名人數（KW 對 K12）、前 20 名進出。
- 球員表（0.2.11→K12→KW 的 TO、TO 名次、OVR、OVR 名次）：Austin Reaves、Kevin Porter Jr.、SGA、Brunson、Luka、Jokić、Cade、Harden、LaMelo Ball、Tyrese Maxey、Ty Jerome、Sam Hauser、Tim Hardaway Jr.、Luke Kornet、Jarrett Allen、Rudy Gobert。預期 Reaves、KPJ 往回掉，持球少的射手與中鋒不回到 TO 榜首；只報告、不當門檻。

## 3. 限制
- 只寫 `reports/card-0.2.12+E205-to-weight/`；其他目錄唯讀。不改 `src/`、`scripts/`、網站、live/。
- 採用後才另做上線（賽中凍結池 `tov-pool` 重算、網站說明「各半」改字、版號）。

## 4. 回報
CLAUDE.md 六段；白話講 Reaves、KPJ 回到哪、TO 榜換成誰；Δρ、區間只寫 `report.md`。
