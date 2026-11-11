"""card 0.2.10g（E-192）：用人層四季窗口。KAU 流程重跑（run KAU 2025-26），部件卡沿用 card-0.2.10d/work/base-KAU-2025-26（用人層不影響部件卡，唯讀）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10g/run_g.py real|selfcheck
  real      ：E192_USAGE＝usage-window-c82.csv（make_usage_window.py 產），工作目錄 work/
  selfcheck ：不給 E192_USAGE（窗口關），工作目錄 work-selfcheck/；ranking.csv 必須和 card-0.2.10d/ranking.csv 逐位元相同
內部：e162_build.run 會以 `<本檔> pipe <tag>` 再起子行程（環境變數 RUN_G_W 帶工作目錄）。"""
import importlib.util, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'reports/card-0.2.10d/work/base-KAU-2025-26'
mode = sys.argv[1]
if mode in ('real', 'selfcheck'):
    os.environ['RUN_G_W'] = str(HERE / ('work' if mode == 'real' else 'work-selfcheck'))
    if mode == 'real':
        os.environ['E192_USAGE'] = str(HERE / 'usage-window-c82.csv')
    else:
        os.environ.pop('E192_USAGE', None)
if 'E185_MPG' not in os.environ:
    os.environ['E185_MPG'] = str(ROOT / 'reports/card-0.2.12/mpg-c82.csv')
W = Path(os.environ['RUN_G_W'])
os.environ.setdefault('E142_WORK', str(W))
spec = importlib.util.spec_from_file_location('e162g', HERE / 'e162_build.py')
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
E.W = W
E.bdir = lambda arm, t: BASE
E.__file__ = str(Path(__file__).resolve())
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if mode == 'pipe':
    sys.exit(E.pipe(sys.argv[2]))
sys.exit(E.run('KAU', '2025-26'))
