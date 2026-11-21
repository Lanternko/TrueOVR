"""E-207 W246 重擬合：usage-window-c82 的窗口版（FIT_WIN=328 必須逐位元重現 card-0.2.10g/usage-window-c82.csv）。
用法（repo root）：FIT_WIN=246|328 python -I -B -X utf8 reports/card-0.2.12c-fit246/make_usage246.py <輸出csv>"""
import csv, hashlib, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ['WIN_LEN'] = os.environ.get('FIT_WIN', '246')
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import win_len  # noqa: E402
win_len.install()
import window11 as W  # noqa: E402

out = Path(sys.argv[1])
Wn = W.Win11()
cur, G = Wn.season_cur(W.PRIOR)
f = Wn.usage_at(G, cur, W.PRIOR, G)
D = Wn.D
with out.open('w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['playerId', 'L', 'a', 'has'])
    n = 0
    for p in D.pids:
        i = D.pidx[p]
        if f['has'][i]:
            w.writerow([p, repr(float(f['L'][i])), repr(float(f['a'][i])), 1]); n += 1
print(win_len.WIN_LEN, n, 'players', hashlib.sha256(out.read_bytes()).hexdigest())
