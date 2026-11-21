"""worktree 缺檔時從主 repo 唯讀複製並記錄（fallback_copied.jsonl）。import 即啟用。
E211_ROOT＝worktree 根；找不到的檔先找主 repo 同路徑，再找 live/_retired/ 同名檔（凍結檔）。
非 _retired 的檔若 mtime 晚於 E211_CUTOFF（'YYYY-MM-DD HH:MM'，預設 E-141 跑完 2026-10-31 12:36）就不複製。"""
import builtins, io, os, shutil, time, json
MAINRAW = 'D:' + os.sep + 'Projects' + os.sep + 'CODING' + os.sep + 'basketball-autochess'
WTRAW = os.environ.get('E211_ROOT', 'D:' + os.sep + 'Projects' + os.sep + 'CODING' + os.sep + '_wt' + os.sep + 'e141-env')
WT = os.path.normcase(WTRAW)
_c = time.strptime(os.environ.get('E211_CUTOFF', '2026-10-31 12:36'), '%Y-%m-%d %H:%M')
CUT = time.mktime(_c)
LOG = 'D:' + os.sep + 'Projects' + os.sep + 'CODING' + os.sep + '_wt' + os.sep + 'fallback_copied.jsonl'
_open = io.open


def _try(path):
    try:
        ap = os.path.abspath(os.fspath(path))
    except Exception:
        return False
    if not os.path.normcase(ap).startswith(WT + os.sep):
        return False
    src = os.path.join(MAINRAW, os.path.relpath(ap, WTRAW))
    if not os.path.isfile(src) and os.sep + 'live' + os.sep in src:
        alt = os.path.join(os.path.dirname(src), '_retired', os.path.basename(src))
        if os.path.isfile(alt):
            src = alt
    if not os.path.isfile(src):
        return False
    m = os.path.getmtime(src)
    rec = {'path': ap, 'src': src, 'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m)), 'size': os.path.getsize(src),
           'newerThanCutoff': m > CUT}
    with _open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    if m > CUT and (os.sep + '_retired' + os.sep) not in src:
        return False
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    shutil.copy2(src, ap)
    return True


def fopen(file, *a, **k):
    try:
        return _open(file, *a, **k)
    except FileNotFoundError:
        mode = a[0] if a else k.get('mode', 'r')
        if isinstance(file, (str, bytes, os.PathLike)) and ('r' in mode) and _try(file):
            return _open(file, *a, **k)
        raise


io.open = fopen
builtins.open = fopen
import pathlib
pathlib.Path.open = lambda self, mode='r', buffering=-1, encoding=None, errors=None, newline=None: fopen(self, mode, buffering, encoding, errors, newline)
