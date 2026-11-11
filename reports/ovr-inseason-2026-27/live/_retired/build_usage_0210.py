raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-114 retired guard
"""card 0.2.10（R-111/R-114，policy B 全凍結）：照 build_usage_029a.py，卡目錄換成 reports/card-0.2.10/cards/K6；
用人層第三次 WLS（coef[card]）、r_repl、兩段映射錨一律取 reports/card-0.2.10/frozen.json（即 0.2.9a 值），不重擬合。
核對對象：reports/card-0.2.10/ranking.csv。輸出 usage-2025-26-card0210.json。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_0210.py
"""
"""R-098 後續（使用者 2026-10-31「一」：賽中基準換 0.2.8）：產生 card 0.2.8 用人層的凍結特徵與係數，給 CARD_MODE=027d 用。
照 build_usage_027b.py，只換兩處：pipeline 卡目錄 E-131 cards/K1（0.2.7c，OVR 迴歸無 physique）；scope_feats 的 d 換成 E-147 連續 d
（reports/card-0.2.7c+E147-continuous-d/e147.py team_badness）。核對對象改成 reports/card-0.2.8/ranking.csv；錨點核對對象改成本程式重算（0.2.8 沒另存錨點）。
以下為 027b 原說明：

card 0.2.7b 的用人層由 reports/card-0.2.6+E107-defense-UL/e107.py 產生：唯讀匯入 reports/card-0.2.5+E094-defense-ceiling/e094.py，
set_card_dir(cards/UL6) 後 M.pipeline(BASE_OPTS, pools, 'season')；係數 coef['card']、r_repl、錨點都是該次 pipeline 的結果
（沒有另存檔），所以這裡照同一流程重跑一次（決定性，不擬合任何新東西），再核對：
  - 錨點對 phase2.json reportOnly.anchors.UL6 差 < 1e-9；
  - 582 人 ovr（.1f）、mpg（.2f）、gRepl（.4f）與 reports/card-0.2.7b/ranking.csv 逐格相同；未四捨五入 ovr 差另列（≤ 0.05）。
分鐘權重 W = w_sat(mpg)（scale 15）。
輸出：live/usage-2025-26-card027b.json（每人 has、L、a、y、v、d、age、mpgAvail、p、predNew；係數、rRepl、錨點；來源 sha256）。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_029a.py
"""
import csv
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
UL = ROOT / 'reports/card-0.2.6+E107-defense-UL'
RB = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a'
import numpy as np  # noqa: E402

