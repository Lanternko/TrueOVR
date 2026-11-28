# E-184 修正 A1（2026-11-01，在任何 a≠1 的模擬之前凍結）

## 為什麼要修
- 預註冊 §0 要改的式子（`src/defense_fourth_game.js:334` 的 `scale = (FTA/FGA)/foulProfileMeans[z]`）在 sim 0.1.2 的 harness 裡不會執行。
- harness（E-140／E-166 同一條鏈）的投籃犯規走 `reports/player-impact-v5/model.mjs` 的 `observedFoulInputs`：對每個球員解一個倍率，讓「這個人的出手區域與命中率」下的期望 FTA/FGA 剛好等於他自己的輸入 r。
- 所以假設寫的「籃下被重複計入」在 harness 裡不成立：harness 已經逐人對準輸入。§1 的斜率檢查仍然有意義（防守者 β、bonus 罰球等其他路徑可能讓模擬放大或縮小）。

## 已看到的
- 只有 a=1（=B2）在校正 seed 20261120、20261121 的斜率：1.063（150 人，FGA≥300），不在 [0.95, 1.05]，依 §1 不停，繼續校正 a。沒有跑過任何 a≠1，沒有看任何判定 seed。
- a=1 的 harness 對 E-166 `rr-k.jsonl` seed 20261036 435 場逐場相同。

## 改成
- `foulDrawExponent` a 改作用在 `observedFoulInputs` 的目標：r → L·(r/L)^a，L = `opt.leagueFTR`（0.2636）。只影響投籃犯規抽樣；持球層的 `pFoul` 照舊用 r。不讀亂數。
- 意義和原 §0 相同：a<1 把造犯規的個人差距往聯盟平均收；a=1 和 B2 逐位元相同。
- 不另外加 clamp（a≤1 時 r/L 只會更接近 1）。
- 其他全部照原預註冊：候選 a ∈ {1, 0.85, 0.7, 0.55, 0.4}、選斜率最接近 1.00、相同選大的；重解 c、pace；§2 判定與門檻不變。
- 實作：`engine-e184.mjs`（v53 engine 複本加一組 game-source 替換）、`core184.mjs`。
