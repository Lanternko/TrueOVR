"""E-095 稽核：唯讀檔 sha256 抽查，不用執行方的 readonly_sha.py。
做法：(1) 隨機抽 12 個 + 指定幾個重點檔，對 readonly-sha-before.json；(2) 用自己的 glob 全量重算一次對 before；
(3) 再用 git 的 blob hash 比對（git hash-object）對沒被改過的 tracked 檔交叉驗證。
用法：python -I audit_readonly_sha.py"""
import glob
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
os.chdir(ROOT)
BASE = 'reports/ovr-inseason-2026-27/e095-card025-minutes/'
before = json.load(open(BASE + 'readonly-sha-before.json', encoding='utf-8'))
after = json.load(open(BASE + 'readonly-sha-after.json', encoding='utf-8'))
print('before/after entries', len(before), len(after), 'identical', before == after)

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
items = sorted(before.items())
random.seed(7)
pick = random.sample(items, 12) + [i for i in items if i[0].endswith(('constants.js', 'backtest_e064.py', 'card-0.2.5/ranking.csv',
                                                                       'anchors.json', 'usage-2025-26-card024.json', 'verdict.json'))]
bad = 0
for k, v in pick:
    ok = sha(k) == v
    bad += not ok
    print('OK ' if ok else 'BAD', k)
print('spot-check bad =', bad, 'of', len(pick))

pats = ['src/**/*', 'reports/card-0.2.4/**/*', 'reports/card-0.2.5/**/*', 'reports/card-0.2.4+E089-minutes-saturation/**/*',
        'reports/ovr-inseason-2026-27/v5/tools/*', 'reports/ovr-inseason-2026-27/v5/pathA/backtest-e064/*',
        'reports/card-0.2.3+E084-current-target/results.json', 'reports/ovr-inseason-2026-27/live/usage-2025-26-card024.json']
cur = {}
for p in pats:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f) and '__pycache__' not in f:
            cur[f.replace(chr(92), '/')] = sha(f)
diff = sorted(k for k in set(cur) | set(before) if cur.get(k) != before.get(k))
print('full recompute files', len(cur), 'differences vs before:', diff)

# git 交叉驗證：tracked 且工作樹乾淨的檔，git blob hash 與 HEAD 一致（只確認沒被改；constants.js 本來就是髒的）
st = subprocess.run(['git', 'status', '--porcelain', '--', 'src', 'reports/card-0.2.4', 'reports/card-0.2.5',
                     'reports/card-0.2.4+E089-minutes-saturation', 'reports/ovr-inseason-2026-27/v5/tools',
                     'reports/ovr-inseason-2026-27/v5/pathA/backtest-e064'], capture_output=True, text=True,
                    creationflags=0x08000000, stdin=subprocess.DEVNULL, timeout=120)
print('git status of protected dirs:', st.stdout.strip().splitlines())
