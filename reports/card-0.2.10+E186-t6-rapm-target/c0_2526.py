"""E-186 c0（2025-26）：重跑 card 0.2.10 的建卡鏈（run_parts U -> use_layer frozen），輸出到 work/c0-2526，比對 reports/card-0.2.10/ranking.csv 的 sha256。"""
import hashlib, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C10 = ROOT / 'reports/card-0.2.10'
PY = [sys.executable, '-I', '-X', 'utf8']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(*a):
    r = subprocess.run(PY + [str(x) for x in a], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=3000)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


run(HERE / 'c0_run_parts.py', 'U', C10 / 'tail-U.csv')
# run_parts 寫 HERE/work/U/cards（本資料夾）
out = HERE / 'work/c0-2526'
run(HERE / 'c0_use_layer.py', 'frozen', HERE / 'work/U/cards', out, C10 / 'frozen.json')
res = {'got': sha(out / 'ranking.csv'), 'want': sha(C10 / 'ranking.csv')}
res['same'] = res['got'] == res['want']
(HERE / 'work/c0-2526.json').write_text(json.dumps(res), encoding='utf-8')
print(res)
