"""inseason／card 0.2.13：能力值 pnr（擋拆持球，E-255／E-258 G50_W05 定義，四季滑動窗口）。
  每季原始量：Synergy PRBallHandler 季總量（跨隊相加）POSS、PTS ＋ player-games 全季分鐘 MIN。
  窗口：rookie_defense.window_weights(c)（win_len 246 格，逐場線性遞減換成季權重），每人只用有上場（MIN>0）的季，
        有效量 X_eff = Σ w_s·X_s ／ max(Σ units_s, max w_s)（同 veteran() 的每人正規化；本季 units＝w·c/82），等於一季份量。
  分數：vol = POSS_eff／MIN_eff×36；rate = (PTS_eff + k·μ)／(POSS_eff + k)（k、μ＝2025-26 常態近似經驗貝氏，E-255 est_k）；
        z_v＝vol 在凍結池（卡片 582 人 c=0 窗口值）的平均名次百分位再 z；z_a＝率只在 POSS_eff≥50 的池裡排再 z，POSS_eff<50 者 z_a＝0（G50）；
        raw = (0.5 z_v + 0.5 z_a)／sqrt(0.5 + 0.5ρ)（ρ＝池內 corrcoef）；0–99＝E-175 PctMapper（池＝卡片 2025-26 GP≥30 且 MPG≥20，頂端尾巴開、底端關：0 回合長人大量同分，見 Mapper）。
  卡片端（2025-26 季末＝card route c=82）與賽中 c=0 的窗口權重相同，所以卡片 pnr＝live(c=0, cur=False)。
  本季窗口沒有上場的人：老將沿用卡片值；新秀用 ROOKIE_P0（卡片 2025 屆新秀 pnr 中位數）。
凍結檔：pnr-pool-card0213.json（python -I -B -X utf8 pnr_live.py freeze；含過去四季每人 POSS／PTS／MIN，賽中不再讀 reports/E239）。
本季檔：data/defense-seventh/2026-27/synergy-pnr.json（scripts/fetch_synergy_pnr.mjs 每天抓；失敗沿用上次成功的檔；不存在＝只用過去季）。
開關：PNR=0 時 run_c4_live 完全不 import 本檔（重現 0.2.12e）。"""
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
import e175_lib as L  # noqa: E402

FROZEN = HERE / 'pnr-pool-card0213.json'
SYN = ROOT / 'reports/E239-tracking-full/data'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')
PG = {s: ROOT / f'data/defense-seventh/{s}/player-games.json' for s in PAST[:-1]}
PG['2025-26'] = ROOT / 'data/season-source/player-games.json'
CUR_FILE = ROOT / 'data/defense-seventh/2026-27/synergy-pnr.json'
CARD_LIST = ROOT / 'reports/card-0.2.12c/gravity-attr.csv'     # 卡片 582 人（playerId, name）
BASE25 = ROOT / 'data/benchmark-source/base.json'
BIO25 = ROOT / 'data/benchmark-source/bio.json'
GATE, WV = 50.0, 0.5
CUR = '2026-27'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
_CACHE = {}


class Mapper(L.PctMapper):
    """E-175 PctMapper，頂端尾巴開、底端關：擋拆 0 回合的長人在池底大量同分（平均名次），池內沒有百分位 ≤1 的值，r1 取池最小值（底端關時不用）。"""

    def __init__(self, pool_vals):
        self.pool = L.Pool(pool_vals)
        s = self.pool.s; pc = self.pool.pct(s)
        r90, r99 = float(s[pc >= 90].min()), float(s[pc >= 99].min())
        sd = float(np.std(s)); gap = (r99 - r90) / L.Z9990
        self.an = {'r90': r90, 'r99': r99, 'r1': float(s.min()), 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd), 'poolN': self.pool.n}
        self.top, self.bot = True, False


def _rs(d):
    d = d.get('data', d)
    t = d['resultSets'] if 'resultSets' in d else d
    t = t[0] if isinstance(t, list) else t
    return t['headers'], t['rowSet']


def _mins(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, str) and ':' in v:
        a, b = v.split(':')
        return int(a) + int(b) / 60.0
    return float(v)


