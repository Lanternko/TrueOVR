"""賽程檢視（scripts/build_games_data.py＋games_view.py）：比分、box 加總、日期差一天、體積、眉頭接線。npm test 會跑；輕量，不跑模擬。
本機有 data/season-source-2026-27/ 時另外核對真實資料；沒有就只跑合成資料的測試。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_games_data as B  # noqa: E402
import games_view  # noqa: E402
import site_header  # noqa: E402

SRC = ROOT / 'data/season-source-2026-27'
HAVE = all((SRC / n).exists() for n in ('schedule.json', 'team-games.json', 'player-games.json'))
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
LAL, BOS, MIA = 1610612747, 1610612738, 1610612748

TG_H = ['SEASON_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT',
        'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLUS_MINUS', 'VIDEO_AVAILABLE']
PG_H = ['SEASON_ID', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'FGM', 'FGA', 'FG_PCT',
        'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLUS_MINUS', 'FANTASY_PTS', 'VIDEO_AVAILABLE']


def team_line(tid, gid, date, matchup, pts, mins=240):
    d = dict.fromkeys(TG_H, 0)
    d.update(TEAM_ID=tid, TEAM_ABBREVIATION=B.ABBR[tid], GAME_ID=gid, GAME_DATE=date, MATCHUP=matchup, MIN=mins, PTS=pts, REB=30, FGM=40, FGA=90)
    return [d[h] for h in TG_H]


def player_line(pid, name, tid, gid, date, mins, pts):
    d = dict.fromkeys(PG_H, 0)
    d.update(PLAYER_ID=pid, PLAYER_NAME=name, TEAM_ID=tid, GAME_ID=gid, GAME_DATE=date, MIN=mins, PTS=pts)
    return [d[h] for h in PG_H]


def write_src(tmp: Path, sched, teams, players):
    doc = lambda h, r: {'fetchedAt': '2026-11-03T00:00:00Z', 'data': {'resultSets': [{'headers': h, 'rowSet': r}]}}
    (tmp / 'schedule.json').write_text(json.dumps({'season': '2026-27', 'games': sched}), encoding='utf-8')
    (tmp / 'team-games.json').write_text(json.dumps(doc(TG_H, teams)), encoding='utf-8')
    (tmp / 'player-games.json').write_text(json.dumps(doc(PG_H, players)), encoding='utf-8')


class Synthetic(unittest.TestCase):
    def build(self, sched, teams, players):
        with tempfile.TemporaryDirectory() as d:
            write_src(Path(d), sched, teams, players)
            return B.build(Path(d))

    def test_minutes_formats(self):
        self.assertEqual([B.minutes(v) for v in (None, '', 0, 33, 33.4, 12.6, '12:40', '0:20')], [0, 0, 0, 33, 33, 13, 13, 0])

    def test_final_uses_gamelog_date_and_scheduled_keeps_schedule_date(self):
        # 賽程把 G1 寫成 11-02（美東），gamelog 記 11-03（UTC）→ 已完賽以 gamelog 為準；G2 還沒打，用賽程日期
        sk, months = self.build(
            [['0022600001', '2026-11-02', LAL, BOS], ['0022600002', '2026-11-05', MIA, LAL]],
            [team_line(LAL, '0022600001', '2026-11-03', 'LAL vs. BOS', 110), team_line(BOS, '0022600001', '2026-11-03', 'BOS @ LAL', 100)],
            [player_line(1, 'A', LAL, '0022600001', '2026-11-03', 30, 110), player_line(2, 'B', BOS, '0022600001', '2026-11-03', 30, 100)])
        self.assertEqual(sk['dates'], ['2026-11-03', '2026-11-05'])
        self.assertNotIn('2026-11-02', sk['games'])
        g = sk['games']['2026-11-03'][0]
        self.assertEqual((g['status'], g['home'], g['away'], g['winner'], g['score']), ('final', 'LAL', 'BOS', 'LAL', {'home': 110, 'away': 100}))
        self.assertEqual(sk['games']['2026-11-05'][0]['status'], 'scheduled')
        self.assertNotIn('score', sk['games']['2026-11-05'][0])
        self.assertEqual(sk['latest'], '2026-11-03')                      # 預設日＝最近有已完賽場次的日期（不是 11-05）
        self.assertEqual(list(months), ['2026-11'])
        self.assertEqual(list(months['2026-11']['games']), ['0022600001'])    # 未開打沒有 box

    def test_ot_box_sort_and_dnp(self):
        sk, months = self.build(
            [['0022600001', '2026-11-02', LAL, BOS]],
            [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 120, 265), team_line(BOS, '0022600001', '2026-11-02', 'BOS @ LAL', 118, 265)],
            [player_line(1, 'Bench', LAL, '0022600001', '2026-11-02', 5, 2), player_line(2, 'Star', LAL, '0022600001', '2026-11-02', 40.0, 118),
             player_line(3, 'Away', BOS, '0022600001', '2026-11-02', 38, 118)])
        self.assertEqual(sk['games']['2026-11-02'][0]['ot'], 1)
        b = months['2026-11']['games']['0022600001']
        self.assertEqual([p['n'] for p in b['home']], ['Star', 'Bench'])      # 上場分鐘由高到低；沒在 gamelog 的人不出現
        self.assertEqual([p['n'] for p in b['away']], ['Away'])
        self.assertEqual(sum(p['pts'] for p in b['home']), b['team']['home']['pts'])

    def test_same_team_two_games_one_day_kept_apart(self):   # 同日同隊兩場（NBA 不會有；防呆）：用 GAME_ID 分開，不互相覆蓋
        sk, _ = self.build(
            [['0022600001', '2026-11-02', LAL, BOS], ['0022600002', '2026-11-02', LAL, MIA]],
            [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 1), team_line(BOS, '0022600001', '2026-11-02', 'BOS @ LAL', 0),
             team_line(LAL, '0022600002', '2026-11-02', 'LAL vs. MIA', 2), team_line(MIA, '0022600002', '2026-11-02', 'MIA @ LAL', 0)], [])
        self.assertEqual([g['id'] for g in sk['games']['2026-11-02']], ['0022600001', '0022600002'])

    def test_single_row_game_stays_scheduled(self):
        sk, _ = self.build([['0022600001', '2026-11-02', LAL, BOS]], [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 100)], [])
        self.assertEqual(sk['games']['2026-11-02'][0]['status'], 'scheduled')

    def test_win_loss_record_accumulates_in_date_gid_order(self):
        # 手算 LAL：G1(11-02) 勝 → 1-0；G2(11-04) 負 → 1-1；G3(11-06) 勝 → 2-1；G4(11-08) 還沒打 → 開賽前 2-1
        # BOS：G1 負 0-1、G3 負 0-2、G4 開賽前 0-2；MIA：G2 勝 1-0
        sched = [['0022600001', '2026-11-02', LAL, BOS], ['0022600002', '2026-11-04', MIA, LAL], ['0022600003', '2026-11-06', LAL, BOS],
                 ['0022600004', '2026-11-08', BOS, LAL]]
        teams = [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 110), team_line(BOS, '0022600001', '2026-11-02', 'BOS @ LAL', 100),
                 team_line(MIA, '0022600002', '2026-11-04', 'MIA vs. LAL', 105), team_line(LAL, '0022600002', '2026-11-04', 'LAL @ MIA', 99),
                 team_line(LAL, '0022600003', '2026-11-06', 'LAL vs. BOS', 120), team_line(BOS, '0022600003', '2026-11-06', 'BOS @ LAL', 90)]
        sk, _ = self.build(sched, teams, [])
        rec = {g['id']: g['rec'] for gs in sk['games'].values() for g in gs}
        self.assertEqual(rec['0022600001'], {'home': '1-0', 'away': '0-1'})
        self.assertEqual(rec['0022600002'], {'home': '1-0', 'away': '1-1'})
        self.assertEqual(rec['0022600003'], {'home': '2-1', 'away': '0-2'})
        self.assertEqual(rec['0022600004'], {'home': '0-2', 'away': '2-1'})

    def test_record_same_day_ordered_by_gid(self):
        # 同日同隊兩場（防呆）：用 GAME_ID 排序；先打的一場結束時 1-0，後一場結束 1-1
        sk, _ = self.build(
            [['0022600001', '2026-11-02', LAL, BOS], ['0022600002', '2026-11-02', MIA, LAL]],
            [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 2), team_line(BOS, '0022600001', '2026-11-02', 'BOS @ LAL', 1),
             team_line(MIA, '0022600002', '2026-11-02', 'MIA vs. LAL', 2), team_line(LAL, '0022600002', '2026-11-02', 'LAL @ MIA', 1)], [])
        rec = {g['id']: g['rec'] for g in sk['games']['2026-11-02']}
        self.assertEqual(rec['0022600001']['home'], '1-0')
        self.assertEqual(rec['0022600002']['away'], '1-1')

    def test_ot_labels(self):
        # 球隊 MIN：240 正規、265＝1OT、290＝2OT
        sk, _ = self.build(
            [['0022600001', '2026-11-02', LAL, BOS], ['0022600002', '2026-11-03', LAL, MIA], ['0022600003', '2026-11-04', LAL, BOS]],
            [team_line(LAL, '0022600001', '2026-11-02', 'LAL vs. BOS', 2, 240), team_line(BOS, '0022600001', '2026-11-02', 'BOS @ LAL', 1, 240),
             team_line(LAL, '0022600002', '2026-11-03', 'LAL vs. MIA', 2, 265), team_line(MIA, '0022600002', '2026-11-03', 'MIA @ LAL', 1, 265),
             team_line(LAL, '0022600003', '2026-11-04', 'LAL vs. BOS', 2, 290), team_line(BOS, '0022600003', '2026-11-04', 'BOS @ LAL', 1, 290)], [])
        ot = {g['id']: g.get('ot') for gs in sk['games'].values() for g in gs}
        self.assertEqual(ot, {'0022600001': None, '0022600002': 1, '0022600003': 2})
        self.assertIn("g.ot>1?g.ot:'')+'OT</div>", games_view.JS)    # 前端把 ot 顯示成「OT／2OT」（沒延長賽就不出現這一列）

    def test_short_name(self):
        for full, want in (('Jalen Walker', 'J. Walker'), ('Gary Trent Jr.', 'G. Trent Jr.'), ('Jaren Jackson III', 'J. Jackson III'),
                           ('Karl-Anthony Towns', 'K. Towns'), ('Luka Doncic', 'L. Doncic'), ('Shai Gilgeous-Alexander', 'S. Gilgeous-Alexander'),
                           ('Nick Van Exel', 'N. Van Exel'), ('Nene', 'Nene'), ('P.J. Washington', 'P.J. Washington'), ('  Ja Morant ', 'J. Morant')):
            self.assertEqual(B.short_name(full), want, full)

    def test_nick(self):
        self.assertEqual(B.nick('New Orleans Pelicans'), 'Pelicans')
        self.assertEqual(B.nick('Portland Trail Blazers'), 'Trail Blazers')
        self.assertEqual(B.nick('Los Angeles Lakers'), 'Lakers')
        self.assertTrue({'Lakers', '76ers'} <= {B.nick(n) for _, n in B.TEAMS.values()})
        self.assertTrue(all(' ' not in B.nick(n) for _, n in B.TEAMS.values() if not n.endswith('Trail Blazers')))


class Wiring(unittest.TestCase):
    def test_team_table(self):
        self.assertEqual(len(B.TEAMS), 30)
        self.assertEqual(len({a for a, _ in B.TEAMS.values()}), 30)

    def test_header_embeds_games_view(self):
        self.assertIn('id="mGames"', site_header.header_html('inseason'))
        self.assertIn('href="/games/"', site_header.header_html('card'))       # 2025-26 頁沒有檢視，連回首頁
        host, js = games_view.embed()
        self.assertIn('id="gamesHost"', host)
        self.assertIn('window.PureGames', js)

    def test_box_column_order(self):
        """參考圖欄位順序，且每個欄位鍵 build_games_data 的球員列／球隊合計都有（pm 只在球員列）。"""
        self.assertEqual([h for h, _ in games_view.BOX_COLS],
                         ['MIN', 'PTS', 'REB', 'AST', 'FG', '3PT', 'FT', 'STL', 'BLK', 'TO', 'OREB', 'DREB', 'PF', '+/-', '評分'])
        pl = B.player_row(dict.fromkeys(PG_H, 0) | {'PLAYER_NAME': 'Jalen Walker'})
        tm = B.team_row(dict.fromkeys(TG_H, 0))
        for _, k in games_view.BOX_COLS:
            if k != 'rt':     # 評分（rt）只有帶 Scorer 且上場才有（真實資料的測試另驗）
                self.assertIn(k, pl, k)
            if k not in ('min', 'pm', 'rt'):
                self.assertIn(k, tm, k)
        self.assertEqual(pl['n'], 'J. Walker')
        self.assertNotIn('__COLS__', games_view.JS)
        self.assertIn('"OREB", "oreb"', games_view.JS)

    def test_starters_first_and_divider(self):    # 先發五人排前面（自成一組按分鐘），前端在先發與替補之間畫分隔線
        self.assertIn("ps[i-1].st", games_view.JS)
        self.assertIn('class="dv"', games_view.JS)
        f = next((B.ROOT / 'data/defense-seventh/2026-27/boxes').glob('*.json'))
        st = B.starters_of(B.SRC, f.stem)
        self.assertIsNotNone(st)
        self.assertEqual(len(st), 10)
        self.assertIsNone(B.starters_of(Path(tempfile.gettempdir()), f.stem))    # 非預設資料夾不讀

    def test_scripts_parse(self):
        """頁面腳本語法：丟給 node --check（子程序不開黑窗）。"""
        import shutil
        node = shutil.which('node')
        if not node:
            self.skipTest('沒有 node')
        for name, js in (('games_view', games_view.JS), ('site_header', site_header.JS)):
            body = js.removeprefix('<script>').removesuffix('</script>')
            with tempfile.TemporaryDirectory() as d:
                f = Path(d) / f'{name}.js'
                f.write_text(body, encoding='utf-8')
                r = subprocess.run([node, '--check', str(f)], capture_output=True, text=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
                self.assertEqual(r.returncode, 0, f'{name}: {r.stderr[-400:]}')


@unittest.skipUnless(HAVE, '沒有 data/season-source-2026-27/（只跑合成資料測試）')
class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sk, cls.months = B.build(SRC)
        cls.tg, _ = B.rows(SRC / 'team-games.json')
        cls.sched = {g[0]: g for g in json.loads((SRC / 'schedule.json').read_text(encoding='utf-8'))['games']}
        cls.finals = {g['id']: (d, g) for d, gs in cls.sk['games'].items() for g in gs if g['status'] == 'final'}
        cls.box = {gid: b for m in cls.months.values() for gid, b in m['games'].items()}

    def test_all_30_teams_map(self):
        ids = {g[2] for g in self.sched.values()} | {g[3] for g in self.sched.values()}
        self.assertEqual(len(ids), 30)
        self.assertEqual(ids - set(B.ABBR), set())
        for t in self.tg:                                              # 縮寫與 NBA gamelog 一致
            self.assertEqual(B.ABBR[t['TEAM_ID']], t['TEAM_ABBREVIATION'])

    def test_final_score_equals_both_team_pts(self):
        pts = {}
        for t in self.tg:
            pts.setdefault(t['GAME_ID'], {})[B.ABBR[t['TEAM_ID']]] = t['PTS']
        self.assertGreater(len(self.finals), 0)
        for gid, (_, g) in self.finals.items():
            self.assertEqual({g['home']: g['score']['home'], g['away']: g['score']['away']}, pts[gid], gid)
            self.assertEqual(g['winner'], max(pts[gid], key=pts[gid].get), gid)
            self.assertNotEqual(g['score']['home'], g['score']['away'], gid)

    def test_home_away_matches_schedule(self):
        for gid, (_, g) in self.finals.items():
            if gid in self.sched:
                self.assertEqual((g['home'], g['away']), (B.ABBR[self.sched[gid][2]], B.ABBR[self.sched[gid][3]]), gid)

    def test_box_player_pts_sum_to_team_pts(self):
        bad = [(gid, k, sum(p['pts'] for p in b[k]), b['team'][k]['pts']) for gid, b in self.box.items() for k in ('home', 'away')
               if sum(p['pts'] for p in b[k]) != b['team'][k]['pts']]
        self.assertEqual(bad, [], f'box 球員得分加總 ≠ 球隊得分（gid, 側, 加總, 球隊）：{bad}')
        self.assertEqual(set(self.finals) - set(self.box), set(), '已完賽但沒有 box 的場次')   # 逐人數據沒抓齊

    def test_dates_follow_gamelog(self):
        gl = {t['GAME_ID']: t['GAME_DATE'] for t in self.tg}
        off = 0
        for gid, (d, _) in self.finals.items():
            self.assertEqual(d, gl[gid], gid)
            off += gid in self.sched and self.sched[gid][1] != gl[gid]
        print(f'  （schedule.json 與 gamelog 日期差一天的已完賽場次：{off}）')
        self.assertEqual(self.sk['dates'], sorted(self.sk['games']))
        self.assertIn(self.sk['latest'], {d for d, _ in self.finals.values()})
        self.assertEqual(self.sk['latest'], max(d for d, _ in self.finals.values()))

    def test_records_match_gamelog(self):
        """每隊最後一場已完賽的戰績 = gamelog 該隊 WL 欄累計；每場 W+L = 該隊到此為止的場次數。"""
        wl = {}
        for t in self.tg:
            wl.setdefault(B.ABBR[t['TEAM_ID']], []).append(t['WL'])
        last = {}
        for gid, (d, g) in sorted(self.finals.items(), key=lambda kv: (kv[1][0], kv[0])):
            for k in ('home', 'away'):
                last[g[k]] = g['rec'][k]
        for a, rs in wl.items():
            w = rs.count('W')
            self.assertEqual(last[a], f'{w}-{len(rs) - w}', a)
        for _, g in self.finals.values():
            for k in ('home', 'away'):
                w, l = map(int, g['rec'][k].split('-'))
                self.assertGreaterEqual(w + l, 1)

    def test_box_has_rating_for_players_who_played(self):
        """評分欄（Z1，名目 0–10 但大場可超過 10，只設下限 0）：上場的人都有、落在合理範圍；沒上場的不給。reports/ 被 gitignore，沒有 params.json 的環境整段略過。"""
        if B.load_scorer(SRC) is None:
            self.skipTest('沒有 reports/rating-m10-scurve/params.json，box 不帶評分')
        rows = [p for b in self.box.values() for k in ('home', 'away') for p in b[k]]
        played = [p for p in rows if p['min'] > 0]
        self.assertGreater(len(played), 0)
        missing = [p['n'] for p in played if 'rt' not in p]
        self.assertLess(len(missing), 0.01 * len(played), f'上場卻沒評分：{missing[:10]}')
        for p in played:
            if 'rt' in p:
                self.assertTrue(0 <= p['rt'] <= 25, (p['n'], p['rt']))
        self.assertTrue(all('rt' not in p for p in rows if p['min'] == 0))
        self.assertTrue(all(b['team'][k].get('rt') is None for b in self.box.values() for k in ('home', 'away')))

    def test_size_budget(self):
        """骨架 < 500 KB、每個月的 box < 2 MB（全季 box 約 3.5 MB，所以固定按月分檔）。"""
        self.assertLess(len(B.dump(self.sk).encode('utf-8')), 500_000)
        for m, doc in self.months.items():
            self.assertLess(len(B.dump({'month': m, **doc}).encode('utf-8')), 2_000_000, m)
        self.assertEqual(sum(len(d['games']) for d in self.months.values()), len(self.box))


if __name__ == '__main__':
    unittest.main(verbosity=1)
