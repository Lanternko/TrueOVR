"""賽程檢視的資料（games_view.py 的 fetch 對象）。讀 data/season-source-2026-27/ 的 schedule.json（全季賽程骨架，含未開打）、
team-games.json（leaguegamelog 球隊，每場 2 列）、player-games.json（每人每場一列），輸出：
  games-data.json                 骨架：賽事日期、每場的主客隊、比分、勝方、狀態（體積小，檢視第一次進入就 fetch）
  games-box-<YYYY-MM>.json        box score：球員逐場數據與球隊合計，按比賽日期分月，點開某場才 fetch 該月
體積決策：已完賽 box 每場約 3 KB，全季 1230 場約 3.5 MB（gzip 前）> 2 MB 上限，所以從一開始就固定按月分檔（不會賽季中途才改格式）；骨架全季約 150 KB。
日期規則：已完賽場次以 gamelog 的 GAME_DATE 為準（schedule.json 是美東日期，兩邊偶爾差一天）；未開打場次用 schedule.json 的日期。
進行中場次：live-games.json（fetch_live_games.mjs，NBA.com liveData）裡還沒出現在 gamelog 的場次，骨架 status='live'（帶即時比分與 live{p,clk,txt}），box 帶即時球員數據
（欄位同已完賽，省略沒有的欄位、不給評分）；gamelog 已有的場次一律以 gamelog 為準，live 丟掉；live 檔不存在或 fetchedAt 超過 3 小時就整份忽略。已完賽／未開打場次的格式不變。

用法：python -I -X utf8 scripts/build_games_data.py <out_dir> [src_dir]
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/season-source-2026-27'
DATA_NAME = 'games-data.json'
BOX_FMT = 'games-box-{}.json'      # {} = YYYY-MM
LIVE_NAME = 'live-games.json'
LIVE_MAX_AGE_S = 3 * 3600          # live 檔超過這麼久沒更新就當作抓取已停擺，整份忽略

TEAMS = {  # NBA team id → (縮寫, 全名)；30 隊固定，未開打的隊也要能對到
    1610612737: ('ATL', 'Atlanta Hawks'), 1610612738: ('BOS', 'Boston Celtics'), 1610612739: ('CLE', 'Cleveland Cavaliers'),
    1610612740: ('NOP', 'New Orleans Pelicans'), 1610612741: ('CHI', 'Chicago Bulls'), 1610612742: ('DAL', 'Dallas Mavericks'),
    1610612743: ('DEN', 'Denver Nuggets'), 1610612744: ('GSW', 'Golden State Warriors'), 1610612745: ('HOU', 'Houston Rockets'),
    1610612746: ('LAC', 'LA Clippers'), 1610612747: ('LAL', 'Los Angeles Lakers'), 1610612748: ('MIA', 'Miami Heat'),
    1610612749: ('MIL', 'Milwaukee Bucks'), 1610612750: ('MIN', 'Minnesota Timberwolves'), 1610612751: ('BKN', 'Brooklyn Nets'),
    1610612752: ('NYK', 'New York Knicks'), 1610612753: ('ORL', 'Orlando Magic'), 1610612754: ('IND', 'Indiana Pacers'),
    1610612755: ('PHI', 'Philadelphia 76ers'), 1610612756: ('PHX', 'Phoenix Suns'), 1610612757: ('POR', 'Portland Trail Blazers'),
    1610612758: ('SAC', 'Sacramento Kings'), 1610612759: ('SAS', 'San Antonio Spurs'), 1610612760: ('OKC', 'Oklahoma City Thunder'),
    1610612761: ('TOR', 'Toronto Raptors'), 1610612762: ('UTA', 'Utah Jazz'), 1610612763: ('MEM', 'Memphis Grizzlies'),
    1610612764: ('WAS', 'Washington Wizards'), 1610612765: ('DET', 'Detroit Pistons'), 1610612766: ('CHA', 'Charlotte Hornets'),
}
ABBR = {i: v[0] for i, v in TEAMS.items()}


def rows(path: Path) -> tuple[list[dict], str]:
    doc = json.loads(path.read_text(encoding='utf-8'))
    rs = doc['data']['resultSets'][0]
    h = rs['headers']
    return [dict(zip(h, r)) for r in rs['rowSet']], doc.get('fetchedAt') or ''


def short_name(full: str) -> str:
    """box score 用的縮寫：名字首字母＋姓（"Jalen Walker"→"J. Walker"）。後綴（Jr./III）與多字姓整段留在姓後；單字名照舊；名字本身已是縮寫（"P.J."）不動。"""
    first, _, rest = full.strip().partition(' ')
    if not rest:
        return first
    return (first if first.endswith('.') else first[0] + '.') + ' ' + rest.strip()


def nick(name: str) -> str:
    """隊名（不含城市）：最後一個字，Trail Blazers 例外。"""
    return 'Trail Blazers' if name.endswith('Trail Blazers') else name.rsplit(' ', 1)[-1]


def minutes(v) -> int:
    """MIN 可能是整數、小數、"MM:SS" 字串或 None（沒上場）。"""
    if v is None or v == '':
        return 0
    if isinstance(v, str) and ':' in v:
        m, s = v.split(':')[:2]
        return round(int(m) + int(s) / 60)
    return round(float(v))


def ma(m, a) -> str:
    return f'{m or 0}-{a or 0}'


def load_scorer(src: Path):
    """單場評分（Z1，0–10，和名單頁同一套 rating_m10.Scorer）。Scorer 固定讀 data/season-source-2026-27，所以只有預設資料夾才算；
    其他資料夾（測試用的假資料）或算不出來（缺 reports/rating-m10-scurve/params.json）回 None，box 就不帶評分欄。"""
    if src.resolve() != SRC.resolve():
        return None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import rating_m10
        return rating_m10.Scorer('2026-27', 'Z1')
    except Exception as e:   # noqa: BLE001  評分是顯示用，算不出來不擋賽程資料
        print(f'WARNING: 單場評分算不出來，box score 不帶評分欄（{e!r}）', file=sys.stderr)
        return None


def player_row(p: dict, scorer=None) -> dict:
    r = {'n': short_name(p['PLAYER_NAME']), 'pid': p['PLAYER_ID'], 'min': minutes(p['MIN']), 'pts': p['PTS'] or 0, 'reb': p['REB'] or 0, 'oreb': p['OREB'] or 0, 'dreb': p['DREB'] or 0, 'ast': p['AST'] or 0,
         'stl': p['STL'] or 0, 'blk': p['BLK'] or 0, 'tov': p['TOV'] or 0, 'pf': p['PF'] or 0,
         'fg': ma(p['FGM'], p['FGA']), 'tp': ma(p['FG3M'], p['FG3A']), 'ft': ma(p['FTM'], p['FTA']), 'pm': p['PLUS_MINUS'] or 0}
    if scorer is not None and r['min'] > 0:      # 沒上場不給評分；fb＝這場抓不到防守對位，只用 box score 算
        try:
            r['rt'] = round(scorer.score(p['GAME_ID'], p['PLAYER_ID']), 1)
            if scorer.fallback(p['GAME_ID'], p['PLAYER_ID']):
                r['fb'] = 1
        except KeyError:
            pass
    return r


def team_row(t: dict) -> dict:
    return {'pts': t['PTS'], 'reb': t['REB'], 'oreb': t['OREB'], 'dreb': t['DREB'], 'ast': t['AST'], 'stl': t['STL'], 'blk': t['BLK'], 'tov': t['TOV'], 'pf': t['PF'],
            'fg': ma(t['FGM'], t['FGA']), 'tp': ma(t['FG3M'], t['FG3A']), 'ft': ma(t['FTM'], t['FTA'])}


def load_live(src: Path, now: dt.datetime | None = None) -> list[dict]:
    """live-games.json 的進行中場次；檔案不存在、壞掉、fetchedAt 缺或超過 LIVE_MAX_AGE_S 回 []。"""
    try:
        doc = json.loads((src / LIVE_NAME).read_text(encoding='utf-8'))
        at = dt.datetime.fromisoformat(str(doc['fetchedAt']).replace('Z', '+00:00'))
        games = doc['games']
    except (OSError, ValueError, KeyError, TypeError):
        return []
    if at.tzinfo is None:
        at = at.replace(tzinfo=dt.timezone.utc)
    now = now or dt.datetime.now(dt.timezone.utc)
    if (now - at).total_seconds() > LIVE_MAX_AGE_S or not isinstance(games, list):
        return []
    return games


def live_player_row(p: dict) -> dict:
    """即時球員列：鍵同 player_row；liveData 沒給的欄位（pm）省略，不給評分。"""
    r = {'n': short_name(p['name']), 'pid': p['pid'], 'min': minutes(p.get('min'))}
    for k in ('pts', 'reb', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'pf'):
        r[k] = p.get(k) or 0
    r['fg'], r['tp'], r['ft'] = ma(p.get('fgm'), p.get('fga')), ma(p.get('tpm'), p.get('tpa')), ma(p.get('ftm'), p.get('fta'))
    if p.get('pm') is not None:
        r['pm'] = p['pm']
    if p.get('starter'):
        r['st'] = 1
    return r


def live_team_row(side: dict) -> dict:
    """球隊合計：優先用 liveData 的球隊統計，缺的欄位用球員加總補。"""
    t, ps = side.get('team') or {}, side.get('players') or []
    g = lambda k: t[k] if t.get(k) is not None else sum(p.get(k) or 0 for p in ps)
    return {'pts': side['score'], 'reb': g('reb'), 'oreb': g('oreb'), 'dreb': g('dreb'), 'ast': g('ast'), 'stl': g('stl'), 'blk': g('blk'), 'tov': g('tov'), 'pf': g('pf'),
            'fg': ma(g('fgm'), g('fga')), 'tp': ma(g('tpm'), g('tpa')), 'ft': ma(g('ftm'), g('fta'))}


def live_game(lg: dict) -> tuple[dict, dict | None]:
    """一場 live 資料 → (骨架欄位, box 或 None)；資料缺欄位時 raise（呼叫端略過該場）。"""
    extra = {'status': 'live', 'score': {'home': lg['home']['score'], 'away': lg['away']['score']},
             'live': {'p': lg['period'], 'clk': lg.get('gameClock') or '', 'txt': lg.get('status') or ''}}
    if not (lg['home'].get('players') and lg['away'].get('players')):
        return extra, None     # box 抓不到：只帶比分
    box = {k: sorted((live_player_row(p) for p in lg[k]['players'] if p.get('played')),
                     key=lambda r: (not r.get('st'), -r['min'], -r['pts'], r['n'])) for k in ('home', 'away')}
    box['team'] = {k: live_team_row(lg[k]) for k in ('home', 'away')}
    return extra, box


def starters_of(src: Path, gid: str) -> set[int] | None:
    """先發名單（NBA.com liveData boxscore 的 starter 旗標；gamelog 沒有）。只有預設資料夾讀得到；檔案缺或不是兩隊各五人回 None（前端就不畫分隔線）。"""
    if src.resolve() != SRC.resolve():
        return None
    f = ROOT / 'data/defense-seventh/2026-27/boxes' / f'{gid}.json'
    try:
        g = json.loads(f.read_text(encoding='utf-8'))['data']['game']
        out = {t: {int(p['personId']) for p in g[t]['players'] if p.get('starter') == '1'} for t in ('homeTeam', 'awayTeam')}
    except (OSError, KeyError, ValueError, TypeError):
        return None
    return out['homeTeam'] | out['awayTeam'] if all(len(v) == 5 for v in out.values()) else None


def build(src: Path = SRC, now: dt.datetime | None = None) -> tuple[dict, dict[str, dict]]:
    """回傳 (骨架 doc, {YYYY-MM: box doc})。now＝判斷 live 檔是否過期的現在時間（測試用）。"""
    sched = json.loads((src / 'schedule.json').read_text(encoding='utf-8'))
    tg, fetched = rows(src / 'team-games.json')
    pg, _ = rows(src / 'player-games.json')
    scorer = load_scorer(src)

    by_game: dict[str, list[dict]] = {}
    for t in tg:
        by_game.setdefault(t['GAME_ID'], []).append(t)
    players: dict[str, list[dict]] = {}
    for p in pg:
        players.setdefault(p['GAME_ID'], []).append(p)

    games: dict[str, dict] = {}     # game id → 骨架
    box_of: dict[str, dict] = {}    # game id → box
    for gid, d, home, away in sched['games']:
        games[gid] = {'date': d, 'g': {'id': gid, 'home': ABBR[home], 'away': ABBR[away], 'status': 'scheduled'}}
        if gid in sched.get('tipoff', {}):
            games[gid]['g']['tip'] = sched['tipoff'][gid]    # 開賽 UTC（前端轉 UTC+8 顯示）
    for gid, ts in by_game.items():
        if len(ts) != 2:     # 另一隊的列還沒抓到：當未完賽
            continue
        h = next((t for t in ts if ' vs. ' in t['MATCHUP']), None)
        a = next((t for t in ts if ' @ ' in t['MATCHUP']), None)
        if h is None or a is None:     # gamelog 偶爾兩列都寫成「X @ Y」（2026-11-08 DEN／IND 實例）：主客改以賽程為準，賽程也沒有這場才略過
            hid = next((g[2] for g in sched['games'] if g[0] == gid), None)
            h = next((t for t in ts if t['TEAM_ID'] == hid), None)
            a = next((t for t in ts if t is not h), None) if h is not None else None
            if h is None or a is None:
                continue
        g = {'id': gid, 'home': ABBR[h['TEAM_ID']], 'away': ABBR[a['TEAM_ID']], 'status': 'final',
             'score': {'home': h['PTS'], 'away': a['PTS']}, 'winner': ABBR[h['TEAM_ID']] if h['PTS'] > a['PTS'] else ABBR[a['TEAM_ID']]}
        ot = round((h['MIN'] - 240) / 25)    # 球隊 MIN：240 + 每節延長賽 25
        if ot > 0:
            g['ot'] = ot
        games[gid] = {'date': h['GAME_DATE'], 'g': g}
        ps = players.get(gid, [])
        if ps:
            st = starters_of(src, gid)
            def side(tid):
                rs = [player_row(p, scorer) for p in ps if p['TEAM_ID'] == tid]
                if st is not None:
                    for r in rs:
                        if r['pid'] in st:
                            r['st'] = 1
                return sorted(rs, key=lambda r: (not r.get('st'), -r['min'], -r['pts'], r['n']))    # 先發五人在前，各自按上場分鐘
            box_of[gid] = {'home': side(h['TEAM_ID']), 'away': side(a['TEAM_ID']), 'team': {'home': team_row(h), 'away': team_row(a)}}

    # 進行中：只收 schedule 有、gamelog 一列都還沒有的場次（gamelog 已有的以 gamelog 為準）；單場 live 資料壞掉就略過該場
    for lg in load_live(src, now):
        gid = lg.get('gameId') if isinstance(lg, dict) else None
        if gid not in games or gid in by_game:
            continue
        try:
            extra, box = live_game(lg)
        except (KeyError, TypeError, ValueError):
            continue
        games[gid]['g'].update(extra)
        if box is not None:
            box_of[gid] = box

    # 戰績：每隊已完賽場次依 (GAME_DATE, GAME_ID) 排序累計勝負；已完賽場次＝該場結束時，未開打＝開賽前（用已完賽的場次數，不用別處的戰績）
    seq: dict[str, list[tuple]] = {}
    for gid, e in games.items():
        g = e['g']
        if g['status'] == 'final':
            for k in ('home', 'away'):
                seq.setdefault(g[k], []).append(((e['date'], gid), g['winner'] == g[k]))
    keys, wins = {}, {}
    for a, lst in seq.items():
        lst.sort()
        keys[a] = [k for k, _ in lst]
        wins[a] = [0]
        for _, w in lst:
            wins[a].append(wins[a][-1] + w)

    def record(a, key, inclusive):
        n = (bisect.bisect_right if inclusive else bisect.bisect_left)(keys.get(a, []), key)
        w = wins[a][n] if a in wins else 0
        return f'{w}-{n - w}'
    for gid, e in games.items():
        g = e['g']
        g['rec'] = {k: record(g[k], (e['date'], gid), g['status'] == 'final') for k in ('home', 'away')}

    by_date: dict[str, list[dict]] = {}
    for gid in sorted(games):
        by_date.setdefault(games[gid]['date'], []).append(games[gid]['g'])
    dates = sorted(by_date)
    finals = [d for d in dates if any(g['status'] == 'final' for g in by_date[d])]
    skeleton = {'generatedAt': fetched, 'season': sched.get('season'),
                'teams': {a: {'id': i, 'name': n, 'nick': nick(n)} for i, (a, n) in sorted(TEAMS.items(), key=lambda kv: kv[1][0])},
                'dates': dates, 'latest': finals[-1] if finals else (dates[0] if dates else None), 'games': by_date}
    months: dict[str, dict] = {}
    for gid, b in box_of.items():
        months.setdefault(games[gid]['date'][:7], {'games': {}})['games'][gid] = b
    return skeleton, months


def dump(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':'))


def write(out: Path, src: Path = SRC) -> dict[str, Path]:
    """寫出骨架＋各月 box，回傳 {檔名: 路徑}（發布清單用）。"""
    skeleton, months = build(src)
    out.mkdir(parents=True, exist_ok=True)
    files = {DATA_NAME: out / DATA_NAME}
    files[DATA_NAME].write_text(dump(skeleton), encoding='utf-8')
    for m, doc in sorted(months.items()):
        name = BOX_FMT.format(m)
        files[name] = out / name
        files[name].write_text(dump({'month': m, **doc}), encoding='utf-8')
    return files


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    files = write(Path(a[0]), Path(a[1]) if len(a) > 1 else SRC)
    print('\n'.join(f'{n}\t{p.stat().st_size}' for n, p in files.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
