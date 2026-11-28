"""把 v5/history/box-games-<季>.csv.gz 還原成 scripts/build_historical_stints.py 讀的 box 格式。

用途：Y6 答案窗（rapm-2018-19_2021-22）的 2021-22 是鏡像重建的 stint，repo 沒收錄 stint 檔，
box 原始三份 csv 也不在本機。box-games 由同一份 box 轉出，load_box 用到的欄位都在：
  season_year、gameId、teamId、personId、personName、points、position（先發旗標）、minutes（mm:ss）。
驗證：重建後的 validLineupGames／stints 要等於 v5/history/summary.json 的紀錄，且 R1 要通過。
"""
import csv
import gzip
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.parent.mkdir(parents=True, exist_ok=True)
with gzip.open(src, 'rt', encoding='utf-8') as fi, open(dst, 'w', encoding='utf-8', newline='') as fo:
    w = csv.writer(fo)
    w.writerow(['season_year', 'gameId', 'game_date', 'teamId', 'personId', 'personName', 'position', 'minutes', 'points'])
    for r in csv.DictReader(fi):
        s = int(r['seconds'] or 0)
        w.writerow([r['season'], r['gameId'], r['gameDate'], r['teamId'], r['playerId'], r['name'],
                    'S' if r['starter'] == '1' else '', f'{s // 60}:{s % 60:02d}' if s else '', r['PTS']])
