"""名單頁 OVR 折線圖的資料：用現行模型（run_c4_live_rookie）把 2026-27 資料截到每個比賽日，逐日重算 OVR。

每天的 ranking.csv 版本不一（0.2.1b → 0.2.7b）、新秀起點又改過（R-096），直接串會有版本跳動，所以改成同一把尺重算。
截斷（2026-11-08 去洩漏）：單日重算時把 DATA26、本季 stints、season-source-2026-27 的讀取全部導到截斷資料夾（換掉 open／stat／scandir），
資料夾裡只有 d 那天以前的東西；重算時讀到真正的本季資料夾就直接報錯。內容：
  逐場：player-games／team-games（兩份）只留 GAME_DATE ≤ d，pbp、boxes、本季 stints 只留那些場；
  季累計可帶日期：防守追蹤 rim／three／hustle／advanced、持球 possessions、bio 用 NBA.com DateTo＝d 抓（scripts/fetch_asof.mjs，
    存 data/defense-seventh/2026-27-asof/<d>/，抓一次就留著）；
  對位 matchups：季表不吃日期，改用 data/matchup-source/2026-27 逐場對位檔加總（只放模型會用的欄）；
  Synergy 擋拆、引力：NBA.com 不吃日期，只能用「當天存下的快照」：每天 build 把當天的 synergy-pnr.json／gravity.json 存進 asof/<截止日>/，
    歷史日用 ≤ d 最近的一份；沒有快照的日子（2026-11-08 以前）預設 HIST_UNDATED=scale：拿最新整季那份，回合數 POSS／PTS、引力 FRAMES
    依每人「截至 d 的分鐘 ÷ 整季分鐘」縮小（量對了，效率／分數仍是整季的＝殘留洩漏，只在這兩項、只在舊日子）；
    HIST_UNDATED=none＝當作沒有本季檔（模型的「只用過去季」，新秀會掉回先驗，到有快照那天折線會跳）。
以前（到 2026-11-08）這些全部讀整季最新那份，歷史日的折線用到之後的比賽。
快取：live/ovr-history-cache.json 記 version、deps、code 與每日 {playerId: ovr}；同版號、同 code、該日截斷資料 sha 相同就不重算。
最後一天不重算，直接用當天正式 ranking.csv。

快取鍵（2026-11-08 改）：以前 code＝live/*.py 全部檔案的雜湊，別的 session 改任何一支沒用到的 .py 都會讓整季重算。
現在 --one 用 audit hook 記下單日重算實際讀了哪些 repo 檔（含 import 的模組），寫成 deps；code＝這些檔的內容雜湊
＋這些 .py 裡讀到的環境變數值。本季最新資料（DATA26、本季 stints、season-source-2026-27）照原設計不進鍵（每天都變）。
平行：HIST_WORKERS 個單日同時跑（預設 CPU 數的一半），每算完一天就寫一次快取（逾時也不會整批白算）。

用法：python -I ovr_history.py <今日輸出夾（有 ranking.csv、meta.json）>   → 寫 <今日輸出夾>/ovr-history.json，並更新快取
      python -I ovr_history.py --one <截斷資料夾> <輸出夾>               （內部：單日重算，另寫 <輸出夾>/deps.json）
環境變數：HIST_WORKERS（本機平行數，預設 CPU 數的一半）
      HIST_REMOTE=kojiek@100.97.181.15（選用：一部分日子 ssh 到 5090 跑；鏡像在 ~/side_projects/pure_ovr/experiments/ovr-history-remote/，
      只同步 deps＋本季資料中內容 sha 不同的檔）、HIST_REMOTE_WORKERS（預設 8）、HIST_REMOTE_PY（預設 python3）。遠端出錯就整批退回本機。
      python -I ovr_history.py --day <日期> <工作夾>   （內部：遠端單日，自己截斷＋重算，最後印結果 JSON）
"""
import csv
import hashlib
import json
import os
import re
import queue
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEASON = '2026-27'
DATA26 = ROOT / 'data/defense-seventh' / SEASON
STINTS = ROOT / f'reports/defense-seventh/{SEASON}/stints/stints.jsonl'
CACHE = HERE / 'ovr-history-cache.json'
PAST_PKL = ROOT / 'data/_inseason_build/def-obs-past.pkl'     # defense_bonus 的過去季快取：不存在時第一個單日會寫它，所以先單獨跑一天
SEASON_SRC = ROOT / f'data/season-source-{SEASON}'
LIVE_DATA = (DATA26, STINTS.parent, SEASON_SRC)   # 本季最新資料：單日重算時整個導到截斷資料夾（見檔頭）
ASOF = ROOT / 'data/defense-seventh' / f'{SEASON}-asof'          # <日期>/ 截至那天的季累計表
MATCHUP_SRC = ROOT / 'data/matchup-source' / SEASON              # 逐場對位 <gameId>.json
ASOF_FETCH = ('tracking/rim.json', 'tracking/three.json', 'tracking/hustle.json', 'tracking/advanced.json', 'possessions.json', 'bio.json')
SNAPSHOTS = ('synergy-pnr.json', 'gravity.json')                 # 不吃日期，只能用每天存下的快照
UNDATED = os.environ.get('HIST_UNDATED', 'scale')                # 沒快照的日子：scale＝整季檔依分鐘比例縮小；none＝當作沒有
STATIC = ('birthdates.json',)
MU_HEADERS = ['SEASON_ID', 'OFF_PLAYER_ID', 'DEF_PLAYER_ID', 'GP', 'PARTIAL_POSS', 'MATCHUP_FGA', 'MATCHUP_TOV']
ENV_RE = re.compile(r"""(?:environ\.get|getenv)\(\s*['"]([A-Za-z0-9_]+)['"]""")
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _under(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except ValueError:
        return False


def one(data_dir: Path, out_dir: Path):
    """單日重算：換掉 DATA26、本季 stints、def-L-live 輸出路徑後照常跑 run_c4_live_rookie；另寫 deps.json（實際讀到的 repo 檔）。"""
    reads, writes = set(), set()

    def hook(ev, args):
        if ev != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        mode, flags = args[1], args[2]
        w = any(c in mode for c in 'wax+') if isinstance(mode, str) else bool(isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR))
        (writes if w else reads).add(os.path.abspath(os.fsdecode(args[0])))
    sys.addaudithook(hook)
    _redirect(data_dir)
    sys.path.insert(0, str(HERE))
    import run_c4_live_rookie as RK
    RK.DB.CUR_STINTS = data_dir / '_stints' / 'stints.jsonl'
    RK.DEF_L_LIVE = out_dir / 'def-L-live.csv'   # 不蓋掉正式那份（名單頁 DIQ 讀它）
    ns = RK.load_ns()
    ns['DATA26'] = data_dir
    sys.argv = [sys.argv[0], str(out_dir)]
    rc = ns['main']()
    leak = sorted(f for f in reads if any(_under(Path(f), b) for b in LIVE_DATA))
    if leak:
        raise RuntimeError(f'歷史日讀到整季資料（沒導到截斷資料夾）：{leak[:5]}')
    files = reads - writes
    files |= {m.__file__ for m in list(sys.modules.values()) if isinstance(getattr(m, '__file__', None), str)}
    deps, live = set(), set()
    for f in files:
        p = Path(f).resolve()
        if p.parent.name == '__pycache__' and p.suffix == '.pyc':   # 讀 pyc 的模組（有些用完會從 sys.modules 移掉）→ 對應原始檔
            p = p.parent.parent / (p.name.split('.')[0] + '.py')
        if (not _under(p, ROOT) or _under(p, data_dir.resolve()) or _under(p, out_dir.resolve()) or p == CACHE
                or '__pycache__' in p.parts or not p.is_file()):
            continue
        (live if any(_under(p, b) for b in LIVE_DATA) else deps).add(p.relative_to(ROOT).as_posix())
    (out_dir / 'deps.json').write_text(json.dumps(sorted(deps), ensure_ascii=False), encoding='utf-8')
    (out_dir / 'live-deps.json').write_text(json.dumps(sorted(live), ensure_ascii=False), encoding='utf-8')   # 遠端同步用（不進快取鍵）
    return rc


