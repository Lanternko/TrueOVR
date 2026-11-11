"""v5 共用：CHAIN（§R.2 預測、§R.3 答案）、v5 prior、v5-min 答案卡。

不改 v4 檔；import v4_common 後在記憶體裡覆寫 CHAIN / PRIOR_PATH / 管線快取。
- pred：D1 2021-22_2022-23、D2 2021-22_2023-24、D3 2021-22_2024-25（§R.2）
- ans ：D1 2021-22_2023-24、D2 2021-22_2024-25、D3 正式卡 card-H1-m0（§R.3）
- prior：v5/data/prior-<season>-v5.json（MIN/GP 跨隊加總，§R.7）
- 答案卡：v5/cards/<target>-v5-min.csv（D1/D2）、正式卡 ranking.csv（D3）

λ、w 不重挑（任務限制「不調參數」）：沿用 v4/fit/lambda.json、v4/fit/w-grid.json。
N=82 只報告；§3.1 寫死 λ_82 = λ_20，w 也照 N=20（v4 沒有 N=82 的 w，另挑會變成調參數）。
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V4_TOOLS = HERE.parents[1] / 'v4' / 'tools'
sys.path.insert(0, str(V4_TOOLS))
sys.path.insert(0, str(HERE))
import v4_common as base  # noqa: E402

V5 = base.REPORT / 'v5'
V5_DATA = V5 / 'data'
V5_CARDS = V5 / 'cards'
V5_FIT = V5 / 'fit'
V5_BACKTEST = V5 / 'backtest'

PRIOR_PATH_V5 = {s: V5_DATA / f'prior-{s}-v5.json' for s in base.SEASONS}
ANS_CARD = {'D1': V5_CARDS / '2023-24-v5-min.csv',
            'D2': V5_CARDS / '2024-25-v5-min.csv'}
CHAIN_V5 = {
    'W':  {'prior': '2021-22', 'target': '2022-23', 'pred': None,
           'ans': '2021-22_2022-23', 'judge': False},
    'D1': {'prior': '2022-23', 'target': '2023-24', 'pred': '2021-22_2022-23',
           'ans': '2021-22_2023-24', 'judge': True},
    'D2': {'prior': '2023-24', 'target': '2024-25', 'pred': '2021-22_2023-24',
           'ans': '2021-22_2024-25', 'judge': True},
    'D3': {'prior': '2024-25', 'target': '2025-26', 'pred': '2021-22_2024-25',
           'ans': 'formal-card-H1-m0', 'judge': True},
    # S* 的預測 RAPM 是 `reports/impact-rapm/rapm.csv`（§R.2 四季合併欄），
    # 不是 v3/v4 的 rapm-<name>.csv；本輪不執行 S*，只把路徑記在這裡避免誤用。
    'S*': {'prior': '2025-26', 'target': '2026-27', 'pred': '2022-23_2025-26',
           'ans': None, 'judge': False},
}
N_FIT = {82: 20}          # §3.1：λ_82 = λ_20；w 同樣沿用 N=20
N_LIST = list(base.N_LIST) + [82]
STARTS = ['D1', 'D2', 'D3']
# §R.2：S* 的預測 RAPM 檔（四季合併欄 pooledNet）；本輪不執行 S*，只記錄。
S_STAR_RAPM = base.ROOT / 'reports/impact-rapm/rapm.csv'


def install():
    base.CHAIN = CHAIN_V5
    base.CHAIN_BY_PRIOR = {v['prior']: v['target'] for v in CHAIN_V5.values()}
    base.PRIOR_PATH = PRIOR_PATH_V5
    base._PIPE_CACHE.clear()


install()


def fit_n(N):
    return N_FIT.get(N, N)


def wgrid_from(grid):
    return {s: {a: {N: grid['w'][s]['attrs'][a]['w'][str(fit_n(N))] for N in N_LIST}
                for a in base.UPD} for s in STARTS}


def lam_for(lam, s, N):
    return lam[s][str(fit_n(N))]


def rapm_files():
    out = {}
    for s in STARTS:
        p = base.rapm_path(CHAIN_V5[s]['pred'])
        out[s] = {'predTag': CHAIN_V5[s]['pred'],
                  'predFile': p.relative_to(base.ROOT).as_posix(),
                  'predSha256': base.sha256_file(p),
                  'answer': (ANS_CARD[s].relative_to(base.ROOT).as_posix()
                             if s in ANS_CARD else 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv')}
    for s, p in ANS_CARD.items():
        out[s]['answerSha256'] = base.sha256_file(p)
    out['D3']['answerSha256'] = base.sha256_file(
        base.ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv')
    out['S*'] = {'predTag': CHAIN_V5['S*']['pred'],
                 'predFile': S_STAR_RAPM.relative_to(base.ROOT).as_posix(),
                 'predSha256': (base.sha256_file(S_STAR_RAPM) if S_STAR_RAPM.exists() else None),
                 'answer': None, 'ran': False,
                 'note': '§R.2 四季合併欄；本輪不執行 S*（不讀 2026-27）'}
    return out


def target_ovr(start):
    """答案卡 OVR（D1/D2 用 v5-min 卡；D3 用正式卡）。"""
    if start == 'D3':
        by_name, _ = base.formal_card_ovr()
        cards, _ = base.deployment('D3')
        return {pid: by_name[c['name']]['ovr'] for pid, c in cards.items()
                if c['name'] in by_name}
    rows = base.load_csv(ANS_CARD[start])
    return {int(r['playerId']): float(r['ovr']) for r in rows}


def sha(path):
    return base.sha256_file(path)


def write_json(path, obj):
    return base.write_json(path, obj)


def write_csv(path, rows, head=None):
    return base.write_csv(path, rows, head)


def load_csv(path):
    return base.load_csv(path)


def load_json(path):
    return base.load_json(path)
