"""評分 M2 權重、2025-26 基準與五色切點（R-066：E-110 通過，第二階段）。

權重：E-110 M2 的 A→B 擬合（A 半 box＋hustle＋對位每 36 分鐘 → rapm1-A net，加權最小平方，A 半 ≥300 分鐘；
      對位 exp(o) 用 A 半），和 reports/E110-defensive-rating/results.json weights_AB.M2 必須相同。
顯示：exp(o) 換成 2025-26 整季（E-110 §2.2）；基準＝每人 2025-26 整季貢獻值（分鐘加權）。
切點：同 E-105 規則，2025-26「單場（≥10 分鐘）／連續 5 場分鐘加權 − 自己整季」絕對值的 20／60 百分位，取到 0.1。

輸出：reports/game-contribution/m2/{weights.json, baseline-2025-26.json}
用法：python -I scripts/fit_rating_m2.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_game_contribution as gc  # noqa: E402
import rating_m2 as rm  # noqa: E402

FEATS = gc.FEATS + list(rm.HUSTLE) + ['PTS_SAVED', 'TOV_FORCED']


def half_totals(rows, h, games, half):
    exp, lg = rm.exp_table(games, half)
    t = gc.totals(rows, h, half)
    for gid, g in games.items():
        if int(gid) % 2 != half:
            continue
        for pid, e in rm.game_extra(g, exp, lg).items():
            if pid in t:
                for k, v in e.items():
                    t[pid][k] += v
    return t


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows, h = gc.load_games()
    games = rm.load_games('2025-26')
    tA, rA = half_totals(rows, h, games, 0), gc.load_rapm('A')
    ps = [p for p, d in tA.items() if d['MIN'] >= gc.MIN_MIN and p in rA]
    X = np.array([np.r_[1.0, gc.per36(tA[p], FEATS)] for p in ps])
    y = np.array([rA[p][0] for p in ps])
    sw = np.sqrt([rA[p][1] for p in ps])
    beta = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]

    ref = json.loads((gc.ROOT / 'reports/E110-defensive-rating/results.json').read_text(encoding='utf-8'))['weights_AB']['M2']
    diff = max(abs(ref['intercept'] - beta[0]), *(abs(ref[k] - b) for k, b in zip(FEATS, beta[1:])))
    assert diff < 1e-9, f'和 E-110 M2 權重不同：{diff}'

    exp, lg = rm.exp_table(games)
    out = rm.M2
    out.mkdir(parents=True, exist_ok=True)
    w = {'note': 'E-110 M2（R-066）：每 36 分鐘 box＋hustle＋防守對位 → rapm1-A net；只顯示用，不進 OVR',
         'fit': '2025-26 A 半（int(GAME_ID)%2==0），上場 ≥300 分鐘，權重 rapm1-A poss；對位 exp 用 A 半',
         'intercept': float(beta[0]), 'per36': {k: float(b) for k, b in zip(FEATS, beta[1:])},
         'exp': {str(o): round(v, 5) for o, v in sorted(exp.items())}, 'leagueExp': lg,
         'eval': {k: ref_v for k, ref_v in json.loads((gc.ROOT / 'reports/E110-defensive-rating/results.json')
                                                      .read_text(encoding='utf-8'))['r'].items() if k.startswith('M2')}}
    (out / 'weights.json').write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding='utf-8')

    rater = rm.Rater('2025-26')
    per = defaultdict(list)
    for r in rows:
        if r[h['MIN']]:
            per[r[h['PLAYER_ID']]].append(r)
    base, d1, d5, nfb = {}, [], [], 0
    for pid, gl in per.items():
        gl.sort(key=lambda r: (r[h['GAME_DATE']], r[h['GAME_ID']]))
        v = np.array([rater.value(r, h) for r in gl])
        m = np.array([r[h['MIN']] for r in gl], float)
        nfb += sum(rater.fallback(r, h) for r in gl)
        b = float((v * m).sum() / m.sum())
        base[str(pid)] = {'box36': round(b, 3), 'min': round(float(m.sum()), 1)}
        d1 += [abs(x - b) for x, mn in zip(v, m) if mn >= 10]
        d5 += [abs((v[j:j + 5] * m[j:j + 5]).sum() / m[j:j + 5].sum() - b) for j in range(len(v) - 4)]
    w['cut1'] = [round(float(x), 1) for x in np.percentile(d1, [20, 60])]
    w['cut5'] = [round(float(x), 1) for x in np.percentile(d5, [20, 60])]
    sc = np.array([max(0, 0.75 * (x + 7.5)) for pid, gl in per.items() for x in
                   [rater.value(r, h) for r in gl if r[h['MIN']] >= 10]])
    w['share'] = {'gt10': float((sc > 10).mean()), 'eq0': float((sc == 0).mean()), 'mean': float(sc.mean()),
                  'fallbackGames': nfb}
    (out / 'weights.json').write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / 'baseline-2025-26.json').write_text(json.dumps(base, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({k: w[k] for k in ('intercept', 'cut1', 'cut5', 'share')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