def _redirect(data_dir: Path):
    """把 LIVE_DATA 底下的路徑換成截斷資料夾裡的同名路徑（open、stat、scandir、listdir；Windows 不分大小寫）。
    截斷資料夾沒有的檔＝不存在（Synergy／引力沒快照的日子就是這樣）。"""
    import builtins
    import glob
    import io
    data_dir = Path(data_dir).resolve()
    pairs = [(os.path.normcase(str(DATA26)), str(data_dir)), (os.path.normcase(str(STINTS.parent)), str(data_dir / '_stints')),
             (os.path.normcase(str(SEASON_SRC)), str(data_dir / '_ss'))]

    def remap(p):
        if isinstance(p, int):
            return p
        try:
            s = os.fspath(p)
        except TypeError:
            return p
        if isinstance(s, bytes):
            return p
        a = os.path.abspath(s)
        n = os.path.normcase(a)
        for real, mir in pairs:
            if n == real or n.startswith(real + os.sep):
                return mir + a[len(real):]
        return p

    def wrap(f):
        def g(path, *a, **k):
            return f(remap(path), *a, **k)
        return g
    builtins.open = io.open = wrap(io.open)
    for name in ('stat', 'lstat', 'scandir', 'listdir'):
        setattr(os, name, wrap(getattr(os, name)))
    sg = getattr(glob, '_StringGlobber', None)   # 3.13 Path.glob 在類別建立時就抓了 os.scandir／lexists
    if sg is not None:
        for name in ('scandir', 'lexists'):
            if name in sg.__dict__:
                setattr(sg, name, staticmethod(wrap(sg.__dict__[name].__func__)))


