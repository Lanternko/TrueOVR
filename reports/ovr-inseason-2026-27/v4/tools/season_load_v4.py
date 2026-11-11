"""v4 單季載入：2021-22 缺 v3-league／dependence／shot-origin 時降級（同 v3），
mid 用座標規則補回（§3；season_attrs_v4.zone_of）。

2022-23..2024-25 直接用 season_attrs_v4.load_season（area 存在 → 官方分區不變）。
2021-22 的逐季 four-factors 沿用 v3/data/four-factors-2021-22.csv（唯讀輸入）。
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import season_attrs_v4 as SA
from ovr_common import load_json

FF_2021_22 = (Path(__file__).resolve().parents[1] / '..' / 'v3' / 'data'
              / 'four-factors-2021-22.csv').resolve()


def read_ff(path):
    out = {}
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            out[int(r['playerId'])] = {'value': float(r['tovNonSteal_defense']),
                                       'defensePossessions': float(r['defensePossessions'])}
    return out


def _load_2021_22():
    P = SA.season_paths('2021-22')
    box = {}
    for r in SA.result_set(P['box']):
        pid = int(r['PLAYER_ID'])
        b = box.setdefault(pid, {'playerId': pid, 'name': r['PLAYER_NAME'], 'rows': []})
        row = {k: SA._f(r.get(k)) for k in SA.BOX_KEYS}
        row.update({'GAME_ID': r['GAME_ID'], 'GAME_DATE': r['GAME_DATE'], 'TEAM_ID': int(r['TEAM_ID'])})
        b['rows'].append(row)
    bio = {int(r['PLAYER_ID']): r for r in SA.result_set(P['bio'])}
    shots, pbp_games, bad = {}, set(), []
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
            zone = SA.zone_of(a)          # 2021-22 無 area → 座標規則（§3.2）
            s[zone + 'M'] += made
            s[zone + 'A'] += 1
    return {'season': '2021-22', 'paths': P, 'box': box, 'bio': bio, 'v3': {}, 'dep': {},
            'fed': {}, 'originMeta': None, 'ff': {}, 'shots': shots,
            'pbpGames': pbp_games, 'badPbp': bad,
            'allGames': {r['GAME_ID'] for b in box.values() for r in b['rows']}}


def load_season_v4(season, ff_path=None):
    if season == '2021-22':
        sd = _load_2021_22()
        ff_path = ff_path or FF_2021_22
    else:
        sd = SA.load_season(season)
        ff_path = ff_path or (SA.DATA / 'four-factors-2022-25.csv')
        # 逐季 four-factors（v4 只用得到 2021-22；其餘沿用 v3 的逐季檔）
        per = (Path(__file__).resolve().parents[1] / '..' / 'v3' / 'data'
               / f'four-factors-{season}.csv').resolve()
        if per.exists():
            ff_path = per
    sd['ff'] = read_ff(ff_path)
    sd['ffSource'] = str(ff_path)
    return sd
