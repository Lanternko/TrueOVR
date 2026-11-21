"""領號並上鎖：E／F／L／R 新編號一律用這支取，取到就鎖給這個對話，其他對話不會再拿到同一號（R-155）。

用法：
  python memory/claim_id.py E "陣容 Transformer"       # 印出新號，例如 E-227
  python memory/claim_id.py --list [E]                 # 列出已領的號

號碼＝max(已領清單、memory/*.md 的條目標題、reports/ 目錄名、所有分支 commit 標題裡出現的號) + 1。
清單放在 git common dir（所有 worktree 共用），用 O_EXCL 鎖檔避免兩個對話同時領到同一號。
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ('E', 'F', 'L', 'R')
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def git(*args) -> str:
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', creationflags=NO_WINDOW).stdout


def common_dir() -> Path:
    p = Path(git('rev-parse', '--git-common-dir').strip())
    return p if p.is_absolute() else ROOT / p


def load_claims(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def used_numbers(kind: str, claims: list) -> set:
    nums = {c['n'] for c in claims if c['kind'] == kind}
    pat = re.compile(rf'\b{kind}-?(\d{{2,4}})\b')
    for f in (ROOT / 'memory').glob('*.md'):
        nums.update(int(m) for m in re.findall(rf'^### {kind}-(\d+)', f.read_text(encoding='utf-8'), re.M))
    if kind == 'E':
        for d in (ROOT / 'reports').iterdir():
            m = re.match(r'E(\d+)\b|.*\+E(\d+)', d.name)
            if m:
                nums.add(int(m.group(1) or m.group(2)))
    for line in git('log', '--all', '--format=%s').splitlines():
        nums.update(int(m) for m in pat.findall(line))
    nums.discard(999)                                     # 各檔範本條目
    return nums


def locked(path: Path):
    lock = path.with_suffix('.lock')
    for _ in range(100):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return lock
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 60:   # 別的程序當掉留下的鎖
                lock.unlink(missing_ok=True)
            time.sleep(0.1)
    sys.exit('拿不到鎖：' + str(lock))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', nargs='?', choices=KINDS)
    ap.add_argument('title', nargs='?', default='')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    path = common_dir() / 'id-claims.jsonl'
    if a.list:
        for c in load_claims(path):
            if not a.kind or c['kind'] == a.kind:
                print(f"{c['kind']}-{c['n']:03d}  {c['at']}  {c['title']}")
        return
    if not a.kind or not a.title:
        ap.error('要給種類（E/F/L/R）和短名')
    lock = locked(path)
    try:
        claims = load_claims(path)
        n = max(used_numbers(a.kind, claims), default=0) + 1
        rec = {'kind': a.kind, 'n': n, 'title': a.title, 'at': dt.datetime.now().isoformat(timespec='seconds'),
               'branch': git('branch', '--show-current').strip()}
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    finally:
        lock.unlink(missing_ok=True)
    print(f'{a.kind}-{n:03d}')


if __name__ == '__main__':
    main()