def day_main(day: str, work: Path):
    """遠端單日（HIST_REMOTE）：在鏡像裡自己截斷、重算，最後一行印 RESULT_MARK＋JSON（sha、ovr、deps、live）。"""
    sha = truncate(day, work / 'data')
    rc = one(work / 'data', work / 'out')
    if rc:
        return rc
    res = {'sha': sha, 'ovr': read_ovr(work / 'out' / 'ranking.csv')}
    for k, name in (('deps', 'deps.json'), ('live', 'live-deps.json')):
        res[k] = json.loads((work / 'out' / name).read_text(encoding='utf-8'))
    sys.stdout.write('\n' + RESULT_MARK + json.dumps(res, ensure_ascii=False) + '\n')
    sys.stdout.flush()
    return 0


# ==== 遠端（5090）分攤：HIST_REMOTE=user@host 時，一部分日子用 ssh 在遠端鏡像跑 ====
REMOTE = os.environ.get('HIST_REMOTE', '')
REMOTE_WORKERS = int(os.environ.get('HIST_REMOTE_WORKERS') or 8)
REMOTE_PY = os.environ.get('HIST_REMOTE_PY', 'python3')
REMOTE_DIR = 'side_projects/pure_ovr/experiments/ovr-history-remote'   # 相對遠端家目錄
RESULT_MARK = '@@OVR_HISTORY_RESULT@@'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30']
_SHA = {}


def _sha_rel(rel: str) -> str:
    if rel not in _SHA:
        try:
            _SHA[rel] = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        except OSError:
            _SHA[rel] = ''
    return _SHA[rel]


def _ssh(cmd: str, **kw):
    kw.setdefault('creationflags', CREATE_NO_WINDOW)
    return subprocess.run(SSH + [REMOTE, cmd], **kw)


