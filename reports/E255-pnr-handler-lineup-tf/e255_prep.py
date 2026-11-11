"""E-255 本機前置準備（擋拆持球 pnr，新增第 16 欄）：
1. 驗證預註冊 sha256。
2. 各季（2021-22～2025-26）Synergy PRBallHandler 季總量（跨隊相加）＋player-games 全季分鐘：
   vol = POSS / MIN × 36；rate = (PTS + k·μ) / (POSS + k)（每回合得分，常態近似經驗貝氏收縮）。
   Synergy 只有季總量，無法排除 test 場次 → 'train' 與 'full' 模式相同（已在預註冊揭露）。
3. 匯出 e255_players.json（沿用 E-245 的 15 欄 base 與 E-179 表）供 5090 使用。
用法：python -I -B -X utf8 reports/E255-pnr-handler-lineup-tf/e255_prep.py [--check]
"""
import csv, hashlib, json, sys
from collections import Counter
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E245 = ROOT / 'reports/E245-mid-lineup-tf-blend/e245_players.json'
SYN = ROOT / 'reports/E239-tracking-full/data'
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
PG = {s: ROOT / f'data/defense-seventh/{s}/player-games.json' for s in SEASONS[:-1]}
PG['2025-26'] = ROOT / 'data/season-source/player-games.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mins(v):
    if v is None:
        return 0.0
    if isinstance(v, str) and ':' in v:
        a, b = v.split(':')
        return int(a) + int(b) / 60.0
    return float(v)


def pct(v):
    """平均名次百分位：Synergy 未列名（擋拆回合極少）的球員 vol=0、rate=μ 會大量同分，同分取平均名次，不靠排序順序。"""
    from scipy.stats import rankdata
    return rankdata(v, method='average') / len(v)


def zscore(v):
    return (v - float(np.mean(v))) / (float(np.std(v)) + 1e-12)


def season_minutes(season):
    d = json.loads(PG[season].read_text(encoding='utf-8'))
    t = d.get('data', d)['resultSets']
    t = t[0] if isinstance(t, list) else t
    c = Counter()
    for r in t['rowSet']:
        r = dict(zip(t['headers'], r))
        m = mins(r['MIN'])
        if m > 0:
            c[str(r['PLAYER_ID'])] += m
    return c


def synergy(season):
    d = json.loads((SYN / f'syn-PRBallHandler-{season}.json').read_text(encoding='utf-8'))
    H = d['headers']
    poss, pts, score = Counter(), Counter(), Counter()
    for row in d['rowSet']:
        r = dict(zip(H, row))
        p = str(r['PLAYER_ID'])
        poss[p] += float(r['POSS'])
        pts[p] += float(r['PTS'])
        score[p] += float(r['SCORE_POSS_PCT']) * float(r['POSS'])
    return poss, pts, score


def est_k(poss, pts, score):
    """常態近似經驗貝氏：每回合得分變異 s2 = PPP·(PPP/score%) − PPP²（得分回合平均分 × PPP − PPP²）；
    var_true = 加權 var_obs − mean(s2/n)（POSS≥50）；k = s2/var_true，夾 [20, 800]。"""
    P = sum(poss.values()); mu = sum(pts.values()) / P
    sc = sum(score.values()) / P
    s2 = mu * (mu / sc) - mu * mu
    ps = [(pts[p] / poss[p], poss[p]) for p in poss if poss[p] >= 50]
    x = np.array([a for a, _ in ps]); n = np.array([b for _, b in ps])
    m = np.average(x, weights=n)
    var_obs = np.average((x - m) ** 2, weights=n)
    var_true = max(var_obs - np.average(s2 / n, weights=n), 1e-6)
    return float(min(max(s2 / var_true, 20.0), 800.0)), float(mu), float(s2), float(var_true)


