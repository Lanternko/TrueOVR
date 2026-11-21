# E-196 spec：三分係數共用＋得分產量（R-133）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。使用者 2026-11-01 裁定（R-133），本實驗量代價，**不發布、不改線上**。

## 背景
- Klay Thompson 在 card 0.2.10g（MIN≥500、342 人）卡排 314，T6 淨值 229、T6 進攻 108；進攻被低估約 1.5 分／36，防守大致對。
- 拆解：自主創造只扣 0.31；SF 三分係數每 10 分 0.28，SG 是 0.48；短、製造犯規、傳球各扣約 0.5。
- E-181：「被助攻得分／36」進迴歸係數約 0（F-119），所以得分產量的權重是使用者裁定的定義，不交給迴歸。

## 基底
card 0.2.10g（`reports/card-0.2.10g/`，`build_0210g.py`、`run_g.py`；用人層與 OVR 映射照 0.2.10g）。不要疊在 0.2.10i 上（另一個 session 進行中）；之後若採用再改疊到當時正式版。

## 臂（定義在此凍結，看結果後不得改，L-026）
- **G**：0.2.10g 原樣重現（開關全關），ranking.csv 必須與 `reports/card-0.2.10g/ranking.csv` 逐位元組相同。
- **S**：G＋三分（long）改全位置共用斜率，做法同 E-187 KAU 的傳球（`--dropInteract pass` → 對 long 做同樣的事；若現有旗標不支援 long，照同樣邏輯補，不改其他行為）。全部係數重擬合。
- **SP**：S＋creation 換成「得分產量」production：
  - 原始值 `prod = (PTS + 0.25 × SELF_FG_PTS) / MIN × 36 × (TS / lgTS)`
    - PTS＝全部得分（含罰球）；SELF_FG_PTS＝0.2.10g creation 分子所計入出手的投籃得分（同一套 creation 分類，不含接球投籃、吃餅）；TS＝該員同窗口真實命中率；lgTS＝同季聯盟 TS。
  - 窗口、季權重、池、to_attribute 全部照 0.2.10g 的 creation（四季滑動窗口、E-175 U 臂權重）。
  - production 用全位置共用斜率（不做位置交互）。
  - 係數下限：擬合後 production 每 1 分能力值的係數若低於 0.2.10g creation 的係數（同單位），改成固定在該下限（當 offset 重擬合其餘係數）。報告寫是否觸發下限。
- 開關用環境變數（例如 `E196_ARM=G|S|SP`）。

## 量什麼（只報告，不設通過門檻，R-131）
硬條件只有 G1（`npm test`）與「沒弄壞」（下列 A 線整體 ρ 退步超過雜訊 2 倍算弄壞）。
- **A 線（機制，樣本外）**：沿用 E-181 的歷史設定（`reports/E181-offball-attr/`：各季原點建卡 → 下一季 RAPM，2022-23～2024-25 原點）。對 G／S／SP 各報：無球組（E-181 Q 組定義）相對下季 RAPM 的平均低估（百分位點）、全體 Spearman ρ。注意 L-096 的符號問題，寫清楚正負號意義。
- **B 線（2025-26 卡，樣本內，只報告）**：
  - Klay、Hauser、Robinson、Kennard、Cam Johnson、Hachimura 等接球射手（long≥75 且 creation≤60）名次 G→S→SP；整群對 T6 的平均名次殘差。
  - 量大效率差的人（Clarkson、Monk、Sexton、Coby White、Jordan Poole 等，PTS/36 前 50 且 TS 低於聯盟）有沒有被抬太多。
  - 使用者原則抽查：列幾組「無球得分高 vs 自主得分少」的配對，看 SP 是否把前者排前面。
  - R-109 版號量：前 20 進出、前 100 移動 ≥10 名人數。
  - production 係數值、是否觸發下限、與 0.2.10g creation 係數對照。

## 限制
- 共用 checkout：開工 `git pull`；只 stage 自己的檔（`git add -f reports/card-0.2.10g+E196-production/` 與必要的 memory 條目），不要 `git add -A`（L-047）；push 前再 pull。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令 `</dev/null` 加 timeout。多季重建若超過本機輕量就到 5090（`ssh kojiek@100.97.181.15`）。
- 不改 `src/`、不改線上（OFFICIAL_CARD、CURRENT.json、season_nav、網站都不碰）。

## 交付
- `reports/card-0.2.10g+E196-production/`：程式、各臂 ranking.csv、results.json、report.md（查證細節、ρ、雜湊放這裡）。
- `memory/experiments.md` E-196 只改狀態欄（加日期）；有新發現寫 findings。
- 回覆用六段格式（CLAUDE.md「回報實驗結果」）：`# 總評` → **這次目標** → **進步了什麼** → **退步了什麼** → **直觀證據** → **要你決定的事**。
