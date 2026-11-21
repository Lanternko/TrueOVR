"""v4 共用：起點鏈（含 S*）、卡片載入、視窗、人群、凍結管線、決定性紀錄。

對應 preregistration-v4.md：
  §2.1  x̂ = clip(x0 + λ(N)·w_a(N)·(y_adj − x0), 40, 99)
  §2.3  λ 只用嚴格更早起點選：E(D2)={D1}、E(D3)={D1,D2}、E(S*)={D1,D2,D3}；λ(D1)=1
  §3    W-missing 只剩 short(sTilde)/creation(dependence)；mid 由座標規則補回
  §5.1  起點鏈；S* 的預測用 RAPM = 2021-22..2024-25
  §5.2  人群：先驗季 MIN>=500、目標季全季 MIN>=500、窗口 MIN>=1

不修改 v3/、tools/、data/：v3 的既有輸出（prior-2022-23..2024-25、rapm-*）
只當唯讀輸入；本檔新增的一切都寫在 v4/。
"""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / 'reports/ovr-inseason-2026-27'
V4 = REPORT / 'v4'
V4_DATA = V4 / 'data'
V4_CARDS = V4 / 'cards'
V4_FIT = V4 / 'fit'
V4_BACKTEST = V4 / 'backtest'
V4_INTERVALS = V4 / 'intervals'
V4_FROZEN = V4 / 'frozen'
V4_LIVE = V4 / 'live'
V3 = REPORT / 'v3'
V3_DATA = V3 / 'data'
V3_BACKTEST = V3 / 'backtest'
V3_FIT = V3 / 'fit'
TOOLS = REPORT / 'tools'
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ovr_common import ATTRS, DATA, load_json, write_json  # noqa: E402
import season_attrs_v4 as SA  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402
import v2_common as V2  # noqa: E402

assert ROOT == Path(__file__).resolve().parents[4]
SEED = 20261026
N_LIST = [3, 5, 10, 20]
LAMBDA_GRID = [round(0.05 * k, 2) for k in range(21)]
FROZEN_ATTRS = IC.FROZEN_ATTRS                 # physique/onBall/help/heightInches
UPD = V2.UPDATABLE                             # 11 項可更新
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
HIST = ['W', 'D1', 'D2', 'D3']                 # 有答案卡、可回測的起點
JUDGE = ['D2', 'D3']                           # C3 只在這兩個判定
CHAIN = {
    'W':  {'prior': '2021-22', 'target': '2022-23', 'pred': None,
           'ans': '2021-22', 'judge': False},
    'D1': {'prior': '2022-23', 'target': '2023-24', 'pred': '2021-22',
           'ans': '2021-22_2022-23', 'judge': True},
    'D2': {'prior': '2023-24', 'target': '2024-25', 'pred': '2021-22_2022-23',
           'ans': '2021-22_2023-24', 'judge': True},
    'D3': {'prior': '2024-25', 'target': '2025-26', 'pred': '2021-22_2023-24',
           'ans': 'formal-card-H1-m0', 'judge': True},
    'S*': {'prior': '2025-26', 'target': '2026-27', 'pred': '2021-22_2024-25',
           'ans': None, 'judge': False},
}
# §3.5：mid 已用座標規則補回，只剩 short/creation 是 W-missing
W_MISSING = {'short': 'sTilde', 'creation': 'dependence'}
CHAIN_BY_PRIOR = {v['prior']: v['target'] for v in CHAIN.values()}


def candidates(s):
    """§2.3 E(s,N)：H(s) 中 judge=true 的起點；W 不進 E。"""
    return [h for h in history(s) if CHAIN[h]['judge']]


def history(s):
    if s == 'S*':
        return list(HIST)
    return HIST[:HIST.index(s)]


def history_for_attr(s, a):
    """§4.3（v3 規則沿用）：缺層的能力值，W 不進該項 H(s)。"""
    return [h for h in history(s) if not (h == 'W' and a in W_MISSING)]


