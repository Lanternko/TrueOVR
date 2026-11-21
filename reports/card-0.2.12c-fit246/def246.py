"""E-207 W246 重擬合：def-L-{primary,fitA,fitB}.csv 的窗口版（E-134 e134_defL.fit_w 的 L 形，窗口＝FIT_WIN 格；fitA／fitB＝gameId 奇偶分半）。
做法：live/defense_bonus.py 的 fit（win_len 補丁後的 positions／WIN）＋ e134 的 parity 遮罩。FIT_WIN=328 必須和 stage1/work/c0/def-L-*.csv 對上。
用法（repo root）：FIT_WIN=246|328 python -I -B -X utf8 reports/card-0.2.12c-fit246/def246.py <輸出資料夾>"""
import csv, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ['WIN_LEN'] = os.environ.get('FIT_WIN', '246')
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import numpy as np  # noqa: E402
import win_len  # noqa: E402
win_len.install()
import defense_bonus as DB  # noqa: E402
F, RR = DB.F, DB.RR

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
D = DB.load_data(with_current=False)
t = DB.positions(D)
W = DB.WIN
nm = {int(r['playerId']): r['name'] for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}


def fit(parity):
    seasons = list(t)
    masks = {s: (None if parity is None else np.array([int(g) % 2 == parity for g in D.s[s]['gid']])) for s in seasons}
    wu = {s: np.maximum(t[s] / W, 0.0) for s in seasons}
    used = set()
    for s in seasons:
        X = D.s[s]['X'] if masks[s] is None else D.s[s]['X'][masks[s]]
        pos = wu[s] if masks[s] is None else wu[s][masks[s]]
        used.update(np.unique(X[pos > 0].indices).tolist())
    used.discard(D.K)
    pl = np.array(sorted({j % D.P for j in used}))
    cols = np.concatenate([pl, D.P + pl, [D.K]])
    n = len(pl)
    A = np.zeros((len(cols), len(cols))); b = np.zeros(len(cols))
    diagW = np.zeros(D.K + 1); diag1 = np.zeros(D.K + 1)
    for s in seasons:
        M, bs = F.weighted_normal(D, s, wu[s], masks[s])
        A += M[cols][:, cols].toarray(); b += bs[cols]
        diagW += M.diagonal()
        diag1 += F.weighted_normal(D, s, (wu[s] > 0).astype(float), masks[s])[0].diagonal()
    coef = RR._solve(A, b, DB.F.LAM, 2 * n)
    return {D.players[j]: (float(coef[n + k]), float(diagW[j] + diagW[D.P + j]), float(diag1[j] + diag1[D.P + j])) for k, j in enumerate(pl)}


for part, par in (('primary', None), ('fitA', 0), ('fitB', 1)):
    o = fit(par)
    with (OUT / f'def-L-{part}.csv').open('w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh); wr.writerow(['playerId', 'name', 'D', 'poss', 'possUnweighted'])
        for pid, v in sorted(o.items(), key=lambda kv: -kv[1][0]):
            wr.writerow([pid, nm.get(pid, ''), repr(v[0]), repr(v[1]), repr(v[2])])
    print(win_len.WIN_LEN, part, len(o))