def remote_sync(files) -> int:
    """把 files（repo 相對路徑）同步到遠端鏡像，只傳內容 sha 不同的檔；回傳傳了幾個。"""
    files = sorted(f for f in set(files) if _sha_rel(f))
    probe = ('import hashlib,sys\n'
             'for l in sys.stdin:\n'
             '    f=l.rstrip("\\r\\n")\n'
             '    try: print(hashlib.sha256(open(f,"rb").read()).hexdigest())\n'
             '    except OSError: print("")\n')
    r = _ssh(f'mkdir -p {REMOTE_DIR}/repo/data/_inseason_build/hist-remote && cd {REMOTE_DIR}/repo && {REMOTE_PY} -c {shlex.quote(probe)}',
             input=''.join(f + '\n' for f in files).encode('utf-8'), capture_output=True, timeout=900)   # bytes：文字模式在 Windows 會把 \n 換成 \r\n
    if r.returncode != 0:
        raise RuntimeError(f'遠端比對失敗：{r.stderr.decode("utf-8", "replace").strip()[-300:]}')
    got = r.stdout.decode('utf-8').splitlines()
    if len(got) != len(files):
        raise RuntimeError(f'遠端比對行數不符 {len(got)}/{len(files)}')
    send = [f for f, s in zip(files, got) if s != _sha_rel(f)]
    if send:
        p = subprocess.Popen(SSH + ['-C', REMOTE, f'cd {REMOTE_DIR}/repo && tar xf -'], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        with tarfile.open(fileobj=p.stdin, mode='w|', format=tarfile.PAX_FORMAT) as tf:
            for f in send:
                tf.add(str(ROOT / f), arcname=f, recursive=False)
        p.stdin.close()
        err = p.stderr.read().decode('utf-8', 'replace')
        if p.wait(timeout=1800) != 0:
            raise RuntimeError(f'遠端上傳失敗：{err.strip()[-300:]}')
    return len(send)


def remote_files(deps, live) -> list:
    """遠端鏡像要有的檔：快取鍵 deps＋本季最新資料（live）＋truncate 的輸入。"""
    rel = lambda p: p.relative_to(ROOT).as_posix()
    src = [rel(DATA26 / n) for n in ('player-games.json', 'team-games.json') + STATIC] + [rel(SEASON_SRC / 'player-games.json')]
    src += [rel(DATA26 / n) for n in SNAPSHOTS if (DATA26 / n).exists()]   # 沒快照的日子 truncate 用整季檔縮小（_scale_undated）；不同步則遠端 sha 對不上、整批退回本機（E-302 踩到）
    for sub in ('pbp', 'boxes'):
        src += [rel(p) for p in sorted((DATA26 / sub).glob('*.json'))]
    src += [rel(p) for p in sorted(MATCHUP_SRC.glob('00*.json'))]
    src += [rel(p) for p in sorted(ASOF.rglob('*.json'))]
    src.append(rel(STINTS))
    return sorted(set(deps) | set(live) | set(src) | {Path(__file__).resolve().relative_to(ROOT).as_posix()})


def remote_day(d: str, threads: int) -> dict:
    me = Path(__file__).resolve().relative_to(ROOT).as_posix()
    w = f'data/_inseason_build/hist-remote/{d}'   # 要在 repo 底下（輸出路徑會 relative_to(ROOT)）
    cmd = (f'cd {REMOTE_DIR}/repo && rm -rf {w} && OPENBLAS_NUM_THREADS={threads} OMP_NUM_THREADS={threads} MKL_NUM_THREADS={threads} '
           f'timeout 1800 {REMOTE_PY} -P -X utf8 {me} --day {d} {w} </dev/null; rc=$?; rm -rf {w}; exit $rc')
    r = _ssh(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, timeout=2000)
    line = next((x for x in reversed(r.stdout.splitlines()) if x.startswith(RESULT_MARK)), None)
    if r.returncode != 0 or line is None:
        raise RuntimeError(f'遠端 {d} 失敗 rc={r.returncode}：{(r.stderr or r.stdout).strip()[-400:]}')
    return json.loads(line[len(RESULT_MARK):])


_SRC = {}


def _src():
    """本季原始資料讀一次：兩張 game log、每場 pbp 的 sha、stints 每行（依 game id）。"""
    if not _SRC:
        for name in ('player-games.json', 'team-games.json'):
            _SRC[name] = (DATA26 / name).read_text(encoding='utf-8')
        _SRC['ss/player-games.json'] = (SEASON_SRC / 'player-games.json').read_text(encoding='utf-8')
        for sub in ('pbp', 'boxes'):
            _SRC[sub] = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((DATA26 / sub).glob('*.json'))}
        _SRC['mu'] = {}
        for p in sorted(MATCHUP_SRC.glob('00*.json')):
            _SRC['mu'][p.stem] = [(m['off'], m['def'], m['partialPossessions'] or 0, m['matchupFieldGoalsAttempted'] or 0, m['matchupTurnovers'] or 0)
                                  for m in json.loads(p.read_text(encoding='utf-8')).get('matchups') or ()]
        _SRC['stints'] = [(json.loads(line)['id'], line) for line in STINTS.open(encoding='utf-8')]
    return _SRC


class NoAsof(Exception):
    """這天截至當天的季累計表還沒抓到（fetch_asof 失敗）。"""


def _file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot_for(day: str, name: str):
    """≤ day 最近一天存下的 Synergy／引力快照；沒有＝None。"""
    best = None
    for d in (sorted(x.name for x in ASOF.iterdir() if x.is_dir()) if ASOF.exists() else ()):
        if d <= day and (ASOF / d / name).exists():
            best = ASOF / d / name
    return best


