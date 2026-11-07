"""名單頁 OVR 折線圖的資料：用現行模型（run_c4_live_rookie）把 2026-27 資料截到每個比賽日，逐日重算 OVR。

每天的 ranking.csv 版本不一（0.2.1b → 0.2.7b）、新秀起點又改過（R-096），直接串會有版本跳動，所以改成同一把尺重算。
截斷：player-games／team-games 只留 GAME_DATE ≤ d，pbp 只留那些場，本季 stints 只留那些場；防守追蹤表是季累計抓不到逐日，
沿用最新那份（新秀／老將 onBall、help 的過去點會用到之後的資料，只影響防守兩項）；0.2.10j 的引力（gravity.json，季累計）同樣沿用最新那份。
快取：<out>.json 記 version 與每日 {playerId: ovr}；同版號、同日期、該日截斷資料 sha 相同就不重算。最後一天不重算，直接用當天正式 ranking.csv。

用法：python -I scripts/... ovr_history.py <今日輸出夾（有 ranking.csv、meta.json）>   → 寫 <今日輸出夾>/ovr-history.json，並更新快取 live/ovr-history-cache.json
      python -I ovr_history.py --one <截斷資料夾> <輸出夾>                              （內部：單日重算）
"""
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEASON = '2026-27'
DATA26 = ROOT / 'data/defense-seventh' / SEASON
STINTS = ROOT / f'reports/defense-seventh/{SEASON}/stints/stints.jsonl'
CACHE = HERE / 'ovr-history-cache.json'
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def one(data_dir: Path, out_dir: Path):
    """單日重算：換掉 DATA26、本季 stints、def-L-live 輸出路徑後照常跑 run_c4_live_rookie。"""
    sys.path.insert(0, str(HERE))
    import run_c4_live_rookie as RK
    RK.DB.CUR_STINTS = data_dir / 'stints.jsonl'
    RK.DEF_L_LIVE = out_dir / 'def-L-live.csv'   # 不蓋掉正式那份（名單頁 DIQ 讀它）
    ns = RK.load_ns()
    ns['DATA26'] = data_dir
    sys.argv = [sys.argv[0], str(out_dir)]
    return ns['main']()


def truncate(day: str, dst: Path) -> str:
    """把 DATA26 截到 GAME_DATE ≤ day 寫進 dst，回傳截斷後內容的 sha256（快取鍵）。"""
    dst.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    games = set()
    for name in ('player-games.json', 'team-games.json'):
        doc = json.loads((DATA26 / name).read_text(encoding='utf-8'))
        rs = doc['data']['resultSets'][0]
        i, j = rs['headers'].index('GAME_DATE'), rs['headers'].index('GAME_ID')
        rs['rowSet'] = [r for r in rs['rowSet'] if r[i] <= day]
        games |= {r[j] for r in rs['rowSet']}
        h.update(json.dumps(rs['rowSet']).encode('utf-8'))   # 只雜湊列（fetchedAt 每次抓都變）
        (dst / name).write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
    shutil.copy2(DATA26 / 'bio.json', dst / 'bio.json')
    (dst / 'pbp').mkdir(exist_ok=True)
    for g in sorted(games):
        p = DATA26 / 'pbp' / f'{g}.json'
        if p.exists():
            shutil.copy2(p, dst / 'pbp' / p.name)
            h.update(p.read_bytes())
    with open(STINTS, encoding='utf-8') as f, open(dst / 'stints.jsonl', 'w', encoding='utf-8') as o:
        for line in f:
            if json.loads(line)['id'] in games:
                o.write(line)
                h.update(line.encode('utf-8'))
    return h.hexdigest()


def read_ovr(path: Path) -> dict:
    return {r['playerId']: float(r['ovr']) for r in csv.DictReader(path.open(encoding='utf-8'))}


def build(today_dir: Path):
    meta = json.loads((today_dir / 'meta.json').read_text(encoding='utf-8'))
    version, cutoff = meta['version'], meta['dataCutoff']
    rows = list(csv.DictReader((today_dir / 'ranking.csv').open(encoding='utf-8')))
    doc = json.loads((DATA26 / 'player-games.json').read_text(encoding='utf-8'))['data']['resultSets'][0]
    days = sorted({r[doc['headers'].index('GAME_DATE')] for r in doc['rowSet']})
    try:
        cache = json.loads(CACHE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    # 同版號也可能改程式或先驗（例：R-096 新秀起點沒升版號），所以模型檔雜湊也進快取鍵
    code = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(HERE.glob('*.py')) + sorted(HERE.glob('*-2026.json')))).hexdigest()
    if cache.get('version') != version or cache.get('code') != code:
        cache = {'version': version, 'code': code, 'days': {}}
    py = Path(sys.executable)
    py = py.with_name('python.exe') if py.name.lower() == 'pythonw.exe' else py
    series = {}
    with tempfile.TemporaryDirectory(dir=ROOT / 'data/_inseason_build') as tmp:
        for d in days[:-1] if days[-1] == cutoff else days:
            work = Path(tmp) / d
            sha = truncate(d, work / 'data')
            hit = cache['days'].get(d)
            if hit and hit['sha'] == sha:
                series[d] = hit['ovr']
                continue
            r = subprocess.run([str(py), '-I', '-X', 'utf8', str(Path(__file__).resolve()), '--one', str(work / 'data'), str(work / 'out')],
                               cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace',
                               creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL, timeout=900)
            if r.returncode != 0:
                raise RuntimeError(f'{d} 重算失敗：{(r.stderr or r.stdout).strip()[-600:]}')
            series[d] = read_ovr(work / 'out' / 'ranking.csv')
            cache['days'][d] = {'sha': sha, 'ovr': series[d]}
            print(f'{d}：重算 {len(series[d])} 人', file=sys.stderr)
    series[cutoff] = read_ovr(today_dir / 'ranking.csv')
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
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
    print(f'wrote {today_dir / "ovr-history.json"}：{len(series)} 天、{len(out["players"])} 人', file=sys.stderr)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == '--one':
        raise SystemExit(one(Path(sys.argv[2]), Path(sys.argv[3])))
    build(Path(sys.argv[1]).resolve())
