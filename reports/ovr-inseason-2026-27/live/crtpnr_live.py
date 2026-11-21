"""card／inseason 0.2.15（E-303 MRG5，使用者 2026-11-10「合併做進卡片」）：CRT（自主創造 creation）＋PNR（擋拆持球 pnr）合成一個能力值「持球進攻」，
放在 creation 那一欄（顯示縮寫沿用 CRT）；pnr 不再當獨立特徵。
  z_crt＝(creation − μ_c)／σ_c（creation＝現行 creationJ 四季滑動窗口的能力值，μ、σ＝卡片 582 人 c=0 值）；
  z_pnr＝(raw − μ_p)／σ_p（raw＝pnr_live 的量率各半合成 z，E-258 G50、w＝0.5；μ、σ 同一批 582 人）；
  r＝corr(z_crt, z_pnr)（582 人都有兩欄）；合成 z＝(z_pnr＋z_crt)／√(2＋2r)（a＝0.5）；只有一欄有值（復出老將沒有擋拆資料）就用那欄；
  新秀本季沒有擋拆回合＝pnr_live 的 ROOKIE_P0 → raw 用 2025 屆新秀卡片 raw 中位數（rookieRawP0）。
  0–99＝E-175 PctMapper（池＝卡片 2025-26 GP≥30 且 MPG≥20；頂端 PR≥99 走和 3PT／creation 同一條尾巴 99＋51(1−e^(−d/1.96S))，底端同 creation 開）。
凍結檔：crtpnr-pool-card0215.json（python -I -B -X utf8 crtpnr_live.py freeze）。屬性本身隨四季窗口每天更新（L-117／R-076），凍結的只有 μ、σ、r、池與錨點。
開關：run_c4_live 的 CRTPNR=0 時完全不 import 本檔（重現 0.2.14d）。"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
import e175_lib as L  # noqa: E402

FROZEN = HERE / 'crtpnr-pool-card0215.json'
TAIL = ROOT / 'reports/card-0.2.12c-fit246/tail-W246full.csv'      # 卡片 582 人 creation（W246 c=0；card 0.2.13a 的 creation 欄＝此值四捨五入）
PNR_FROZEN = HERE / 'pnr-pool-card0213a.json'                        # 現行 pnr 凍結池（卡片 raw）
BASE25 = ROOT / 'data/benchmark-source/base.json'
BIO25 = ROOT / 'data/benchmark-source/bio.json'
A = 0.5
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
_CACHE = {}


def _rs(d):
    d = d.get('data', d)
    t = d['resultSets'] if 'resultSets' in d else d
    t = t[0] if isinstance(t, list) else t
    return t['headers'], t['rowSet']


def _z(F, crt, raw):
    """回傳 (合成 z, z_crt, z_pnr)；raw=None＝只有 creation。"""
    zc = (crt - F['crtMu']) / F['crtSd'] if crt is not None else None
    zp = (raw - F['pnrMu']) / F['pnrSd'] if raw is not None else None
    if zc is not None and zp is not None:
        return (A * zp + (1 - A) * zc) / math.sqrt(A * A + (1 - A) ** 2 + 2 * A * (1 - A) * F['r']), zc, zp
    return (zc if zc is not None else zp), zc, zp


def freeze():
    pf = json.loads(PNR_FROZEN.read_text(encoding='utf-8'))
    tail = [(int(r['playerId']), r['name'], float(r['creation'])) for r in csv.DictReader(open(TAIL, encoding='utf-8'))]
    raw = np.array([pf['card'][str(p)]['raw'] for p, _, _ in tail])
    crt = np.array([c for _, _, c in tail])
    F = {'crtMu': float(crt.mean()), 'crtSd': float(crt.std()), 'pnrMu': float(raw.mean()), 'pnrSd': float(raw.std())}
    zc, zp = (crt - F['crtMu']) / F['crtSd'], (raw - F['pnrMu']) / F['pnrSd']
    F['r'] = float(np.corrcoef(zc, zp)[0, 1])
    m = np.array([_z(F, c, x)[0] for c, x in zip(crt, raw)])
    direct = (zp + zc) / math.sqrt(2 + 2 * F['r'])
    assert np.max(np.abs(m - direct)) < 1e-12
    H, R = _rs(json.loads(BASE25.read_text(encoding='utf-8')))
    b = {int(r[H.index('PLAYER_ID')]): (float(r[H.index('GP')]), float(r[H.index('MIN')])) for r in R}
    pool = [float(m[i]) for i, (p, _, _) in enumerate(tail) if b[p][0] >= L.POOL_GP and b[p][1] / max(b[p][0], 1) >= L.POOL_MPG]
    mp = L.PctMapper(pool, True, True)
    attr = mp(m)
    Hb, Rb = _rs(json.loads(BIO25.read_text(encoding='utf-8')))
    dy = {int(r[Hb.index('PLAYER_ID')]): str(r[Hb.index('DRAFT_YEAR')]) for r in Rb}
    rk = sorted(float(raw[i]) for i, (p, _, _) in enumerate(tail) if dy.get(p) == '2025')
    # 提示卡用的百分位：各自在同一個池（GP≥30、MPG≥20）裡的百分位
    pin = [i for i, (p, _, _) in enumerate(tail) if b[p][0] >= L.POOL_GP and b[p][1] / max(b[p][0], 1) >= L.POOL_MPG]
    doc = {'doc': 'card／inseason 0.2.15 持球進攻（CRT＝creation＋pnr 合成，E-303 MRG5）凍結（crtpnr_live.py freeze）：crtMu／crtSd＝卡片 582 人 creation（tail-W246full）；'
                  'pnrMu／pnrSd＝同 582 人 pnr raw（pnr-pool-card0213a.json）；r＝corr；pool＝合成 z 的 PctMapper 池（GP≥30、MPG≥20）；card＝卡片值；rookieRawP0＝2025 屆新秀 pnr raw 中位數',
           'a': A, **F, 'pool': pool, 'tails': {'top': True, 'bot': True}, 'anchors': mp.an,
           'crtPool': sorted(float(crt[i]) for i in pin), 'pnrPool': sorted(float(pf['card'][str(tail[i][0])]['pnr']) for i in pin),
           'rookieRawP0': float(np.median(rk)), 'rookieRawP0N': len(rk),
           'card': {str(p): {'name': n, 'crtpnr': float(attr[i]), 'z': float(m[i]), 'creation': float(crt[i]), 'pnr': float(pf['card'][str(p)]['pnr']), 'pnrRaw': float(raw[i])}
                    for i, (p, n, _) in enumerate(tail)},
           'sourcesSha256': {q.relative_to(ROOT).as_posix(): sha(q) for q in (TAIL, PNR_FROZEN, BASE25, BIO25)}}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: doc[k] for k in ('crtMu', 'crtSd', 'pnrMu', 'pnrSd', 'r', 'rookieRawP0', 'rookieRawP0N', 'anchors')}, ensure_ascii=False))
    print('pool', len(pool))
    return doc


def frozen():
    if 'f' not in _CACHE:
        d = json.loads(FROZEN.read_text(encoding='utf-8'))
        d['mapper'] = L.PctMapper(d['pool'], d['tails']['top'], d['tails']['bot'])
        d['card'] = {int(k): v for k, v in d['card'].items()}
        _CACHE['f'] = d
    return _CACHE['f']


def merge(crt, raw):
    """crt＝creation 能力值（窗口值），raw＝pnr_live 的 raw（None＝沒有擋拆資料）。回傳 dict（crtpnr、z、zCrt、zPnr）。"""
    F = frozen()
    z, zc, zp = _z(F, crt, raw)
    return {'crtpnr': float(F['mapper'](np.array([z]))[0]), 'z': float(z), 'zCrt': zc, 'zPnr': zp}


def pct(pool_key, x):
    s = frozen()[pool_key]
    import bisect
    lo, hi = bisect.bisect_left(s, x), bisect.bisect_right(s, x)
    return 100.0 * (lo + 0.5 * (hi - lo)) / len(s)


def rookie_raw_p0():
    return float(frozen()['rookieRawP0'])


def write_tail(path):
    """係數擬合用 --tailSource：tail-W246full.csv 的 creation 欄換成合成值（未四捨五入），其他欄原樣。"""
    F = frozen()
    rows = list(csv.DictReader(open(TAIL, encoding='utf-8')))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader()
        for r in rows:
            r['creation'] = repr(float(F['card'][int(r['playerId'])]['crtpnr']))
            w.writerow(r)


def check_card():
    """卡片值：merge(tail creation, 凍結 pnr raw) 必須與凍結卡片值逐位元相同。"""
    F = frozen()
    bad = [v['name'] for v in F['card'].values() if repr(merge(v['creation'], v['pnrRaw'])['crtpnr']) != repr(v['crtpnr'])]
    print(json.dumps({'n': len(F['card']), 'bad': bad[:10]}, ensure_ascii=False))
    assert not bad


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['freeze']:
        freeze()
    elif sys.argv[1:] == ['check']:
        check_card()
    elif sys.argv[1:2] == ['tail']:
        write_tail(sys.argv[2])
