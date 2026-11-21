"""E-151 驗收：凍結的 K0（0.2.7d）與 A1y（年輕側連續）卡片 OVR 對 2026-27 純 RAPM（無先驗）的 Spearman。
只在預註冊觸發條件成立後執行一次；先核對兩份排名與本預註冊的 sha256。
用法（repo 根目錄）：python -I -X utf8 "reports/card-0.2.7d+E151-young-curve/e151_eval.py"
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHA = {'K0-ranking.csv': '696a8ac7b235acf51cdb5634fa9896a6905fec81adb96166b6995b9015c20649',
       'A1y-ranking.csv': 'a99bf3e170af22e9928ced23990b11346600f00e17cae89f6baf06f84912031b'}
MIN_GAMES, MIN_POSS, MIN_CARD_MIN, YOUNG_MAX_AGE = 450, 1500, 500, 24
B, SEED = 2000, 151
_spec = importlib.util.spec_from_file_location('rapm', ROOT / 'reports/impact-rapm/rapm.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bio():
    rs = json.load(open(ROOT / 'data/benchmark-source/bio.json', encoding='utf-8'))['data']['resultSets'][0]
    h = rs['headers']
    i, n, a = h.index('PLAYER_ID'), h.index('PLAYER_NAME'), h.index('AGE')
    return {r[n]: (int(r[i]), r[a]) for r in rs['rowSet']}


def main():
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().split()[0], '預註冊被改過'
    for f, want in SHA.items():
        assert sha(HERE / f) == want, f + ' 與凍結值不同'
    obs = list(R.observations(['2026-27']))
    games = len({o[1] for o in obs})
    if games < MIN_GAMES:
        print(json.dumps({'games': games, 'status': '未達觸發條件，不評估'}, ensure_ascii=False)); return 1
    players = sorted({p for o in obs for p in o[2] + o[3]})
    fit, info = R.fit_rapm(obs, players)
    nm = bio()
    card = {a: {r['name']: r for r in csv.DictReader(open(HERE / f'{a}-ranking.csv', encoding='utf-8'))} for a in ('K0', 'A1y')}
    rows = []
    for n, r in card['K0'].items():
        if float(r['MIN']) < MIN_CARD_MIN or n not in nm or n not in card['A1y']:
            continue
        pid, age = nm[n]
        v = fit.get(pid)
        if v is None or v['poss'] < MIN_POSS:
            continue
        rows.append((n, age, float(r['ovr']), float(card['A1y'][n]['ovr']), v['net']))
    rng = np.random.default_rng(SEED)

    def block(sel):
        x = np.array([[k, a, y] for _, _, k, a, y in sel])
        rho = lambda idx, c: spearmanr(x[idx, c], x[idx, 2])[0]
        allx = np.arange(len(x))
        d0 = rho(allx, 1) - rho(allx, 0)
        bs = []
        for _ in range(B):
            i = rng.integers(0, len(x), len(x))
            bs.append(rho(i, 1) - rho(i, 0))
        return {'n': len(x), 'rho_K0': float(rho(allx, 0)), 'rho_A1y': float(rho(allx, 1)), 'delta': float(d0),
                'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]}
    res = {'games': games, 'lambda': info['lambda'], 'all': block(rows),
           'young': block([r for r in rows if r[1] is not None and r[1] <= YOUNG_MAX_AGE])}
    y, a = res['young'], res['all']
    res['adopt_A1y'] = bool(y['delta'] >= 0.01 and y['ci90'][0] > -0.02 and a['delta'] >= -0.005)
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
