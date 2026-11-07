# E-140 修正 A1（2026-10-31，任何模擬結果產出前）

- 原因：預註冊 §0 說基準是主 checkout 現行引擎（sim 0.1.1，含 83ceb63 刪體力、af79a0a doubleThreat 拿掉體格項），但 k0、k1 與報告項卻沿用 E-122 在舊引擎（fd39bcd＋E-120／E-122 未提交改動）跑出的 `rr-off.jsonl`、`rr-off2.jsonl`、`checkpoint-off.jsonl`。兩者不可能逐場相同（lead 寫規格的錯，L-085）。
- 修正時已知：執行者在現行引擎上試跑一次 β 關互打，harness 傳體力選項直接報錯，沒有任何比分輸出。沒有任何 E-140 數字被看到。
- 改動（其他條文全不變）：
  1. 基準一律是主 checkout HEAD（af79a0a 起）的 `src/`，加上 E-120／E-122 兩個預設關選項與新的 `foulBaseShift`。harness 拿掉體力相關選項，其他照 E-122。
  2. k0 改為：β 關、c=0、pace=1 時，(a) 和不帶 E-120／E-122／foulBaseShift 改動的 HEAD 引擎在判定 seed 前 2 個 seed 逐場相同；(b) `npm test` 過。
  3. 關閉版對照全部在現行引擎重跑：判定 seed 20261028–059 的 `rr-off`、雜訊底 seed 20261060–091 的 `rr-off2`、WinImp 關閉版（同 E-122 c3 的 N、seed、人群）。k1 與報告項都改對這些新檔比。
  4. 運算量：互打 32（on）＋32（off）＋32（off2）＋校正 16×(1＋迭代)；WinImp on／off 各一次。