def _link(p: Path, q: Path):
    q.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(p, q)
    except OSError:
        shutil.copy2(p, q)


def truncate(day: str, dst: Path | None = None) -> str:
    """把本季資料截到 GAME_DATE ≤ day（見檔頭），回傳截斷後內容的 sha256（快取鍵）；給 dst 才寫檔（大檔用硬連結，不能連結才複製）。"""
    src = _src()
    h = hashlib.sha256()
    games, docs = set(), {}
    for name in ('player-games.json', 'team-games.json', 'ss/player-games.json'):
        doc = json.loads(src[name])
        rs = doc['data']['resultSets'][0]
        i, j = rs['headers'].index('GAME_DATE'), rs['headers'].index('GAME_ID')
        rs['rowSet'] = [r for r in rs['rowSet'] if r[i] <= day]
        games |= {r[j] for r in rs['rowSet']}
        h.update(json.dumps(rs['rowSet']).encode('utf-8'))   # 只雜湊列（fetchedAt 每次抓都變）
        docs[name] = doc
    per_game = {}
    for sub in ('pbp', 'boxes'):
        per_game[sub] = [g for g in sorted(games) if g in src[sub]]
        for g in per_game[sub]:
            h.update(f'{sub}/{g}:{src[sub][g]}\n'.encode('utf-8'))
    lines = [line for gid, line in src['stints'] if gid in games]
    for line in lines:
        h.update(line.encode('utf-8'))
    pair = {}                                   # 對位：逐場加總 → 季表格式
    for g in sorted(games):
        for o, d_, pp, fga, tov in src['mu'].get(g, ()):
            q = pair.setdefault((o, d_), [0, 0.0, 0.0, 0.0])
            q[0] += 1
            q[1] += pp
            q[2] += fga
            q[3] += tov
    sid = '2' + SEASON[:4]
    mu_rows = [[sid, o, d_, n, round(pp, 6), fga, tov] for (o, d_), (n, pp, fga, tov) in sorted(pair.items())]
    h.update(json.dumps(mu_rows).encode('utf-8'))
    asof = []
    for name in ASOF_FETCH:
        p = ASOF / day / name
        if not p.exists():
            raise NoAsof(f'{day} 缺 {p.relative_to(ROOT).as_posix()}')
        asof.append((name, p))
    scaled = {}
    for name in SNAPSHOTS:
        p = snapshot_for(day, name)
        if p is not None:
            asof.append((name, p))
        elif UNDATED == 'scale' and (DATA26 / name).exists():
            scaled[name] = _scale_undated(name, docs['player-games.json'])
            h.update(f'{name}:scaled:{hashlib.sha256(scaled[name].encode("utf-8")).hexdigest()}\n'.encode('utf-8'))
    asof += [(name, DATA26 / name) for name in STATIC]
    for name, p in asof:
        h.update(f'{name}:{_file_sha(p)}\n'.encode('utf-8'))
    if dst is not None:
        dst.mkdir(parents=True, exist_ok=True)
        for name, doc in docs.items():
            q = dst / name.replace('ss/', '_ss/')
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
        for sub, gs in per_game.items():
            (dst / sub).mkdir(parents=True, exist_ok=True)
            for g in gs:
                _link(DATA26 / sub / f'{g}.json', dst / sub / f'{g}.json')
        (dst / '_stints').mkdir(parents=True, exist_ok=True)
        (dst / '_stints' / 'stints.jsonl').write_text(''.join(lines), encoding='utf-8')
        for name, p in asof:
            _link(p, dst / name)
        for name, txt in scaled.items():
            (dst / name).write_text(txt, encoding='utf-8')
        (dst / 'tracking').mkdir(parents=True, exist_ok=True)
        (dst / 'tracking' / 'matchups.json').write_text(json.dumps(
            {'url': None, 'season': SEASON, 'note': f'ovr_history：data/matchup-source 逐場加總到 {day}',
             'data': {'resultSets': [{'name': 'SeasonMatchups', 'headers': MU_HEADERS, 'rowSet': mu_rows}]}}), encoding='utf-8')
    return h.hexdigest()


