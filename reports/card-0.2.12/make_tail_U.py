"""card 0.2.12 步驟 1：tail-U.csv ＝ card 0.2.10 的 tail-U.csv，只把 long、creation 兩欄換成 E-185 窗口值（c=82，2025-26 季末；window10.Win10.end）。
同時寫 mpg-c82.csv（MPG_hat 窗口值，L 取 mpg-L-selection.json 的 selected_L）與 three-value.csv（threeValue 窗口版，卡片端）。
用法：python -I -X utf8 reports/card-0.2.12/make_tail_U.py"""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window10 as W10
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SRC = ROOT / 'reports/card-0.2.10/tail-U.csv'
TV10 = ROOT / 'reports/card-0.2.10/three-value.csv'


def main():
    W = W10.Win10()
    Lsel = json.loads((H / 'mpg-L-selection.json').read_text(encoding='utf-8'))['selected_L']
    pid_i = {int(p): i for i, p in enumerate(W.pids)}
    rows = list(csv.DictReader(open(SRC, encoding='utf-8')))
    assert len(rows) == 582 and all(int(r['playerId']) in pid_i for r in rows)
    keys = list(rows[0].keys())
    with open(H / 'tail-U.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(keys)
        for r in rows:
            i = pid_i[int(r['playerId'])]
            o = dict(r)
            for a in W10.EXTRA:
                o[a] = repr(float(W.end[a][i]))
            w.writerow([o[k] for k in keys])
    cur, G = W.season_cur(W10.PRIOR)
    mp = W.mpg_at(G, cur, W10.PRIOR, G, Lsel)
    with open(H / 'mpg-c82.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['playerId', 'mpg'])
        for r in rows:
            q = int(r['playerId'])
            if q in mp:
                w.writerow([q, repr(mp[q])])
    # threeValue 窗口版（卡片端）：規則同 E-123 build_tails 的 T 段（池＝四季單季值 MIN>=500，2025-26 這季換成窗口值；E-101 合併池尾巴 h1 開關；沒資料者 70）
    E123W = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work'
    SV = json.loads((E123W / 'season-values.json').read_text(encoding='utf-8'))['vals']['T']
    H1 = json.loads((E123W.parent / 'h1-results.json').read_text(encoding='utf-8'))['h1']['threeValue']
    top, bot = bool(H1['top']['pass']), bool(H1['bot']['pass'])
    nl = json.loads((ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json').read_text(encoding='utf-8'))
    tv26 = SV['2025-26']
    names = {int(r['playerId']): r['name'] for r in rows}
    has = [q for q in names if str(q) in nl and str(q) in tv26]
    pool_past = [float(v['value']) for s in ('2022-23', '2023-24', '2024-25') for v in SV[s].values() if (v['MIN'] or 0) >= 500]
    old_vals = {q: float(tv26[str(q)]['value']) for q in has}
    pool_old = pool_past + [float(v['value']) for v in tv26.values() if (v['MIN'] or 0) >= 500]
    ref = {int(r['playerId']): r for r in csv.DictReader(open(TV10, encoding='utf-8'))}
    chk = W10.L.PctMapper(pool_old, top, bot)(np.array([old_vals[q] for q in has]))
    self_diff = max(abs(float(ref[q]['tv_main']) - chk[k]) for k, q in enumerate(has))
    n, a, mn = W.tv_raw(G, cur, W10.PRIOR, G, 4)
    m_, a_ = W10.lg_total(W.T10[W10.PRIOR])
    mu = m_ / a_
    vol, acc, val = W.tv_value(n, a, mn, mu)
    ix = {int(p): i for i, p in enumerate(W.D.pids)}
    new_vals = {q: float(val[ix[q]]) for q in has if not np.isnan(val[ix[q]])}
    pool_new = pool_past + [new_vals[q] for q in new_vals if (tv26[str(q)]['MIN'] or 0) >= 500]
    mp3 = W10.L.PctMapper(pool_new, top, bot)
    mapped = dict(zip(new_vals, mp3(np.array(list(new_vals.values())))))
    with open(H / 'three-value.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main'])
        for r in csv.DictReader(open(TV10, encoding='utf-8')):
            q = int(r['playerId'])
            if q in mapped:
                i = ix[q]
                r = dict(r, vol=repr(float(vol[i])), acc=repr(float(acc[i])), value_main=repr(new_vals[q]), tv_main=repr(float(mapped[q])))
            else:
                r = dict(r, tv_main='70.0') if q not in has else r   # has 但窗口 MIN＝0：維持 0.2.10 值
            w.writerow([r[k] for k in ('playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main')])
    info = {'tail-U': sha(H / 'tail-U.csv'), 'mpg-c82': sha(H / 'mpg-c82.csv'), 'three-value': sha(H / 'three-value.csv'), 'L': Lsel, 'n_mpg': len(mp),
            'n_tv_window': len(mapped), 'tv_selfcheck_maxdiff_vs_0.2.10': self_diff, 'tv_mu': mu, 'tv_top_bot': [top, bot]}
    (H / 'work/make_tail_U.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    main()
