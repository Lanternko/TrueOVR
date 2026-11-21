"""把 RAPM 依 gameId 奇偶切成 A/B 兩半各擬合一次（樣本外驗證用）。

沿用 reports/impact-rapm/rapm.py 的 observations / fit_rapm（以模組匯入，原檔不改）：
同一組 4 個賽季（2022-23..2025-26）的 stint、同一個 ridge（各半各自用 5 折 CV 選 lambda）。
卡片讀的是 pooled（4 季合併）RAPM，所以切分也在合併後的比賽上做，才是同口徑的「半份資料」。

  python reports/ovr-v58-holdout-2025-26/rapm-split.py            # 寫 rapm-A.csv / rapm-B.csv / split-summary.json
  python reports/ovr-v58-holdout-2025-26/rapm-split.py --full-check   # 另用全量重跑 pooled，對 rapm.csv 驗證
"""
import csv, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('rapm_orig', ROOT / 'reports/impact-rapm/rapm.py')
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)


def main():
    obs = list(R.observations(R.SEASONS))
    league = json.loads((ROOT / 'data/season-league.json').read_text(encoding='utf-8'))
    names = {p['playerId']: p['name'] for t in league['teams'] for p in t['roster']}
    summary = {'seasons': R.SEASONS, 'split': 'int(gameId) % 2 (0 = A, 1 = B)', 'observationsTotal': len(obs)}
    halves = {'A': [o for o in obs if int(o[1]) % 2 == 0], 'B': [o for o in obs if int(o[1]) % 2 == 1]}
    fits = {}
    for h, ob in halves.items():
        players = sorted({p for o in ob for p in o[2] + o[3]})
        fit, info = R.fit_rapm(ob, players)
        fits[h] = fit
        games = {o[1] for o in ob}
        summary[h] = {'observations': len(ob), 'games': len(games), 'players': len(players), 'lambda': info['lambda'],
                      'defPossessionsTotal': round(sum(o[5] for o in ob))}
        with open(HERE / f'rapm-{h}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss'])
            for p in sorted(fit, key=lambda p: -fit[p]['net']):
                a = fit[p]
                w.writerow([p, names.get(p, ''), round(a['net'], 3), round(a['O'], 3), round(a['D'], 3), round(a['poss'])])
    if '--full-check' in sys.argv:
        players = sorted({p for o in obs for p in o[2] + o[3]})
        fit, info = R.fit_rapm(obs, players)
        ref = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8'))}
        diff = max(abs(round(fit[p]['net'], 3) - float(ref[p]['pooledNet'])) for p in ref if p in fit)
        summary['fullCheck'] = {'lambda': info['lambda'], 'players': len(players), 'maxAbsDiffPooledNet': diff,
                                'refLambda': json.loads((ROOT / 'reports/impact-rapm/rapm-summary.json').read_text(encoding='utf-8'))['pooled']['lambda']}
    (HERE / 'split-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
