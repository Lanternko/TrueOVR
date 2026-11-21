"""card／inseason 0.2.10g 用人窗口驗證（輕量，本機跑）：
  (1) 分類移植：2025-26 單季 pl/ap 對 card-0.2.10d/usage-features.json 的 a（全人須逐位元相同）、has 相同；
  (2) L 單季 log1p(MIN/ap) 對 usage-features.json 的 L（player-games MIN 與卡 MIN 的差）；
  (3) 本季「只列上場名單」定義（2026-27 boxes 的樣子）對完整定義的偏差：在 2025-26 把 INACTIVE 列拿掉，量 L、a 差；
  (4) 窗口 c=82 的 L、a 與單季差多少。
用法：python -I -B -X utf8 validate_usage_0210g.py"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import window11 as W  # noqa: E402

ROOT = W.ROOT


def main():
    Wn = W.Win11()
    uf = json.loads((ROOT / 'reports/card-0.2.10d/usage-features.json').read_text(encoding='utf-8'))['players']
    D = Wn.D
    tab = Wn.T10[W.PRIOR]['ap']
    ap, pl = tab.agg()
    mn, _ = Wn.T10[W.PRIOR]['mpg'].agg()
    bad_a = bad_has = n = 0
    dL = []
    for q, u in uf.items():
        i = D.pidx.get(int(q))
        n += 1
        if i is None:
            bad_has += u['has']
            continue
        has = ap[i] > 0
        if has != u['has']:
            bad_has += 1
            continue
        if has:
            if pl[i] / ap[i] != u['a']:
                bad_a += 1
            dL.append(abs(np.log1p(mn[i] / ap[i]) - u['L']))
    print(f'(1) players {n}  has 不符 {bad_has}  a 不逐位元相同 {bad_a}')
    print(f'(2) L 單季差 max {max(dL):.5f}  mean {np.mean(dL):.6f}  >0.01 的 {sum(d > 0.01 for d in dL)} 人')
    # (3) 只列上場名單（ACTIVE）的定義
    hg = W.hist_games(W.PRIOR)
    gi_of = {g: i for i, g in enumerate(D.gids[W.PRIOR])}
    act = {g: [r for r in v if r[2] == 'ACTIVE'] for g, v in hg.items()}
    games = sorted(((gi_of[g], v) for g, v in act.items() if g in gi_of), key=lambda x: x[0])
    t2 = Wn._tab_from(W.classify(games))
    ap2, pl2 = t2.agg()
    sel = [D.pidx[int(q)] for q, u in uf.items() if int(q) in D.pidx and ap[D.pidx[int(q)]] > 0]
    big = [i for i in sel if mn[i] >= 500]
    for tag, ix in (('全部', sel), ('MIN>=500', big)):
        ix = [i for i in ix if ap2[i] > 0]
        dLx = np.array([np.log1p(mn[i] / ap2[i]) - np.log1p(mn[i] / ap[i]) for i in ix])
        dax = np.array([pl2[i] / ap2[i] - pl[i] / ap[i] for i in ix])
        print(f'(3) {tag} n={len(ix)}  L 差 mean {dLx.mean():+.4f} max {np.abs(dLx).max():.4f} p95 {np.percentile(np.abs(dLx), 95):.4f}  a 差 mean {dax.mean():+.4f} max {np.abs(dax).max():.4f}')
    # (4) 窗口 c=82
    cur, G = Wn.season_cur(W.PRIOR)
    f = Wn.usage_at(G, cur, W.PRIOR, G)
    ix = [D.pidx[int(q)] for q, u in uf.items() if int(q) in D.pidx and u['has']]
    dd = np.array([[f['L'][i] - np.log1p(mn[i] / ap[i]), f['a'][i] - pl[i] / ap[i]] for i in ix if f['has'][i]])
    print(f'(4) 窗口(c=82) − 單季  L: mean {dd[:,0].mean():+.4f} sd {dd[:,0].std():.4f} max|.| {np.abs(dd[:,0]).max():.3f}   a: mean {dd[:,1].mean():+.4f} sd {dd[:,1].std():.4f} max|.| {np.abs(dd[:,1]).max():.3f}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
