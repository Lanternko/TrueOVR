# Path A 專用 2021-22 four-factors

依使用者 2026-10-28 的決定（pressure 樣本規則 A：Path A 每一季同一規則），這裡放 Path A 專用的 2021-22 four-factors。
v3 的 `four-factors-2021-22.csv` 不動；D1–D3 仍用 v3 版。

- `four-factors.csv`：SHA256 `b3e5cd79107ea3c2b3ce407bb84f4c31e56b5a77dbae35beec0cbadc9a71ddcc`，605 人。
- `stints-ff/stints.jsonl`：SHA256 `f4ae7b419249f38bf7c255e5b87971699c34ff38fcfca9d23c6daf5557375fc7`，1,167 場有效、35,406 段。
- `stints-ff/source-manifest.sha256`：轉換出來的 2021-22 manifest 的 SHA（轉換資料暫存在 `D:\Projects\temp\nba-old-seasons\pa2122\data\2021-22\`）。

重現：

    python -I scripts/fetch_old_seasons_v5.py --season 2021-22 --source cdn --out D:/Projects/temp/nba-old-seasons/pa2122/data
    node scripts/fetch_old_seasons_v5_stints.js 2021-22 D:/Projects/temp/nba-old-seasons/pa2122/data/2021-22 D:/Projects/temp/nba-old-seasons/pa2122/stints
    python -I scripts/fetch_old_seasons_v5_ff.py --season 2021-22 --stints reports/ovr-inseason-2026-27/v5/pathA/ff-2021-22/stints-ff/stints.jsonl --out reports/ovr-inseason-2026-27/v5/pathA/ff-2021-22/four-factors.csv

詳見 `../fetch-README.md` §5.5。
