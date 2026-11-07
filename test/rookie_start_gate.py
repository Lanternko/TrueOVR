"""新秀開季起點閘門（R-096；2026-11-01 0.2.10e～h 換版後 δ 沒重解，起點悄悄跑掉）。npm test 會跑。
檢查：live/rookie-prior-2026.json 每個新秀，用現行版本（CURRENT.json 指定的 run_c4_live_rookie 管線）算出的「沒有數據時的 OVR」
（＝頁面 ovr-history 的 start／ranking 的 lastOVR 同一個量）與該人存在檔裡的目標差 ≤ 0.5；不合就失敗並列名字。
目標＝T(順位) = 73 − 5.9·ln 順位（R-096）＋季前賽位移 ps.shift（R-162，0.2.12e；沒有 ps 的檔就是 0）。另外檢查存檔目標 = T + ps.shift，位移不超過 ±12。
失敗時：python -I -X utf8 reports/ovr-inseason-2026-27/live/apply_ps_start.py 重解 δ（換版後都要重跑）。
環境變數 ROOKIE_PRIOR_PATH 可指定別的 rookie-prior 檔（驗證用）。
"""
import json
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'reports' / 'ovr-inseason-2026-27' / 'live'
NW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
CURVE_A, CURVE_B = 73.0, 5.9        # R-096
TOL = 0.5

CODE = r'''
import json, os, sys
sys.path.insert(0, %r)
import run_c4_live_rookie as RW
ns = RW.load_ns()
C, V2 = ns['C'], ns['V2']
ns['setup']()
pw = ns['PW'].for_start(C, 'S*')
anc, r_repl = ns['e064_anchors']()
rel = V2.load_reliability()
doc = json.load(open(os.environ.get('ROOKIE_PRIOR_PATH') or RW.ROOKIE_JSON, encoding='utf-8'))
out = [[rk['name'], rk['pick'], RW.eval_rookie(ns, pw, anc, r_repl, rk, None, 'e116', rel)['ovr'], (rk.get('ps') or {}).get('shift', 0.0), rk['e121']['target']] for rk in doc['players']]
sys.stderr.flush()
print('@@' + json.dumps(out, ensure_ascii=False))
''' % str(LIVE)


def start_ovrs():
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', CODE], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', env=dict(os.environ), creationflags=NW, timeout=300, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    line = [x for x in r.stdout.splitlines() if x.startswith('@@')][-1]
    return json.loads(line[2:])


class RookieStart(unittest.TestCase):
    def test_start_on_r096_curve(self):
        rows = start_ovrs()
        self.assertGreater(len(rows), 30, '新秀人數太少，rookie-prior 檔不對')
        bad = []
        for name, pick, ovr, shift, stored in rows:
            t = CURVE_A - CURVE_B * math.log(pick) + shift
            if abs(shift) > 12:
                bad.append(f'{name}（順位 {pick}）PS 位移 {shift:+.1f} 超過 ±12')
            if abs(stored - t) > 0.02:
                bad.append(f'{name}（順位 {pick}）存檔目標 {stored:.2f} ≠ 曲線＋位移 {t:.2f}')
            if abs(ovr - t) > TOL:
                bad.append(f'{name}（順位 {pick}）起點 {ovr:.1f}、目標 {t:.1f}（含 PS 位移 {shift:+.1f}）')
        self.assertEqual(bad, [], '新秀起點跑掉（換版後要重跑 reports/ovr-inseason-2026-27/live/apply_ps_start.py）：\n' + '\n'.join(bad))


if __name__ == '__main__':
    unittest.main()
