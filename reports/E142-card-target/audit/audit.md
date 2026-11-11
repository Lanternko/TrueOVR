# E-142 稽核（role-audit）

稽核者：派工子 session（非產出者）。腳本 `recompute.py` 只照 preregistration + errata-1/2/3 文字寫，不 import、不複製 phase1_eval.py；
但我寫腳本前已讀過 phase1_eval.py，所以「獨立」是程式碼獨立，不是盲讀（見下方限制）。

## 1 雜湊與時間線
| 檔 | 記錄的 sha256 前綴 | 實算前綴 | 結果 |
|---|---|---|---|
| preregistration.md | dc1624bb8eab | dc1624bb8eab | 符合 |
| errata-1.md | de5c389c279 | de5c389c279 | 符合 |
| errata-2.md | d20e0a251eceab | d20e0a251eceab | 符合 |
| errata-3.md | （無 .sha256 檔；commit 56f0435 訊息寫 a34ce181…） | a34ce181356c | 符合訊息 |
| 2k-merged-e142.csv | cb40f9a0c14e | cb40f9a0c14e | 符合 |

指令：`sha256sum`、`cat *.sha256`、`git log --format='%h %ad' --date=iso -- <file>`。
時間：errata-2 5152f9d 14:02；暫時版輸出 37e55e9 14:16；errata-3 56f0435 15:25；正式版（phase1.json、report.md）768ee5d 23:27。
errata-3 早於任何正式結果檔（phase1.json 首次加入就是 768ee5d）。errata-3 沒有獨立 .sha256 檔，只靠 commit 訊息，建議補。

## 2 獨立重算
`python -I recompute.py --out main.json`（種子 20261031、2000 抽）。`compare.py` 比對 phase1.json：
- 4 季 × 5 候選 × (C, M_sal, M_2k, M_rapm, 各 n) 全部相同，最大絕對差 0（超出容許 0.002 的零個）。
- 三折 T*：2022-23=T6、2023-24=T6、2024-25=T4；全折合併 T6。相同。
- 樣本外差：C +0.0202、sal +0.0373、2K +0.0368、RAPM −0.0325。相同。
- bootstrap 下界 0.00174、上界 0.03869，小數點後 16 位相同。判定 adopt。
- 沒有任何對不上的地方。完全相同本身也代表：我的讀法和 phase1_eval.py 在所有細節上一致，沒找到解讀分歧。

errata 文字 vs phase1_eval.py 讀法逐項：
- 人群（ranking MIN≥500、對 player-games MIN≥500 以 norm(name) 配對、五張卡取交集、百分位在 player-games 全人群上算）：我照文字做，結果相同。若百分位改在評估人群內算（敏感度 c），結論不變。
- 缺項重分配（分母只加有值的項）：相同。
- 人頭權重（C 與差值以 n 加權）：相同。
- 文字有模糊處：「續約年」靠 tx 事件推年資、被截斷合約的假設（只有 ext 事件者歸 1 年）屬 errata-1 沒寫死的實作選擇。我實作了同一假設才對上；換假設我沒試，這是未覆蓋的缺口。

## 3 樣本內外
fold k 的 T*_k 只用另外兩季的 C（見 main.json folds.*.train 與 trainC）；2025-26 完全不進判定（RAPM 項不存在，只報告）。成立。

## 4 盲測
- 暫時版（舊 2K、單季訓練、無模擬）判定 no_improvement，下界 −0.0118，RAPM 項不過。
- errata-3 的檔頭寫「lead 與使用者都沒看過任何候選數字」。commit 順序：暫時版輸出 14:16 → errata-3 15:25，間隔 69 分鐘，我無法用 git 證明沒人看過暫時版數字（commit 訊息只說「provisional outputs」）。
- 風險：暫時版不過之後才改成三折，改動方向（更多訓練資料、較穩）有學理支持，但剛好把 no_improvement 變成下界 0.0017 的 adopt。這是分叉路徑疑慮：無法排除，也無法證實。
- 對照：三折本身不依賴暫時版數字就能被推導（把單季訓練的雜訊問題換成輪流），且我用原 errata-2 的單季設計重算（見 5b）確實判不過，所以結論對「設計選擇」敏感。

## 5 敏感度（只報告）
| 變體 | T*（折） | 樣本外 C 差 | sal | 2K | RAPM | 下界 | 判定 |
|---|---|---|---|---|---|---|---|
| 主（正式） | T6/T6/T4 | +0.0202 | +0.0373 | +0.0368 | −0.0325 | +0.0017 | adopt |
| a 舊 2K 檔 | T6/T6/T4 | +0.0182 | +0.0373 | +0.0333 | −0.0325 | +0.0001 | 四項都過，但下界貼 0 |
| b errata-2 單季訓練（2022-23 訓練，測 23-24、24-25） | T4/T4 | +0.0131 | +0.0560 | +0.0233 | −0.0522 | −0.0085 | no_improvement（下界不過，RAPM 超出 −0.05） |
| c 百分位改在評估人群內算 | T6/T6/T4 | +0.0217 | +0.0373 | +0.0368 | −0.0325 | +0.0036 | adopt |

結論：主結論在 a、c 不翻，但 a 的下界只剩 0.0001，幾乎是邊緣；b 翻成不過。adopt 依賴 errata-3 的三折設計。

## 6 2025-26 主卡只換 RAPM 半
- `build_card_t.py` c0 路徑：只呼叫 `swap_rapm` 改寫 `split/rapm-A.csv`、`rapm-B.csv`（fitA／fitB 的 `--rapm`），其他輸入（mpgDir、dnp、rapm1Dir、target 表）指向 T0 的 c0。
- 逐鍵比較 `phase1-work/T0` 與 `T6` 的 `c0-pipe.json`、`c0-e094cfg.json`：只差輸出路徑。`build-c0.json`：差 swap（T0→custom）、part_card／ranking sha、split 列數；`part_equal_E131_K1` 與 `pass` 在 T6 為 False 是預期（卡已換，不再等於 E-131 K1）。
- 沒有證據顯示 B12 目標表那一半被動到。限制：我沒有重跑建卡，只看設定與紀錄。

## 限制
- 我讀過 phase1_eval.py 後才寫腳本，所以重算逐位相同只證明「文字讀法一致、無實作錯字」，不證明規格本身沒爭議。
- 沒重跑建卡（5090 工作）；ranking.csv 視為給定輸入。
- 沒做 npm test（本任務不是 G1）。
