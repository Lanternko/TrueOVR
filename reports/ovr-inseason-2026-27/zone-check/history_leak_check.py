"""問題 2 驗證：逐日重算（ovr_history.one 同路徑：換 ns['DATA26'] 後 win8_load）的 8 項值，要等於直接用截斷資料夾跑 Win8(dir).attrs_at。
也量「舊行為」（Win8() 預設讀全季資料）和截斷版差多少。用法：python -I -X utf8 history_leak_check.py [YYYY-MM-DD]"""
import sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
import ovr_history as H  # noqa: E402
import run_c4_live_rookie as RK  # noqa: E402
import window8 as W8  # noqa: E402

day = sys.argv[1] if len(sys.argv) > 1 else '2026-10-27'
with tempfile.TemporaryDirectory(dir=ROOT / 'data/_inseason_build') as tmp:
    d = Path(tmp) / 'data'
    H.truncate(day, d)
    t0 = time.time()
    W = W8.Win8(d)
    tabs, gd = W.cur_tabs()
    direct = W.attrs_at(gd, tabs)
    print('direct', gd, 'games', round(time.time() - t0, 1), 's')
    ns = RK.load_ns()
    ns['DATA26'] = d
    got = ns['win8_load']()
    print('win8_load games', got['games'])
    full = W8.Win8()          # 舊行為：Win8() 預設讀全季資料
    ftabs, fgd = full.cur_tabs()
    mx = 0.0
    for p, v in direct.items():
        for a, x in v.items():
            mx = max(mx, abs(got['now'][p][a] - x))
    print('max|win8_load(ns[DATA26]=trunc) - Win8(trunc).attrs_at| =', mx)
    old = W8.Win8().attrs_at(fgd, ftabs)
    dd = max(abs(old[p][a] - direct[p][a]) for p in direct for a in direct[p])
    print('舊行為（全季資料、全季場數）vs 截斷：max|diff| =', round(dd, 3), '（參考：舊 win8_load 在逐日重算會讀到全季 now）')
    assert mx == 0.0
