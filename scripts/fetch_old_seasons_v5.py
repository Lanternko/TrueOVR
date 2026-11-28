"""v5 Path A：把 2014-15..2020-21 的公開存檔轉成和 data/defense-seventh/2021-22/ 相同的格式。

來源（全部是 NBA 官方端點原始輸出的 GitHub 存檔，只當資料讀）：
- pbp：shufinskiy/nba_data `nbastatsv3_<起始年>`（stats.nba.com playbyplayv3）＋ `nbastats_<起始年>`
  （playbyplayv2，只補 v3 沒有的 personId：助攻者、換人進場者、跳球三方）；2020-21 起有
  `cdnnba_<起始年>`（cdn.nba.com liveData playbyplay 的 csv 攤平）就直接還原。
- bio：Fekouto/ciencias_de_dados_nba `perfis_por_temporada/<季>.csv`（leaguedashplayerbiostats 逐季）。
- box：PR #5 的 v5/history/box-games-<季>.csv.gz（NocturneBear boxscoretraditionalv3）。

輸出 <out>/<季>/：pbp/<gameId>.json、bio.json、player-games.json、team-games.json、league.json、
game-exposure.json、manifest.json。決定性：同輸入重跑 bytes 相同（不寫時間戳）。

用法：python -I scripts/fetch_old_seasons_v5.py --season 2016-17 [--source v3|cdn] [--out DIR]
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(r'D:\Projects\temp\nba-old-seasons')
HIST = ROOT / 'reports/ovr-inseason-2026-27/v5/history'
GH = 'https://github.com/shufinskiy/nba_data/raw/main/datasets/'
BIO_URL = 'https://raw.githubusercontent.com/Fekouto/ciencias_de_dados_nba/HEAD/dados/perfis_por_temporada/{s}.csv'
BOX_UPSTREAM = 'https://github.com/NocturneBear/NBA-Data-2010-2024'
BUBBLE = ('2020-07-30', '2020-10-11')
csv.field_size_limit(1 << 30)

BIO_HEADERS = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'AGE', 'PLAYER_HEIGHT',
               'PLAYER_HEIGHT_INCHES', 'PLAYER_WEIGHT', 'COLLEGE', 'COUNTRY', 'DRAFT_YEAR', 'DRAFT_ROUND',
               'DRAFT_NUMBER', 'GP', 'PTS', 'REB', 'AST', 'NET_RATING', 'OREB_PCT', 'DREB_PCT', 'USG_PCT',
               'TS_PCT', 'AST_PCT']
BIO_STR = {'PLAYER_NAME', 'TEAM_ABBREVIATION', 'PLAYER_HEIGHT', 'PLAYER_WEIGHT', 'COLLEGE', 'COUNTRY',
           'DRAFT_YEAR', 'DRAFT_ROUND', 'DRAFT_NUMBER'}
PG_HEADERS = ['SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME', 'GAME_ID',
              'GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM',
              'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLUS_MINUS',
              'FANTASY_PTS', 'VIDEO_AVAILABLE']
TG_HEADERS = ['SEASON_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL',
              'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
              'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLUS_MINUS', 'VIDEO_AVAILABLE']
STATS = ['FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF',
         'PTS', 'PLUS_MINUS']

# cdn liveData 欄位型別（照本機 2021-22 pbp/*.json）
BLOCK_STEAL_AN_OFFSET = 100000   # v3 抄截/阻攻列改用的 actionNumber 位移（避免與原動作同號）
CDN_COMMON = ['actionNumber', 'clock', 'timeActual', 'period', 'periodType', 'actionType', 'subType',
              'qualifiers', 'personId', 'x', 'y', 'possession', 'scoreHome', 'scoreAway', 'edited',
              'orderNumber', 'xLegacy', 'yLegacy', 'isFieldGoal', 'side', 'description', 'personIdsFilter']
CDN_INT = {'actionNumber', 'period', 'personId', 'possession', 'orderNumber', 'xLegacy', 'yLegacy',
           'isFieldGoal', 'teamId', 'jumpBallRecoverdPersonId', 'jumpBallWonPersonId', 'jumpBallLostPersonId',
           'shotActionNumber', 'reboundTotal', 'reboundDefensiveTotal', 'reboundOffensiveTotal', 'officialId',
           'foulPersonalTotal', 'foulTechnicalTotal', 'foulDrawnPersonId', 'pointsTotal', 'assistPersonId',
           'assistTotal', 'blockPersonId', 'turnoverTotal', 'stealPersonId'}
CDN_FLOAT = {'x', 'y', 'shotDistance'}
CDN_STR = {'scoreHome', 'scoreAway'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def gid10(g):
    return str(int(float(g))).zfill(10)


def to_int(v):
    return int(float(v))


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def dump(path, obj, indent=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(',', ':') if indent is None else None, indent=indent)
    path.write_text(text + '\n', encoding='utf-8', newline='\n')


def archive_entry(name, csv_path):
    tar = RAW / 'dl' / f'{name}.tar.xz'
    out = {'name': name, 'url': GH + f'{name}.tar.xz', 'extractedCsv': str(csv_path),
           'csvSha256': sha256(csv_path), 'csvBytes': csv_path.stat().st_size}
    if tar.exists():
        out.update({'sha256': sha256(tar), 'bytes': tar.stat().st_size})
    return out


def grouped_rows(path, key):
    """csv 依 gameId 連續分組（檢查同一場不會分成兩段）。"""
    with open(path, encoding='utf-8', newline='') as fh:
        r = csv.reader(fh)
        head = next(r)
        k = head.index(key)
        seen, cur, rows = set(), None, []
        for row in r:
            g = row[k]
            if g != cur:
                if cur is not None:
                    yield cur, head, rows
                if g in seen:
                    raise RuntimeError(f'{path}: game {g} not contiguous')
                seen.add(g)
                cur, rows = g, []
            rows.append(row)
        if cur is not None:
            yield cur, head, rows


# ---------------------------------------------------------------- cdn csv → liveData JSON

def cdn_value(k, v):
    if k == 'qualifiers':
        return [q for q in v.split(', ')] if v else []
    if k == 'personIdsFilter':
        return [to_int(q) for q in v.split(', ')] if v else []
    if v == '':
        return None
    if k in CDN_INT:
        return to_int(v)
    if k in CDN_FLOAT:
        return float(v)
    return v


def cdn_actions(head, rows):
    out = []
    for row in rows:
        d = dict(zip(head, row))
        a = {k: cdn_value(k, d.get(k, '')) for k in CDN_COMMON}
        for k in head:
            if k in a or k == 'gameId':
                continue
            if d[k] != '':
                a[k] = cdn_value(k, d[k])
        out.append(a)
    return out


# ---------------------------------------------------------------- playbyplayv3 (+v2) → liveData-like JSON

TOV_MAP = {'shot clock turnover': 'shot clock', 'shot clock': 'shot clock', 'bad pass': 'bad pass',
           'lost ball': 'lost ball', 'offensive foul turnover': 'offensive foul', 'traveling': 'traveling',
           'out of bounds - bad pass turnover': 'out-of-bounds', 'out of bounds lost ball turnover': 'out-of-bounds',
           'step out of bounds turnover': 'out-of-bounds', '3 second violation': '3-second-violation',
           'backcourt turnover': 'backcourt', 'offensive goaltending': 'offensive goaltending',
           'double dribble': 'double dribble', 'discontinue dribble': 'discontinued dribble',
           'palming turnover': 'palming', '5 second violation': '5-second-violation',
           'lane violation': 'LaneViolation', 'kicked ball violation': 'offensive-kicked-ball',
           'inbound turnover': 'inbound', '8 second violation': '8-second-violation',
           'illegal assist turnover': 'illegal assist', 'jump ball violation': 'jumpball violation',
           'basket from below turnover': 'basket-from-below', 'punched ball turnover': 'punched ball',
           'too many players turnover': 'too-many-players'}
TYPE_MAP = {'Timeout': 'timeout', 'Instant Replay': 'instantreplay', 'Violation': 'violation',
            'Ejection': 'ejection'}
FT_RE = re.compile(r'(\d+) of (\d+)')
REB_RE = re.compile(r'\(Off:(\d+) Def:(\d+)\)')
AST_RE = re.compile(r'\(([^()]+?) \d+ AST\)')
SUB_RE = re.compile(r'SUB: (.+?) FOR (.+)$')
TIP_RE = re.compile(r'Tip to (.+)$')


def foul_type(st):
    if 'Technical' in st or st == 'Defense 3 Second':
        if st == 'Double Technical':
            return 'technical', 'double'
        if st == 'Defense 3 Second':
            return 'technical', 'defensive-3-second'
        return 'technical', st.lower()
    if st in ('Offensive', 'Offensive Charge'):
        return 'offensive', 'charge' if st == 'Offensive Charge' else None
    return 'personal', st.lower() or None


def v3_actions(head, rows, v2, stats):
    R = [dict(zip(head, r)) for r in rows]
    teams = {int(r['teamId']) for r in R if r['teamId'] not in ('', '0')}
    pteam, names = {}, {}
    for r in R:
        p, t = int(r['personId'] or 0), int(r['teamId'] or 0)
        if p and t and p not in teams:
            pteam[p] = t
            for n in (r['playerName'], r['playerNameI']):
                if n:
                    names.setdefault((t, n), set()).add(p)
    if v2:
        for e in v2.values():
            for i in (1, 2, 3):
                p, t = e[f'p{i}'], e[f't{i}']
                if p and t and p not in teams:
                    pteam.setdefault(p, t)

    def by_name(t, n):
        hit = names.get((t, n.strip()))
        if hit and len(hit) == 1:
            return next(iter(hit))
        stats['nameMiss'] += 1
        return 0

    extra = {}   # actionNumber → {'steal': pid, 'block': pid}
    for r in R:
        if r['actionType'].strip() == '' and r['personId'] not in ('', '0'):
            k = 'steal' if 'STEAL' in r['description'] else 'block' if 'BLOCK' in r['description'] else None
            if k:
                extra.setdefault(int(r['actionNumber']), {})[k] = int(r['personId'])
    out, score, last_miss, rebc = [], ['0', '0'], None, {}
    for r in R:
        at, st, desc = r['actionType'].strip(), r['subType'].strip(), r['description'].strip()
        an, pid, tid = int(r['actionNumber']), int(r['personId'] or 0), int(r['teamId'] or 0)
        e = v2.get(an) if v2 else None
        team_row = False
        if pid in teams:
            tid, pid, team_row = pid, 0, True
        if r['scoreHome'] != '' and r['scoreAway'] != '':
            score = [str(int(float(r['scoreHome']))), str(int(float(r['scoreAway'])))]
        a = {'actionNumber': an, 'clock': r['clock'], 'period': int(r['period']), 'teamId': tid or None,
             'teamTricode': r['teamTricode'] or None, 'personId': pid, 'actionType': None, 'subType': None,
             'qualifiers': ['team'] if team_row else [], 'descriptor': None, 'xLegacy': None, 'yLegacy': None,
             'isFieldGoal': 0, 'scoreHome': score[0], 'scoreAway': score[1], 'description': desc,
             'personIdsFilter': [pid] if pid else [], 'location': r['location'] or None}
        rows_out = [a]
        if at == 'period':
            a.update(actionType='period', subType=st)
        elif at == '':
            k = 'steal' if 'STEAL' in desc else 'block' if 'BLOCK' in desc else None
            if not k:
                stats['unknownBlank'] += 1
                continue
            # v3 的抄截/阻攻列與其投籃/失誤共用 actionNumber；liveData 各有自己的編號。
            # 共用會讓 stints 的 shotMap（後者覆蓋前者）把籃板的 shotActionNumber 對到阻攻，掉籃板機會。
            a.update(actionType=k, actionNumber=an + BLOCK_STEAL_AN_OFFSET)
        elif at == 'Jump Ball':
            p1, p2, p3 = (e['p1'], e['p2'], e['p3']) if e else (pid, 0, 0)
            t3 = e['t3'] if e else 0
            if not e:
                m = TIP_RE.search(desc)
                if m:
                    for t in teams:
                        p3 = by_name(t, m.group(1)) or p3
                    t3 = pteam.get(p3, 0)
            if p3 in teams:
                a.update(personId=0, teamId=p3)
            elif p3:
                a.update(personId=p3, teamId=t3 or pteam.get(p3) or tid)
            a.update(actionType='jumpball', subType='recovered', jumpBallRecoverdPersonId=a['personId'] or None,
                     personIdsFilter=[p for p in (a['personId'], p1, p2) if p and p not in teams])
        elif at in ('Made Shot', 'Missed Shot'):
            made = at == 'Made Shot'
            a.update(actionType='3pt' if '3PT' in desc else '2pt', subType=st, isFieldGoal=1,
                     shotResult='Made' if made else 'Missed', xLegacy=to_int(r['xLegacy'] or 0),
                     yLegacy=to_int(r['yLegacy'] or 0), shotDistance=float(r['shotDistance'] or 0))
            if made:
                ast = 0
                if e and e['type'] == 1 and e['p2'] and e['p2'] not in teams:
                    ast = e['p2']
                elif not e:
                    m = AST_RE.search(desc)
                    ast = by_name(tid, m.group(1)) if m else 0
                if ast:
                    a['assistPersonId'] = ast
                    a['personIdsFilter'].append(ast)
                last_miss = None
            else:
                last_miss = (an, tid)
                blk = extra.get(an, {}).get('block')
                if blk:
                    a['blockPersonId'] = blk
                    a['personIdsFilter'].append(blk)
        elif at == 'Free Throw':
            m = FT_RE.search(st)
            sub = f'{m.group(1)} of {m.group(2)}' if m else '1 of 1'
            descr = ('technical' if 'Technical' in st else 'flagrant' if 'Flagrant' in st
                     else 'clear path' if 'Clear Path' in st else None)
            made = not desc.upper().startswith('MISS')
            a.update(actionType='freethrow', subType=sub, descriptor=descr, shotResult='Made' if made else 'Missed')
            last_miss = None if made else (an, tid)
        elif at == 'Rebound':
            off = None
            m = REB_RE.search(desc)
            if pid and m:
                o, d = int(m.group(1)), int(m.group(2))
                po, pd = rebc.get(pid, (0, 0))
                rebc[pid] = (o, d)
                if o == po + 1 and d == pd:
                    off = True
                elif d == pd + 1 and o == po:
                    off = False
            inferred = bool(last_miss and last_miss[1] == tid)
            if off is None:
                off = inferred
                stats['rebInferred'] += 1
            elif off != inferred and last_miss:
                stats['rebCounterVsInference'] += 1
            a.update(actionType='rebound', subType='offensive' if off else 'defensive',
                     shotActionNumber=last_miss[0] if last_miss else None)
            last_miss = None
        elif at == 'Turnover':
            if 'No Turnover' in desc:
                stats['noTurnoverDropped'] += 1
                continue
            stl = extra.get(an, {}).get('steal') or (e['p2'] if e and e['type'] == 5 and e['p2'] not in teams else 0)
            a.update(actionType='turnover', subType=TOV_MAP.get(st.lower(), st.lower()))
            if stl:
                a['stealPersonId'] = stl
                a['personIdsFilter'].append(stl)
            last_miss = None
        elif at == 'Foul':
            sub, descr = foul_type(st)
            a.update(actionType='foul', subType=sub, descriptor=descr)
            if e and e['p2'] and e['p2'] not in teams:
                a['foulDrawnPersonId'] = e['p2']
        elif at == 'Substitution':
            pin = e['p2'] if e and e['type'] == 8 else 0
            if not e:
                m = SUB_RE.search(desc)
                pin = by_name(tid, m.group(1)) if m else 0
            if not pin:
                stats['subNoIn'] += 1
            a.update(actionType='substitution', subType='out')
            b = dict(a, personId=pin, subType='in', personIdsFilter=[pin] if pin else [])
            rows_out = [a, b]
        else:
            a['actionType'] = TYPE_MAP.get(at, at.lower().replace(' ', ''))
            a['subType'] = st or None
        out.extend(rows_out)
    for i, a in enumerate(out):
        a['orderNumber'] = i + 1
    return out


def load_v2(path):
    keep = {}
    if not path.exists():
        return keep
    with open(path, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            g = gid10(r['GAME_ID'])
            ids = {}
            for i in (1, 2, 3):
                p = r[f'PLAYER{i}_ID']
                t = r[f'PLAYER{i}_TEAM_ID']
                ids[f'p{i}'] = to_int(p) if p not in ('', 'None') else 0
                ids[f't{i}'] = to_int(t) if t not in ('', 'None') else 0
            ids['type'] = to_int(r['EVENTMSGTYPE'])
            keep.setdefault(g, {})[to_int(r['EVENTNUM'])] = ids
    return keep


# ---------------------------------------------------------------- box / bio / league

def load_box(season):
    path = HIST / f'box-games-{season}.csv.gz'
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    return path, rows


def pct(a, b):
    return round(a / b, 3) if b else None


def game_min(sec):
    # box 存檔秒數是整數；剛好 x:30 時 leaguegamelog 依未存的小數秒決定上下（2021-22 對照：往上 306 列、往下 64 列）
    return math.floor(sec / 60 + 0.5)


def build_box_files(season, box_rows, meta, out):
    """meta[gameId] = {'home': tid, 'away': tid, 'tricode': {tid: 'ATL'}, 'periods': n}"""
    sid = '2' + season[:4]
    games = {}
    for r in box_rows:
        g = games.setdefault(r['gameId'], {'date': r['gameDate'], 'teams': {}})
        g['teams'].setdefault(int(r['teamId']), []).append(r)
    pg, tg, expo, sched = [], [], [], []
    roster = {}
    for gid in sorted(games):
        g = games[gid]
        m = meta.get(gid, {})
        tids = sorted(g['teams'])
        home, away = m.get('home'), m.get('away')
        if home not in g['teams'] or away not in g['teams']:
            home, away = None, None
        tri = m.get('tricode', {})
        tot = {t: {k: sum(int(float(r[k])) for r in g['teams'][t]) for k in STATS} for t in tids}
        exp_teams = []
        for t in ([home, away] if home else tids):
            opp = [x for x in tids if x != t][0] if len(tids) == 2 else None
            matchup = None
            if home and opp:
                matchup = (f'{tri.get(t)} vs. {tri.get(opp)}' if t == home else f'{tri.get(t)} @ {tri.get(opp)}')
            wl = None if opp is None else ('W' if tot[t]['PTS'] > tot[opp]['PTS'] else 'L')
            secs = sum(float(r['seconds']) for r in g['teams'][t])
            team_min = 240 + 25 * (m['periods'] - 4) if m.get('periods') else 5 * round(secs / 300)
            players = []
            for r in g['teams'][t]:
                pid = int(r['playerId'])
                roster.setdefault(t, {})[pid] = r['name']
                s = {k: int(float(r[k])) for k in STATS}
                sec = float(r['seconds'])
                fp = s['PTS'] + 1.2 * s['REB'] + 1.5 * s['AST'] + 3 * s['STL'] + 3 * s['BLK'] - s['TOV']
                pg.append([sid, pid, r['name'], t, tri.get(t), None, gid, g['date'], matchup, wl, game_min(sec),
                           s['FGM'], s['FGA'], pct(s['FGM'], s['FGA']), s['FG3M'], s['FG3A'], pct(s['FG3M'], s['FG3A']),
                           s['FTM'], s['FTA'], pct(s['FTM'], s['FTA']), s['OREB'], s['DREB'], s['REB'], s['AST'],
                           s['STL'], s['BLK'], s['TOV'], s['PF'], s['PTS'], s['PLUS_MINUS'], round(fp, 1), None])
                players.append({'playerId': pid, 'seconds': sec, 'starter': r['starter'] in ('1', 'True', 'true'),
                                'position': None, 'points': s['PTS'], 'plusMinus': s['PLUS_MINUS']})
            T = tot[t]
            pm = T['PTS'] - tot[opp]['PTS'] if opp else None
            tg.append([sid, t, tri.get(t), None, gid, g['date'], matchup, wl, team_min, T['FGM'], T['FGA'],
                       pct(T['FGM'], T['FGA']), T['FG3M'], T['FG3A'], pct(T['FG3M'], T['FG3A']), T['FTM'], T['FTA'],
                       pct(T['FTM'], T['FTA']), T['OREB'], T['DREB'], T['REB'], T['AST'], T['STL'], T['BLK'],
                       T['TOV'] + m.get('teamTov', {}).get(t, 0), T['PF'], T['PTS'], pm, None])
            exp_teams.append({'teamId': t, 'players': players})
        expo.append({'id': gid, 'teams': exp_teams})
        if home:
            sched.append({'id': gid, 'date': g['date'], 'homeId': home, 'awayId': away,
                          'neutral': BUBBLE[0] <= g['date'] <= BUBBLE[1],
                          'observed': {'homeScore': tot[home]['PTS'], 'awayScore': tot[away]['PTS']},
                          'homePlayerIds': [int(r['playerId']) for r in g['teams'][home]],
                          'awayPlayerIds': [int(r['playerId']) for r in g['teams'][away]]})
    pg.sort(key=lambda x: (x[7], x[6], x[3], x[1]), reverse=True)
    tg.sort(key=lambda x: (x[5], x[4], x[1]), reverse=True)
    common = {'LeagueID': '00', 'Season': season, 'SeasonType': 'Regular Season'}
    gl = lambda kind, headers, rows: {
        'url': f'derived:{rel(HIST / f"box-games-{season}.csv.gz")}', 'season': season, 'fetchedAt': None,
        'data': {'resource': 'leaguegamelog', 'parameters': dict(common, PlayerOrTeam=kind),
                 'derivedFrom': 'boxscoretraditionalv3 archive (PR #5 box-games); not the leaguegamelog endpoint',
                 'resultSets': [{'name': 'LeagueGameLog', 'headers': headers, 'rowSet': rows}]}}
    dump(out / 'player-games.json', gl('P', PG_HEADERS, pg))
    dump(out / 'team-games.json', gl('T', TG_HEADERS, tg))
    dump(out / 'game-exposure.json', {'season': season, 'games': expo,
                                      'sources': [{'file': rel(HIST / f'box-games-{season}.csv.gz'),
                                                   'sha256': sha256(HIST / f'box-games-{season}.csv.gz')}],
                                      'failures': []})
    teams = [{'id': t, 'name': None, 'roster': [{'playerId': p, 'name': n} for p, n in sorted(roster[t].items())]}
             for t in sorted(roster)]
    return sched, teams, len(games)


def build_bio(season, out):
    path = RAW / 'bio' / f'perfis-{season}.csv'
    if not path.exists():
        return None
    rows = []
    with open(path, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            row = []
            for h in BIO_HEADERS:
                v = r.get(h, '')
                if h in BIO_STR:
                    row.append(v if v != '' else None)
                elif v == '':
                    row.append(None)
                else:
                    f = float(v)
                    row.append(int(f) if f.is_integer() and h not in ('NET_RATING', 'OREB_PCT', 'DREB_PCT',
                                                                         'USG_PCT', 'TS_PCT', 'AST_PCT') else f)
            rows.append(row)
    rows.sort(key=lambda x: (x[1] or '', x[0]))
    url = BIO_URL.format(s=season)
    dump(out / 'bio.json', {'url': url, 'season': season, 'fetchedAt': None,
                            'data': {'resource': 'leaguedashplayerbiostats',
                                     'parameters': {'PerMode': 'Totals', 'LeagueID': '00', 'Season': season,
                                                    'SeasonType': 'Regular Season'},
                                     'resultSets': [{'name': 'LeagueDashPlayerBioStats', 'headers': BIO_HEADERS,
                                                     'rowSet': rows}]}})
    return {'url': url, 'file': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size, 'rows': len(rows)}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', required=True)
    ap.add_argument('--source', choices=['v3', 'cdn'])
    ap.add_argument('--out')
    args = ap.parse_args()
    season = args.season
    y = int(season[:4])
    source = args.source or ('cdn' if y >= 2020 else 'v3')
    out = Path(args.out) / season if args.out else ROOT / 'data/defense-seventh' / season
    if not args.out and y >= 2021:
        raise SystemExit('refuse to write data/defense-seventh/2021-22+ (use --out)')
    pbp_dir = out / 'pbp'
    pbp_dir.mkdir(parents=True, exist_ok=True)
    for old in pbp_dir.glob('*.json'):
        old.unlink()
    stats = {k: 0 for k in ('nameMiss', 'unknownBlank', 'rebInferred', 'rebCounterVsInference',
                            'noTurnoverDropped', 'subNoIn')}
    archives = []
    if source == 'cdn':
        csv_path = RAW / 'x' / f'cdnnba_{y}.csv'
        archives.append(archive_entry(f'cdnnba_{y}', csv_path))
        v2 = {}
    else:
        csv_path = RAW / 'x' / f'nbastatsv3_{y}.csv'
        archives.append(archive_entry(f'nbastatsv3_{y}', csv_path))
        v2_path = RAW / 'x2' / f'nbastats_{y}.csv'
        archives.append(archive_entry(f'nbastats_{y}', v2_path))
        v2 = load_v2(v2_path)
    box_path, box_rows = load_box(season)
    box_games = {r['gameId'] for r in box_rows}
    meta, sources, without_v2 = {}, [], []
    for g, head, rows in grouped_rows(csv_path, 'gameId'):
        gid = gid10(g)
        if gid not in box_games:      # 季後賽／附加賽等不在例行賽 box 內
            continue
        if source == 'cdn':
            acts = cdn_actions(head, rows)
        else:
            if gid not in v2:
                without_v2.append(gid)
            acts = v3_actions(head, rows, v2.get(gid), stats)
        loc = {}
        if source == 'cdn':
            ih = head.index('teamId')
            # cdn csv 沒有主客欄；用 scoreHome 變化歸屬判斷主隊
            for a in acts:
                if a.get('actionType') in ('2pt', '3pt', 'freethrow') and a.get('shotResult') == 'Made' and a.get('teamId'):
                    loc.setdefault(a['teamId'], 0)
            prev = (0, 0)
            for a in acts:
                cur = (int(a.get('scoreHome') or 0), int(a.get('scoreAway') or 0))
                if cur != prev and a.get('teamId'):
                    loc[a['teamId']] = loc.get(a['teamId'], 0) + (1 if cur[0] > prev[0] else -1)
                prev = cur
            ordered = sorted(loc, key=lambda t: -loc[t])
            home, away = (ordered + [None, None])[:2]
            tri = {a['teamId']: a.get('teamTricode') for a in acts if a.get('teamId')}
        else:
            hv = {}
            for r in rows:
                d = dict(zip(head, r))
                if d['location'] in ('h', 'v') and d['teamId'] not in ('', '0'):
                    hv[d['location']] = int(d['teamId'])
            home, away = hv.get('h'), hv.get('v')
            tri = {a['teamId']: a.get('teamTricode') for a in acts if a.get('teamId') and a.get('teamTricode')}
        team_tov = {}
        for a in acts:   # leaguegamelog 球隊 TOV 含球隊失誤（personId 0）
            if a.get('actionType') == 'turnover' and not a.get('personId') and a.get('teamId'):
                team_tov[a['teamId']] = team_tov.get(a['teamId'], 0) + 1
        meta[gid] = {'home': home, 'away': away, 'tricode': tri, 'teamTov': team_tov,
                     'periods': max((a['period'] for a in acts), default=4)}
        doc = {'url': archives[0]['url'] + f'#gameId={gid}', 'season': season, 'fetchedAt': None,
               'data': {'meta': {'source': f'archive:{archives[0]["name"]}', 'converter': rel(__file__)},
                        'game': {'gameId': gid, 'actions': acts}}}
        p = pbp_dir / f'{gid}.json'
        dump(p, doc)
        sources.append({'id': gid, 'file': rel(p), 'url': doc['url'], 'sha256': sha256(p)})
    sched, teams, n_box = build_box_files(season, box_rows, meta, out)
    dump(out / 'league.json', {'season': season, 'teams': teams, 'schedule': sched,
                               'sources': [{'file': rel(out / f), 'sha256': sha256(out / f)}
                                           for f in ('team-games.json', 'player-games.json', 'game-exposure.json')],
                               'note': 'v5 fetch: schedule/rosters from box archive; no ratings attached'})
    bio = build_bio(season, out)
    have = {s['id'] for s in sources}
    failures = [{'id': g, 'error': 'missing pbp in archive'} for g in sorted(box_games - have)]
    manifest = {'season': season, 'sources': sorted(sources, key=lambda s: s['id']), 'failures': failures,
                'v5fetch': {'pbpSource': source, 'archives': archives,
                            'box': {'file': rel(box_path), 'sha256': sha256(box_path), 'games': n_box,
                                    'upstream': BOX_UPSTREAM},
                            'bio': bio or {'missing': True,
                                           'reason': f'no per-season leaguedashplayerbiostats archive found for {season}'},
                            'gamesWithoutV2': without_v2, 'conversionStats': stats,
                            'converter': {'file': rel(__file__), 'sha256': sha256(Path(__file__))}}}
    dump(out / 'manifest.json', manifest, indent=1)
    print(json.dumps({'season': season, 'source': source, 'pbpGames': len(sources), 'boxGames': n_box,
                      'missingPbp': len(failures), 'bio': bool(bio), 'withoutV2': len(without_v2), **stats}))


if __name__ == '__main__':
    main()
