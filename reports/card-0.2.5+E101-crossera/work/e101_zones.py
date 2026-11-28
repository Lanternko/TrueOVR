"""E-101 共用：讓 V61 引擎（reports/ovr-v61-shrink-history-2025-26/engine.py）改讀本實驗修正後的投籃區檔，不動 V61 原檔。

做法：engine.season_halves 經 engine 模組全域的 read_gz_csv 讀 HIST / 'pbp-zones-<季>.csv.gz'；這裡把 engine.read_gz_csv
包一層，檔名是 pbp-zones-*.csv.gz 時改讀 E-101 history/ 的同名檔，其餘（pergame、drive、positions）照讀 V61。
build_attrs 以 `from engine import *` 取得的 season_halves 也是同一個函式物件（全域字典是 engine 的），所以一起生效。
use(True) 開、use(False) 關（還原），供同一程序裡做 V61 對照。
"""
from pathlib import Path

E101_HIST = Path(__file__).resolve().parent.parent / 'history'
_state = {'orig': None, 'on': False, 'reads': []}


def use(on, E):
    if _state['orig'] is None:
        _state['orig'] = E.read_gz_csv
    orig = _state['orig']
    if on:
        def patched(path):
            p = Path(path)
            if p.name.startswith('pbp-zones-'):
                q = E101_HIST / p.name
                assert q.exists(), q
                _state['reads'].append(p.name)
                return orig(q)
            return orig(path)
        E.read_gz_csv = patched
    else:
        E.read_gz_csv = orig
    _state['on'] = on


def reads():
    return list(_state['reads'])
