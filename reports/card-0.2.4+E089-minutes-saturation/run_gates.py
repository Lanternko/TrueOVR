import subprocess, sys, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
F = subprocess.CREATE_NO_WINDOW
with open(HERE / 'npm-test.log', 'wb') as f:
    r = subprocess.run('npm test', cwd=ROOT, shell=True, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=F, env=env, timeout=1500)
(HERE / 'npm-test.exit').write_text(str(r.returncode) + '\n', encoding='utf-8')
with open(HERE / 'evaluate.log', 'wb') as f:
    r2 = subprocess.run(['node', str(HERE / 'evaluate.mjs')], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=F, env=env, timeout=1500)
(HERE / 'evaluate.exit').write_text(str(r2.returncode) + '\n', encoding='utf-8')
print(r.returncode, r2.returncode)
