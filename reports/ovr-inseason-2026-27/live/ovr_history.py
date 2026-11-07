"""名單頁 OVR 折線圖的資料：用現行模型（run_c4_live_rookie）把 2026-27 資料截到每個比賽日，逐日重算 OVR。

每天的 ranking.csv 版本不一（0.2.1b → 0.2.7b）、新秀起點又改過（R-096），直接串會有版本跳動，所以改成同一把尺重算。
截斷：player-games／team-games 只留 GAME_DATE ≤ d，pbp 只留那些場，本季 stints 只留那些場；防守追蹤表是季累計抓不到逐日，
沿用最新那份（新秀／老將 onBall、help 的過去點會用到之後的資料，只影響防守兩項）；0.2.10j 的引力（gravity.json，季累計）同樣沿用最新那份。
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
LIVE_DATA = (DATA26, STINTS.parent, ROOT / 'data/season-source-2026-27')   # 本季最新資料：不進快取鍵（見檔頭）
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
    sys.path.insert(0, str(HERE))
    import run_c4_live_rookie as RK
    RK.DB.CUR_STINTS = data_dir / 'stints.jsonl'
    RK.DEF_L_LIVE = out_dir / 'def-L-live.csv'   # 不蓋掉正式那份（名單頁 DIQ 讀它）
    ns = RK.load_ns()
    ns['DATA26'] = data_dir
    sys.argv = [sys.argv[0], str(out_dir)]
    rc = ns['main']()
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
    src = [f'{(DATA26 / n).relative_to(ROOT).as_posix()}' for n in ('player-games.json', 'team-games.json', 'bio.json')]
    src += [p.relative_to(ROOT).as_posix() for p in sorted((DATA26 / 'pbp').glob('*.json'))]
    src.append(STINTS.relative_to(ROOT).as_posix())
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
        _SRC['pbp'] = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((DATA26 / 'pbp').glob('*.json'))}
        _SRC['stints'] = [(json.loads(line)['id'], line) for line in STINTS.open(encoding='utf-8')]
    return _SRC


def truncate(day: str, dst: Path | None = None) -> str:
    """把 DATA26 截到 GAME_DATE ≤ day，回傳截斷後內容的 sha256（快取鍵）；給 dst 才寫檔（pbp 用硬連結，不能連結才複製）。"""
    src = _src()
    h = hashlib.sha256()
    games, docs = set(), {}
    for name in ('player-games.json', 'team-games.json'):
        doc = json.loads(src[name])
        rs = doc['data']['resultSets'][0]
        i, j = rs['headers'].index('GAME_DATE'), rs['headers'].index('GAME_ID')
        rs['rowSet'] = [r for r in rs['rowSet'] if r[i] <= day]
        games |= {r[j] for r in rs['rowSet']}
        h.update(json.dumps(rs['rowSet']).encode('utf-8'))   # 只雜湊列（fetchedAt 每次抓都變）
        docs[name] = doc
    pbp = [g for g in sorted(games) if g in src['pbp']]
    for g in pbp:
        h.update(f'{g}:{src["pbp"][g]}\n'.encode('utf-8'))
    lines = [line for gid, line in src['stints'] if gid in games]
    for line in lines:
        h.update(line.encode('utf-8'))
    if dst is not None:
        (dst / 'pbp').mkdir(parents=True, exist_ok=True)
        for name, doc in docs.items():
            (dst / name).write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
        shutil.copy2(DATA26 / 'bio.json', dst / 'bio.json')
        for g in pbp:
            p, q = DATA26 / 'pbp' / f'{g}.json', dst / 'pbp' / f'{g}.json'
            try:
                os.link(p, q)
            except OSError:
                shutil.copy2(p, q)
        (dst / 'stints.jsonl').write_text(''.join(lines), encoding='utf-8')
    return h.hexdigest()


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
