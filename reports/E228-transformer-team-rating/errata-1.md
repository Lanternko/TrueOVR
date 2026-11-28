# E-228 errata-1（2026-11-04，凍結後、看結果前）
`eval_t.py`（已凍結）第 9 行 `from e223_lib import *` 把第 5 行的 `HERE` 蓋成 E-223 目錄，導致 2025-26 守門去 E-223 找 `FREEZE.txt` 而拒絕執行，相對路徑也會解析到 E-223。
處理：不改 `eval_t.py`；新增 `run_eval_2526.py`，讀原始碼後只把守門條件換成「E-228 的 FREEZE.txt 存在」（先 assert 存在），`--pred`／`--out` 改傳絕對路徑。評估公式、資料、bootstrap 完全沒動。判定不受影響，不需重核可。
