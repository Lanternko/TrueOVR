"""role-audit：用凍結的 e290_eval.py 原封重跑，輸出寫到 audit 目錄（不覆寫 E-290 的 results.json），再逐數比對。
用法（repo root）：python -I -B -X utf8 reports/audit-0.2.14-cand/rerun_e290.py"""
import importlib.util, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'reports/E290-reb-bonus-0213a'
DST = Path(__file__).resolve().parent / 'e290_rerun'
DST.mkdir(exist_ok=True)
for f in ('preregistration.md', 'preregistration.sha256'):
    shutil.copyfile(SRC / f, DST / f)
s = importlib.util.spec_from_file_location('e290', SRC / 'e290_eval.py')
m = importlib.util.module_from_spec(s); sys.modules['e290'] = m; s.loader.exec_module(m)
m.HERE = DST
m.main()
a = json.loads((SRC / 'results.json').read_text(encoding='utf-8')); b = json.loads((DST / 'results.json').read_text(encoding='utf-8'))
worst = 0.0
def walk(x, y, path):
    global worst
    if isinstance(x, dict):
        for k in x: walk(x[k], y.get(k), path + '/' + k)
    elif isinstance(x, list):
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, f'{path}[{i}]')
    elif isinstance(x, float):
        worst = max(worst, abs(x - y))
    elif x != y:
        print('MISMATCH', path, x, y)
walk(a, b, '')
print('max abs float diff vs committed results.json =', worst)
