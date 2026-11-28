"""0.2.10d 拆項（只報告用，不進卡）：tailonly＝只換 long／creation 窗口（MPG 不覆寫）；mpgonly＝只換預測 MPG 窗口（long／creation 用 0.2.10a）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10d/ablate.py tailonly|mpgonly   → 輸出 work-<名>/KAU-2025-26/out/ranking.csv"""
import os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
m = sys.argv[1]
env = dict(os.environ, E185_WORK=str(HERE / f'work-{m}'))
if m == 'tailonly':
    env['E185_MPG'] = ''
else:
    env['E185_TAIL_U'] = str(ROOT / 'reports/card-0.2.10a/tail-U.csv')
for step in ('cards', 'run'):
    r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(HERE / 'build.py'), step, 'KAU', '2025-26'], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, env=env, timeout=3000)
    print(m, step, r.returncode)
    if r.returncode:
        print(r.stderr[-500:]); sys.exit(1)
