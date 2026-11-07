"""live/ 現行版本閘門（R-107）：舊執行路徑不能再被誤用。npm test 會跑。
檢查：(1) 直接執行 run_c4_live.py 非 0 結束；(2) 舊 CARD_MODE 失敗；(3) CURRENT.json 的版本、檔案與 run_c4_live.py／daily 入口一致；
(4) live/ 頂層沒有其他版本的 build_usage_*／build_prior_*／usage-*／prior-*／pool-* 檔。
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'reports' / 'ovr-inseason-2026-27' / 'live'
sys.path.insert(0, str(ROOT / 'scripts'))
NW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
CUR = json.loads((LIVE / 'CURRENT.json').read_text(encoding='utf-8'))


def run(args, env=None):
    return subprocess.run([sys.executable, '-I', '-X', 'utf8', *args], cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', env={**os.environ, **(env or {})}, creationflags=NW, timeout=120, stdin=subprocess.DEVNULL)


class LiveCurrent(unittest.TestCase):
    def test_direct_run_blocked(self):
        r = run([str(LIVE / 'run_c4_live.py')])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('run_c4_live_rookie.py', r.stdout + r.stderr)

    def test_old_card_mode_fails(self):
        code = ("import sys; sys.path.insert(0, r'%s'); import run_c4_live_rookie as R; R.load_ns()" % str(LIVE))
        for bad in ('029a', '029', '028', '027b'):
            r = run(['-c', code], env={'CARD_MODE': bad})
            self.assertNotEqual(r.returncode, 0, f'CARD_MODE={bad} 應失敗')
        r = run(['-c', code], env={'CARD_MODE': CUR['cardMode']})
        self.assertEqual(r.returncode, 0, r.stderr[-500:])

    def test_current_matches_source(self):
        src = (LIVE / CUR['base']).read_text(encoding='utf-8')
        self.assertEqual(re.search(r"^VERSION\s*=\s*'([^']+)'", src, re.M).group(1), CUR['inseason'])
        self.assertEqual(re.search(r"^CARD_VERSION\s*=\s*'([^']+)'", src, re.M).group(1), CUR['card'])
        import daily_inseason_update as D
        self.assertEqual(D.probe_base_version(), CUR['inseason'])
        self.assertEqual(D.RUN_LIVE.name, CUR['entry'])
        self.assertEqual(D.RUN_C4.name, CUR['base'])
        for f in CUR['files']:
            self.assertTrue((LIVE / f).exists(), f'CURRENT.json 列的檔不存在：{f}')

    def test_no_stray_versions(self):
        pat = re.compile(r'^(build_usage_|build_prior_|usage-|prior-|pool-)')
        keep = set(CUR['files']) | {'build_rookie_prior.py'}
        stray = [p.name for p in LIVE.iterdir() if p.is_file() and pat.match(p.name) and p.name not in keep]
        self.assertEqual(stray, [], f'live/ 頂層有不在 CURRENT.json 的版本檔，請搬進 _retired/：{stray}')


if __name__ == '__main__':
    unittest.main()
