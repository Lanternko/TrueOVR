"""賽中名單每日自動更新並發布到 GitHub Pages（gh-pages 分支的 index.html＝2026-27 賽中頁、2025-26.html＝2025-26 正式卡頁）。

流程：抓比賽 → 抓 PBP/bio → run_c4_live → 依資料 sha256 決定是否發布 → build viewer
      → 在可丟棄的 git worktree 中把 roster-viewer.html 提交成 gh-pages 的 index.html 並 push。

規則（memory/rulings.md R-063、R-024）：
- 只有比賽資料變、模型沒動：版號不變，只換 meta.json 的 `dataCutoff`（頁面標題列顯示「數據截至」）。
- 版號照 meta.json 的 `version`（由 run_c4_live.py 產生）原樣顯示；字母後綴是小版本（R-064），由那邊寫進版號。

用法（工作目錄不限，會自動切到 repo 根）：
  pythonw scripts/daily_inseason_update.py [--dry-run] [--force]
  python -I scripts/daily_inseason_update.py --shell   # deploy-shell：只改頁面（UI／顯示），資料與版號不動
子程序一律 CREATE_NO_WINDOW；排程用 pythonw 啟動。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import logging.handlers
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
STATE_PATH = LIVE / 'publish_state.json'
LOG_PATH = LIVE / 'logs/daily.log'
LOCK_PATH = LIVE / '.daily_update.lock'
SEASON = '2026-27'
PLAYER_GAMES = ROOT / f'data/season-source-{SEASON}/player-games.json'
PBP_DIR = ROOT / f'data/defense-seventh/{SEASON}/pbp'
BUILD_ROOT = ROOT / 'data/_inseason_build'
RUN_C4 = LIVE / 'run_c4_live.py'
RUN_LIVE = LIVE / 'run_c4_live_rookie.py'   # E-116：包 run_c4_live，補上沒有先驗卡的當季新秀（版號仍讀 RUN_C4）
VIEWER = ROOT / 'scripts/build_inseason_viewer.py'
HISTORY = LIVE / 'ovr_history.py'               # 名單頁 OVR 折線：逐日截斷重算
CARD_VIEWER = ROOT / 'scripts/build_card_viewer.py'
E151_EVAL = ROOT / 'reports/card-0.2.7d+E151-young-curve/e151_eval.py'   # 預註冊驗收，達標跑一次
E151_RESULT = E151_EVAL.parent / 'results.json'
E222_EVAL = ROOT / 'reports/E222-recent-boost-diagnostic/e222_eval.py'   # 預註冊診斷：30 隊打滿 20 場後跑一次
E222_RESULT = E222_EVAL.parent / 'result.json'
TEAM_RATINGS = ROOT / 'scripts/team_ratings_daily.py'      # E-208 第二階段：傷病名單＋球隊評分
TEAMS_PAGE = ROOT / 'scripts/build_teams_page.py'
GAMES_DATA = ROOT / 'scripts/build_games_data.py'
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

TIMEOUTS = {'games': 900, 'matchups': 1800, 'inseason': 3600, 'tracking': 600, 'gravity': 300, 'possessions': 300, 'stints': 1800, 'c4': 3600, 'viewer': 600, 'history': 3600, 'prereg': 900, 'ratings': 1800, 'e229': 900, 'ratings_m0': 1800, 'git': 180}
CO_AUTHOR = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'

log = logging.getLogger('daily_inseason')


# ----------------------------------------------------------------- 版號
def decide(state: dict, base: str, data_sha: str, pbp_count: int, force: bool) -> dict:
    """回傳 {publish, reason}。版號一律用 base，只更新資料不改版號（R-063）。"""
    prev_base = state.get('base')
    if prev_base != base:
        return {'publish': True, 'reason': f'版號 {prev_base!r} -> {base!r}'}
    changed = state.get('dataSha256') != data_sha or state.get('pbpCount') != pbp_count
    if changed:
        return {'publish': True, 'reason': '資料有變（player-games sha256 或 PBP 檔數）'}
    if force:
        return {'publish': True, 'reason': '--force，資料沒變'}
    return {'publish': False, 'reason': '資料沒有變化，不發布'}


# ----------------------------------------------------------------- 工具
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def py_exe() -> str:
    exe = Path(sys.executable)
    if exe.name.lower() == 'pythonw.exe':
        cand = exe.with_name('python.exe')
        if cand.exists():
            return str(cand)
    return str(exe)


def run(cmd, cwd: Path, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    log.info('$ %s  (cwd=%s, timeout=%ss)', ' '.join(map(str, cmd)), cwd, timeout)
    e = dict(os.environ)
    e.update({'GIT_TERMINAL_PROMPT': '0', 'PYTHONIOENCODING': 'utf-8'})
    if env:
        e.update(env)
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout, env=e,
                          creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)


def log_tail(text: str, n: int = 12) -> None:
    for line in (text or '').strip().splitlines()[-n:]:
        log.info('  | %s', line)


def checked(cmd, cwd: Path, timeout: int, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        r = run(cmd, cwd, timeout, env)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'逾時 {timeout}s：{" ".join(map(str, cmd))}')
    if r.returncode != 0:
        log_tail(r.stdout)
        log_tail(r.stderr)
        raise RuntimeError(f'exit={r.returncode}：{" ".join(map(str, cmd))}\n{(r.stderr or r.stdout).strip()[-800:]}')
    return r


def node_exe() -> str:
    for c in (shutil.which('node'), r'C:\Program Files\nodejs\node.exe'):
        if c and Path(c).exists():
            return c
    raise RuntimeError('找不到 node')


# ----------------------------------------------------------------- 鎖
class Lock:
    def __init__(self, path: Path, stale_s: int = 4 * 3600):
        self.path, self.stale_s = path, stale_s

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f'{os.getpid()} {time.time()}'.encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age > self.stale_s:
                    log.warning('鎖檔已過期（%.0f 分鐘），接手', age / 60)
                    self.path.unlink(missing_ok=True)
                    continue
                raise LockBusy(f'另一個更新正在跑（鎖檔 {self.path}，{age / 60:.0f} 分鐘前）')
        raise LockBusy('取鎖失敗')

    def __exit__(self, *a):
        self.path.unlink(missing_ok=True)


class LockBusy(RuntimeError):
    pass


# ----------------------------------------------------------------- 四步
def step_fetch_games() -> None:
    checked([node_exe(), 'scripts/fetch_season_games.js', SEASON], ROOT, TIMEOUTS['games'])


def step_fetch_matchups() -> None:
    """評分 M2（R-066）要的防守對位＋hustle；失敗不擋發布，抓不到的場次評分退回 M0（tooltip 註明）。"""
    try:
        r = run([node_exe(), 'scripts/fetch_matchups.mjs', SEASON], ROOT, TIMEOUTS['matchups'])
    except subprocess.TimeoutExpired:
        log.warning('fetch_matchups 逾時；沒抓到的場次評分退回 M0')
        return
    tail = (r.stdout or '').strip().splitlines()[-1:] or ['']
    if r.returncode != 0:
        log.warning('fetch_matchups exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])
    else:
        log.info('fetch_matchups：%s', tail[0])


def step_fetch_gravity() -> None:
    """inseason 0.2.10j（R-134）：本季無球外線引力（NBA.com gravityleaders，季累計）→ data/defense-seventh/2026-27/gravity.json。
    失敗不擋發布：fetch_gravity.mjs 失敗不覆寫，沿用上次抓到的檔（檔不存在時 gravity_live 只用 2025-26＋OLS 補值）。"""
    try:
        r = run([node_exe(), 'scripts/fetch_gravity.mjs', SEASON], ROOT, TIMEOUTS['gravity'])
    except subprocess.TimeoutExpired:
        log.warning('fetch_gravity 逾時；引力沿用上次的檔')
        return
    if r.returncode != 0:
        log.warning('fetch_gravity exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])
    else:
        log.info('fetch_gravity：%s', ((r.stdout or '').strip().splitlines()[-1:] or [''])[0])


def step_fetch_possessions() -> None:
    """inseason 0.2.12（R-139）：本季持球時間（NBA.com tracking Possessions，季累計）→ data/defense-seventh/2026-27/possessions.json。
    失敗不擋發布：fetch_possessions.mjs 失敗不覆寫，沿用上次抓到的檔（檔不存在時 tov_live 對本季沒資料的人照預註冊 §1 第 6 點處理）。"""
    try:
        r = run([node_exe(), 'scripts/fetch_possessions.mjs', SEASON], ROOT, TIMEOUTS['possessions'])
    except subprocess.TimeoutExpired:
        log.warning('fetch_possessions 逾時；持球時間沿用上次的檔')
        return
    if r.returncode != 0:
        log.warning('fetch_possessions exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])
    else:
        log.info('fetch_possessions：%s', ((r.stdout or '').strip().splitlines()[-1:] or [''])[0])


def step_fetch_tracking() -> None:
    """新秀賽中防守（2026-10-30）：整季累計的防守追蹤表；失敗不擋發布，沿用上次抓到的檔（新秀防守停在那天）。"""
    try:
        r = run([node_exe(), 'scripts/fetch_defense_tracking.mjs', SEASON], ROOT, TIMEOUTS['tracking'])
    except subprocess.TimeoutExpired:
        log.warning('fetch_defense_tracking 逾時；新秀防守沿用上次的表')
        return
    if r.returncode != 0:
        log.warning('fetch_defense_tracking exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])
    else:
        log.info('fetch_defense_tracking：%s', ((r.stdout or '').strip().splitlines()[-1:] or [''])[0])


def step_build_stints() -> None:
    """賽中 defenseBonus（2026-10-30）：本季已賽場次做成 stints（box 補抓、pbp 用快取），live 每天重擬合 E-104 D。
    失敗不擋發布，沿用上次的 stints（防守加成停在那天）。要在 fetch_inseason 之後（讀它寫的 team-games／pbp）。"""
    try:
        r = run([node_exe(), 'scripts/build_inseason_stints.js', SEASON], ROOT, TIMEOUTS['stints'])
    except subprocess.TimeoutExpired:
        log.warning('build_inseason_stints 逾時；防守加成沿用上次的 stints')
        return
    if r.returncode != 0:
        log.warning('build_inseason_stints exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])
    else:
        log.info('build_inseason_stints：%s', ((r.stdout or '').strip().splitlines()[-1:] or [''])[0])


def step_prereg_e151() -> None:
    """E-151 預註冊（2026-11-01）：stints 達 450 場後跑一次凍結的 e151_eval.py；寫出 results.json 後不再跑。
    未達門檻時程式自己退出、不算相關。失敗不擋發布。"""
    if E151_RESULT.exists():
        return
    try:
        r = run([py_exe(), '-I', '-X', 'utf8', str(E151_EVAL)], ROOT, TIMEOUTS['prereg'])
    except subprocess.TimeoutExpired:
        log.warning('E-151 評估逾時')
        return
    last = ((r.stdout or '').strip().splitlines()[-1:] or [(r.stderr or '').strip()[-300:]])[0]
    if E151_RESULT.exists():
        log.warning('E-151 評估完成（只跑這一次）：%s', last[:500])
    else:
        log.info('E-151 未評估 exit=%s：%s', r.returncode, last[:300])


def step_prereg_e222() -> None:
    """E-222 預註冊（2026-11-03）：30 隊都打滿 20 場後跑一次凍結的 e222_eval.py；寫出 result.json 後不再跑。
    未達門檻時程式自己 exit 1（印 JSON status）、不算相關。任何失敗都不擋發布。"""
    if E222_RESULT.exists():
        return
    try:
        r = run([py_exe(), '-I', '-X', 'utf8', str(E222_EVAL)], ROOT, TIMEOUTS['prereg'])
    except subprocess.TimeoutExpired:
        log.warning('E-222 評估逾時')
        return
    except Exception as e:  # noqa: BLE001  評估壞掉不得讓每日更新失敗
        log.warning('E-222 評估略過：%s', str(e)[-300:])
        return
    last = ((r.stdout or '').strip().splitlines()[-1:] or [(r.stderr or '').strip()[-300:]])[0]
    if E222_RESULT.exists():
        log.warning('E-222 評估完成（只跑這一次）：%s', last[:500])
    else:
        log.info('E-222 未評估 exit=%s：%s', r.returncode, last[:300])


def step_e229_forward(live_dir: Path | None) -> None:
    """E-229：T 對 M0 的前向預測記錄（reports/E229-transformer-vs-m0-forward/predict_daily.py）。R-160 起 team-ratings.json 是 T，
    這裡另跑一次舊引擎 M0（不重抓傷病／賽程）寫 team-ratings-m0.json 給記錄器比對。任何失敗只記警告，不擋發布。"""
    try:
        checked([py_exe(), '-I', '-X', 'utf8', str(TEAM_RATINGS), str(live_dir), '--engine', 'm0', '--no-fetch',
                 '--out', str(ROOT / 'data/season-source-2026-27/team-ratings-m0.json')], ROOT, TIMEOUTS['ratings_m0'])
        checked([py_exe(), '-I', '-X', 'utf8', str(ROOT / 'reports' / 'E229-transformer-vs-m0-forward' / 'predict_daily.py')], ROOT, TIMEOUTS['e229'])
    except Exception as e:
        log.warning('E-229 前向預測略過（不影響發布）：%s', str(e)[-400:])


def step_team_ratings(out_dir: Path, live_dir: Path | None, recompute: bool = True) -> Path | None:
    """每日傷病名單＋球隊評分（team_ratings_daily.py）→ teams.html（轉址頁）＋同資料夾 teams-data.json（名單頁排行檢視 fetch 的資料）。回傳 teams.html 路徑；任何失敗只記警告、回傳 None，
    不擋原本頁面的發布。recompute=False（--shell）只用上次算好的 team-ratings.json 重畫頁面。"""
    try:
        if recompute:
            checked([py_exe(), '-I', '-X', 'utf8', str(TEAM_RATINGS), str(live_dir)], ROOT, TIMEOUTS['ratings'])
            step_e229_forward(live_dir)
        html = out_dir / 'teams.html'
        checked([py_exe(), '-I', '-X', 'utf8', str(TEAMS_PAGE), str(html)], ROOT, TIMEOUTS['viewer'])
        return html
    except Exception as e:
        log.warning('球隊評分頁略過（不影響其他頁面）：%s', str(e)[-400:])
        return None


def step_games_data(out_dir: Path) -> dict[str, Path]:
    """賽程檢視的資料（build_games_data.py）→ out_dir 下的 games-data.json＋games-box-YYYY-MM.json。回傳 {檔名: 路徑}；
    失敗只記警告、回傳 {}，不擋原發布（頁面的檢視 fetch 不到會顯示載入失敗）。"""
    try:
        r = checked([py_exe(), '-I', '-X', 'utf8', str(GAMES_DATA), str(out_dir)], ROOT, TIMEOUTS['viewer'])
        return {n: out_dir / n for n in (ln.split('\t')[0] for ln in (r.stdout or '').splitlines()) if n}
    except Exception as e:
        log.warning('賽程資料略過（不影響其他頁面）：%s', str(e)[-400:])
        return {}


def teams_message(cutoff: str) -> str:
    return f'teams 球隊評分 數據至 {cutoff}\n\n{CO_AUTHOR}\n'


def publish_teams_only(state: dict, args) -> None:
    """沒有新比賽時傷病名單仍會變：只重算球隊評分並更新 gh-pages 的 teams.html。"""
    cutoff = state.get('dataCutoff')
    live_dir = LIVE / cutoff if cutoff else None
    if not live_dir or not (live_dir / 'ranking.csv').exists() or args.dry_run:
        return
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='teams-', dir=BUILD_ROOT))
    try:
        html = step_team_ratings(work, live_dir)
        if html is None:
            return
        try:
            pages = {'teams.html': html, 'teams-data.json': html.with_name('teams-data.json'), **step_games_data(work)}
            sha = publish_html(ROOT, pages, teams_message(cutoff), remote=args.remote, branch=args.branch)
            log.info('球隊評分頁已發布，gh-pages commit=%s', sha or '（內容未變）')
        except Exception as e:
            log.warning('球隊評分頁發布失敗（不影響其他頁面）：%s', str(e)[-400:])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def step_fetch_inseason() -> dict:
    """fetch_inseason 在有 PBP 抓不到時 exit 1（預期）。末行是 JSON 摘要＝腳本跑完了，才算「預期的 exit 1」；
    沒有摘要（bio 抓失敗、例外、逾時）才是真失敗。"""
    try:
        r = run([node_exe(), 'scripts/fetch_inseason_2026_27.js', SEASON], ROOT, TIMEOUTS['inseason'])
    except subprocess.TimeoutExpired:
        raise RuntimeError('fetch_inseason 逾時')
    summary = None
    for line in reversed((r.stdout or '').strip().splitlines()):
        try:
            cand = json.loads(line)
        except ValueError:
            continue
        if isinstance(cand, dict) and 'failures' in cand:
            summary = cand
            break
    if r.returncode == 0:
        return summary or {}
    if summary is not None and r.returncode == 1:
        log.warning('PBP 不完整（預期）：抓到 %s、快取 %s、失敗 %d 場 %s', summary.get('fetched'),
                    summary.get('cached'), len(summary['failures']),
                    [f.get('id') for f in summary['failures']][:10])
        return summary
    log_tail(r.stdout)
    log_tail(r.stderr)
    raise RuntimeError(f'fetch_inseason 真的失敗 exit={r.returncode}：{(r.stderr or r.stdout).strip()[-500:]}')


def probe_base_version() -> str | None:
    """不執行 run_c4_live，從原始碼讀基底版號（只用來判斷「資料沒變時是否還得重跑」）。"""
    m = re.search(r"^VERSION\s*=\s*'([^']+)'", RUN_C4.read_text(encoding='utf-8'), re.M)
    return m.group(1) if m else None


def step_c4(out_dir: Path) -> dict:
    checked([py_exe(), '-I', '-X', 'utf8', str(RUN_LIVE), str(out_dir)], ROOT, TIMEOUTS['c4'])
    meta = load_json(out_dir / 'meta.json')
    if not meta.get('version') or not meta.get('dataCutoff'):
        raise RuntimeError(f'meta.json 缺 version/dataCutoff：{out_dir}')
    return meta


def step_history(out_dir: Path) -> None:
    """名單頁 OVR 折線（2026-10-31）：資料截到每個比賽日重算 OVR → ovr-history.json（同版號、同資料的日子走快取）。
    失敗不擋發布，名單頁就不畫折線。"""
    try:
        r = run([py_exe(), '-I', '-X', 'utf8', str(HISTORY), str(out_dir)], ROOT, TIMEOUTS['history'])
    except subprocess.TimeoutExpired:
        log.warning('ovr_history 逾時；這次不畫 OVR 折線')
        return
    if r.returncode != 0:
        log.warning('ovr_history exit=%s：%s', r.returncode, (r.stderr or r.stdout).strip()[-300:])


def step_viewer(out_dir: Path) -> Path:
    checked([py_exe(), '-I', '-X', 'utf8', str(VIEWER), str(out_dir)], ROOT, TIMEOUTS['viewer'])
    html = out_dir / 'roster-viewer.html'
    if not html.exists() or html.stat().st_size < 10_000:
        raise RuntimeError(f'roster-viewer.html 不存在或太小：{html}')
    return html


# 球隊不放網址（使用者 2026-11-04 改回：只存瀏覽器記憶）。11-04 上午發過的 /hawks、/rookies 舊連結沒有實體檔，
# GitHub Pages 回 404.html：直接轉回首頁，保留 ?query 與 #hash
# 2026-11-04 起 /rank/、/games/ 是路徑式檢視（arammeta 做法：部署時各複製一份 index.html，HTTP 200）；
# 更深的 /rank/LAL/、/games/日期/[場次/] 沒有實體檔，404.html 把完整路徑存進 sessionStorage 再轉到 /rank/ 或 /games/，
# 頁面載入時用 history.replaceState 還原。其他路徑一律回首頁
NOT_FOUND_HTML = ('<!doctype html><meta charset="utf-8"><title>TrueOVR</title>'
                  "<script>var p=location.pathname,m=/^\\/(rank|games)\\//.exec(p);"
                  "if(m){try{sessionStorage.setItem('bbac.spa',p)}catch(e){}}"
                  "location.replace((m?'/'+m[1]+'/':'/')+location.search+location.hash)</script>"
                  '<a href="/">TrueOVR</a>')
SPA_SECTIONS = ('rank', 'games')


def add_spa_pages(pages: dict) -> dict:
    """把 index.html 的來源檔再登記成 rank/index.html、games/index.html（同一份內容，路徑決定顯示哪個檢視）；
    連結預覽縮圖 og-image.png（scripts/build_og_image.py 產生，commit 在 assets/）一併發到根目錄。"""
    for s in SPA_SECTIONS:
        pages[f'{s}/index.html'] = pages['index.html']
    pages['og-image.png'] = ROOT / 'assets' / 'og-image.png'
    return pages


def write_not_found(html: Path) -> Path:
    out = html.with_name('404.html')
    out.write_text(NOT_FOUND_HTML, encoding='utf-8')
    return out


def step_card_viewer(out_dir: Path) -> Path:
    """建 2025-26 正式卡頁（含賽季切換列），輸出到工作夾，與賽中頁一起發布成 2025-26.html。"""
    html = out_dir / 'card-roster-viewer.html'
    checked([py_exe(), '-I', '-X', 'utf8', str(CARD_VIEWER), str(html)], ROOT, TIMEOUTS['viewer'])
    if not html.exists() or html.stat().st_size < 10_000:
        raise RuntimeError(f'card-roster-viewer.html 不存在或太小：{html}')
    return html


# ----------------------------------------------------------------- 發布（仿 arammeta static_publish）
class GitRunner:
    def __init__(self, cwd: Path, timeout: int = TIMEOUTS['git']):
        self.cwd, self.timeout = cwd, timeout

    def __call__(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        try:
            r = run(['git', *args], self.cwd, self.timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f'git 逾時：{" ".join(args)}')
        if check and r.returncode != 0:
            raise RuntimeError(f'git {" ".join(args)} exit={r.returncode}: {(r.stderr or r.stdout).strip()[-500:]}')
        return r


def publish_html(repo: Path, html, message: str, *, remote: str = 'origin', branch: str = 'gh-pages',
                 target_name: str = 'index.html', before_push=None) -> str | None:
    """把一或多個檔案提交成 <branch> 上的檔案並 push。回傳新 commit sha；內容都沒變回傳 None。

    html：Path（發布成 target_name，向下相容）或 {目標檔名: 來源 Path}。
    在 temp 目錄開 detached worktree（開發中的 checkout 有未 commit 改動也不受影響），只 stage 白名單
    檔名（files 的鍵）；push 非快轉時 fetch＋merge（-X ours：以我們為準）後再推一次；最後一律移除工作樹。
    before_push：測試用掛鉤，在第一次 push 前呼叫（模擬競態）。
    """
    files = dict(html) if isinstance(html, dict) else {target_name: html}
    for name in files:
        if chr(92) in name or name.startswith(('.', '/')) or any(p in ('', '.', '..') for p in name.split('/')):
            raise ValueError(f'不合法的目標檔名：{name}')
    main_git = GitRunner(repo)
    main_git('fetch', remote, branch)
    tmp = Path(tempfile.mkdtemp(prefix='inseason-pages-'))
    wt = tmp / 'wt'
    try:
        main_git('worktree', 'add', '--detach', str(wt), f'{remote}/{branch}')
        g = GitRunner(wt)
        for name, src in files.items():
            (wt / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, wt / name)
        g('add', '--', *files)
        if g('diff', '--cached', '--quiet', check=False).returncode == 0:
            log.info('%s:%s 內容與上次相同，不提交', branch, ','.join(files))
            return None
        g('commit', '-m', message)
        if before_push:
            before_push()
        r = g('push', remote, f'HEAD:{branch}', check=False)
        if r.returncode != 0:
            log.warning('push 失敗，fetch＋merge 後重推：%s', (r.stderr or r.stdout).strip()[-300:])
            g('fetch', remote, branch)
            m = g('merge', '--no-edit', '-X', 'ours', f'{remote}/{branch}', check=False)
            if m.returncode != 0:
                g('merge', '--abort', check=False)
                raise RuntimeError(f'無法合併 {remote}/{branch}：{(m.stderr or m.stdout).strip()[-300:]}')
            g('push', remote, f'HEAD:{branch}')
        return g('rev-parse', 'HEAD').stdout.strip()
    finally:
        main_git('worktree', 'remove', '--force', str(wt), check=False)
        shutil.rmtree(tmp, ignore_errors=True)
        main_git('worktree', 'prune', check=False)


def commit_message(version: str, cutoff: str) -> str:
    return f'inseason {version.removeprefix("inseason ")} 數據至 {cutoff}\n\n{CO_AUTHOR}\n'


def shell_commit_message(version: str, cutoff: str) -> str:
    return f'inseason {version.removeprefix("inseason ")} 頁面更新（數據至 {cutoff}，資料不變）\n\n{CO_AUTHOR}\n'


# ----------------------------------------------------------------- 主流程
def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    fh.setFormatter(fmt)
    log.setLevel(logging.INFO)
    log.addHandler(fh)
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(sh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='照常建構（輸出到暫存夾），不 push、不寫 publish_state')
    ap.add_argument('--force', action='store_true', help='資料沒變也發布')
    ap.add_argument('--shell', action='store_true',
                    help='只重建頁面（UI／顯示改動）：沿用最後發布那天的 live 資料，不抓資料、不跑 C4、版號不動')
    ap.add_argument('--remote', default='origin')
    ap.add_argument('--branch', default='gh-pages')
    args = ap.parse_args(argv)
    setup_logging()
    log.info('==== 開始 dry_run=%s force=%s shell=%s ====', args.dry_run, args.force, args.shell)
    try:
        with Lock(LOCK_PATH):
            return _run_shell(args) if args.shell else _run(args)
    except LockBusy as e:
        log.warning('%s', e)
        return 0
    except Exception as e:  # noqa: BLE001
        log.error('失敗：%s', e)
        return 1


def _run(args) -> int:
    state = load_json(STATE_PATH)
    step_fetch_games()
    step_fetch_matchups()
    step_fetch_inseason()
    step_build_stints()
    step_prereg_e151()
    step_prereg_e222()
    step_fetch_tracking()
    step_fetch_gravity()
    step_fetch_possessions()
    data_sha = sha256_file(PLAYER_GAMES)
    pbp_count = len(list(PBP_DIR.glob('*.json'))) if PBP_DIR.exists() else 0
    log.info('player-games sha256=%s…  pbp=%d', data_sha[:12], pbp_count)

    unchanged = state.get('dataSha256') == data_sha and state.get('pbpCount') == pbp_count
    probe = probe_base_version()
    if unchanged and not args.force and probe is not None and probe == state.get('base'):
        log.info('沒有新比賽資料且版號未動（%s），不發布', state.get('base'))
        publish_teams_only(state, args)
        return 0

    # run_c4_live 的 rel() 要求輸出夾在 repo 內；data/ 已被 .gitignore
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='build-', dir=BUILD_ROOT))
    try:
        meta = step_c4(work)
        base = meta['version']
        d = decide(state, base, data_sha, pbp_count, args.force)
        log.info('決定：publish=%s 版號=%s（%s）', d['publish'], base, d['reason'])
        if not d['publish']:
            return 0
        shown = base
        meta['dataSha256'] = data_sha
        save_json(work / 'meta.json', meta)
        step_history(work)
        html = step_viewer(work)
        card_html = step_card_viewer(work)
        cutoff = meta['dataCutoff']
        teams_html = step_team_ratings(work, work)      # 用剛算好的 ranking.csv；失敗回 None，不擋其他頁
        games_files = step_games_data(work)             # 賽程檢視的資料；失敗回 {}，不擋其他頁

        if args.dry_run:
            log.info('dry-run：不 push、不寫 state、不複製到 live/。輸出夾 %s（保留）', work)
            work = None
            return 0

        final = LIVE / cutoff
        shutil.copytree(work, final, dirs_exist_ok=True)
        write_not_found(final / 'roster-viewer.html')
        pages = {'index.html': final / 'roster-viewer.html', '404.html': final / '404.html', '2025-26.html': final / card_html.name}
        if teams_html is not None:
            pages['teams.html'] = final / teams_html.name
            pages['teams-data.json'] = final / 'teams-data.json'
        pages.update({n: final / n for n in games_files})
        add_spa_pages(pages)
        sha = publish_html(ROOT, pages, commit_message(shown, cutoff),
                           remote=args.remote, branch=args.branch)
        state.pop('letter', None)
        state.update({'base': base, 'displayVersion': shown, 'dataSha256': data_sha,
                      'pbpCount': pbp_count, 'dataCutoff': cutoff,
                      'lastPublished': dt.datetime.now().astimezone().isoformat(timespec='seconds')})
        if sha:
            state['ghPagesCommit'] = sha
        save_json(STATE_PATH, state)
        log.info('已發布 %s 數據至 %s，gh-pages commit=%s', shown, cutoff, sha or '（內容未變）')
        return 0
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)


def _run_shell(args) -> int:
    """deploy-shell：OVR 數字不變的頁面改動。改公式會動到數字，要走完整流程並改版號（G2）。"""
    state = load_json(STATE_PATH)
    cutoff = state.get('dataCutoff')
    if not cutoff or not (LIVE / cutoff / 'meta.json').exists():
        raise RuntimeError(f'找不到最後發布的 live 資料（dataCutoff={cutoff}），先跑一次完整發布')
    final = LIVE / cutoff
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='shell-', dir=BUILD_ROOT))
    try:
        shutil.copytree(final, work, dirs_exist_ok=True)
        html = step_viewer(work)
        card_html = step_card_viewer(work)
        teams_html = step_team_ratings(work, None, recompute=False)
        games_files = step_games_data(work)
        if args.dry_run:
            log.info('dry-run（shell）：不 push、不寫 state。輸出夾 %s（保留）', work)
            work = None
            return 0
        shutil.copyfile(html, final / html.name)
        write_not_found(final / html.name)
        shutil.copyfile(card_html, final / card_html.name)
        pages = {'index.html': final / html.name, '404.html': final / '404.html', '2025-26.html': final / card_html.name}
        if teams_html is not None:
            shutil.copyfile(teams_html, final / teams_html.name)
            shutil.copyfile(teams_html.with_name('teams-data.json'), final / 'teams-data.json')
            pages['teams.html'] = final / teams_html.name
            pages['teams-data.json'] = final / 'teams-data.json'
        for n, src in games_files.items():
            shutil.copyfile(src, final / n)
            pages[n] = final / n
        add_spa_pages(pages)
        shown = state.get('displayVersion', '')
        sha = publish_html(ROOT, pages, shell_commit_message(shown, cutoff), remote=args.remote, branch=args.branch)
        if sha:
            state['ghPagesCommit'] = sha
            state['lastShellPublished'] = dt.datetime.now().astimezone().isoformat(timespec='seconds')
            save_json(STATE_PATH, state)
        log.info('shell 發布 %s（數據至 %s），gh-pages commit=%s', shown, cutoff, sha or '（內容未變）')
        return 0
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
