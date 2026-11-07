"""daily_inseason_update 的單元測試與本機 bare repo 發布測試。
執行：python -m unittest test/daily_inseason_update.py  （或 pytest test/daily_inseason_update.py）
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import daily_inseason_update as D  # noqa: E402

NW = subprocess.CREATE_NO_WINDOW
ENV = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
       'GIT_COMMITTER_EMAIL': 't@t', 'GIT_TERMINAL_PROMPT': '0'}


def git(cwd, *a):
    r = subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, encoding='utf-8', env=ENV, creationflags=NW)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


class Versions(unittest.TestCase):
    def test_decide(self):
        base = 'inseason 0.1.1'
        # 第一次：無 state -> 發布
        d = D.decide({}, base, 'h1', 5, False)
        self.assertTrue(d['publish']); self.assertNotIn('letter', d)
        st = {'base': base, 'dataSha256': 'h1', 'pbpCount': 5}
        # 資料沒變不發布
        self.assertFalse(D.decide(st, base, 'h1', 5, False)['publish'])
        # 資料變 -> 發布，版號不變（R-063：只更新資料不加字母）
        self.assertTrue(D.decide(st, base, 'h2', 5, False)['publish'])
        # 只有 PBP 檔數變也算
        self.assertTrue(D.decide(st, base, 'h1', 6, False)['publish'])
        # force：資料沒變也發布
        self.assertTrue(D.decide(st, base, 'h1', 5, True)['publish'])
        # 版號變（含 hotfix 字母）-> 發布，即使資料沒變
        self.assertTrue(D.decide(st, 'inseason 0.1.1a', 'h1', 5, False)['publish'])
        self.assertFalse(hasattr(D, 'letter_next'))

    def test_commit_message(self):
        m = D.commit_message('inseason 0.1.1a', '2026-10-28')
        self.assertTrue(m.startswith('inseason 0.1.1a 數據至 2026-10-28'))
        self.assertTrue(m.rstrip().endswith('Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'))


class Lock(unittest.TestCase):
    def test_lock(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'x.lock'
            with D.Lock(p):
                with self.assertRaises(D.LockBusy):
                    with D.Lock(p):
                        pass
            self.assertFalse(p.exists())
            with D.Lock(p):
                pass


class Publish(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = Path(self.t.name)
        self.bare = t / 'origin.git'
        git(t, 'init', '--bare', '-b', 'main', str(self.bare))
        self.dev = t / 'dev'
        git(t, 'clone', str(self.bare), str(self.dev))
        git(self.dev, 'checkout', '-b', 'gh-pages')
        (self.dev / 'index.html').write_text('v0', encoding='utf-8')
        git(self.dev, 'add', '.'); git(self.dev, 'commit', '-m', 'init'); git(self.dev, 'push', 'origin', 'gh-pages')
        # 開發 checkout 有未 commit 改動，不應被碰
        (self.dev / 'wip.txt').write_text('wip', encoding='utf-8')
        self.html = t / 'roster-viewer.html'

    def tearDown(self):
        self.t.cleanup()

    def pub(self, text, **kw):
        self.html.write_text(text, encoding='utf-8')
        self.card = self.html.with_name('card.html')
        self.card.write_text(text + '-card', encoding='utf-8')
        return D.publish_html(self.dev, {'index.html': self.html, '2025-26.html': self.card},
                              D.commit_message('inseason 0.1.1a', '2026-10-28'), **kw)

    def show(self, ref='gh-pages', name='index.html'):
        return git(self.bare, 'show', f'{ref}:{name}')

    def test_publish_and_noop(self):
        sha = self.pub('v1')
        self.assertTrue(sha)
        self.assertEqual(self.show(), 'v1')
        self.assertEqual(git(self.bare, 'rev-parse', 'gh-pages'), sha)
        self.assertEqual(self.show(name='2025-26.html'), 'v1-card')
        self.assertEqual(git(self.bare, 'ls-tree', '--name-only', 'gh-pages').splitlines(), ['2025-26.html', 'index.html'])
        self.assertNotIn('wip.txt', git(self.bare, 'ls-tree', '--name-only', 'gh-pages'))
        self.assertIsNone(self.pub('v1'))  # 內容相同不提交
        self.assertTrue((self.dev / 'wip.txt').exists())
        self.assertNotIn('inseason-pages', git(self.dev, 'worktree', 'list'))  # 工作樹已清掉
        self.assertIn('Claude Opus 5.5', git(self.bare, 'log', '-1', '--format=%B', 'gh-pages'))

    def test_non_fast_forward_retry(self):
        other = Path(self.t.name) / 'other'
        git(Path(self.t.name), 'clone', '-b', 'gh-pages', str(self.bare), str(other))

        def race():  # 在我們 push 前，別處先推了一個 commit（改別的檔）
            (other / 'extra.txt').write_text('x', encoding='utf-8')
            git(other, 'add', '.'); git(other, 'commit', '-m', 'race'); git(other, 'push', 'origin', 'gh-pages')

        sha = self.pub('v2', before_push=race)
        self.assertTrue(sha)
        self.assertEqual(self.show(), 'v2')
        self.assertEqual(self.show(name='2025-26.html'), 'v2-card')
        self.assertIn('extra.txt', git(self.bare, 'ls-tree', '--name-only', 'gh-pages'))
        self.assertEqual(git(self.bare, 'rev-parse', 'gh-pages'), sha)

    def test_race_conflict_on_index_prefers_ours(self):
        other = Path(self.t.name) / 'other2'
        git(Path(self.t.name), 'clone', '-b', 'gh-pages', str(self.bare), str(other))

        def race():
            (other / 'index.html').write_text('theirs', encoding='utf-8')
            git(other, 'add', '.'); git(other, 'commit', '-m', 'race'); git(other, 'push', 'origin', 'gh-pages')

        self.pub('ours', before_push=race)
        self.assertEqual(self.show(), 'ours')
        self.assertEqual(self.show(name='2025-26.html'), 'ours-card')

    def test_single_file_backward_compat(self):
        self.html.write_text('solo', encoding='utf-8')
        self.assertTrue(D.publish_html(self.dev, self.html, 'm'))
        self.assertEqual(self.show(), 'solo')


class Shell(unittest.TestCase):
    """--shell：只重建頁面並發布；不抓資料、不跑 C4，版號與 dataSha256 不動。"""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = Path(self.t.name)
        self.saved = {k: getattr(D, k) for k in ['LIVE', 'STATE_PATH', 'BUILD_ROOT', 'LOG_PATH', 'LOCK_PATH',
                                                  'step_fetch_games', 'step_fetch_inseason', 'step_c4',
                                                  'step_viewer', 'step_card_viewer', 'step_team_ratings', 'step_games_data', 'publish_html']}
        D.LIVE, D.STATE_PATH, D.BUILD_ROOT = t / 'live', t / 'live/publish_state.json', t / 'build'
        D.LOG_PATH, D.LOCK_PATH = t / 'daily.log', t / 'daily.lock'
        (D.LIVE / '2026-10-27').mkdir(parents=True)
        (D.LIVE / '2026-10-27/meta.json').write_text('{}', encoding='utf-8')
        self.state = {'base': 'inseason 0.2.0', 'letter': 'a', 'displayVersion': 'inseason 0.2.0a',
                      'dataSha256': 'h1', 'pbpCount': 5, 'dataCutoff': '2026-10-27', 'ghPagesCommit': 'old'}
        D.save_json(D.STATE_PATH, self.state)

        def boom(*a, **k):
            raise AssertionError('shell 不該抓資料或跑 C4')
        D.step_fetch_games = D.step_fetch_inseason = D.step_c4 = boom

        def viewer(name):
            def f(work):
                (work / name).write_text('x' * 20_000, encoding='utf-8')
                return work / name
            return f
        D.step_viewer, D.step_card_viewer = viewer('roster-viewer.html'), viewer('card-roster-viewer.html')
        make_teams = viewer('teams.html')

        def teams(out_dir, live_dir, recompute=True):
            (out_dir / 'teams-data.json').write_text('{}', encoding='utf-8')
            return make_teams(out_dir)
        D.step_team_ratings = teams
        D.step_games_data = lambda work: {}                 # 賽程資料另有測試；這裡只看頁面清單
        self.calls = []
        D.publish_html = lambda repo, files, msg, **kw: self.calls.append((files, msg)) or 'new'

    def tearDown(self):
        for h in D.log.handlers[:]:  # main() 每次掛新的 log handler，關掉才刪得掉暫存 log
            h.close()
            D.log.removeHandler(h)
        for k, v in self.saved.items():
            setattr(D, k, v)
        self.t.cleanup()

    def test_shell_publish(self):
        self.assertEqual(D.main(['--shell']), 0)
        files, msg = self.calls[0]
        self.assertEqual(sorted(files), ['2025-26.html', '404.html', 'games/index.html', 'index.html', 'rank/index.html',
                                         'teams-data.json', 'teams.html'])
        self.assertTrue(msg.startswith('inseason 0.2.0a 頁面更新（數據至 2026-10-27'))
        st = D.load_json(D.STATE_PATH)
        self.assertEqual(st['ghPagesCommit'], 'new')
        for k in ['base', 'letter', 'displayVersion', 'dataSha256', 'pbpCount', 'dataCutoff']:
            self.assertEqual(st[k], self.state[k])
        self.assertTrue((D.LIVE / '2026-10-27/roster-viewer.html').exists())

    def test_shell_teams_failure_does_not_block_other_pages(self):
        D.step_team_ratings = lambda *a, **k: None          # 球隊評分失敗：step 回 None，原頁照常發布
        self.assertEqual(D.main(['--shell']), 0)
        self.assertEqual(sorted(self.calls[0][0]), ['2025-26.html', '404.html', 'games/index.html', 'index.html', 'rank/index.html'])

    def test_step_team_ratings_swallows_errors(self):
        D.step_team_ratings = self.saved['step_team_ratings']
        saved = D.checked
        D.checked = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom'))
        try:
            self.assertIsNone(D.step_team_ratings(Path(self.t.name), Path(self.t.name)))
        finally:
            D.checked = saved

    def test_shell_dry_run(self):
        self.assertEqual(D.main(['--shell', '--dry-run']), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(D.load_json(D.STATE_PATH), self.state)

    def test_shell_without_state_fails(self):
        D.save_json(D.STATE_PATH, {})
        self.assertEqual(D.main(['--shell']), 1)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
