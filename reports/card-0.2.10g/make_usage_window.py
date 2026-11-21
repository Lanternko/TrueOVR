"""card 0.2.10g：2025-26 季末（c=82）的用人層窗口值 -> usage-window-c82.csv（playerId,L,a,has）。
L = log1p(窗口加權 MIN ÷ 窗口加權 ap)、a = 窗口加權 pl ÷ 窗口加權 ap（reports/ovr-inseason-2026-27/live/window11.py）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10g/make_usage_window.py"""
import csv, hashlib, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window11 as W  # noqa: E402


def main():
    Wn = W.Win11()
    cur, G = Wn.season_cur(W.PRIOR)
    f = Wn.usage_at(G, cur, W.PRIOR, G)
    D = Wn.D
    with (HERE / 'usage-window-c82.csv').open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n'); w.writerow(['playerId', 'L', 'a', 'has'])
        n = 0
        for p in D.pids:
            i = D.pidx[p]
            if f['has'][i]:
                w.writerow([p, repr(float(f['L'][i])), repr(float(f['a'][i])), 1]); n += 1
    print(n, 'players', hashlib.sha256((HERE / 'usage-window-c82.csv').read_bytes()).hexdigest())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
