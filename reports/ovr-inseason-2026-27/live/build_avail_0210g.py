"""card／inseason 0.2.10g：把 2022-23～2024-25 的 boxes 壓成 avail-hist-0210g.json.gz（{季: {gid: [[pid, tid, status, reason, mn], ...]}}）。
來源 data/defense-seventh/<季>/boxes/*.json（NBA liveData boxscore，含 INACTIVE 名單）；解析器 = window11.box_rows。
先驗證解析器：用 2025-26 的原始 boxscore（data/season-source/dnp-2025-26-raw）解析，須與 dnp-2025-26.json 逐列相同（pid、tid、status、reason；mn 差 <1e-3）。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_avail_0210g.py"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import window11 as W  # noqa: E402

ROOT = W.ROOT


def check_parser():
    raw = ROOT / 'data/season-source/dnp-2025-26-raw'
    ref = json.loads(W.DNP_PRIOR.read_text(encoding='utf-8'))['games']
    files = sorted(raw.glob('boxscore_*.json.gz'))
    bad = n = 0
    for f in files:
        gid, rows = W.box_rows(json.loads(gzip.open(f, 'rt', encoding='utf-8').read()))
        r0 = {(int(p[0]), int(p[1])): p for p in ref[gid]['players']}
        n += 1
        if len(r0) != len(rows):
            bad += 1
            continue
        for pid, tid, st, rs, mn in rows:
            p = r0.get((pid, tid))
            if p is None or p[2] != st or p[3] != rs or abs(float(p[4]) - mn) > 1e-3:
                bad += 1
                break
    return n, bad


def main():
    n, bad = check_parser()
    print('parser check vs dnp-2025-26.json:', n, 'games,', bad, 'mismatch')
    assert n >= 1200 and bad == 0
    out = {}
    for s in W.HIST_SEASONS:
        d = {}
        for f in sorted((ROOT / 'data/defense-seventh' / s / 'boxes').glob('*.json')):
            gid, rows = W.box_rows(json.loads(f.read_text(encoding='utf-8')))
            d[gid] = rows
        out[s] = d
        print(s, len(d), 'games', sum(len(v) for v in d.values()), 'rows')
    body = json.dumps(out, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')
    with gzip.GzipFile(W.AVAIL_HIST, 'wb', mtime=0) as fh:
        fh.write(body)
    print(W.AVAIL_HIST.name, hashlib.sha256(W.AVAIL_HIST.read_bytes()).hexdigest(), W.AVAIL_HIST.stat().st_size, 'bytes')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
