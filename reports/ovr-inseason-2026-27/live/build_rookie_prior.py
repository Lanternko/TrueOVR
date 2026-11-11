"""E-116 新秀先驗（預註冊 reports/E116-rookie-prior/preregistration.md §2）。

產出：
  reports/E116-rookie-prior/fit.json          每項能力的迴歸係數、τ²、k、n
  reports/ovr-inseason-2026-27/live/rookie-prior-2026.json   2026 新秀的 x0、k、順位、位置
用法：python -I -X utf8 build_rookie_prior.py
迴歸：a = b0 + b1·ln(順位) + gF·[F] + gC·[C]；282 人（2017–2021 五屆新秀，各自新秀季的 027 卡）。
"""
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'v5' / 'tools'))
import pathA_common as PA  # noqa: E402,F401
import v2_common as V2  # noqa: E402

OUT = ROOT / 'reports' / 'E116-rookie-prior'
SEASONS = ['2017-18', '2018-19', '2019-20', '2020-21', '2021-22']
ABIL = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall',
        'help', 'stamina', 'creation', 'pressure', 'foulDraw']
UPDATABLE = V2.UPDATABLE + ['foulDraw']            # 有 k 的（foulDraw 借 drive 的 σ²、nRef）
LO, HI = 0.0, 150.0                                # 與 run_c4_live m26_clip 同範圍（D4）
UNDRAFTED = 61
POS_G = {'PG': 'G', 'SG': 'G', 'SF': 'F', 'PF': 'F', 'C': 'C'}


def height_pos(inches):
    return 'G' if inches <= 76 else ('C' if inches >= 82 else 'F')


def load_bio(season):
    d = json.load(open(ROOT / 'data/defense-seventh' / season / 'bio.json', encoding='utf-8'))
    rs = d['data']['resultSets'][0]
    return {r[0]: dict(zip(rs['headers'], r)) for r in rs['rowSet']}


def pick_of(b):
    n = b.get('DRAFT_NUMBER')
    try:
        return int(n)
    except (TypeError, ValueError):
        return UNDRAFTED


def design(pick, pos):
    return [1.0, math.log(pick), 1.0 if pos == 'F' else 0.0, 1.0 if pos == 'C' else 0.0]


def rookies_of_fit():
    rows = []
    for s in SEASONS:
        yr = s[:4]
        bio = load_bio(s)
        cards = json.load(open(REPORT / 'e111-card027/cards' / f'prior-{s}-027.json', encoding='utf-8'))['players']
        for c in cards:
            b = bio.get(c['playerId'])
            if b is None or str(b.get('DRAFT_YEAR')) != yr:
                continue
            obs = c.get('observed', {})
            rows.append({'season': s, 'pid': c['playerId'], 'name': c['name'], 'pick': pick_of(b),
                         'pos': POS_G[c['pos']], 'card': c,
                         'mpg': float(obs['MIN']) / float(obs['GP']) if float(obs.get('GP') or 0) > 0 else None})
    return rows


def main():
    rows = rookies_of_fit()
    per_season = {s: sum(1 for r in rows if r['season'] == s) for s in SEASONS}
    rel = V2.load_reliability()
    fit = {}
    for a in ABIL:
        use = [r for r in rows if r['card'].get(a) is not None]
        X = np.array([design(r['pick'], r['pos']) for r in use])
        y = np.array([float(r['card'][a]) for r in use])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        n = len(use)
        tau2 = float(res @ res / (n - 4))
        ent = {'b0': float(beta[0]), 'b1_lnPick': float(beta[1]), 'gF': float(beta[2]), 'gC': float(beta[3]),
               'tau2': tau2, 'n': n, 'k': None, 'sigma2': None, 'nRef': None, 'kClamped': None, 'kRaw': None}
        src = 'drive' if a == 'foulDraw' else a
        if a in UPDATABLE:
            s2, nref = rel[src]['sigma2'], rel[src]['nRef']
            raw = s2 / tau2 if tau2 > 0 else 50.0 * nref
            ent.update({'sigma2': s2, 'nRef': nref, 'kRaw': raw,
                        'k': min(max(raw, 0.02 * nref), 50.0 * nref),
                        'kClamped': 'lo' if raw < 0.02 * nref else ('hi' if raw > 50.0 * nref else None)})
        fit[a] = ent
    mpgs = [r['mpg'] for r in rows if r['mpg'] is not None]
    meds = {'mpg0': float(statistics.median(mpgs)), 'usg0': 0.0}
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({'experiment': 'E-116', 'nRookies': len(rows), 'perSeason': per_season,
               'form': 'a = b0 + b1*ln(pick) + gF*[F] + gC*[C]；位置基準 G；落選＝61',
               'tau2Def': '殘差平方和／(n−4)，單位＝能力值（與 δ² 同單位，沒有扣量測噪音）',
               'kDef': 'k = sigma2/tau2，夾 [0.02, 50]*nRef；foulDraw 借 drive 的 sigma2、nRef',
               'clip': [LO, HI], 'medians': meds, 'abilities': fit},
              open(OUT / 'fit.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ---- 2026 新秀：bio DRAFT_YEAR=='2026'、沒有正式卡（D7：落選者無法和沒卡的老將區分，不納入）
    bio = load_bio('2026-27')
    live = json.load(open(HERE / 'prior-2025-26-card027.json', encoding='utf-8'))['players']
    have = {p['playerId'] for p in live}
    teams = {}
    out = []
    for pid, b in sorted(bio.items(), key=lambda kv: pick_of(kv[1])):
        if str(b.get('DRAFT_YEAR')) != '2026' or pid in have:
            continue
        pick = pick_of(b)
        h = float(b['PLAYER_HEIGHT_INCHES'])
        pos = height_pos(h)
        x = design(pick, pos)
        x0 = {}
        k = {}
        for a in ABIL:
            f = fit[a]
            v = f['b0'] + f['b1_lnPick'] * x[1] + f['gF'] * x[2] + f['gC'] * x[3]
            x0[a] = min(max(v, LO), HI)
            if f['k'] is not None:
                k[a] = f['k']
        out.append({'playerId': pid, 'name': b['PLAYER_NAME'], 'team': b['TEAM_ABBREVIATION'], 'pick': pick,
                    'pos': pos, 'posSource': 'height' if True else 'boxscore', 'heightInches': h,
                    'mpg0': meds['mpg0'], 'usg0': meds['usg0'], 'x0': x0, 'k': k})
    json.dump({'experiment': 'E-116', 'season': '2026-27', 'nFit': len(rows), 'players': out,
               'note': '位置一律用身高（boxscore 沒有 position 欄，D3）；usg0＝0（無來源，D2）'},
              open(HERE / 'rookie-prior-2026.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'n': len(rows), 'perSeason': per_season, 'rookies2026': len(out),
                      'kClamp': {a: fit[a]['kClamped'] for a in ABIL if fit[a]['k'] is not None},
                      'mpg0': meds['mpg0']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
