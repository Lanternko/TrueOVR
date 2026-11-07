"""card 0.2.10d 建卡：build.py cards KAU -> run KAU（2025-26）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10d/run_all.py real|selfcheck
  real      ：預設輸入（card-0.2.12 的 tail-U.csv、mpg-c82.csv），工作目錄 work/
  selfcheck ：輸入換成 0.2.10a 的 tail-U.csv、不覆寫 MPG，工作目錄 work-selfcheck/；ranking.csv 必須和 card-0.2.10c 逐位元相同"""
import os, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
mode = sys.argv[1]
env = dict(os.environ)
if mode == 'selfcheck':
    env.update(E185_TAIL_U=str(ROOT / 'reports/card-0.2.10a/tail-U.csv'), E185_MPG='', E185_WORK=str(HERE / 'work-selfcheck'))
(HERE / 'logs').mkdir(exist_ok=True)
for step in ('cards', 'run'):
    t0 = time.time()
    r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(HERE / 'build.py'), step, 'KAU', '2025-26'], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, env=env, timeout=7000)
    (HERE / 'logs' / f'{step}-{mode}.log').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
    print(mode, step, r.returncode, round(time.time() - t0), flush=True)
    if r.returncode:
        sys.exit(r.returncode)
