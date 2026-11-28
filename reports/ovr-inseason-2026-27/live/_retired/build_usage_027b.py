raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-107 retired guard
"""E-128：產生 card 0.2.7b 用人層的「凍結特徵」與係數（2025-26 全季），給賽中 CARD_MODE=027b 用（照 build_usage_027.py；pools 用 rebase-027a/cards/c0，pipeline 用 cards/e123a，照 e123a.py cards_stage）。

card 0.2.7b 的用人層由 reports/card-0.2.6+E107-defense-UL/e107.py 產生：唯讀匯入 reports/card-0.2.5+E094-defense-ceiling/e094.py，
set_card_dir(cards/UL6) 後 M.pipeline(BASE_OPTS, pools, 'season')；係數 coef['card']、r_repl、錨點都是該次 pipeline 的結果
（沒有另存檔），所以這裡照同一流程重跑一次（決定性，不擬合任何新東西），再核對：
  - 錨點對 phase2.json reportOnly.anchors.UL6 差 < 1e-9；
  - 582 人 ovr（.1f）、mpg（.2f）、gRepl（.4f）與 reports/card-0.2.7b/ranking.csv 逐格相同；未四捨五入 ovr 差另列（≤ 0.05）。
分鐘權重 W = w_sat(mpg)（scale 15）。
輸出：live/usage-2025-26-card027b.json（每人 has、L、a、y、v、d、age、mpgAvail、p、predNew；係數、rRepl、錨點；來源 sha256）。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_027.py
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

_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
_TMP = Path(tempfile.mkdtemp(prefix='e111-usage-'))
M.HERE, M.W, M.CARDS = RB, _TMP / 'work', RB / 'cards'    # 不寫任何檔（pipeline 本身不寫）

OUT = HERE / 'usage-2025-26-card027b.json'
CARD_RANKING = ROOT / 'reports/card-0.2.7b/ranking.csv'
CARD_SUMMARY = ROOT / 'reports/card-0.2.7b/summary.json'
PHASE2 = RB / 'work/cards-result.json'
SRC = {
    'e094.py': E94 / 'e094.py',
    'e107.py': UL / 'e107.py',
    'cards-result.json': PHASE2,
    'card-0.2.7b ranking.csv': CARD_RANKING,
    'card-0.2.7b summary.json': CARD_SUMMARY,
    'e123a.py': RB / 'e123a.py',
    'e123a primary pred.csv': RB / 'cards/e123a/primary/pred.csv',
    'e123a fitA pred.csv': RB / 'cards/e123a/fitA/pred.csv',
    'e123a fitB pred.csv': RB / 'cards/e123a/fitB/pred.csv',
    '2025-26 player-games': ROOT / 'data/season-source/player-games.json',
    '2025-26 team-games': ROOT / 'data/season-source/team-games.json',
    '2025-26 dnp': ROOT / 'data/season-source/dnp-2025-26.json',
    'bio (age)': ROOT / 'data/benchmark-source/bio.json',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    summ = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))
    assert sha(CARD_RANKING) == summ['ranking_csv_sha256'], 'card 0.2.7b ranking.csv sha256 與 summary.json 不符'
    anc_p2 = json.loads(PHASE2.read_text(encoding='utf-8'))['anchors']
    M.load_data()
    M.set_card_dir(RB / 'cards/c0')
    pools = M.build_pools()
    M.set_card_dir(RB / 'cards/e123a')
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    coef = np.array([r_['coef']['card'][k] for k in M.COEF_NAMES])
    r_repl, anc = float(r_['card']['r_repl']), {k: float(v) for k, v in r_['card']['anchors'].items()}
    d_anc_p2 = max(abs(anc[k] - anc_p2[k]) for k in anc_p2)

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
    assert len(card) == N == 582 and set(card) == set(names), '名單與 card 0.2.7b 不一致'
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
        'doc': 'E-111 card 0.2.7b 用人層凍結特徵（2025-26 全季；e094.pipeline(pools@c0, set_card_dir(e123a)) 重跑取係數、r_repl、錨點，'
               'scope_feats("full") 重算特徵，不擬合新參數；W = w_sat(mpg)）',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（has=True）；has=False → predNew = p',
        'check': {'anchorsVsCardsResult': d_anc_p2, 'rReplRecomputeDiff': d_r, 'anchorsRecomputeDiff': d_anc,
                  'predNewVsPipeline': d_pipe, 'mismatchOvr1dp': int(bad['ovr']),
                  'mismatchMpg2dp': int(bad['mpg']), 'mismatchGRepl4dp': int(bad['gRepl']),
                  'maxAbsOvrUnroundedVsCsv': max_unrounded, 'n': N, 'hasFalse': int((~sf['has']).sum())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {k: sha(v) for k, v in SRC.items()},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False), encoding='utf-8')
    ok = bool(d_anc_p2 < 1e-9 and d_r < 1e-9 and d_anc < 1e-9 and d_pipe < 1e-12 and not any(bad.values())
              and max_unrounded <= 0.05 + 1e-9)
    print(json.dumps({'out': str(OUT), 'check': doc['check'], 'payloadSha256': doc['payloadSha256'], 'pass': ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
