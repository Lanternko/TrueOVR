"""E-116：唯讀輸入的 sha256 快照（跑前／跑後各一次，寫進 results.json）。"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVR = 'reports/ovr-inseason-2026-27'
FILES = (
    [f'{OVR}/e111-card027/cards/prior-{s}-027.json' for s in ('2017-18', '2018-19', '2019-20', '2020-21', '2021-22')]
    + [f'data/defense-seventh/{s}/bio.json' for s in ('2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2026-27')]
    + ['data/defense-seventh/2026-27/player-games.json', 'data/defense-seventh/2026-27/team-games.json',
       'data/benchmark-source/bio.json',
       f'{OVR}/live/prior-2025-26-card027.json', f'{OVR}/live/pool-027.json', f'{OVR}/live/usage-2025-26-card027.json',
       f'{OVR}/live/run_c4_live.py', f'{OVR}/live/2026-10-28/no-prior.csv',
       'reports/E116-rookie-prior/preregistration.md', 'reports/impact-rapm/rapm.csv']
)


def sha(p):
    h = hashlib.sha256()
    with open(ROOT / p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def snapshot():
    out = {}
    for p in FILES:
        try:
            out[p] = sha(p)
        except OSError as e:
            out[p] = f'MISSING {e.__class__.__name__}'
    return out


if __name__ == '__main__':
    json.dump(snapshot(), open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
