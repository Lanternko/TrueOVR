"""E-307 共用：讀 parse_blocks.py 的逐人逐季計數，做收縮，產生各臂的每 36 分鐘指標。
收縮強度一律用動差法（method of moments）在 2021-22～2025-26 五季逐季估 τ²，五季平均後換算成先驗強度（prereg §2）：
  retention（二項）：k_r ＝ r̄(1−r̄)/τ²            ；rS ＝(retained＋k_r·r̄季)/(n＋k_r)
  ptsAfter（平均）：k_pa＝σ²(每次蓋帽內變異)/τ² ；paS＝(ptsAfter＋k_pa·m̄季)/(n＋k_pa)
  goaltend 率（Poisson，分鐘）：K_gt＝λ̄/τ²（分鐘）；gt36S＝(gt＋K_gt·λ̄季)/(min＋K_gt)·36
  goaltend 佔比（二項，n＝blk＋gt）：k_gs；gtShareS
各臂（per 36）：A0＝blk36（box 原值）；AE＝blk36·rS；AG＝blk36·rS − gt36S；AV＝blk36·(P0 − paS) − gt36S·(2 − P0)。
P0＝該季聯盟「沒被蓋的禁區兩分」每次出手得分（parse-info.json）。"""
import csv, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DR = ROOT if (ROOT / 'data/defense-seventh/2022-23/pbp').exists() else ROOT.parents[2]
STATS = DR / 'reports/E227-lineup-transformer-r2/data'
FIT = ('2021-22', '2022-23', '2023-24', '2024-25', '2025-26')
ALL = FIT + ('2026-27',)
INFO = json.loads((HERE / 'data/parse-info.json').read_text(encoding='utf-8'))
P0 = {s: 2 * INFO[s]['paint2pm_nb'] / INFO[s]['paint2pa_nb'] for s in ALL}
ARMS = ('A0', 'AE', 'AG', 'AV')


def events(s):
    out = {}
    for r in csv.DictReader(open(HERE / 'data' / f'blk-events-{s}.csv', encoding='utf-8')):
        out[int(r['pid'])] = {k: float(r[k]) for k in ('blk_pbp', 'known', 'retained', 'ptsAfter', 'gt', 'ptsSq')}
    return out


def minutes_blk(s):
    """{pid: (minutes, blk36 原值或 None, name)}，E227 stats 檔（2021-22～2025-26）。"""
    out = {}
    for r in csv.DictReader(open(STATS / f'stats-{s}.csv', encoding='utf-8')):
        m = float(r['minutes'] or 0)
        out[int(r['pid'])] = (m, float(r['blk36']) if r['blk36'] != '' else None, r['name'])
    return out


def _binom_tau2(n, x):
    n, x = np.asarray(n, float), np.asarray(x, float)
    k = n > 0; n, x = n[k], x[k]
    N = n.sum(); rb = x.sum() / N; r = x / n; P = len(n)
    return (np.sum(n * (r - rb) ** 2) - (P - 1) * rb * (1 - rb)) / (N - np.sum(n ** 2) / N), rb


def _mean_tau2(n, s1, s2):
    n, s1, s2 = (np.asarray(v, float) for v in (n, s1, s2))
    k = n > 0; n, s1, s2 = n[k], s1[k], s2[k]
    N = n.sum(); mb = s1.sum() / N; m = s1 / n; P = len(n)
    sig2 = (s2.sum() - np.sum(n * m ** 2)) / (N - P)
    return (np.sum(n * (m - mb) ** 2) - (P - 1) * sig2) / (N - np.sum(n ** 2) / N), mb, sig2


def _pois_tau2(mins, x):
    m, x = np.asarray(mins, float), np.asarray(x, float)
    k = m > 0; m, x = m[k], x[k]
    M = m.sum(); lb = x.sum() / M; lam = x / m; P = len(m)
    return (np.sum(m * (lam - lb) ** 2) - (P - 1) * lb) / (M - np.sum(m ** 2) / M), lb


def fit_priors():
    """回傳收縮強度與逐季聯盟均值。"""
    t = {'r': [], 'pa': [], 'gt': [], 'gs': []}; lg = {}
    for s in FIT:
        ev, mb = events(s), minutes_blk(s)
        ps = [p for p in ev if ev[p]['known'] > 0]
        tr, rb = _binom_tau2([ev[p]['known'] for p in ps], [ev[p]['retained'] for p in ps])
        tp, pb, sig2 = _mean_tau2([ev[p]['known'] for p in ps], [ev[p]['ptsAfter'] for p in ps], [ev[p]['ptsSq'] for p in ps])
        pm = [p for p in mb if mb[p][0] > 0]
        tg, lb = _pois_tau2([mb[p][0] for p in pm], [ev.get(p, {}).get('gt', 0) for p in pm])
        pg = [p for p in ev if ev[p]['blk_pbp'] + ev[p]['gt'] > 0]
        ts, gb = _binom_tau2([ev[p]['blk_pbp'] + ev[p]['gt'] for p in pg], [ev[p]['gt'] for p in pg])
        t['r'].append(tr); t['pa'].append(tp); t['gt'].append(tg); t['gs'].append(ts)
        lg[s] = {'r': rb, 'pa': pb, 'sig2pa': sig2, 'gtPerMin': lb, 'gtShare': gb}
    for s in ('2026-27',):   # 本季聯盟均值（只當收縮目標）
        ev = events(s)
        n = sum(v['known'] for v in ev.values())
        lg[s] = {'r': sum(v['retained'] for v in ev.values()) / n, 'pa': sum(v['ptsAfter'] for v in ev.values()) / n,
                 'gtShare': sum(v['gt'] for v in ev.values()) / sum(v['gt'] + v['blk_pbp'] for v in ev.values())}
    rbar = np.mean([lg[s]['r'] for s in FIT]); sig2 = np.mean([lg[s]['sig2pa'] for s in FIT])
    lbar = np.mean([lg[s]['gtPerMin'] for s in FIT]); gbar = np.mean([lg[s]['gtShare'] for s in FIT])
    big = 1e9
    tau = {k: float(np.mean(v)) for k, v in t.items()}
    k = {'k_r': rbar * (1 - rbar) / tau['r'] if tau['r'] > 0 else big,
         'k_pa': sig2 / tau['pa'] if tau['pa'] > 0 else big,
         'K_gt': lbar / tau['gt'] if tau['gt'] > 0 else big,
         'k_gs': gbar * (1 - gbar) / tau['gs'] if tau['gs'] > 0 else big}
    # 2026-27 的每分鐘干擾球率：用五季平均（本季沒有 E227 分鐘表）
    lg['2026-27']['gtPerMin'] = lbar
    return {'tau2': tau, 'k': {a: float(b) for a, b in k.items()}, 'league': lg, 'P0': P0}


