"""E-081：2025-26 單季分半 RAPM（答案 N 的來源）。

沿用 reports/impact-rapm/rapm.py 的 observations / normal_equations / solve（以模組匯入，原檔不改），
但 lambda 固定 3000（不做 CV），只用 2025-26 的 stint；比賽依 int(gameId) % 2 分 A（0）／B（1），切法同 rapm-split.py。

  python rapm1.py     # 寫 rapm1-A.csv、rapm1-B.csv、rapm1-summary.json，並做 (k1) 自檢
"""
import csv, importlib.util, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('rapm_orig', ROOT / 'reports/impact-rapm/rapm.py')
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
LAM = 3000
SEASON = '2025-26'


def fit(obs):
    """固定 lambda 的 ridge（截距不罰），回傳 {playerId: {O, D, net, poss}}。與 R.fit_rapm 最後一步同式。"""
    players = sorted({p for o in obs for p in o[2] + o[3]})
    index = {p: i for i, p in enumerate(players)}
    P = len(players); K = 2 * P
    XtX, Xty, yy, wsum = R.normal_equations(obs, index)
    b = R.solve(XtX.sum(0), Xty.sum(0), LAM, K)
    poss = np.diag(XtX.sum(0))[:K]
    out = {p: {'O': float(b[i]), 'D': float(b[P + i]), 'poss': float(poss[i] + poss[P + i])} for p, i in index.items()}
    for v in out.values():
        v['net'] = v['O'] + v['D']
    return out, float(b[K])


def main():
    obs = list(R.observations([SEASON]))
    league = json.loads((ROOT / 'data/season-league.json').read_text(encoding='utf-8'))
    names = {p['playerId']: p['name'] for t in league['teams'] for p in t['roster']}
    summary = {'season': SEASON, 'lambda': LAM, 'split': 'int(gameId) % 2 (0 = A, 1 = B)', 'observationsTotal': len(obs)}
    for h, par in (('A', 0), ('B', 1)):
        ob = [o for o in obs if int(o[1]) % 2 == par]
        f, icpt = fit(ob)
        summary[h] = {'observations': len(ob), 'games': len({o[1] for o in ob}), 'players': len(f), 'intercept': icpt}
        with open(HERE / f'rapm1-{h}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['playerId', 'name', 'net', 'O', 'D', 'poss'])
            for p in sorted(f, key=lambda p: -f[p]['net']):
                a = f[p]
                w.writerow([p, names.get(p, ''), repr(a['net']), repr(a['O']), repr(a['D']), repr(a['poss'])])
    # (k1) 全季擬合 vs rapm.csv 的 lastSeason* 欄（csv 是四捨五入到 3 位，所以把我們的值也四捨五入後比）
    f, icpt = fit(obs)
    ref = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
    diffs = []; n_cmp = 0; n_ref_absent = 0
    for p, r in ref.items():
        if p not in f:
            n_ref_absent += 1
            diffs += [abs(float(r['lastSeasonNet'])), abs(float(r['lastSeasonO'])), abs(float(r['lastSeasonD']))]   # csv 對不在本季的人填 0
            continue
        n_cmp += 1
        for key, col in (('net', 'lastSeasonNet'), ('O', 'lastSeasonO'), ('D', 'lastSeasonD')):
            diffs.append(abs(round(f[p][key], 3) - float(r[col])))
    extra = [p for p in f if p not in ref]
    summary['k1'] = {'maxAbsDiff': max(diffs), 'pass': bool(max(diffs) < 1e-6), 'threshold': '< 1e-6（兩邊都四捨五入到 3 位小數後比）',
                     'players_fit': len(f), 'players_in_ref': len(ref), 'compared_present': n_cmp, 'ref_players_absent_in_season(csv=0)': n_ref_absent,
                     'fit_players_not_in_ref': len(extra), 'intercept': icpt,
                     'poss_maxAbsDiff_rounded': max(abs(round(f[p]['poss']) - float(ref[p]['lastSeasonPoss'])) for p in ref if p in f)}
    (HERE / 'rapm1-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    assert summary['k1']['pass'], '(k1) 自檢失敗，停下回報'


if __name__ == '__main__':
    main()
