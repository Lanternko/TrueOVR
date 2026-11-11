"""Path A 共用：Y1–Y6 + D1–D3 統一鏈（preregistration-v5 §5.2、errata-c4）。

不改 v4/v5 既有檔；import v4_common 後在記憶體裡覆寫 CHAIN / PRIOR_PATH / season_cards /
rapm_path / load_target_season / history，讓 fit_w_grid_v4 的 C1/C2/raw 函式直接沿用。

- Y0（2014-15→2015-16）：2014-15 沒有 bio，建不出先驗卡（d0-gate.md §3.1）。
  照 §3.2 它仍計入 E 的起點數，但不在 E_eff，也沒有預測。
- W 不進統一鏈：§3.2 寫明 W 不進 E；它的 x0（v4 c_2021-22）與 Y6 的答案卡是同季兩張卡，
  放進來會讓 2021-22 這個 prior key 撞名。
- 舊季缺層（§5.6、d0-gate §2）：v3-league→onBall/help=70、dependence→creation 觀測=x0、
  shot-origin→short=shortBase、mid 由座標規則。整條 Y 鏈一致缺，所以 Y 起點之間不做 W-missing 排除；
  D 起點的 H 裡，Y 起點對 short/creation 視同 W-missing（同 v4 §4.3 的理由：兩端資料層不同）。
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
sys.path.insert(0, str(HERE))
import v4_common as base  # noqa: E402
import season_attrs_v4 as SA  # noqa: E402
import v5_common as V5C  # noqa: E402  (install() 先跑 v5 的覆寫，下面再蓋掉)
from ovr_common import load_json  # noqa: E402

PATHA = base.REPORT / 'v5' / 'pathA'
PA_DATA = PATHA / 'data'
PA_CARDS = PATHA / 'cards'
PA_RAPM = PATHA / 'rapm'
PA_BACKTEST = PATHA / 'backtest'

PA_SEASONS = ['2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22']
FF_PATH = {s: base.ROOT / 'data/defense-seventh' / s / 'four-factors.csv' for s in PA_SEASONS[:-1]}
FF_PATH['2021-22'] = PATHA / 'ff-2021-22' / 'four-factors.csv'

CHAIN_Y = {
    'Y0': {'prior': '2014-15', 'target': '2015-16', 'pred': '2014-15',
           'ans': '2014-15_2015-16', 'judge': False, 'buildable': False},
    'Y1': {'prior': '2015-16', 'target': '2016-17', 'pred': '2014-15_2015-16',
           'ans': '2014-15_2016-17', 'judge': False},
    'Y2': {'prior': '2016-17', 'target': '2017-18', 'pred': '2014-15_2016-17',
           'ans': '2014-15_2017-18', 'judge': False},
    'Y3': {'prior': '2017-18', 'target': '2018-19', 'pred': '2014-15_2017-18',
           'ans': '2015-16_2018-19', 'judge': True},
    'Y4': {'prior': '2018-19', 'target': '2019-20', 'pred': '2015-16_2018-19',
           'ans': '2016-17_2019-20', 'judge': False},      # COVID 目標，§5.5
    'Y5': {'prior': '2019-20', 'target': '2020-21', 'pred': '2016-17_2019-20',
           'ans': '2017-18_2020-21', 'judge': True},
    'Y6': {'prior': '2020-21', 'target': '2021-22', 'pred': '2017-18_2020-21',
           'ans': '2018-19_2021-22', 'judge': True},
}
CHAIN_D = {k: dict(V5C.CHAIN_V5[k]) for k in ('D1', 'D2', 'D3')}
for _k in CHAIN_D:
    CHAIN_D[_k]['judge'] = False          # 已看過 → 次要
CHAIN_U = {**CHAIN_Y, **CHAIN_D}
ORDER = list(CHAIN_U)                     # Y0..Y6, D1, D2, D3
BUILT = [s for s in ORDER if CHAIN_U[s].get('buildable', True)]
FRESH = ['Y3', 'Y5', 'Y6']                # §5.2 表的新鮮主判定（再經 §3.2 門檻）
Y_STARTS = [s for s in ORDER if s.startswith('Y')]

# 每隊例行賽場數（errata §2：2019-20 用各隊實際場數，另行計算）
G_SEASON = {s: 82 for s in PA_SEASONS + ['2022-23', '2023-24', '2024-25', '2025-26']}
G_SEASON['2020-21'] = 72

PRIOR_PATH_U = dict(V5C.PRIOR_PATH_V5)
for _s in PA_SEASONS:
    PRIOR_PATH_U[_s] = PA_DATA / f'prior-{_s}.json'

_orig = {'season_cards': base.season_cards, 'season_cards_cards': base.season_cards_cards,
         'rapm_path': base.rapm_path, 'load_target_season': base.load_target_season}


def season_cards(season):
    if season in PA_SEASONS:
        doc = load_json(PA_DATA / f'season-cards-{season}.json')
        return doc['priors'], doc['pools']
    return _orig['season_cards'](season)


def season_cards_cards(season):
    if season in PA_SEASONS:
        doc = load_json(PA_DATA / f'season-cards-{season}.json')
        return {int(k): v for k, v in doc['cards'].items()}
    return _orig['season_cards_cards'](season)


def rapm_path(name):
    p = PA_RAPM / f'pipe-{name}.csv'
    if name is not None and p.exists():
        return p
    return _orig['rapm_path'](name)


def read_ff(path):
    out = {}
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            out[int(r['playerId'])] = {'value': float(r['tovNonSteal_defense']),
                                       'defensePossessions': float(r['defensePossessions'])}
    return out


def load_season_pa(season, with_pbp=True):
    """舊季載入：season_load_v4._load_2021_22 的逐季通用版（缺層照 d0-gate §2 降級）。"""
    P = SA.season_paths(season)
    box = {}
    for r in SA.result_set(P['box']):
        pid = int(r['PLAYER_ID'])
        b = box.setdefault(pid, {'playerId': pid, 'name': r['PLAYER_NAME'], 'rows': []})
        row = {k: SA._f(r.get(k)) for k in SA.BOX_KEYS}
        row.update({'GAME_ID': r['GAME_ID'], 'GAME_DATE': r['GAME_DATE'], 'TEAM_ID': int(r['TEAM_ID'])})
        b['rows'].append(row)
    bio = {int(r['PLAYER_ID']): r for r in SA.result_set(P['bio'])}
    shots, pbp_games, bad = {}, set(), []
    if with_pbp:
        for path in sorted(P['pbp'].glob('*.json')):
            try:
                actions = load_json(path)['data']['game']['actions']
            except Exception as exc:
                bad.append({'file': path.name, 'error': str(exc)})
                continue
            pbp_games.add(path.stem)
            for a in actions:
                if a.get('isFieldGoal') != 1 or a.get('personId') in (None, 0):
                    continue
                if a.get('shotResult') not in ('Made', 'Missed') or a.get('actionType') != '2pt':
                    continue
                key = (int(a['personId']), path.stem)
                s = shots.setdefault(key, {'midM': 0, 'midA': 0, 'shortM': 0, 'shortA': 0})
                made = 1 if a['shotResult'] == 'Made' else 0
                zone = SA.zone_of(a)
                s[zone + 'M'] += made
                s[zone + 'A'] += 1
    sd = {'season': season, 'paths': P, 'box': box, 'bio': bio, 'v3': {}, 'dep': {},
          'fed': {}, 'originMeta': None, 'ff': read_ff(FF_PATH[season]),
          'ffSource': str(FF_PATH[season]), 'shots': shots,
          'pbpGames': pbp_games, 'badPbp': bad,
          'allGames': {r['GAME_ID'] for b in box.values() for r in b['rows']}}
    sd['teamRows'] = SA.result_set(P['team_games'])
    return sd


def load_target_season(season):
    if season not in PA_SEASONS:
        return _orig['load_target_season'](season)
    key = ('target', season)
    if key not in base._CACHE:
        base._CACHE[key] = load_season_pa(season)
    return base._CACHE[key]


def history(s):
    return [h for h in ORDER[:ORDER.index(s)]]


def history_for_attr(s, a):
    """w / δ² 的配對來源：只用建得出先驗卡的起點（Y0 沒有 2014-15 先驗卡，配對為空）。"""
    hs = [h for h in history(s) if h in BUILT]
    if s.startswith('D'):
        hs = [h for h in hs if not (h.startswith('Y') and a in base.W_MISSING)]
    return hs


def E_of(s):
    """§3.2 E(s)：比 s 早、有答案卡的起點（W 不在統一鏈）。"""
    return history(s)


def install():
    base.CHAIN = CHAIN_U
    base.CHAIN_BY_PRIOR = {v['prior']: v['target'] for v in CHAIN_U.values()}
    base.PRIOR_PATH = PRIOR_PATH_U
    base.HIST = list(ORDER)
    base.season_cards = season_cards
    base.season_cards_cards = season_cards_cards
    base.rapm_path = rapm_path
    base.load_target_season = load_target_season
    base.history = history
    base.history_for_attr = history_for_attr
    base._PIPE_CACHE.clear()


def answer_card_path(start):
    return PA_CARDS / f"{CHAIN_U[start]['target']}.csv"


def target_ovr(start):
    if start.startswith('Y'):
        rows = base.load_csv(answer_card_path(start))
        return {int(r['playerId']): float(r['ovr']) for r in rows}
    return V5C.target_ovr(start)


def games_per_team(season):
    sd = load_target_season(season)
    cnt = {}
    for r in sd['teamRows']:
        cnt[int(r['TEAM_ID'])] = cnt.get(int(r['TEAM_ID']), 0) + 1
    return cnt