# ---------------------------------------------------------------- 基本工具
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd=None, check=True):
    kwargs = {'cwd': str(cwd or ROOT), 'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    p = subprocess.run(cmd, **kwargs)
    out = p.stdout.decode('utf-8', 'replace')
    if check and p.returncode != 0:
        raise RuntimeError(f'command failed ({p.returncode}): {cmd}\n{out[-4000:]}')
    return p.returncode, out


def determinism(step, files, note=''):
    path = V4 / 'determinism-hashes.txt'
    lines = []
    for f in sorted(files):
        f = Path(f)
        if f.exists():
            lines.append(f'{sha256_file(f)}  {f.relative_to(ROOT).as_posix()}')
    block = f'# {step}' + (f' ({note})' if note else '') + '\n' + '\n'.join(lines) + '\n'
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(block)
    return block


def load_csv(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, head=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = head or (list(rows[0].keys()) if rows else [])
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=head, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- 卡片與映射
PRIOR_PATH = {
    '2021-22': V4_DATA / 'prior-2021-22.json',
    '2022-23': V3_DATA / 'prior-2022-23.json',
    '2023-24': V3_DATA / 'prior-2023-24.json',
    '2024-25': V3_DATA / 'prior-2024-25.json',
    '2025-26': V4_DATA / 'prior-2025-26.json',
}


def load_card(season):
    doc = load_json(PRIOR_PATH[season])
    return {int(c['playerId']): c for c in doc['players']}, doc


def season_cards(season):
    if season == '2021-22':
        doc = load_json(V4_DATA / 'season-cards-2021-22.json')
        return doc['priors'], doc['pools']
    doc = load_json(DATA / 'season-cards-2022-25.json')
    return doc['seasons'][season]['priors'], doc['seasons'][season]['pools']


def season_cards_cards(season):
    if season == '2021-22':
        doc = load_json(V4_DATA / 'season-cards-2021-22.json')
        return {int(k): v for k, v in doc['cards'].items()}
    doc = load_json(DATA / 'season-cards-2022-25.json')
    return {int(k): v for k, v in doc['seasons'][season]['cards'].items()}


def mapping_for(prior):
    priors, pools = season_cards(prior)
    return {'priors': priors, 'pools': pools}


def usg_prior(season):
    return {p: float(c.get('usg') or 0.0) * 100.0 for p, c in season_cards_cards(season).items()}


# ---------------------------------------------------------------- 視窗
_CACHE = {}


def load_target_season(season):
    """目標季逐場資料（同 v3：2025-26 走 inseason_common，其他季走 season_attrs）。"""
    key = ('target', season)
    if key in _CACHE:
        return _CACHE[key]
    if season == '2025-26':
        sd = IC.load_target_season()
    else:
        sd = SA.load_season(season)
        sd['teamRows'] = SA.result_set(sd['paths']['team_games'])
    sd = dict(sd)
    sd['season'] = season
    _CACHE[key] = sd
    return sd


def full_minutes(sd):
    return {pid: sum(r['MIN'] for r in b['rows']) for pid, b in sd['box'].items()}


def windows(prior, N):
    key = ('win', prior, N)
    if key in _CACHE:
        return _CACHE[key]
    target = CHAIN_BY_PRIOR[prior]
    sd = load_target_season(target)
    prior_cards, _ = load_card(prior)
    received = IC.received_prior(prior)
    w = IC.window_cards(sd, N, mapping_for(prior), prior_cards, received)
    _CACHE[key] = (w, sd)
    return w, sd


def sample_of(card, attr):
    return IC.sample_of(card, attr)


def usage_adjust(x0, w, attr, u_prior):
    y, x0v = w[attr], x0[attr]
    u_obs = w['u_proxy']
    if u_prior <= 0 or u_obs <= 0:
        return y
    ratio = u_obs / u_prior
    if ratio >= 1.1 or ratio <= 0.9:
        return x0v + (y - x0v) * min(1.0, u_prior / u_obs)
    return y


def population(prior, N):
    """§5.2（v3 定義）：先驗季 MIN>=500、目標季全季 MIN>=500、窗口 MIN>=1。"""
    prior_cards, _ = load_card(prior)
    w, sd = windows(prior, N)
    tmin = full_minutes(sd)
    out = []
    for pid, card in prior_cards.items():
        if float(card['observed']['MIN']) < 500:
            continue
        if tmin.get(pid, 0.0) < 500:
            continue
        if w.get(pid, {}).get('MIN', 0.0) < 1:
            continue
        out.append(pid)
    return sorted(out)


# ---------------------------------------------------------------- 管線與答案
def deployment(start):
    cards, _ = load_card(CHAIN[start]['prior'])
    attrs = {pid: {a: float(c[a]) for a in ATTRS} for pid, c in cards.items()}
    return cards, attrs


def rapm_path(name):
    if name is None:
        return V3_DATA / 'rapm-empty.csv'
    p = V4_DATA / f'rapm-{name}.csv'
    return p if p.exists() else V3_DATA / f'rapm-{name}.csv'


_PIPE_CACHE = {}


def pipeline_for(start):
    from ovr_pipeline import OVRPipeline
    if start not in _PIPE_CACHE:
        cards, _ = load_card(CHAIN[start]['prior'])
        _PIPE_CACHE[start] = OVRPipeline(str(V2.FROZEN_SUMMARY),
                                         str(rapm_path(CHAIN[start]['pred'])), cards)
    return _PIPE_CACHE[start]


def formal_card_ovr():
    path = ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv'
    rows = load_csv(path)
    by_name = {}
    for r in rows:
        by_name.setdefault(r['name'], []).append(r)
    return {name: {'ovr': float(v[0]['ovr']), 'row': v[0]} for name, v in by_name.items()}, rows


def clip(v):
    return max(40.0, min(99.0, v))


if __name__ == '__main__':
    print(json.dumps({'root': str(ROOT), 'hist': HIST, 'judge': JUDGE,
                      'candidates': {s: candidates(s) for s in HIST + ['S*']}},
                     ensure_ascii=False))