def minutes_of(pg_path):
    H, R = _rs(json.loads(Path(pg_path).read_text(encoding='utf-8')))
    i, j = H.index('PLAYER_ID'), H.index('MIN')
    c = Counter()
    for r in R:
        m = _mins(r[j])
        if m > 0:
            c[int(r[i])] += m
    return c


def synergy_of(d):
    H, R = _rs(d)
    ip, iP, it, isc = H.index('PLAYER_ID'), H.index('POSS'), H.index('PTS'), H.index('SCORE_POSS_PCT')
    poss, pts, score = Counter(), Counter(), Counter()
    for r in R:
        p = int(r[ip])
        poss[p] += float(r[iP]); pts[p] += float(r[it]); score[p] += float(r[isc]) * float(r[iP])
    return poss, pts, score


def counts(syn_d, mins):
    """{pid: [POSS, PTS, MIN]}：有上場（MIN>0）的人；Synergy 沒列名＝0 回合。"""
    poss, pts, _ = synergy_of(syn_d)
    return {p: [float(poss.get(p, 0.0)), float(pts.get(p, 0.0)), float(m)] for p, m in mins.items() if m > 0}


def est_k(poss, pts, score):
    """同 E-255 e255_prep.est_k（常態近似經驗貝氏，POSS≥50，夾 [20, 800]）。"""
    P = sum(poss.values()); mu = sum(pts.values()) / P
    sc = sum(score.values()) / P
    s2 = mu * (mu / sc) - mu * mu
    ps = [(pts[p] / poss[p], poss[p]) for p in poss if poss[p] >= 50]
    x = np.array([a for a, _ in ps]); n = np.array([b for _, b in ps])
    m = np.average(x, weights=n)
    var_obs = np.average((x - m) ** 2, weights=n)
    var_true = max(var_obs - np.average(s2 / n, weights=n), 1e-6)
    return float(min(max(s2 / var_true, 20.0), 800.0)), float(mu)


def window(c, past, cur=None):
    """{pid: (POSS_eff, PTS_eff, MIN_eff)}。past：{季: {pid: [poss, pts, min]}}；cur：本季同格式或 None。"""
    import rookie_defense as RD
    ww = RD.window_weights(c)
    parts = [(s, past[s]) for s in PAST if s in ww and s in past]
    if cur is not None and c > 0 and CUR in ww:
        parts.append((CUR, cur))
    acc = {}
    for s, tab in parts:
        w = ww[s]; u = w * (c / 82.0 if s == CUR else 1.0)
        for p, (a, b, m) in tab.items():
            if m <= 0:
                continue
            x = acc.setdefault(p, [0.0, 0.0, 0.0, 0.0, 0.0])
            x[0] += w * a; x[1] += w * b; x[2] += w * m; x[3] += u; x[4] = max(x[4], w)
    return {p: (x[0] / max(x[3], x[4]), x[1] / max(x[3], x[4]), x[2] / max(x[3], x[4])) for p, x in acc.items()}, ww


def _pct(pool, x):
    """平均名次百分位（對凍結池；池內成員＝scipy rankdata average／n）。"""
    lo = np.searchsorted(pool, x, 'left'); hi = np.searchsorted(pool, x, 'right')
    return (lo + (hi - lo + 1) / 2.0) / len(pool) if hi > lo else (lo + 0.5) / len(pool)


def _vr(e, k, mu):
    poss, pts, mn = e
    return poss / mn * 36.0, (pts + k * mu) / (poss + k)


def _raw(F, e):
    vol, rate = _vr(e, F['k'], F['mu'])
    zv = (_pct(F['volPool'], vol) - F['pv'][0]) / F['pv'][1]
    za = (_pct(F['ratePool'], rate) - F['pa'][0]) / F['pa'][1] if e[0] >= GATE else 0.0
    return (WV * zv + (1 - WV) * za) / math.sqrt(WV * WV + (1 - WV) ** 2 + 2 * WV * (1 - WV) * F['rho']), vol, rate


