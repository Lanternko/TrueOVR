"""E-129 §2.5 live 示範：以不同 C_PARAM 呼叫 live/run_c4_live.py 的 main（輸出寫到絕對路徑，不寫 live/）。
用法：python -I -B -X utf8 live_run_e129.py <C_PARAM> <絕對輸出資料夾>"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import run_c4_live as L  # noqa: E402
L.C_PARAM = float(sys.argv[1])
sys.argv = [sys.argv[0], sys.argv[2]]
raise SystemExit(L.main())
