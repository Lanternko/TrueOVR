"""v5 Path A §5.1 D0 資料閘門（2014-15..2021-22）。

只掃本機檔案：不下載、不補 0、不用現代身高回填、不讀 2026-27。
輸出 d0-gate.json（表格與判定），人看版在 d0-gate.md。

判定規則（全部照 preregistration-v5 §5.1／§5.6）：
  1. 每季每層列出有／無與場數。
  2. 缺層先看 §5.6 有沒有對應規則：
     - tracking：常數 70（v4 §3.4）
     - dependence：creation=x0／received=0.5（v4 P0 先例）
     - shot-origin：short=shortBase（v4 §3.5）
     - 2K：P3 降級為內部一致性
     以上缺層不擋卡片。
  3. 卡片管線**必要**且 §5.6 沒有建卡規則的層 → 該季「不能進鏈」：
     - bio：身高/體重/AST%/REB% → physique/heightInches/pass/rebound/pos
     - pbp/shot 座標：mid/short/shortBase；沒有 pbp 就沒有投籃分區
     - 每季 four-factors：pressure；pipeline 需要全部 15 項
  4. 任一「不能進鏈」的季被某個 Y 起點用到（先驗季或目標季）→ 該起點失效。
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / 'reports/ovr-inseason-2026-27'
HIST = REPORT / 'v5/history'
V3_DATA = REPORT / 'v3/data'
V4_DATA = REPORT / 'v4/data'
OUTDIR = Path(__file__).resolve().parent

SEASONS = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20',
           '2020-21', '2021-22']
# §5.1：場數用 league schedule 實算；2019-20 含泡泡、2020-21 1080。
# 來源：v5/history/stints/preparation-<season>.json 的 boxGames（PR #5 重建紀錄）；
# 2021-22 沒有 preparation 檔，用本機 manifest 的 1230 場 pbp/box（附錄 A.1）。
EXPECTED_GAMES = {'2014-15': 1230, '2015-16': 1230, '2016-17': 1230, '2017-18': 1230,
                  '2018-19': 1230, '2019-20': 1059, '2020-21': 1080, '2021-22': 1230}
BUBBLE_FROM, BUBBLE_TO = '2020-07-30', '2020-10-11'

# §5.2 Path A 鏈（pred/ans 是 RAPM 季集；檔名照「最大季」慣例）
PATH_A = {
    'Y0': {'prior': '2014-15', 'target': '2015-16',
           'pred': ['2014-15'], 'ans': ['2014-15', '2015-16'], 'judge': False},
    'Y1': {'prior': '2015-16', 'target': '2016-17',
           'pred': ['2014-15', '2015-16'], 'ans': ['2014-15', '2015-16', '2016-17'],
           'judge': False},
    'Y2': {'prior': '2016-17', 'target': '2017-18',
           'pred': ['2014-15', '2015-16', '2016-17'],
           'ans': ['2014-15', '2015-16', '2016-17', '2017-18'], 'judge': False},
    'Y3': {'prior': '2017-18', 'target': '2018-19',
           'pred': ['2014-15', '2015-16', '2016-17', '2017-18'],
           'ans': ['2015-16', '2016-17', '2017-18', '2018-19'], 'judge': True},
    'Y4': {'prior': '2018-19', 'target': '2019-20',
           'pred': ['2015-16', '2016-17', '2017-18', '2018-19'],
           'ans': ['2016-17', '2017-18', '2018-19', '2019-20'], 'judge': False},
    'Y5': {'prior': '2019-20', 'target': '2020-21',
           'pred': ['2016-17', '2017-18', '2018-19', '2019-20'],
           'ans': ['2017-18', '2018-19', '2019-20', '2020-21'], 'judge': True},
    'Y6': {'prior': '2020-21', 'target': '2021-22',
           'pred': ['2017-18', '2018-19', '2019-20', '2020-21'],
           'ans': ['2018-19', '2019-20', '2020-21', '2021-22'], 'judge': True},
    'W':  {'prior': '2021-22', 'target': '2022-23', 'pred': [],
           'ans': ['2021-22', '2022-23'], 'judge': False},
    'D1': {'prior': '2022-23', 'target': '2023-24', 'pred': ['2021-22', '2022-23'],
           'ans': ['2021-22', '2022-23', '2023-24'], 'judge': True},
    'D2': {'prior': '2023-24', 'target': '2024-25',
           'pred': ['2021-22', '2022-23', '2023-24'],
           'ans': ['2021-22', '2022-23', '2023-24', '2024-25'], 'judge': True},
    'D3': {'prior': '2024-25', 'target': '2025-26',
           'pred': ['2021-22', '2022-23', '2023-24', '2024-25'],
           'ans': 'formal-card-H1-m0', 'judge': True},
}
FRESH = ['Y3', 'Y5', 'Y6']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def count_lines(path):
    with open(path, 'rb') as fh:
        return sum(1 for _ in fh)


def count_gz_lines(path):
    with gzip.open(path, 'rb') as fh:
        return sum(1 for _ in fh)


def box_totals(season):
    """PR #5 官方 box 合計：teamId=ALL 是跨隊加總。"""
    path = HIST / f'box-totals-{season}.csv'
    if not path.exists():
        return None
    mins, players = {}, set()
    for r in csv.DictReader(open(path, encoding='utf-8')):
        players.add(int(r['playerId']))
        if r['teamId'] == 'ALL':
            mins[int(r['playerId'])] = float(r['MIN'])
    return {'file': rel(path), 'sha256': sha256(path), 'players': len(players),
            'minutes': mins}