# ------------------------------------------------------------------ 凍結
def freeze():
    import win_len
    win_len.install()
    past = {s: counts(json.loads((SYN / f'syn-PRBallHandler-{s}.json').read_text(encoding='utf-8')), minutes_of(PG[s])) for s in PAST}
    d25 = json.loads((SYN / 'syn-PRBallHandler-2025-26.json').read_text(encoding='utf-8'))
    k, mu = est_k(*synergy_of(d25))
    card = [(int(r['playerId']), r['name']) for r in csv.DictReader(open(CARD_LIST, encoding='utf-8'))]
    eff, ww = window(0.0, past)
    miss = [n for p, n in card if p not in eff]
    assert not miss, f'卡片球員窗口內沒有分鐘：{miss[:5]}'
    from scipy.stats import rankdata
    E = [eff[p] for p, _ in card]
    vol = np.array([_vr(e, k, mu)[0] for e in E]); rate = np.array([_vr(e, k, mu)[1] for e in E])
    ok = np.array([e[0] >= GATE for e in E])
    pv = rankdata(vol, method='average') / len(vol)
    pa_ok = rankdata(rate[ok], method='average') / ok.sum()
    zv = (pv - pv.mean()) / pv.std()
    za = np.zeros(len(card)); za[ok] = (pa_ok - pa_ok.mean()) / pa_ok.std()
    rho = float(np.corrcoef(zv, za)[0, 1])
    F = {'k': k, 'mu': mu, 'volPool': np.sort(vol), 'ratePool': np.sort(rate[ok]), 'pv': (float(pv.mean()), float(pv.std())),
         'pa': (float(pa_ok.mean()), float(pa_ok.std())), 'rho': rho}
    raw = np.array([_raw(F, e)[0] for e in E])
    raw_direct = (WV * zv + (1 - WV) * za) / math.sqrt(WV * WV + (1 - WV) ** 2 + 2 * WV * (1 - WV) * rho)
    assert np.max(np.abs(raw - raw_direct)) < 1e-9, '凍結池百分位重現不了直接 rankdata'
    H, R = _rs(json.loads(BASE25.read_text(encoding='utf-8')))
    b = {int(r[H.index('PLAYER_ID')]): (float(r[H.index('GP')]), float(r[H.index('MIN')])) for r in R}
    pool = [float(raw[i]) for i, (p, _) in enumerate(card) if b[p][0] >= L.POOL_GP and b[p][1] / max(b[p][0], 1) >= L.POOL_MPG]
    mp = Mapper(pool)
    attr = mp(raw)
    Hb, Rb = _rs(json.loads(BIO25.read_text(encoding='utf-8')))
    dy = {int(r[Hb.index('PLAYER_ID')]): str(r[Hb.index('DRAFT_YEAR')]) for r in Rb}
    rk = sorted(float(attr[i]) for i, (p, _) in enumerate(card) if dy.get(p) == '2025')
    doc = {'doc': 'card／inseason 0.2.13 pnr 凍結（pnr_live.py freeze）：past＝四季 {pid: [POSS, PTS, MIN]}；k、mu＝2025-26 經驗貝氏；volPool／ratePool＝卡片 582 人 c=0 窗口值'
                  '（ratePool 只含 POSS_eff≥50）；pv、pa＝池內百分位的平均／標準差；rho＝corrcoef(z_v, z_a)；pool＝PctMapper 池（GP≥30、MPG≥20）；card＝卡片值；rookieP0＝2025 屆新秀卡片中位數',
           'gate': GATE, 'w': WV, 'k': k, 'mu': mu, 'rho': rho, 'pv': list(F['pv']), 'pa': list(F['pa']),
           'volPool': F['volPool'].tolist(), 'ratePool': F['ratePool'].tolist(), 'pool': pool, 'tails': {'top': True, 'bot': False}, 'anchors': mp.an,
           'weights_c0': ww, 'rookieP0': float(np.median(rk)), 'rookieP0N': len(rk),
           'card': {str(p): {'name': n, 'pnr': float(attr[i]), 'raw': float(raw[i]), 'poss': E[i][0], 'vol': float(vol[i]), 'rate': float(rate[i])}
                    for i, (p, n) in enumerate(card)},
           'past': {s: {str(p): v for p, v in t.items()} for s, t in past.items()},
           'sourcesSha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in
                             [SYN / f'syn-PRBallHandler-{s}.json' for s in PAST] + [PG[s] for s in PAST] + [CARD_LIST, BASE25, BIO25]}}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'k': k, 'mu': mu, 'rho': rho, 'n_rate': int(ok.sum()), 'pool': len(pool), 'rookieP0': doc['rookieP0'], 'n_rk': len(rk), 'weights': ww}, ensure_ascii=False))
    return doc


