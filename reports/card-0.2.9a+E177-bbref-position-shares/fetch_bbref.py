"""E-177：抓 BBRef play-by-play 頁（每季一次，間隔 >= 5 秒，UA Mozilla/5.0）。原始 HTML 放 work/bbref/（不 commit）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.9a+E177-bbref-position-shares/fetch_bbref.py"""
import sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/bbref'
OUT.mkdir(parents=True, exist_ok=True)
for i, y in enumerate((2023, 2024, 2025, 2026)):
    f = OUT / f'NBA_{y}_play-by-play.html'
    if f.exists():
        continue
    if i:
        time.sleep(6)
    req = urllib.request.Request(f'https://www.basketball-reference.com/leagues/NBA_{y}_play-by-play.html', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    f.write_bytes(data)
    print(y, r.status, len(data), flush=True)
