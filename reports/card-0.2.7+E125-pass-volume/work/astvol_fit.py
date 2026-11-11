"""E-125：astvol = AST/(MIN/36) 的方法 (c) 擬合（程序同 E-070 e070_vol.py：同擬合季、同 MIN_D2=300/36、位置／聯盟先驗由 fit_attr 選）。
擬合只用 < 2025-26 的季；2025-26 只做收縮檢查（和 E-070 同）。輸出 ../astvol-fit.json。
用法（repo 根目錄）：python -I -B reports/card-0.2.7+E125-pass-volume/work/astvol_fit.py </dev/null
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
V61 = OUT.parents[0] / 'ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import engine as E  # noqa: E402
from lib import SEASONS, TEST_SEASON  # noqa: E402

E.ATTR_SEASONS['astvol'] = list(SEASONS)
E.MIN_D2['astvol'] = 300 / 36


def build_astvol(season):
    acc = E._acc()
    for r in E.load_pergame(season):
        i = 0 if int(r['half']) == 1 else 2
        pid = int(r['playerId'])
        acc[pid][i] += float(r['AST'])
        acc[pid][i + 1] += float(r['MIN']) / 36
    return acc


def main():
    cache = {s: E.season_halves(s) for s in SEASONS}
    for s in SEASONS:
        cache[s]['astvol'] = build_astvol(s)
    pos_by = E.positions()
    ts = [s for s in SEASONS if SEASONS.index(s) < SEASONS.index(TEST_SEASON) and E.hist_seasons('astvol', s)]
    fit = E.fit_attr('astvol', ts, cache, pos_by)
    fc = fit['c']
    ds = E.Dataset('astvol', TEST_SEASON, cache, pos_by)
    m = ds.m_league if fc['prior'] == 'league' else ds.m_pos
    y = ds.target
    chk = {'n': int(len(y)), 'shrunk': E.mae(E.pred_c(ds, m, fc['k'], fc['lam'], fc['kh']), y),
           'k0': E.mae(E.pred_c(ds, m, 0.0, fc['lam'], fc['kh']), y), 'firstHalfOnly': E.mae(E.pred_a(ds, ds.m_league), y)}
    out = {'fit': {k: fc[k] for k in ('k', 'lam', 'kh', 'prior', 'trainMae')}, 'trainSeasons': ts, 'trainN': fit['trainN'], 'trainA': fit['trainA'],
           'cAll': fit['cAll'], 'shrinkCheck2025_26': chk, 'minD2': 300 / 36}
    (OUT / 'astvol-fit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