def build_season(season, base_tb):
    pids = base_tb['pids']
    c_min = season_minutes(season)
    poss, pts, score = synergy(season)
    k, mu, s2, vt = est_k(poss, pts, score)
    has = np.array([c_min[p] > 0 for p in pids], dtype=bool)
    idx = np.where(has)[0]
    vol = np.array([poss[pids[i]] / c_min[pids[i]] * 36.0 for i in idx])
    rate = np.array([(pts[pids[i]] + k * mu) / (poss[pids[i]] + k) for i in idx])
    pv, pa = pct(vol), pct(rate)
    zv, za = zscore(pv), zscore(pa)
    rho = float(np.mean(zv * za))
    N = len(pids)
    ZV = np.zeros(N); ZA = np.zeros(N); M = np.zeros(N); PV = np.zeros(N); PA = np.zeros(N)
    ZV[idx] = zv; ZA[idx] = za; M[idx] = 1.0; PV[idx] = pv; PA[idx] = pa
    md = {'kf': round(k, 3), 'mu': round(mu, 5), 's2': round(s2, 4), 'var_true': round(vt, 6), 'rho': round(rho, 5),
          'n_valid': int(has.sum()), 'n_syn': len(poss),
          'zv': [round(float(x), 6) for x in ZV], 'za': [round(float(x), 6) for x in ZA],
          'zval': [0.0] * N, 'pv': [round(float(x), 6) for x in PV], 'pa': [round(float(x), 6) for x in PA],
          'mask3': [float(x) for x in M]}
    tb = dict(base_tb)
    tb['fallback'] = False
    tb['modes'] = {'train': md, 'full': md}
    # 診斷：pnr 原始量／率，供 E-179 每點換算（不進訓練）
    tb['pnr_raw'] = {pids[i]: [round(float(vol[j]), 4), round(float(rate[j]), 4), round(float(poss[pids[i]]), 1)]
                     for j, i in enumerate(idx)}
    return tb


def main():
    check = '--check' in sys.argv
    base = json.loads(E245.read_text(encoding='utf-8'))
    attrs = base['attrs'] + ['pnr']
    tabs = {}
    for s in SEASONS:
        tb = build_season(s, base['player_tables'][s])
        # base_z / base_m 加第 16 欄 pnr 佔位（T0＝0、mask 0；其他臂由 fit 腳本填）
        N = len(tb['pids'])
        tb['base_z'] = dict(tb['base_z']); tb['base_z']['pnr'] = [0.0] * N
        tb['base_m'] = dict(tb['base_m']); tb['base_m']['pnr'] = [0.0] * N
        tabs[s] = tb
        m = tb['modes']['full']
        # 與 creation 的相關（凍結前資料檢查，非結果）
        cr = np.array(tb['base_z']['creation']); ok = np.array(m['mask3']) > 0
        r_cv = float(np.corrcoef(cr[ok], np.array(m['zv'])[ok])[0, 1])
        r_ca = float(np.corrcoef(cr[ok], np.array(m['za'])[ok])[0, 1])
        print(s, 'N', N, 'valid', m['n_valid'], 'syn', m['n_syn'], 'k', m['kf'], 'mu', m['mu'], 's2', m['s2'],
              'rho(v,a)', m['rho'], 'r(creation,vol)', round(r_cv, 3), 'r(creation,rate)', round(r_ca, 3))
    if check:
        return
    pre = HERE / 'preregistration.md'
    pre_ok = sha(pre) == (HERE / 'preregistration.sha256').read_text().strip()
    out = {'prereg_sha256_ok': pre_ok, 'seasons': SEASONS, 'attrs': attrs, 'player_tables': tabs,
           'e179': base['e179'], 'e179_base_attr': base['e179_base_attr'], 'e179_pos': base['e179_pos'],
           'e245_players_sha256': sha(E245)}
    (HERE / 'e255_players.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print('prereg_ok:', pre_ok, 'wrote e255_players.json')


if __name__ == '__main__':
    main()
