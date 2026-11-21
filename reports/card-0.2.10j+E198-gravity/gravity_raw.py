"""E-198 步驟 2（預註冊 §1）：gravity 原始值、缺值 OLS 補、0–99 映射。
  原始值：reports/F126-shot-difficulty/gravity-split/gravity-2025-26.json 的 AVGOFFBALLPERIMETERGRAVITYSCORE（PLAYERID）。
  補值：有值的卡片球員上 OLS：raw ~ 1 + 3PA/36 + 3P% + USG% + 位置啞變數（PG 為基準；SG/SF/PF/C），預測值補缺；gravityImputed=1。
        3PA、3PM、MIN、GP：data/benchmark-source/base.json（2025-26 Totals）；USG%：advanced.json USG_PCT；位置：card-0.2.10i/ranking.csv pos。
        3PA=0 的人 3P%＝0（3PA/36 已是 0；預註冊未指定，取最簡單的定義）。
  0–99：照 creation（E-175 L.PctMapper：合併池百分位 attr_of＋尾巴，頂／底開關取 h1 的 creation＝兩端都開），
        池＝2025-26 GP≥30 且 MPG≥20（L.POOL_GP／POOL_MPG）的卡片球員（原始或補值，同 creation 池含池內所有人）；gravity 只有一季，沒有過去季池值。
輸出：gravity-raw.csv（playerId,name,raw,imputed）、gravity-attr.csv（playerId,name,gravity，calibrate 的 --offBallSource）、work/gravity-impute.json。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j+E198-gravity/gravity_raw.py"""
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
import e175_lib as L  # noqa: E402
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
GJ = ROOT / 'reports/F126-shot-difficulty/gravity-split/gravity-2025-26.json'
BASE = ROOT / 'data/benchmark-source/base.json'
ADV = ROOT / 'data/benchmark-source/advanced.json'
TAIL = ROOT / 'reports/card-0.2.10i/tail-U.csv'
RANK = ROOT / 'reports/card-0.2.10i/ranking.csv'
POS = ['SG', 'SF', 'PF', 'C']


def rs(p):
    d = json.load(open(p, encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(d['headers'], r)) for r in d['rowSet']]


def main():
    card = [(int(r['playerId']), r['name']) for r in csv.DictReader(open(TAIL, encoding='utf-8'))]
    pos = {r['name']: r['pos'] for r in csv.DictReader(open(RANK, encoding='utf-8'))}
    assert len(card) == 582 and all(n in pos for _, n in card)
    g = {int(r['PLAYERID']): float(r['AVGOFFBALLPERIMETERGRAVITYSCORE']) for r in json.load(open(GJ, encoding='utf-8'))
         if r.get('AVGOFFBALLPERIMETERGRAVITYSCORE') is not None}
    b = {int(r['PLAYER_ID']): r for r in rs(BASE)}
    a = {int(r['PLAYER_ID']): r for r in rs(ADV)}
    X, has = [], []
    for pid, nm in card:
        br, ar = b[pid], a[pid]
        mn = float(br['MIN'])
        fa, fm = float(br['FG3A']), float(br['FG3M'])
        X.append([1.0, 36 * fa / max(mn, 1e-9), fm / fa if fa > 0 else 0.0, float(ar['USG_PCT'])] + [float(pos[nm] == q) for q in POS])
        has.append(pid in g)
    X, has = np.array(X), np.array(has)
    y = np.array([g.get(pid, np.nan) for pid, _ in card])
    beta, *_ = np.linalg.lstsq(X[has], y[has], rcond=None)
    pred = X @ beta
    res = y[has] - pred[has]
    r2 = 1 - res.var() / y[has].var()
    raw = np.where(has, y, pred)
    gp = np.array([float(b[p]['GP']) for p, _ in card]); mn = np.array([float(b[p]['MIN']) for p, _ in card])
    pool = (gp >= L.POOL_GP) & (gp > 0) & (mn / np.maximum(gp, 1) >= L.POOL_MPG)
    mp = L.PctMapper(list(raw[pool]), True, True)
    attr = mp(raw)
    with open(HERE / 'gravity-raw.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['playerId', 'name', 'raw', 'imputed'])
        for (pid, nm), r_, h in zip(card, raw, has):
            w.writerow([pid, nm, repr(float(r_)), int(not h)])
    with open(HERE / 'gravity-attr.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['playerId', 'name', 'gravity', 'gravityImputed'])
        for (pid, nm), v, h in zip(card, attr, has):
            w.writerow([pid, nm, repr(float(v)), int(not h)])
    info = {'n_card': len(card), 'n_has': int(has.sum()), 'n_imputed': int((~has).sum()), 'n_api_total': len(g),
            'ols': {'cols': ['const', '3PA/36', '3P%', 'USG%'] + [f'pos_{q}' for q in POS], 'beta': beta.tolist(), 'r2': float(r2), 'resid_sd': float(res.std())},
            'pool_n': int(pool.sum()), 'pool_imputed_n': int((pool & ~has).sum()), 'anchors': mp.an, 'tails': {'top': True, 'bot': True},
            'sources_sha256': {str(p.relative_to(ROOT).as_posix()): sha(p) for p in (GJ, BASE, ADV, TAIL, RANK)},
            'gravity_raw_csv_sha256': sha(HERE / 'gravity-raw.csv'), 'gravity_attr_csv_sha256': sha(HERE / 'gravity-attr.csv')}
    (HERE / 'work/gravity-impute.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
