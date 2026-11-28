# 總評

**4/5 大致達成 有部分退步**

診斷乾淨地回答了問題：資料齊（303/303 人、覆蓋率 100%）、規則先定好、只跑一次、沒改過程式。但答案和使用者的預期方向相反（見「要你決定的事」），且逐球紀錄只涵蓋約 94% 的出手，所以不給 5。

**這次目標**

量「出手能力 SM＝(命中數 − Σ逐球 xFG)/(FGA+k)」能不能解釋卡片 0.2.10 OVR 對半季 RAPM 的殘差（使用者認為投難球還投得進的人沒被卡片獎勵）。診斷、不改卡片、不調參數。

**進步了什麼**（診斷成立的部分）

1. **SM 是可量的真訊號**：兩半季 SM 的加權相關 r＝0.556（285 人），收縮常數 k＝243 次出手。不是雜訊。
2. **主斜率有明確方向**：每 +1 SD 的 SM，RAPM 殘差 **−0.228**（每 100 回合）；90% 區間 **[−0.317, −0.142]**，整段在 0 以下。兩個方向各自都是負的（A→B −0.118、B→A −0.338）。
3. **預定判讀結論：「卡片高估難球命中者」**（hi90 < 0）。MDE＝0.134，點估計比 MDE 大，所以不是檢定力不足的偶然。
4. **換算**：SM 第 90 百分位的人（約 +1.3 SD），卡片比 RAPM 實際多給約 **0.30**（每 100 回合）。
5. **加 Gravity 當共變數幾乎不動**：n＝224、斜率 −0.249 → −0.227。SM 與 Gravity 的 Spearman 為 0.38，但不是 Gravity 在撐這個結果。

**退步了什麼**（疑慮與限制）

1. **方向與預期相反**：不是「卡片漏獎勵難球命中者」，而是「這群人卡片反而給多了」。可能的原因（未檢定）：卡片的投籃與得分輸入已含命中率，連同運氣一起給了分，而 RAPM 沒有同等回報。這只是推測，這次診斷分不出來。
2. **偏保守的限制**：卡片 0.2.10 的 OVR 是用含全季 RAPM 的目標擬合的，殘差被壓向 0；真實效果可能比 −0.228 更大，但方向不太會變。
3. **xFG 已含防守者位置**，所以 SM 衡量的是「扣掉防守者位置後仍多投進的部分」，不等於「難球」本身。
4. **逐球紀錄涵蓋不全**：shotqualityvideologs 逐球加總的 FGA 為 177,242，球隊 box score 為 188,305（94.1%）；FGM 85,799 對 89,558（95.8%）。約六千場、每場少 1–2 球（最多 38 球）。SM 是用同一份逐球紀錄算分子與分母，內部一致，但漏掉的球是不是隨機沒驗證。
5. **14 筆缺漏**（19,303 筆中，API 持續回 500，已重試）：14 位球員各缺 1 場——Jamal Murray、Bruce Brown、Cameron Johnson、Christian Braun、Taylor Hendricks、GG Jackson、Olivier-Maxence Prosper、Cam Spencer、Jaylen Wells、Walter Clayton Jr.、Spencer Jones、Cedric Coward、Tim Hardaway Jr.、Nikola Jokić。每人少不到 1 場的出手，player_game.csv 覆蓋率仍是 303/303（≥95% 驗收通過）。
6. 另有 153 個 FGA＝0 場次的 error 檔（球員沒出手，API 本來就回 500），不算缺漏，不進 player_game.csv。

**直觀證據**

SM 前 15 名與卡片名次（SM 第一名是 Jokić；FGA 為全季逐球加總）：

| SM 名次 | 球員 | 比 xFG 多命中（每 100 球） | 卡片名次 |
|---|---|---|---|
| 1 | Nikola Jokić | +11.9 | 7 |
| 2 | Kevin Durant | +9.8 | 17 |
| 3 | Luka Dončić | +8.7 | 5 |
| **4** | **Shai Gilgeous-Alexander** | **+8.8** | **1** |
| 5 | Luke Kennard | +10.4 | 173 |
| 6 | Jakob Poeltl | +11.1 | 116 |
| 7 | Zion Williamson | +8.0 | 26 |
| 8 | Stephen Curry | +7.9 | 18 |
| 9 | Jamal Murray | +6.8 | 14 |
| 10 | Cam Spencer | +7.9 | 93 |
| 11 | Donovan Mitchell | +6.4 | 6 |
| 12 | DeMar DeRozan | +6.7 | 78 |
| 13 | Ryan Kalkbrenner | +10.0 | 295 |
| 14 | Kawhi Leonard | +6.2 | 3 |
| 15 | Bobby Portis Jr. | +6.7 | 171 |

- SGA：SM 第 4（303 人），卡片本來就第 1，所以他的案例沒有「被漏獎勵」，卡片已經把他放最前面。
- SM 與卡片 OVR 的 Spearman＝0.44；與 long／mid／short 分項為 0.59／0.39／0.25，就是說卡片的外線分項已經吃進了大部分 SM（也和上面「卡片給多了」一致）。
- 前 15 名裡，Kennard、Poeltl、Kalkbrenner、Portis 的卡片名次在 170 以後，但他們出手數少（272–718），收縮後仍在前段。

**要你決定的事**

1. 「低估難球命中者」這個假設在資料上不成立，反方向才成立。要不要停掉 F-126 的「加獎勵」方向？
2. 若還想追：下一步可以是（a）驗證卡片高估是不是來自卡片輸入已含命中率（拆 SM 為 long／mid／short 各自的斜率）；（b）用沒看過的季重複（G4 樣本外），因為這次只有一季、且是分半的樣本內診斷；（c）先確認逐球紀錄漏掉的 6% 是否隨機。
3. 這是診斷，沒有改卡片；要不要把「SM 作為負向修正」開成預註冊實驗，由你決定。

---

## 附：預定判讀規則（照抄）

lo90 > 0 →「低估成立」；hi90 < 0 →「卡片高估難球命中者」；區間含 0 →「未偵測到」，並附 MDE。

## 附：方法備註

- 球員池：card-0.2.10 ranking MIN≥900，303 人；playerId 對應照 F-125 noise.py（live/2026-10-31 ranking，缺的用 `data/season-source/player-games.json` 的名字補）。
- 場次來源：`data/season-source/player-games.json`（2025-26 leaguegamelog），FGA>0 的場次共 19,303 筆。stats.nba.com 對 curl／Python requests 逾時，Node fetch 可通，故抓取用 Node（`fetch_videologs.mjs`）。
- half：`int(gameId)%2==0` → A，否則 B。SM 收縮用兩半 FGA≥100 的 285 人、權重＝兩半 FGA 調和平均；k＝半季平均 FGA 304.6 × (1−r)/r。
- 主統計量：AB（SM 用 A 半、殘差用 B 半）與 BA 的平均；球員層 bootstrap 2000 次（seed 20261101），兩方向同一組抽樣；MDE＝2.49 × SE（SE＝0.0536）。斜率單位：每 1 SD SM 的 RAPM 殘差／100 回合。
- 程式修改：`diag0.py` 與 `build_player_game.py` 在看結果前就寫好，之後沒有改動；`diag0.py` 只跑了一次最終資料。
- 逐球資料中，`shots` 欄與 shotList 筆數有 1,549 場不一致（多為差 1），一律以 shotList 逐球加總為準。
- 重現：repo 根目錄 `python reports/F126-shot-difficulty/diag0/build_player_game.py`，再 `python reports/F126-shot-difficulty/diag0/diag0.py`（raw/ 不進 git）。
