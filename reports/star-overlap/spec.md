# 球星重疊遞減驗證 spec（role-model，診斷，不改引擎）

lead：Claude Code App，2026-11-02。使用者裁定「兩個都做」：補缺卡（另一份工作）＋本實驗。

## 起因（App 粗測，不含在證據內）
費城今日輪替（Maxey、Brown、Embiid、LeBron＋隊友），其他人換成聯盟平均球員，200 seed 對平均隊：
- 單放一人增加的淨勝分：Embiid +7.7、Maxey +6.3、Brown +4.1、LeBron +2.9，加總 +20.9；
- 四人同時上場只 +7.2，約三分之二的價值消失。
- 費城實際 6-1，評分卻是 −0.7。
- 疑問：引擎對「多個高用量／創造者同場」的遞減是不是扣太重？
- 腳本參考：`reports/star-overlap/phi3.mjs`（＋`phi_d.json`）（沿用 `reports/E120-foul-defense/winimp-core-e120.mjs` 的 `loadX/makeRunner` 與 `reports/player-impact-v29/benchmark.mjs` 的 `options`，引擎 sim 0.1.4）。

## 問題
模型的「球星重疊損失」大的隊，實際淨效率是否系統性高於模型預測？若是，代表引擎遞減扣太重。

## 設計（跑前寫預註冊並 commit `preregistration.md`＋`.sha256`，之後不得改；L-026）
- **季與名單**：用 E-208 已有的設定，不重做能力值：
  - 2024-25：P″ 能力值。
  - 2025-26：P′ 能力值。
  - 兩季都用 (c) 分鐘規則，每隊整季的代表輪替＝整季各場 (c) 分鐘的平均，前 10 人、240 分鐘。
  - 檔案在 `reports/E208-team-rating/`（`inputs*.json`、`minutes-*.json`、`lib.mjs`、`lib2425.mjs`、`analysis-*.json`）。先讀 `report.md`、`report-2024-25.md` 弄清楚怎麼組隊。
- **球星**：每隊代表輪替中 ≥20 分鐘、依卡片 OVR 前 4 名。
- **單人增益**：其餘 9 人換成聯盟平均 profile（`xAvg.profiles[2]`），分鐘不變；對平均隊打，算淨勝分，再減掉全平均隊的淨勝分。
- **四人同場增益**：四人都在、其餘換平均，同樣扣全平均隊。
- **重疊損失 OL**＝單人增益加總 − 四人同場增益。另算比例 OLr＝OL ÷ 單人增益加總。
- **殘差 R**：
  - 模型隊淨效率＝代表輪替對平均隊的淨勝分，扣聯盟 30 隊平均。
  - 實際淨效率取 `data/defense-source/advanced-teams.json` 該季 NET，同樣扣聯盟平均。
  - R＝實際 − 模型。
- **主檢定 H1**：Spearman(OL, R) > 0。
  - 通過條件：2024-25 的 ρ>0 且 90% bootstrap CI（以隊重抽，5000 次）不含 0；同時 2025-26 的 ρ 也 >0（2025-26 能力值部分污染，只當同向確認）。
  - 次要：兩季合併，OL 前 10 隊的平均 R 減後 10 隊的平均 R。
  - 也用 OLr 報同樣數字，但只列為描述，不當主檢定。
- **機制描述**（不當檢定）：
  - 四人中「創造者／高用量」的人數與 OL 的關係；
  - 引擎裡造成遞減的位置，例如創造者邊際遞減、球權分配、spacing，列出程式位置與機制說明。
- seed：每個組合 ≥200（換主客），同一隊各變體共用 seed（G3）。

## 運算
多 seed 放 5090：`ssh kojiek@100.97.181.15`，長指令加 `</dev/null` 與 timeout。本機只跑輕量。

## 限制
- 不改 `src/`、引擎係數、卡片、E-208 凍結檔與既有結果檔；新檔全放 `reports/star-overlap/`。
- 共用工作樹：
  - 另一個 session 正在改 `scripts/team_ratings_daily.py`、`scripts/build_teams_page.py`、`test/team_ratings_gate.py`，不要碰這些檔。
  - 禁止 `git stash`／`checkout`／`reset`／`restore`（L-115）。
  - 只 stage 自己的檔；`reports/` 被 .gitignore，用 `git add -f`。
- 不用 `HANDOFF_OK=1`；pre-commit 擋 handoff 時照 E-214 做法（HEAD 版改一行＋update-index），不動工作樹別人的版本。
- 記錄 G2：引擎版本、輸入 sha256。

## 收尾
- `report.md`：查證過程、CI、雜湊寫這裡。
- `memory/experiments.md` 追加新 ID（檔尾最大號 +1）；重要事實寫 F 條目；被抓到的錯寫 lesson。
- `npm test` 過；commit＋push。
- 回覆用 CLAUDE.md「回報實驗結果」六段格式（第一行 `# 總評`）。附例子：OL 最大的 5 隊（隊名、季、OL、模型 vs 實際淨效率）。若 H1 通過，在「要你決定的事」提出修正方向選項，但這次不實作。
