"""v2 共用：逐人 k_eff（§2.5）、漂移檔讀取、可靠度讀取。

k_eff,a,i = σ²_a / P_a,i，P_a,i = δ²_a + σ²_a / n_i^p，夾在 [0.02·nRef_a, 50·nRef_a]。
τ²（fit/reliability.csv 的 tau2）在本檔完全不出現於收縮式，只當報告對照。
樣本數 key 與 season_attrs／inseason_common 一致；本檔不讀任何目標季資料。
"""
import csv
import math

from ovr_common import FIT, OUTDIR, ROOT, load_json

V2 = OUTDIR / 'v2'
V2_FIT = V2 / 'fit'
V2_VALIDATION = V2 / 'validation'
V2_PREDICTIONS = V2 / 'predictions'

# 凍結 v58 H1-m0 管線常數檔（§0：工具與常數全凍結；2025-26 校準的正式卡片 summary）。
# 只在 P3／S3／S4 載入常數，不含任何目標季逐場或彙總表現資料。
FROZEN_SUMMARY = ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/summary.json'

SAMPLE_KEY = {'long': 'fg3a', 'mid': 'midA', 'short': 'shortA', 'ft': 'fta', 'drive': 'fga',
              'tovSkill': 'possDen', 'pass': 'min', 'rebound': 'min', 'stamina': 'gp',
              'creation': 'min', 'pressure': 'defensePossessions'}
UPDATABLE = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'stamina',
             'creation', 'pressure']


def sample_n(card, attr):
    return float(card.get('sample', {}).get(SAMPLE_KEY[attr], 0.0))


def load_reliability():
    """fit/reliability.csv 的 2022-25 列：sigma2／tau2／nRef／k（v1 對照）。"""
    rows = list(csv.DictReader(open(FIT / 'reliability.csv', encoding='utf-8')))
    return {r['attr']: {'k': float(r['k']), 'sigma2': float(r['sigma2']),
                        'tau2': float(r['tau2']), 'nRef': float(r['nRef'])}
            for r in rows if r['season'] == '2022-25'}


def k_eff(delta2, sigma2, n_prior, n_ref):
    """單一球員單一能力值的 k_eff（§2.5），含夾擠。n_prior<=0 時視為未知先驗 → 上界。"""
    if n_prior > 0 and math.isfinite(n_prior):
        p = delta2 + sigma2 / n_prior
        k = sigma2 / p if p > 0 else 50.0 * n_ref
    else:
        k = 50.0 * n_ref
    return min(max(k, 0.02 * n_ref), 50.0 * n_ref)


def k_eff_table(prior_cards, delta2, rel):
    """{pid: {attr: k}}，prior_cards 為部署／驗證季的先驗卡（提供 n^p）。"""
    out = {}
    for pid, card in prior_cards.items():
        row = {}
        for a in UPDATABLE:
            row[a] = k_eff(delta2[a], rel[a]['sigma2'], sample_n(card, a), rel[a]['nRef'])
        out[pid] = row
    return out


def load_drift():
    return load_json(V2_FIT / 'drift.json')


def chosen_delta2(drift=None):
    d = drift or load_drift()
    if 'chosen' not in d:
        raise SystemExit('drift.json has no chosen candidate yet; run validate_2024_25.py --select')
    return {a: float(v) for a, v in d['delta2'][d['chosen']].items()}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def quantile(xs, q):
    """線性內插分位數（與 numpy 預設同義，避免額外相依）。"""
    s = sorted(xs)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(s[lo])
    return float(s[lo] + (s[hi] - s[lo]) * (pos - lo))