def frozen():
    if 'f' not in _CACHE:
        d = json.loads(FROZEN.read_text(encoding='utf-8'))
        d['mapper'] = Mapper(d['pool'])
        d['volPool'] = np.array(d['volPool']); d['ratePool'] = np.array(d['ratePool'])
        d['card'] = {int(k): v for k, v in d['card'].items()}
        d['past'] = {s: {int(p): v for p, v in t.items()} for s, t in d['past'].items()}
        _CACHE['f'] = d
    return _CACHE['f']


def rookie_p0():
    return float(frozen()['rookieP0'])


def write_card_csv(path, gravity_csv):
    """係數擬合用 --offBallSource：gravity 欄照 card 0.2.12c gravity-attr.csv，加 pnr 欄（卡片值）。"""
    F = frozen()
    rows = list(csv.DictReader(open(gravity_csv, encoding='utf-8')))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['playerId', 'name', 'gravity', 'gravityImputed', 'pnr'])
        for r in rows:
            w.writerow([r['playerId'], r['name'], r['gravity'], r['gravityImputed'], repr(float(F['card'][int(r['playerId'])]['pnr']))])


# ------------------------------------------------------------------ 賽中
def cur_counts(data26):
    if not CUR_FILE.exists():
        return None, {'file': None, 'note': 'synergy-pnr.json 不存在，只用過去季'}
    d = json.loads(CUR_FILE.read_text(encoding='utf-8'))
    # 分鐘跟 synergy-pnr.json 取同一天的整季檔（ovr_history 截短 data26 時，回合與分鐘才同口徑；同 gravity.json 沿用最新一份的慣例）
    return counts(d, minutes_of(CUR_FILE.parent / 'player-games.json')), {
        'file': CUR_FILE.relative_to(ROOT).as_posix(), 'fetchedAt': d.get('fetchedAt'), 'n': len(_rs(d)[1]), 'sha256': sha(CUR_FILE)}


def live(c, data26, pids, rookies=(), cur=True):
    """回傳 ({pid: {'pnr','raw','poss','vol','rate','src'}}, info)。cur=False：同一個 c 但不讀本季（基準用）。"""
    F = frozen()
    cc, finfo = cur_counts(data26) if cur else (None, {'file': None})
    eff, ww = window(c, F['past'], cc)
    rk = set(rookies)
    out = {}
    for p in set(pids) | rk:
        e = eff.get(p)
        if e is not None and e[2] > 0:
            r, vol, rate = _raw(F, e)
            src = 'window' if not (cc and p in cc and c > 0) else ('cur' if all(p not in F['past'][s] for s in PAST) else 'window+cur')
            out[p] = {'pnr': float(F['mapper'](np.array([r]))[0]), 'raw': float(r), 'poss': float(e[0]), 'vol': float(vol), 'rate': float(rate), 'src': src}
        elif p in F['card']:
            v = F['card'][p]
            out[p] = {'pnr': v['pnr'], 'raw': v['raw'], 'poss': v['poss'], 'vol': v['vol'], 'rate': v['rate'], 'src': 'card'}
        elif p in rk:
            out[p] = {'pnr': rookie_p0(), 'raw': None, 'poss': 0.0, 'vol': None, 'rate': None, 'src': 'rookie-p0'}
    info = {'c': c, 'weights': ww, 'cur': finfo, 'src': dict(Counter(v['src'] for v in out.values()))}
    return out, info


def check_card():
    """c=0、不讀本季：每個卡片球員的 live 值必須與凍結卡片值逐位元相同。"""
    import win_len
    win_len.install()
    F = frozen()
    out, _ = live(0.0, None, list(F['card']), cur=False)
    bad = [F['card'][p]['name'] for p in F['card'] if repr(out[p]['pnr']) != repr(F['card'][p]['pnr'])]
    print(json.dumps({'n': len(F['card']), 'bad': bad[:10]}, ensure_ascii=False))
    assert not bad


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['freeze']:
        freeze()
    elif sys.argv[1:] == ['check']:
        check_card()