def box_games(season):
    path = HIST / f'box-games-{season}.csv.gz'
    if not path.exists():
        return None
    games, dates, rows = set(), {}, 0
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            rows += 1
            games.add(r['gameId'])
            dates[r['gameId']] = r['gameDate']
    bubble = sum(1 for d in dates.values() if BUBBLE_FROM <= d <= BUBBLE_TO)
    return {'file': rel(path), 'sha256': sha256(path), 'games': len(games),
            'playerGameRows': rows, 'bubbleGames': bubble,
            'dateRange': [min(dates.values()), max(dates.values())]}


LOCAL_BIO_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25']


def local_bio_pids():
    pids = set()
    for s in LOCAL_BIO_SEASONS:
        path = ROOT / 'data/defense-seventh' / s / 'bio.json'
        if not path.exists():
            continue
        doc = read_json(path)
        rs = doc['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        i = rs['headers'].index('PLAYER_ID')
        pids |= {int(r[i]) for r in rs['rowSet']}
    return pids


def bio_coverage(season, totals):
    """本機 bio 只涵蓋 2021-22..2024-25。用「後來還有出賽」的球員算分鐘加權覆蓋率。

    這只是「若硬用未來球季的 bio 回填」的上限；§5.6 明文禁止現代身高回填，
    列出來是為了證明即使違規回填也補不齊。
    """
    if season == '2021-22' or not totals:
        return None
    bio = local_bio_pids()
    have = sum(m for pid, m in totals['minutes'].items() if pid in bio)
    allmin = sum(totals['minutes'].values())
    return {'source': 'data/defense-seventh/{%s}/bio.json 聯集' % ','.join(LOCAL_BIO_SEASONS),
            'minuteWeightedCoverage': round(have / allmin, 4) if allmin else 0.0,
            'playersCovered': sum(1 for pid in totals['minutes'] if pid in bio),
            'players': len(totals['minutes']),
            'note': '§5.6 禁止用未來球季身高回填；此列只證明上限也不足'}


def shot_coverage(season):
    pbp = ROOT / 'data/defense-seventh' / season / 'pbp'
    files = sorted(pbp.glob('*.json')) if pbp.is_dir() else []
    if not files:
        return {'present': False, 'path': rel(pbp), 'files': 0}
    n2 = xy = area = 0
    for path in files:
        actions = read_json(path)['data']['game']['actions']
        for a in actions:
            if (a.get('isFieldGoal') == 1 and a.get('actionType') == '2pt'
                    and a.get('shotResult') in ('Made', 'Missed')):
                n2 += 1
                if a.get('xLegacy') is not None and a.get('yLegacy') is not None:
                    xy += 1
                if a.get('area'):
                    area += 1
    return {'present': True, 'path': rel(pbp), 'files': len(files), 'twoPointers': n2,
            'xyPresent': xy, 'xyCoverage': round(xy / n2, 6) if n2 else None,
            'areaPresent': area, 'areaCoverage': round(area / n2, 6) if n2 else None}


def season_attr_inputs(season, dep_seasons, origin_seasons):
    """season_attrs_v4.season_paths() 的每一個輸入。"""
    base = ROOT / 'data/defense-seventh' / season
    bio_path = base / 'bio.json'
    bio_players = 0
    if bio_path.exists():
        doc = read_json(bio_path)
        s = doc['data']['resultSets']
        s = s[0] if isinstance(s, list) else s
        bio_players = len(s['rowSet'])
    # 路徑偵測：v3 既有檔優先；2014-15..2020-21 由 scripts/fetch_old_seasons_v5_ff.py 寫在 data/defense-seventh/<season>/
    ff = V3_DATA / f'four-factors-{season}.csv'
    if not ff.exists() and (base / 'four-factors.csv').exists():
        ff = base / 'four-factors.csv'
    return {
        'boxPlayerGames': {'file': rel(base / 'player-games.json'),
                           'present': (base / 'player-games.json').exists()},
        'bio': {'file': rel(bio_path), 'present': bio_path.exists(),
                'players': bio_players},
        'pbpDir': {'file': rel(base / 'pbp'),
                   'present': (base / 'pbp').is_dir(),
                   'files': len(list((base / 'pbp').glob('*.json')))
                   if (base / 'pbp').is_dir() else 0},
        'teamGames': {'file': rel(base / 'team-games.json'),
                      'present': (base / 'team-games.json').exists()},
        'v3League': {'file': rel(ROOT / 'reports/defense-seventh' / season /
                                 'calendar-55/v3-league.json'),
                     'present': (ROOT / 'reports/defense-seventh' / season /
                                 'calendar-55/v3-league.json').exists()},
        'dependence': {'file': 'reports/player-impact-v30/dependence-audit.json',
                       'seasonCovered': season in dep_seasons},
        'shotOrigin': {'file': 'reports/ovr-v55-finisher-fix-2025-26/shot-origin.json',
                       'seasonCovered': season in origin_seasons},
        'fourFactors': {'file': rel(ff), 'present': ff.exists()},
    }


def stint_info(season):
    expected = ROOT / 'reports/defense-seventh' / season / 'stints' / 'stints.jsonl'
    gz = HIST / 'stints' / f'stints-{season}.jsonl.gz'
    prep = HIST / 'stints' / f'preparation-{season}.json'
    out = {'expectedPath': {'file': rel(expected), 'present': expected.exists()},
           'historyGz': {'file': rel(gz), 'present': gz.exists()},
           'preparation': {'file': rel(prep), 'present': prep.exists()}}
    if season == '2021-22':
        alt = V3_DATA / 'derived-2021-22' / 'stints' / 'stints.jsonl'
        out['alternateLocal'] = {'file': rel(alt), 'present': alt.exists()}
        if alt.exists():
            out['alternateLocal']['lines'] = count_lines(alt)
            out['alternateLocal']['sha256'] = sha256(alt)
    else:
        out['alternateLocal'] = {'file': None, 'present': False}
    if expected.exists():
        out['expectedPath']['lines'] = count_lines(expected)
    if gz.exists():
        out['historyGz']['lines'] = count_gz_lines(gz)
        out['historyGz']['sha256'] = sha256(gz)
    if prep.exists():
        p = read_json(prep)
        out['preparation'].update({k: p[k] for k in
                                   ('boxGames', 'pbpGames', 'validLineupGames',
                                    'failedGames', 'stints')})
    return out


def rapm_candidates(tag):
    if tag is None:
        return []
    names = [f'rapm-{tag}.csv']
    return [HIST / n for n in names] + [V3_DATA / n for n in names] + \
           [V4_DATA / n for n in names]


def rapm_players(path):
    return len(list(csv.DictReader(open(path, encoding='utf-8'))))


def player_universe(season):
    """該季所有登場球員：box-totals 只到 2023-24，之後用 player-games.json。"""
    totals = box_totals(season)
    if totals:
        return set(totals['minutes'])
    path = ROOT / 'data/defense-seventh' / season / 'player-games.json'
    if not path.exists():
        return None
    doc = read_json(path)
    s = doc['data']['resultSets']
    s = s[0] if isinstance(s, list) else s
    i = s['headers'].index('PLAYER_ID')
    return {int(r[i]) for r in s['rowSet']}


def rapm_windows():
    """§5.2 每個起點的 pred/ans RAPM 檔；檔名照「最大季」慣例。"""
    summary = read_json(HIST / 'summary.json')
    win_meta = summary['windows']
    windows, starts = {}, {}

    def resolve(seasons):
        key = seasons[0] if len(seasons) == 1 else f'{seasons[0]}_{seasons[-1]}'
        if key in windows:
            return key
        found = next((p for p in rapm_candidates(key) if p.exists()), None)
        rec = {'tag': key, 'seasons': seasons,
               'kind': 'window' if len(seasons) > 1 else 'single',
               'present': found is not None, 'expectedName': f'rapm-{key}.csv'}
        if found is not None:
            rec.update({'file': rel(found), 'sha256': sha256(found),
                        'players': rapm_players(found)})
            meta = win_meta.get(key)
            rec['seasonSetMatches'] = (meta['seasons'] == seasons) if meta else None
            if meta:
                rec['lambda'] = meta['lambda']
            league = set()
            for s in seasons:
                u = player_universe(s)
                if u:
                    league |= u
            if league:
                rec['leaguePlayers'] = len(league)
                rec['playerCoverage'] = round(rec['players'] / len(league), 4)
                rec['coveragePass90'] = rec['playerCoverage'] >= 0.90
        windows[key] = rec
        return key

    for start, cfg in PATH_A.items():
        entry = {}
        for side in ('pred', 'ans'):
            tag = cfg[side]
            if tag == 'formal-card-H1-m0':
                entry[side] = {'tag': tag, 'kind': 'formal-card', 'present': True}
            elif isinstance(tag, list) and tag:
                entry[side] = {'tag': resolve(tag)}
            else:
                entry[side] = None
        starts[start] = entry
    return {'starts': starts, 'windows': windows}


def card_readiness(season, layers):
    """依 §5.6 判卡片能不能建；回傳致命缺層與可套用降級。"""
    fatal, fallback = [], []
    inputs = layers['seasonAttrsInputs']
    if not inputs['bio']['present']:
        fatal.append('bio 缺：physique/heightInches/pass/rebound/pos 無來源'
                     '（§5.6 只有「不進 H」，沒有建卡規則）')
    if not inputs['pbpDir']['present']:
        fatal.append('pbp 缺：mid/short/shortBase 無投籃分區來源；0 出手會變聯盟平均（等於補值）')
    if not inputs['fourFactors']['present']:
        fatal.append('每季 four-factors 缺：pressure 無來源；OVRPipeline 需要全部 15 項屬性')
    if not inputs['v3League']['present']:
        fallback.append('tracking 缺 → onBall/help=70（v4 §3.4）')
    if not inputs['dependence']['seasonCovered']:
        fallback.append('dependence 缺 → creation=x0／received=0.5（v4 P0 先例）')
    if not inputs['shotOrigin']['seasonCovered']:
        fallback.append('shot-origin 缺 → short=shortBase（v4 §3.5）')
    if not inputs['teamGames']['present']:
        fallback.append('team-games 缺 → prior 用 bio 官方 AST%/REB%；視窗層需另建（本輪不建）')
    if not inputs['boxPlayerGames']['present']:
        fallback.append('player-games.json 缺 → PR #5 box-games 可用，但需轉換（格式不同）')
    return {'buildable': not fatal, 'fatal': fatal, 'fallback': fallback}


def gate51(layers):
    """§5.1 的七層逐列判定；檔案不在預定路徑但資料存在時標 alternate。"""
    pbp_ok = layers['pbp']['files'] > 0
    boxes = layers['box']['boxesFiles'] > 0
    hist_box = bool(layers['box']['historyBoxGames'])
    bio_ok = layers['bio']['present']
    st = layers['stints']
    stint_status = ('present' if st['expectedPath']['present']
                    else 'gz' if st['historyGz']['present']
                    else 'alternate' if st['alternateLocal']['present'] else 'missing')
    sc = layers['shotCoords']
    shot_ok = bool(sc.get('present')) and (
        (sc.get('areaCoverage') or 0) >= 0.99 or (sc.get('xyCoverage') or 0) >= 0.99)
    card_ok = layers['card']['buildable']
    rows = {
        'pbp': {'pass': pbp_ok,
                'status': 'present' if pbp_ok else 'missing'},
        'box': {'pass': boxes or hist_box,
                'status': 'present' if boxes else 'history-box-games' if hist_box else 'missing'},
        'bio': {'pass': bio_ok,
                'status': 'present' if bio_ok else 'missing'},
        'stints': {'pass': stint_status != 'missing', 'status': stint_status},
        'shotCoords': {'pass': shot_ok,
                       'status': ('present' if shot_ok else 'no-pbp' if not sc.get('present')
                                  else 'below-99pct')},
        'card': {'pass': card_ok,
                 'status': 'buildable' if card_ok else 'not-buildable'},
    }
    rows['allPass'] = all(r['pass'] for r in rows.values())
    return rows


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    dep = read_json(ROOT / 'reports/player-impact-v30/dependence-audit.json')
    dep_seasons = [s['season'] for s in dep['seasons']]
    origin = read_json(ROOT / 'reports/ovr-v55-finisher-fix-2025-26/shot-origin.json')
    origin_seasons = list(origin['seasons'])

    out = {'generatedBy': rel(Path(__file__)),
           'spec': 'preregistration-v5 §5.1（D0）、§5.6（缺層）；§5.2（Path A 鏈）',
           'scope': '只掃本機檔案；不下載、不補值、不讀 2026-27',
           'seasons': {}, 'rapm': {}, 'consequences': {}, 'decision': {}}

    for s in SEASONS:
        totals = box_totals(s)
        bg = box_games(s)
        layers = {
            'expectedGames': {'games': EXPECTED_GAMES[s],
                              'source': ('v5/history/stints/preparation-%s.json' % s)
                              if (HIST / 'stints' / f'preparation-{s}.json').exists()
                              else 'data/defense-seventh/2021-22/pbp + boxes（本機 1230 場）'},
            'pbp': {'expectedPath': rel(ROOT / 'data/defense-seventh' / s / 'pbp'),
                    'files': len(list((ROOT / 'data/defense-seventh' / s /
                                       'pbp').glob('*.json')))
                    if (ROOT / 'data/defense-seventh' / s / 'pbp').is_dir() else 0},
            'box': {'expectedPath': rel(ROOT / 'data/defense-seventh' / s / 'boxes'),
                    'boxesFiles': (len(list((ROOT / 'data/defense-seventh' / s /
                                             'boxes').glob('*.json')))
                                   if (ROOT / 'data/defense-seventh' / s /
                                       'boxes').is_dir() else 0),
                    'playerGamesPath': rel(ROOT / 'data/defense-seventh' / s /
                                           'player-games.json'),
                    'present': (ROOT / 'data/defense-seventh' / s /
                                'player-games.json').exists(),
                    'historyBoxGames': bg,
                    'historyBoxTotals': ({k: totals[k] for k in ('file', 'sha256', 'players')}
                                         if totals else None)},
            'bio': {'expectedPath': rel(ROOT / 'data/defense-seventh' / s / 'bio.json'),
                    'present': (ROOT / 'data/defense-seventh' / s / 'bio.json').exists(),
                    'backfillUpperBound': bio_coverage(s, totals)},
            'stints': stint_info(s),
            'shotCoords': shot_coverage(s),
            'seasonAttrsInputs': season_attr_inputs(s, dep_seasons, origin_seasons),
            'possession': {'file': rel(ROOT / 'reports/player-impact-v21/raw' / s /
                                       'Possessions.json'),
                           'present': (ROOT / 'reports/player-impact-v21/raw' / s /
                                       'Possessions.json').exists(),
                           'neededByCardPipeline': False},
            'prior': {'file': rel(REPORT / 'v5/data' / f'prior-{s}-v5.json'),
                      'present': (REPORT / 'v5/data' / f'prior-{s}-v5.json').exists()
                      or (V4_DATA / f'prior-{s}.json').exists()
                      or (V3_DATA / f'prior-{s}.json').exists()},
        }
        # 場數核對
        got = bg['games'] if bg else layers['pbp']['files']
        layers['gameCount'] = {'expected': EXPECTED_GAMES[s], 'got': got,
                               'match': got == EXPECTED_GAMES[s],
                               'bubbleGames': bg['bubbleGames'] if bg else 0}
        layers['card'] = card_readiness(s, layers)
        layers['gate51'] = gate51(layers)
        layers['entersChain'] = layers['gate51']['allPass']
        out['seasons'][s] = {'expectedGames': EXPECTED_GAMES[s], 'layers': layers}

    out['rapm'] = rapm_windows()

    # 每個 Y 起點：先驗季卡、目標季答案卡、RAPM 檔
    for start, cfg in PATH_A.items():
        prior_ok = out['seasons'].get(cfg['prior'], {}).get('layers', {}) \
            .get('card', {}).get('buildable')
        target_ok = out['seasons'].get(cfg['target'], {}).get('layers', {}) \
            .get('card', {}).get('buildable')
        entry = out['rapm']['starts'].get(start, {})
        refs = [entry.get(side) for side in ('pred', 'ans') if entry.get(side)]
        rapm_ok = all(
            out['rapm']['windows'][r['tag']]['present']
            if r.get('tag') in out['rapm']['windows'] else r.get('present', True)
            for r in refs) if refs else None
        rec_out = {'gateScope': start.startswith('Y'),
                   'prior': cfg['prior'], 'priorCardBuildable': prior_ok,
                   'target': cfg['target'], 'targetAnswerCardBuildable': target_ok,
                   'judgePerPrereg': cfg['judge'],
                   'rapmWindowsPresent': rapm_ok}
        if start in FRESH:
            rec_out['canJudge'] = bool(prior_ok and target_ok and rapm_ok)
        elif rec_out['gateScope']:
            rec_out['canJudge'] = None
        else:
            rec_out['canJudge'] = None
            rec_out['note'] = '不在 D0 掃描範圍（2014-15..2021-22）；D1–D3 用 v5/backtest 上一輪結果'
        out['consequences'][start] = rec_out

    fresh_lost = [s for s in FRESH if out['consequences'][s]['canJudge'] is not True]
    out['decision'] = {
        'd0Pass': all(v['layers']['entersChain'] for v in out['seasons'].values()),
        'seasonsNotEntering': [s for s, v in out['seasons'].items()
                               if not v['layers']['entersChain']],
        'freshJudgmentsLost': fresh_lost,
        'v1v2': '從缺（新鮮主判定全部失效）' if fresh_lost else '可判定',
        'note': 'D0 不通過即停止；不建 RAPM、不建卡、不跑回測（§5.1 停止條件）',
    }
    out['decision']['pass'] = out['decision']['d0Pass']

    path = OUTDIR / 'd0-gate.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'seasons': {s: {'entersChain': v['layers']['entersChain'],
                                      'fatal': v['layers']['card']['fatal'],
                                      'gameCount': v['layers']['gameCount']}
                                  for s, v in out['seasons'].items()},
                      'fresh': {s: out['consequences'][s] for s in FRESH},
                      'decision': out['decision']}, ensure_ascii=False, indent=1))
    return 0 if out['decision']['d0Pass'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