def _minutes(doc) -> dict:
    rs = doc['data']['resultSets'][0]
    i, j = rs['headers'].index('PLAYER_ID'), rs['headers'].index('MIN')
    out = {}
    for r in rs['rowSet']:
        v = r[j]
        if isinstance(v, str) and ':' in v:
            a, b = v.split(':')
            v = int(a) + int(b) / 60.0
        out[int(r[i])] = out.get(int(r[i]), 0.0) + float(v or 0)
    return out


def _scale_undated(name: str, pg_doc) -> str:
    """沒快照的日子（HIST_UNDATED=scale）：最新整季 Synergy／引力，量類欄依每人截至 d 的分鐘比例縮小；那天前沒上場的人拿掉。"""
    full = _src().setdefault('min_full', _minutes(json.loads(_src()['player-games.json'])))
    part = _minutes(pg_doc)
    share = {p: min(1.0, part.get(p, 0.0) / m) for p, m in full.items() if m > 0}
    d = json.loads((DATA26 / name).read_text(encoding='utf-8'))
    if name == 'gravity.json':
        rows = []
        for r in d.get('leaders', []):
            f = share.get(int(r['PLAYERID']), 0.0)
            if f > 0:
                rows.append(dict(r, FRAMES=float(r['FRAMES']) * f))
        d['leaders'] = rows
    else:
        rs = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
        H = rs['headers']
        ip, iP, it = H.index('PLAYER_ID'), H.index('POSS'), H.index('PTS')
        rows = []
        for r in rs['rowSet']:
            f = share.get(int(r[ip]), 0.0)
            if f > 0:
                r = list(r)
                r[iP] = float(r[iP]) * f
                r[it] = float(r[it]) * f
                rows.append(r)
        rs['rowSet'] = rows
    d['ovrHistoryNote'] = 'HIST_UNDATED=scale：整季檔依截至當天分鐘比例縮小'
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def ensure_asof(days) -> list:
    """缺截至當天季累計表的日子用 scripts/fetch_asof.mjs 補抓（3 個同時）；回傳抓不到的日子。"""
    need = [d for d in days if not all((ASOF / d / n).exists() for n in ASOF_FETCH)]
    if not need:
        return []
    node = os.environ.get('NODE_EXE') or shutil.which('node') or r'C:\Program Files\nodejs\node.exe'
    bad, lock = [], threading.Lock()
    q = queue.Queue()
    for d in need:
        q.put(d)

    def w():
        while True:
            try:
                d = q.get_nowait()
            except queue.Empty:
                return
            try:
                r = subprocess.run([node, str(ROOT / 'scripts/fetch_asof.mjs'), SEASON, d, str(ASOF / d)], cwd=str(ROOT), capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL,
                                   timeout=600)
                ok, msg = r.returncode == 0, (r.stdout or r.stderr).strip()[-300:]
            except (OSError, subprocess.TimeoutExpired) as e:
                ok, msg = False, str(e)
            if not ok:
                with lock:
                    bad.append(d)
                print(f'{d} 截至當天的季累計表抓不到：{msg}', file=sys.stderr, flush=True)
    t = time.time()
    ths = [threading.Thread(target=w) for _ in range(3)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    print(f'補抓截至當天季累計表 {len(need) - len(bad)}/{len(need)} 天（{time.time() - t:.0f}s）', file=sys.stderr, flush=True)
    return bad


def archive_snapshots(cutoff: str):
    """今天的 Synergy 擋拆／引力季累計（不吃日期）存一份到 asof/<截止日>/，之後的歷史日才有當天的版本。"""
    for name in SNAPSHOTS:
        p, q = DATA26 / name, ASOF / cutoff / name
        if p.exists() and not q.exists():
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)


def read_ovr(path: Path) -> dict:
    return {r['playerId']: float(r['ovr']) for r in csv.DictReader(path.open(encoding='utf-8'))}


_FILE_SHA = {}    # rel → (sha, 讀到的環境變數名)


