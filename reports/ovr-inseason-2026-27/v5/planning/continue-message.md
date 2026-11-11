# DS 儲值後續接用訊息（dispatch_continue 20261027-144318-0d826f，backend ds-local，cwd D:\Projects\CODING\basketball-autochess）

上一輪因為 DeepSeek 餘額不足（402）中斷，`preregistration-v5.md` 還沒寫完。現在檔案已存在，裡面是 App 寫的 §R（RAPM 季集，使用者已定案）。

1. 先讀 `reports/ovr-inseason-2026-27/preregistration-v5.md` 全文和 `v4/curves/gap/pipeline-README.md`。§R 原文一字不改；如果發現事實錯誤，寫進〈未決問題〉。
2. 依原任務 spec 補完〈待補章節〉的 1–5 項，寫在同一個檔案的 §R 之後。所有回測設計都要建立在 §R.2、§R.3 的新起點鏈和新答案卡之上。
3. 查證 §R.7 第 1 條：`v4/tools/build_prior_v4.py` 是否沒有把被交易球員的分鐘數跨隊加總。附 grep 或行號作為證據，結果寫回 §R.7 第 1 條的「查證結果」。
4. 已經存在的 `v5/planning/{inventory.py, inventory.json, bootstrap_v4.py, bootstrap-v4.json, probe/}` 是上一輪留下的檔案，可以沿用，但要先重跑確認輸出一致。
5. 只寫 spec，不實作；不改 v4 和既有工具。