def season_metrics(s, pri, mins_blk=None):
    """逐季指標 {pid: dict}；mins_blk＝{pid:(min, blk36, name)}，預設 E227 stats（只有 FIT 季）。"""
    ev = events(s); mb = mins_blk or minutes_blk(s); k = pri['k']; L = pri['league'][s]; p0 = P0[s]
    out = {}
    for p, (m, b36, name) in mb.items():
        e = ev.get(p, {'blk_pbp': 0, 'known': 0, 'retained': 0, 'ptsAfter': 0, 'gt': 0, 'ptsSq': 0})
        rS = (e['retained'] + k['k_r'] * L['r']) / (e['known'] + k['k_r'])
        paS = (e['ptsAfter'] + k['k_pa'] * L['pa']) / (e['known'] + k['k_pa'])
        gt36S = (e['gt'] + k['K_gt'] * L['gtPerMin']) / (m + k['K_gt']) * 36 if m > 0 else None
        gsS = (e['gt'] + k['k_gs'] * L['gtShare']) / (e['blk_pbp'] + e['gt'] + k['k_gs'])
        d = {'name': name, 'min': m, 'blk': e['blk_pbp'], 'known': e['known'], 'retained': e['retained'], 'ptsAfter': e['ptsAfter'], 'gt': e['gt'],
             'rRaw': e['retained'] / e['known'] if e['known'] else None, 'paRaw': e['ptsAfter'] / e['known'] if e['known'] else None,
             'gsRaw': e['gt'] / (e['blk_pbp'] + e['gt']) if e['blk_pbp'] + e['gt'] else None,
             'gt36Raw': e['gt'] / m * 36 if m > 0 else None,
             'rS': rS, 'paS': paS, 'gt36S': gt36S, 'gsS': gsS, 'A0': b36}
        if b36 is not None and gt36S is not None:
            d['AE'] = b36 * rS
            d['AG'] = b36 * rS - gt36S
            d['AV'] = b36 * (p0 - paS) - gt36S * (2 - p0)
        out[p] = d
    return out


def window_metrics(tabs, ww, pool, pri):
    """四季滑動窗口（RIM 顯示用，同 E-305 權重）。tabs＝{季: {pid: (min, blk_box)}}；回傳 {pid: {A0,AE,AG,AV}}。
    blk36 照 E-305：每人除以自己有資料季的最大權重，向人群平均收縮 200 分鐘；rS／paS／gt36S 用窗口加權計數收縮。"""
    k = pri['k']
    EV = {s: events(s) for s in tabs}
    acc = {}
    for p in set().union(*[set(t) for t in tabs.values()]):
        a = dict(m=0.0, b=0.0, n=0.0, ret=0.0, pa=0.0, gt=0.0); mx = 0.0
        for s, t in tabs.items():
            w = ww.get(s, 0)
            if p not in t or w <= 0:
                continue
            m, b = t[p]; e = EV[s].get(p)
            a['m'] += w * m; a['b'] += w * (b or 0); mx = max(mx, w)
            if e:
                a['n'] += w * e['known']; a['ret'] += w * e['retained']; a['pa'] += w * e['ptsAfter']; a['gt'] += w * e['gt']
        if mx > 0:
            acc[p] = {kk: v / mx for kk, v in a.items()}
    pp = [p for p in pool if p in acc]
    mu_b = sum(acc[p]['b'] for p in pp) / sum(acc[p]['m'] for p in pp)
    sw = {s: w for s, w in ww.items() if w > 0}
    W = sum(sw.values())
    rbar = sum(w * pri['league'][s]['r'] for s, w in sw.items()) / W
    pabar = sum(w * pri['league'][s]['pa'] for s, w in sw.items()) / W
    lbar = sum(w * pri['league'][s]['gtPerMin'] for s, w in sw.items()) / W
    p0 = sum(w * P0[s] for s, w in sw.items()) / W
    out = {}
    for p, a in acc.items():
        b36 = (a['b'] + 200.0 * mu_b) / (a['m'] + 200.0) * 36
        rS = (a['ret'] + k['k_r'] * rbar) / (a['n'] + k['k_r'])
        paS = (a['pa'] + k['k_pa'] * pabar) / (a['n'] + k['k_pa'])
        gt36 = (a['gt'] + k['K_gt'] * lbar) / (a['m'] + k['K_gt']) * 36
        out[p] = {'A0': b36, 'AE': b36 * rS, 'AG': b36 * rS - gt36, 'AV': b36 * (p0 - paS) - gt36 * (2 - p0),
                  'rS': rS, 'paS': paS, 'gt36S': gt36, 'blkW': a['n'], 'gtW': a['gt']}
    return out
