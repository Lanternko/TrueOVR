"""E-062 回測入口：python -I backtest_e062.py <off|C4s|C4r>；輸出 v5/pathA/backtest-e062/<mode>/。
每個模式一個獨立 process（避免快取混用）。其餘流程完全是 backtest_pathA.main()。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e062_switch as SW  # noqa: E402
import backtest_pathA as BP  # noqa: E402

mode = sys.argv[1]
SW.install(mode)
BP.OUT = BP.PA.PATHA / 'backtest-e062' / mode
t = time.time()
rc = BP.main()
print('runtime_s', round(time.time() - t, 1), flush=True)
raise SystemExit(rc)
