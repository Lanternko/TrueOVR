"""球隊戰力排行資料與舊網址轉址頁（E-208；2026-11-02 起排行已併進名單頁 index.html 當第二個檢視，見 scripts/rank_view.py）。
讀 data/season-source-2026-27/team-ratings.json（scripts/team_ratings_daily.py 產生），輸出：
  <out.html>（舊 teams.html，轉址到 /rank/，#LAL 轉 /rank/LAL/）＋同資料夾的 teams-data.json（排行檢視 fetch 的資料）。

用法：python -I -X utf8 scripts/build_teams_page.py <out.html> [team-ratings.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from injury_desc import injury_desc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RATINGS = ROOT / 'data/season-source-2026-27/team-ratings.json'
DATA_NAME = 'teams-data.json'

STUB = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>戰力排行 · TrueOVR</title><meta name="robots" content="noindex">
<script>var h=location.hash.slice(1);location.replace('/rank/'+(h?h+'/':''));</script>
<noscript><meta http-equiv="refresh" content="0;url=/rank/"></noscript>
</head><body><a href="/rank/">戰力排行已移到首頁，點這裡前往</a></body></html>
"""


def data_json(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, separators=(',', ':'))


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    out = Path(a[0])
    src = Path(a[1]) if len(a) > 1 else RATINGS
    doc = json.loads(src.read_text(encoding='utf-8'))
    teams = doc.get('teams') or []
    for t in (teams.values() if isinstance(teams, dict) else teams):                  # 舊資料（--shell 不重算）沒有 injury 欄，這裡補
        for x in t.get('injured') or []:
            x.setdefault('injury', injury_desc(x.get('comment')))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(STUB, encoding='utf-8')
    (out.parent / DATA_NAME).write_text(data_json(doc), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
