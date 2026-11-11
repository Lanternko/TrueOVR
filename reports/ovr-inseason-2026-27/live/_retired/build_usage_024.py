raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-107 retired guard
"""E-091：產生 card 0.2.4 用人層的「凍結特徵」（2025-26 全季），給賽中 inseason 0.2.2 用。

不擬合任何東西。特徵一律呼叫 reports/card-0.2.3+E084-current-target/e084.py 的 load_data / classify / scope_feats /
design 重算（不重抄公式）；係數、r_repl、錨點讀同資料夾 results.json（card 0.2.4 的來源）。

輸出：live/usage-2025-26-card024.json（每人 has、L、a、y、v、d、age、mpgAvail、p、predNew；含來源檔 sha256）。
驗證（失敗 exit 1）：以這些特徵＋coefficients.card 套回，r_repl／錨點對 results.json 差 <1e-9，
582 人 ovr（.1f）、mpg（.2f）、gRepl（.4f）與 reports/card-0.2.4/ranking.csv 逐格相同，未四捨五入的 ovr 差另列。

用法：python -I reports/ovr-inseason-2026-27/live/build_usage_024.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import os  # noqa: E402
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E084D = ROOT / 'reports/card-0.2.3+E084-current-target'
sys.path.insert(0, str(E084D))
import numpy as np  # noqa: E402
import e084  # noqa: E402

OUT = HERE / 'usage-2025-26-card024.json'
CARD_RANKING = ROOT / 'reports/card-0.2.4/ranking.csv'
CARD_SUMMARY = ROOT / 'reports/card-0.2.4/summary.json'
RESULTS = E084D / 'results.json'
SRC = {
    'e084.py': E084D / 'e084.py',
    'results.json': RESULTS,
    'card-0.2.4 ranking.csv': CARD_RANKING,
    'card-0.2.4 summary.json': CARD_SUMMARY,
    'card-0.2.2 primary pred.csv': e084.C022 / 'primary/pred.csv',
    '2025-26 player-games': ROOT / 'data/season-source/player-games.json',
    '2025-26 team-games': ROOT / 'data/season-source/team-games.json',
    '2025-26 dnp': ROOT / 'data/season-source/dnp-2025-26.json',
    'bio (age)': ROOT / 'data/benchmark-source/bio.json',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    res = json.loads(RESULTS.read_text(encoding='utf-8'))
    summ = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))
    assert sha(CARD_RANKING) == summ['ranking_csv_sha256'], 'card 0.2.4 ranking.csv sha256 與 summary.json 不符'
    assert sha(CARD_RANKING) == res['ranking_csv_sha256'], 'card 0.2.4 ranking.csv sha256 與 results.json 不符'
    coef = np.array([res['coefficients']['card'][k] for k in e084.COEF_NAMES])
    r_repl, anc = res['card']['r_repl'], res['card']['anchors']

    e084.load_data()
    C = e084.classify(e084.BASE_OPTS)
    sf = e084.scope_feats('full', e084.D['prim'], C, e084.BASE_OPTS)
    pids, N = sf['pids'], sf['n']
    X = e084.design(sf, np.arange(N), 9)
    pred_new = np.where(sf['has'], X @ coef, sf['p'])
    pool = sf['MIN'] >= e084.POOL_MIN
    r_chk = e084.qf(pred_new, pool, 10)
    g = (pred_new - r_chk) * sf['mp'] / 36
    anc_chk = {'PR1': e084.qf(g, pool, 1), 'PR50': e084.qf(g, pool, 50), 'PR99': e084.qf(g, pool, 99)}
    d_r = abs(r_chk - r_repl)
    d_anc = max(abs(anc_chk[k] - anc[k]) for k in anc)
    # 用 results.json 的 r_repl／錨點（與重算同到 1e-9）
    g_use = (pred_new - r_repl) * sf['mp'] / 36
    ovr = e084.two_segment(g_use, anc['PR1'], anc['PR50'], anc['PR99'])

    names = [e084.D['prim'][q]['name'] for q in pids]
    card = {r['name']: r for r in csv.DictReader(CARD_RANKING.open(encoding='utf-8'))}
    assert len(card) == N == 582 and set(card) == set(names), '名單與 card 0.2.4 不一致'
    bad = {'ovr': 0, 'mpg': 0, 'gRepl': 0}
    max_unrounded = 0.0
    for i, nm in enumerate(names):
        c = card[nm]
        bad['ovr'] += f'{ovr[i]:.1f}' != c['ovr']
        bad['mpg'] += f"{sf['mp'][i]:.2f}" != c['mpg']
        bad['gRepl'] += f'{g_use[i]:.4f}' != c['gRepl']
        max_unrounded = max(max_unrounded, abs(ovr[i] - float(c['ovr'])))
    players = {}
    for i, q in enumerate(pids):
        players[str(q)] = {
            'name': names[i], 'has': bool(sf['has'][i]), 'L': float(sf['L'][i]), 'a': float(sf['a'][i]),
            'y': float(sf['y'][i]), 'v': float(sf['v'][i]), 'd': float(sf['d'][i]),
            'age': sf['age'][i], 'mpgAvail': float(sf['mp'][i]), 'p': float(sf['p'][i]), 'predNew': float(pred_new[i]),
            'ovrCard': float(card[names[i]]['ovr']),
        }
    payload = {'coef': dict(zip(e084.COEF_NAMES, map(float, coef))), 'rRepl': r_repl, 'anchors': anc, 'players': players}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    doc = {
        'doc': 'E-091 card 0.2.4 用人層凍結特徵（2025-26 全季；e084.scope_feats("full") 重算，不擬合）',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（has=True）；has=False → predNew = p',
        'check': {'rReplRecomputeDiff': d_r, 'anchorsRecomputeDiff': d_anc, 'mismatchOvr1dp': int(bad['ovr']),
                  'mismatchMpg2dp': int(bad['mpg']), 'mismatchGRepl4dp': int(bad['gRepl']),
                  'maxAbsOvrUnroundedVsCsv': max_unrounded, 'n': N, 'hasFalse': int((~sf['has']).sum())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {k: sha(v) for k, v in SRC.items()},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False), encoding='utf-8')
    ok = bool(d_r < 1e-9 and d_anc < 1e-9 and not any(bad.values()) and max_unrounded <= 0.05 + 1e-9)
    print(json.dumps({'out': str(OUT), 'check': doc['check'], 'payloadSha256': doc['payloadSha256'], 'pass': ok},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