def code_key(deps) -> str:
    """deps 檔案內容＋這些 .py 讀到的環境變數值 → 快取鍵。檔案不見了也算不同。"""
    h = hashlib.sha256()
    names = set()
    for rel in sorted(deps):
        if rel not in _FILE_SHA:
            try:
                b = (ROOT / rel).read_bytes()
                _FILE_SHA[rel] = (hashlib.sha256(b).hexdigest(),
                                  set(ENV_RE.findall(b.decode('utf-8', 'replace'))) if rel.endswith('.py') else set())
            except OSError:
                _FILE_SHA[rel] = ('missing', set())
        sha, env = _FILE_SHA[rel]
        names |= env
        h.update(f'{rel}\0{sha}\n'.encode('utf-8'))
    h.update(json.dumps({k: os.environ.get(k) for k in sorted(names)}, sort_keys=True).encode('utf-8'))
    return h.hexdigest()


def build(today_dir: Path):
    t0 = time.time()
    meta = json.loads((today_dir / 'meta.json').read_text(encoding='utf-8'))
    version, cutoff = meta['version'], meta['dataCutoff']
    rows = list(csv.DictReader((today_dir / 'ranking.csv').open(encoding='utf-8')))
    doc = json.loads((DATA26 / 'player-games.json').read_text(encoding='utf-8'))['data']['resultSets'][0]
    days = sorted({r[doc['headers'].index('GAME_DATE')] for r in doc['rowSet']})
    try:
        cache = json.loads(CACHE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    deps = set(cache.get('deps') or ())
    known = set(cache.get('deps') or ()), set(cache.get('live') or ())   # 遠端同步用：失效也沿用上次記到的檔案清單
    if cache.get('version') != version or not deps or cache.get('code') != code_key(deps):
        why = 'version' if cache.get('version') != version else 'deps' if not deps else 'code'
        print(f'快取失效（{why}）：全部重算', file=sys.stderr)
        cache, deps = {'version': version, 'deps': [], 'live': [], 'code': '', 'days': {}}, set()
    live = set(cache.get('live') or ())
    py = Path(sys.executable)
    py = py.with_name('python.exe') if py.name.lower() == 'pythonw.exe' else py
    todo_days = days[:-1] if days[-1] == cutoff else days
    if cutoff == days[-1]:   # 本季資料夾的快照＝截止日當天的；拿舊的今日輸出夾重跑時不能存（會存到錯的日期）
        archive_snapshots(cutoff)
    skipped = set(ensure_asof(todo_days))
    todo_days = [d for d in todo_days if d not in skipped]   # 抓不到的日子這次不畫（下次再補）
    workers = max(1, int(os.environ.get('HIST_WORKERS') or max(1, (os.cpu_count() or 2) // 2)))
    env = dict(os.environ)
    if workers > 1:   # 每個單日的 BLAS 執行緒數，避免 workers×核心數 互搶
        n = str(max(1, (os.cpu_count() or 2) // workers))
        env.update(OPENBLAS_NUM_THREADS=n, OMP_NUM_THREADS=n, MKL_NUM_THREADS=n)
    series, lock, errors = {}, threading.Lock(), []
    where = {'local': 0, 'remote': 0}

    def save():
        cache['deps'] = sorted(deps)
        cache['live'] = sorted(live)
        cache['code'] = code_key(deps)
        tmp = CACHE.with_name(CACHE.name + '.tmp')
        tmp.write_text(json.dumps(cache, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        os.replace(tmp, CACHE)

    def done(d, sha, ovr, dd, ll, tag, t):
        with lock:
            deps.update(dd)
            live.update(ll)
            cache['days'][d] = {'sha': sha, 'ovr': ovr}
            series[d] = ovr
            where[tag] += 1
            save()
        print(f'{d}：重算 {len(ovr)} 人（{tag} {time.time() - t:.0f}s）', file=sys.stderr, flush=True)

    with tempfile.TemporaryDirectory(dir=ROOT / 'data/_inseason_build') as tmp:
        def job(d, sha):
            work = Path(tmp) / d
            try:
                truncate(d, work / 'data')
                t = time.time()
                r = subprocess.run([str(py), '-I', '-X', 'utf8', str(Path(__file__).resolve()), '--one', str(work / 'data'), str(work / 'out')],
                                   cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', env=env,
                                   creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, timeout=1800)
                if r.returncode != 0:
                    raise RuntimeError(f'{d} 重算失敗：{(r.stderr or r.stdout).strip()[-600:]}')
                rd = lambda name: json.loads((work / 'out' / name).read_text(encoding='utf-8'))
                done(d, sha, read_ovr(work / 'out' / 'ranking.csv'), rd('deps.json'), rd('live-deps.json'), 'local', t)
            finally:
                shutil.rmtree(work, ignore_errors=True)

        miss = {}
        for d in todo_days:          # 命中快取的日子不寫截斷檔、不重算
            sha = truncate(d)
            hit = cache['days'].get(d)
            if hit and hit['sha'] == sha:
                series[d] = hit['ovr']
            else:
                miss[d] = sha
        use_remote = bool(REMOTE) and len(miss) > 1
        print(f'{len(todo_days)} 天：命中 {len(series)}、重算 {len(miss)}（本機 {workers} 平行'
              f'{f"＋{REMOTE} {REMOTE_WORKERS} 平行" if use_remote else ""}）', file=sys.stderr, flush=True)
        # 先單獨跑一天：防守過去季快取還沒有，或要遠端但還不知道要同步哪些檔
        first = list(miss)[:1] if miss and (not PAST_PKL.exists() or (use_remote and not (known[0] or deps))) else []
        for d in first:
            try:
                job(d, miss[d])
            except Exception as e:
                errors.append(e)
        q = queue.Queue()
        for d in miss:
            if d not in first:
                q.put(d)
        remote_ok = threading.Event()
        if use_remote and not q.empty():
            try:
                t = time.time()
                k = remote_sync(remote_files(deps or known[0], live or known[1]))
                print(f'遠端同步：上傳 {k} 個檔（{time.time() - t:.0f}s）', file=sys.stderr, flush=True)
                remote_ok.set()
            except Exception as e:
                print(f'遠端不可用，全部本機跑：{e}', file=sys.stderr, flush=True)

        def local_worker():
            while True:
                try:
                    d = q.get_nowait()
                except queue.Empty:
                    return
                try:
                    job(d, miss[d])
                except Exception as e:   # 其他日子照跑完、照寫快取，最後再報錯
                    errors.append(e)

        def remote_worker():
            while remote_ok.is_set():
                try:
                    d = q.get_nowait()
                except queue.Empty:
                    return
                t = time.time()
                try:
                    res = remote_day(d, threads=2)
                    if res['sha'] != miss[d]:
                        raise RuntimeError(f'遠端 {d} 截斷資料 sha 對不上（鏡像沒同步好）')
                    done(d, miss[d], res['ovr'], res['deps'], res['live'], 'remote', t)
                except Exception as e:   # 遠端出事：這天放回佇列給本機，遠端全部停
                    remote_ok.clear()
                    q.put(d)
                    print(f'遠端停用：{e}', file=sys.stderr, flush=True)

        ths = [threading.Thread(target=local_worker) for _ in range(workers)]
        ths += [threading.Thread(target=remote_worker) for _ in range(REMOTE_WORKERS if remote_ok.is_set() else 0)]
        for th in ths:
            th.start()
        for th in ths:
            th.join()
        local_worker()               # 遠端最後才失敗、放回來的日子
    if errors:
        raise errors[0]
    series[cutoff] = read_ovr(today_dir / 'ranking.csv')
    # 輸出：逐場＝這個人自己有上場的日期，取那天截斷後的 OVR；start＝開季先驗（lastOVR，新秀＝R-096 起點）
    i, j = doc['headers'].index('PLAYER_ID'), doc['headers'].index('GAME_DATE')
    played = {}
    for g in doc['rowSet']:
        played.setdefault(str(g[i]), set()).add(g[j])
    out = {'version': version, 'cutoff': cutoff, 'players': {}}
    for r in rows:
        pid = r['playerId']
        pts = [[d, series[d][pid]] for d in sorted(played.get(pid, ())) if d in series and pid in series[d]]
        out['players'][pid] = {'name': r['name'], 'start': float(r['lastOVR']), 'pts': pts}
    (today_dir / 'ovr-history.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'wrote {today_dir / "ovr-history.json"}：{len(series)} 天、{len(out["players"])} 人，本機 {where["local"]}／遠端 {where["remote"]} 天，{time.time() - t0:.0f}s', file=sys.stderr)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == '--one':
        raise SystemExit(one(Path(sys.argv[2]), Path(sys.argv[3])))
    if sys.argv[1] == '--day':
        raise SystemExit(day_main(sys.argv[2], Path(sys.argv[3]).resolve()))
    build(Path(sys.argv[1]).resolve())