E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E134S1 = ROOT / 'reports/card-0.2.7c+E134-rolling-prior/stage1'
_cfg = {   # 同 E-153 K6 pipe 階段的 E134_CFG（errata-1：split RAPM 換 T6；rapm1 不換）
    'dnp': str(E134S1 / 'work/c0p/dnp-2025-26.json'),
    'mpgDir': str(E134S1 / 'work/c0p/mpg'),
    'splitDir': str(E153 / 'work/K6-2025-26/c0/split'),
    'rapm1Dir': str(E134S1 / 'work/c0p/rapm1'),
}
_cfgp = Path(tempfile.mkdtemp(prefix='c028-cfg-')) / 'cfg.json'
_cfgp.write_text(json.dumps(_cfg), encoding='utf-8')
os.environ['E134_CFG'] = str(_cfgp)
_spec = importlib.util.spec_from_file_location('e094t', E134S1 / 'e094_t.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
_TMP = Path(tempfile.mkdtemp(prefix='e111-usage-'))
M.HERE, M.W, M.CARDS = RB, _TMP / 'work', RB / 'cards'    # 不寫任何檔（pipeline 本身不寫）

OUT = HERE / 'usage-2025-26-card0210.json'
C028 = ROOT / 'reports/card-0.2.10'
E131 = ROOT / 'reports/card-0.2.7b+E131-no-physique'
E147 = ROOT / 'reports/card-0.2.7c+E147-continuous-d'
CARD_RANKING = ROOT / 'reports/card-0.2.10/ranking.csv'
CARD_SUMMARY = ROOT / 'reports/card-0.2.10/summary.json'
PHASE2 = ROOT / 'reports/card-0.2.8+E158-young-under-T6/results.json'
SRC = {
    'e094.py': E94 / 'e094.py',
    'e107.py': UL / 'e107.py',
    'E-158 results.json': PHASE2,
    'card-0.2.10 ranking.csv': CARD_RANKING,
    'card-0.2.10 summary.json': CARD_SUMMARY,
    'e147.py': E147 / 'e147.py',
    'K6 primary pred.csv': C028 / 'cards/K6/primary/pred.csv',
    'K6 fitA pred.csv': C028 / 'cards/K6/fitA/pred.csv',
    'K6 fitB pred.csv': C028 / 'cards/K6/fitB/pred.csv',
    '2025-26 player-games': ROOT / 'data/season-source/player-games.json',
    '2025-26 team-games': ROOT / 'data/season-source/team-games.json',
    '2025-26 dnp': ROOT / 'data/season-source/dnp-2025-26.json',
    'bio (age)': ROOT / 'data/benchmark-source/bio.json',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def team_badness():
    """同 e147.py team_badness（2025-26 全季 team-games）→ {TEAM_ID: d}。"""
    tg = M.jload(ROOT / 'data/season-source/team-games.json')['data']['resultSets'][0]
    h = tg['headers']
    it, iw, ipm = h.index('TEAM_ID'), h.index('WL'), h.index('PLUS_MINUS')
    acc = {}
    for r in tg['rowSet']:
        a = acc.setdefault(r[it], [0, 0, 0.0])
        a[0] += 1; a[1] += r[iw] == 'W'; a[2] += float(r[ipm])
    return {t: min(1.0, max(0.0, (0.40 - (0.7 * (0.5 + 0.033 * pm / (gp + 10)) + 0.3 * (w + 5) / (gp + 10))) / 0.10)) for t, (gp, w, pm) in acc.items()}


def main():
    summ = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))
    assert sha(CARD_RANKING) == summ['ranking_csv_sha256'], 'card 0.2.9a ranking.csv sha256 與 summary.json 不符'
    tb = team_badness()
    sf0 = M.scope_feats

    def sf_cont(*a):   # E-147 D1：d 換連續（主隊全季）
        r = sf0(*a)
        r['d'] = np.array([tb[t] if t is not None else 0.0 for t in r['main']])
        return r
    M.scope_feats = sf_cont
    design9 = M.design

    def design_y0(sf, sel, k, p=None):   # E-158 Y0：同 e158_build.design0，刪掉 y·d·L
        p = sf['p'][sel] if p is None else p
        L, a, y, v = (sf[c][sel] for c in 'L a y v'.split())
        return np.column_stack([np.ones_like(p), p, L, a, y, v, y * L, v * L])
    M.design = design_y0
    FZ = json.loads((ROOT / 'reports/card-0.2.10/frozen.json').read_text(encoding='utf-8'))['use_layer']
    _ow, _cnt = M.wls, []

    def wls_fz(X, y, w):
        c = _ow(X, y, w)
        _cnt.append(1)
        return np.array(FZ['wls_card']) if len(_cnt) == 3 else c
    M.wls = wls_fz
    M.load_data()
    M.set_card_dir(RB / 'cards/c0')
    pools = M.build_pools()
    M.set_card_dir(C028 / 'cards/K6')
    for _h in 'AB':   # 同 card-0.2.10/use_layer.py：凍結模式下 PR10 一致性斷言改用本次 pred 的重算值（不進卡）
        _fs = M.D['fitsum'][_h]
        if _fs and 'rRepl_if_refit_on_this_pred' in _fs:
            _fs['rRepl_PR10_of_pred'] = _fs['rRepl_if_refit_on_this_pred']
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    assert 'b8_ydL' not in r_['coef']['card'] and len(r_['coef']['card']) == 8
    coef = np.array([r_['coef']['card'].get(k, 0.0) for k in M.COEF_NAMES])   # b8_ydL＝0
    assert len(_cnt) == 3
    M.design = design9
    r_repl, anc = float(FZ['r_repl']), {k: float(v) for k, v in FZ['anchors'].items()}

    C = M.classify(M.BASE_OPTS)
    sf = M.scope_feats('full', M.D['prim'], C, M.BASE_OPTS)
    pids, N = sf['pids'], sf['n']
    X = M.design(sf, np.arange(N), 9)
    pred_new = np.where(sf['has'], X @ coef, sf['p'])
    pool = sf['MIN'] >= M.POOL_MIN
    r_chk = M.qf(pred_new, pool, 10)
    g = (pred_new - r_repl) * M.w_sat(sf['mp'])
    anc_chk = {'PR1': M.qf(g, pool, 1), 'PR50': M.qf(g, pool, 50), 'PR99': M.qf(g, pool, 99)}
    d_r = abs(r_chk - r_repl)
    d_anc = max(abs(anc_chk[k] - anc[k]) for k in anc)
    ovr = M.two_segment(g, anc['PR1'], anc['PR50'], anc['PR99'])
    d_pipe = float(np.max(np.abs(pred_new - r_['_aux']['pred_new'])))

    names = [M.D['prim'][q]['name'] for q in pids]
    card = {r['name']: r for r in csv.DictReader(CARD_RANKING.open(encoding='utf-8'))}
    assert len(card) == N == 582 and set(card) == set(names), '名單與 card 0.2.9a 不一致'
    bad = {'ovr': 0, 'mpg': 0, 'gRepl': 0}
    max_unrounded = 0.0
    for i, nm in enumerate(names):
        c = card[nm]
        bad['ovr'] += f'{ovr[i]:.1f}' != c['ovr']
        bad['mpg'] += f"{sf['mp'][i]:.2f}" != c['mpg']
        bad['gRepl'] += f'{g[i]:.4f}' != c['gRepl']
        max_unrounded = max(max_unrounded, abs(ovr[i] - float(c['ovr'])))
    players = {}
    for i, q in enumerate(pids):
        players[str(q)] = {
            'name': names[i], 'has': bool(sf['has'][i]), 'L': float(sf['L'][i]), 'a': float(sf['a'][i]),
            'y': float(sf['y'][i]), 'v': float(sf['v'][i]), 'd': float(sf['d'][i]),
            'age': sf['age'][i], 'mpgAvail': float(sf['mp'][i]), 'p': float(sf['p'][i]), 'predNew': float(pred_new[i]),
            'ovrCard': float(card[names[i]]['ovr']),
        }
    payload = {'coef': dict(zip(M.COEF_NAMES, map(float, coef))), 'rRepl': r_repl, 'anchors': anc, 'players': players}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    doc = {
        'doc': 'card 0.2.10 用人層凍結特徵（部件卡 E-164 S 臂拿掉 stamina；用人層同 0.2.9：E-158 Y0：y·d·L 拿掉，b8_ydL＝0）（2025-26 全季；e094.pipeline(pools@c0, set_card_dir(E-131 K1))＋E-147 連續 d 重跑取係數、r_repl、錨點，'
               'scope_feats("full") 重算特徵，不擬合新參數；W = w_sat(mpg)）',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（has=True；0.2.9／0.2.9a 的 b8＝0）；has=False → predNew = p',
        'check': {'rReplRecomputeDiff': d_r, 'anchorsRecomputeDiff': d_anc,
                  'predNewVsPipeline': d_pipe, 'mismatchOvr1dp': int(bad['ovr']),
                  'mismatchMpg2dp': int(bad['mpg']), 'mismatchGRepl4dp': int(bad['gRepl']),
                  'maxAbsOvrUnroundedVsCsv': max_unrounded, 'n': N, 'hasFalse': int((~sf['has']).sum())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {k: sha(v) for k, v in SRC.items()},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False), encoding='utf-8')
    ok = bool(d_pipe < 1e-12 and not any(bad.values())
              and max_unrounded <= 0.05 + 1e-9)
    print(json.dumps({'out': str(OUT), 'check': doc['check'], 'payloadSha256': doc['payloadSha256'], 'pass': ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
