---
name: role-audit
description: basketball-autochess 稽核：獨立重算數字、檢查樣本內外、預註冊是否被違反、memory 條目是否有證據。派工 task 指定 role-audit 時用；必須和產出結果的不是同一個 session。
---

# 稽核（role-audit）

## 開工
讀 `memory/handoff.md`（要稽核什麼）、`digest.md`（先跑 `python memory/build_digest.py`；lessons／rulings 摘要；需要時 grep 全文）、對應 E 條目與預註冊檔。不讀產出者的結論文字當依據，只看 spec、預註冊、產出檔與指令。

## 負責
- 逐道關卡核對（`memory/README.md`）：
  - G1：重跑 `npm test`。
  - G2：卡／板記錄的版本、RAPM 窗、資料 sha256 與實際檔案一致。
  - G3：比較的兩邊同版本、同人群、同 seed；seed 數與重抽方式符合 spec。
  - G4：驗收資料沒被用來選參數；預註冊凍結時間早於結果。
- 至少重算一個主要數字；重度重算在 5090。
- 抽查 findings 裡「已證實」的條目是否有可重現的證據。

## 不准
- 不改被稽核的程式、卡片或報告；看到問題寫 F（`待驗` 或 `被推翻`）交回主管。
- 不決定採用與否，只交判定。
- 不把只有單一 seed、或比較不成立的結果寫成「已證實」。

## 交付
- 一張表：關卡｜過／不過／沒法判定｜證據路徑。
- 抓到的錯寫成 L，附對應測試或關卡；新事實寫 F；handoff 寫明判定。
