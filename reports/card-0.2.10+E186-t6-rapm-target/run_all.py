"""依序對每個 (臂, 原點) 跑 e186_build.py cards -> run，4 個並行；記錄 logs/。用法：python -I -B -X utf8 run_all.py <臂:原點> ..."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def one(job):
    arm, t = job.split(':')
    res = []
    for mode in ('cards', 'run'):
        t0 = time.time()
        r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(HERE / 'e186_build.py'), mode, arm, t], cwd=ROOT, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=7000)
        (HERE / 'logs' / f'{mode}-{arm}-{t}.log').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
        res.append((mode, r.returncode, round(time.time() - t0)))
        print(job, res[-1], flush=True)
        if r.returncode:
            break
    return job, res


if __name__ == '__main__':
    with ThreadPoolExecutor(4) as ex:
        out = list(ex.map(one, sys.argv[1:]))
    print('DONE', out)
