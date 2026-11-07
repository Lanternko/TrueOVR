# E-194 spec：切入型球員被高估從哪來（F-133 診斷，不佔 F-132 額度）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。只寫 `reports/F133-drive-scoring/`（含 `work/`、`logs/`）。

## 背景（已知，不要重查）
- 使用者裁定 R-130：切入與自主一定拆開，creation＝E-190 KJ 的 creationJ、drive＝drive_D（量 0.5＋效率 0.5）。要回答的是「怎麼給分合理」。
- E-190（`reports/card-0.2.10c+E190-creation-jumper/`）：KJ 三歷史原點合併 Spearman(drive, 殘差) −0.244，drive 係數每 10 點 ≈0。殘差＝pct(下季 RAPM net×wfun) − pct(卡 OVR)（`reports/E173-pressure-vs-rapm/e173_eval.py` 的 `resid`；E-190 的 `e190_eval.py` 已改成吃 KJ 卡，`s_data`／`s_stat` 照用）。負＝切入高的人卡片比下季 RAPM 高。
- 卡片是擬合 T6（`rapm-R.csv` 的 pooledNet，e173 `season_data` 已讀成 `t6net`）。

## 要做的事（全部用 KJ 卡：`work/KJ-<季>/`，三歷史原點 2022-23～2024-25，MIN≥500，人群同 E-190 a2；bootstrap 球員層 2000 次、seed 20261101，報 90% 區間）
先把這份 spec 的 D1–D3 寫成 `diag_plan.md`（含計算式）後才跑，跑完不改定義（L-026）。

- **D1 目標 vs 擬合**：殘差恰好拆成 e_target＝pct(net) − pct(t6net) 與 e_fit＝pct(t6net) − pct(ovr)。報 Spearman(drive, e_target)、Spearman(drive, e_fit)，三季各自＋合併。檢查 e_target＋e_fit＝e_net（差 <1e-9）。
- **D2 哪一欄多給分**：對 KJ 每個屬性 j，貢獻 c_j＝β_j ×（x_j − 人群平均）（β 用該原點卡擬合出來的係數，讀卡建置輸出，找不到就照 E-190 `coefs` 重算並寫明）。報每欄 Spearman(drive, c_j) 與「drive 前 25% 的人」c_j 平均 − 其他人平均（OVR 分），以及這些人在 e_fit 上的平均。列出給切入型球員最多分的前 3 欄。
- **D3 切入在現實值多少**：同一組欄（KJ 擬合用的 13 項＋help、heightInches）直接對「下季 RAPM net」做同樣形式的迴歸（同標準化、同權重），報 drive 每 10 點係數±bootstrap SE，並排 KJ 對 T6 的 drive 係數。另報只拿掉 drive 時對下季 RAPM 名次 ρ 的變化（看 drive 有沒有獨立資訊）。
- 球員表：E-190 預註冊 §2 那 15 人＋三季合併 drive 前 10 名，欄：drive、e_target、e_fit、前 3 欄的 c_j。

## 限制
- 不改 `src/`、`scripts/`、網站、memory、`reports/card-*`、`live/`（別的 session 在發版）。只讀 E-190 的 work/。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令加 timeout。輕量運算，本機即可。
- 不 commit、不 push。不提採用、不改卡。

## 驗收
- `diag_plan.md`、`diag.py`、`results.json`、`report.md` 存在；`python diag.py` 可重跑出同樣 results.json。
- D1 恆等式檢查通過；人數與 E-190 a2 相同（寫出每季 n）。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。白話回答三題：(1) 高估主要來自 T6 目標還是卡片擬合（各占幾成）；(2) 哪幾欄給切入型球員多給分；(3) 對下季 RAPM，切入每 10 點值多少、跟對 T6 的差多少。**要你決定的事**列 2–3 個給分方案（例如：drive 加符號限制、改目標權重、調某欄），只描述不推薦採用。Δρ、區間只寫 report.md。
