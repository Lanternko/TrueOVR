"""E-198：自 reports/card-0.2.10i/run_i.py 複本；模式改 KAU|KG，部件卡＝work/A/base-<模式>-2025-26（build_kg.py cards），工作目錄 work/B-<模式>/。
以下原說明。
card 0.2.10i 步驟 4b：用人層＋KAU 管線（同 card-0.2.10g/run_g.py real，e162_build 用 card-0.2.10g 的同一份），只把部件卡改成本版重擬合的
work/A-<mode>/base-KAU-2025-26（步驟 4a：card-0.2.10d/build.py cards＋run，E185_TAIL_U＝本版 tail-U.csv；c0 用 card-0.2.12/tail-U.csv）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/run_i.py c0|real
  c0  ：工作目錄 work/B-c0/；ranking.csv 必須和 card-0.2.10g/work/KAU-2025-26/out/ranking.csv 逐位元相同
  real：工作目錄 work/B-real/
內部：e162_build.run 會以 `<本檔> pipe <tag>` 再起子行程（環境變數 RUN_I_MODE 帶模式）。"""
import importlib.util, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
G = ROOT / 'reports/card-0.2.10g'
mode = sys.argv[1]
if mode in ('KAU', 'KG'):
    os.environ['RUN_I_MODE'] = mode
M = os.environ['RUN_I_MODE']
BASE = HERE / f'work/A/base-{M}-2025-26'
os.environ['E192_USAGE'] = str(G / 'usage-window-c82.csv')
if 'E185_MPG' not in os.environ:
    os.environ['E185_MPG'] = str(ROOT / 'reports/card-0.2.12/mpg-c82.csv')
W = HERE / f'work/B-{M}'
os.environ.setdefault('E142_WORK', str(W))
spec = importlib.util.spec_from_file_location('e162i', G / 'e162_build.py')
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
E.W = W
E.bdir = lambda arm, t: BASE
E.__file__ = str(Path(__file__).resolve())
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if mode == 'pipe':
    sys.exit(E.pipe(sys.argv[2]))
sys.exit(E.run('KAU', '2025-26'))
