# 球隊頁：上季缺陣球員補卡 spec

lead：Claude Code App，2026-11-02。使用者裁定「兩個都做」之一：補 Kyrie 等人的卡。

## 問題
- `scripts/team_ratings_sim.mjs` 的 `profile()` 遇到引擎卡（`loadX()` 的 `x.players`，2025-26 卡）裡沒有的人，一律用聯盟平均 profile `xAvg.profiles[2]`，再加 live − 卡片聯盟平均的 delta。
- live ranking（`data/_inseason_build/*/ranking.csv`）也沒有這些人，所以頁面上的 OVR 是空的，delta 也沒有。
- 今天 `team-ratings.json` 的 `missingProfiles` 有 33 人，其中不是新秀、而且有輪替分鐘的至少有：Kyrie Irving（DAL 25.8 分鐘）、Damian Lillard（POR 30 分鐘）、Tyrese Haliburton（IND）、Fred VanVleet（HOU）、Trey Lyles、Georges Niang、Mario Hezonja。這些人都被當成平均球員。

## 要做的
1. **找底卡**：
   - 對 `missingProfiles` 裡「不是本季新秀」的人，找 repo 內最近一份有他的卡或能力值資料。可能的來源：
     - 歷史卡片目錄 `reports/card-*`；
     - E-208 2024-25 用的能力值 `reports/E208-team-rating/inputs-2425.json`、`pprime-day0-2425.json`；
     - 歷史賽季 builder。
   - 先列出候選來源和每個來源涵蓋的人，再選「最接近 2025-26 開季」的那份。
   - 欄位要能轉成引擎的 profile（與 `x.players` 同欄位）。
   - 不做年齡衰退調整，不看結果挑來源（L-026）。
   - 選擇規則寫進程式註解。
2. **用底卡建 profile**：
   - 這些人改用底卡建 profile。
   - 有 live 列的（本季有出場）再加 live − 底卡的 delta，做法同其他人；沒有就直接用底卡。
   - 新秀照舊。
   - 找不到任何底卡的人保持平均 profile，列進 log 和 `missingProfiles`。
3. **頁面**：
   - 這些人的 OVR 顯示底卡 OVR，加小標「上季前卡」（或「24-25 卡」，照實際來源年份）。
   - 頁尾說明補一句。
4. **回報需含**：
   - 補卡名單：人、隊、來源、OVR。
   - 補卡前後 Net 變最多的 5 隊。
   - 特別列 DAL、POR、IND、HOU 的 Net 與預測勝場，舊→新。
5. **POR 異常（只調查，不修）**：
   - 現象：上一輪發現 POR 拿掉 Morant、Sharpe 後 Net 從 −1.2 升到 +4.1。
   - 補卡後再看一次是否仍成立，用單人替換列出各主力的邊際值。
   - 若仍是「加人反而變差」，寫成一段描述交給 lead。另一個實驗 `reports/star-overlap/` 正在查球星重疊遞減，不要碰那個目錄。
6. **測試**：
   - `test/team_ratings_gate.py` 加：缺卡非新秀用底卡；新秀照舊；找不到底卡時退回平均。
   - `npm test` 要過。
7. **發布**：重建、發 gh-pages、截一張桌面圖（展開 DAL），存 `reports/E208-team-rating/site-shots/teams-v4-dal.png`。

## 限制
- 不改 `src/`、引擎係數、正式卡片、凍結檔、E-208 回測檔。
- 不碰 `reports/star-overlap/`，那是另一個正在跑的派工。
- 共用工作樹：
  - 禁止 `git stash`／`checkout`／`reset`／`restore`（L-115）。
  - 只 stage 自己的檔；`reports/` 用 `git add -f`。
- 不用 `HANDOFF_OK=1`；pre-commit 擋 handoff 照 E-214 做法。
- 子程序不閃黑窗；每日耗時 ≤5 分鐘。
- 截圖要看就縮到 ≤800px 寬再讀。
- `memory/experiments.md` 追加新 ID（檔尾最大號 +1）。

## 回報
不是實驗結果，不用六段格式。回報第 4、5 點的內容，加上 commit／gh-pages hash、偏離 spec 之處。
