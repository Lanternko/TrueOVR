"""S2/S3 前置：2022-23..2024-25 三季全季卡片與凍結映射。

輸出 data/season-cards-2022-25.json：
  seasons[season] = {priors, pools, poolPlayerIds, cards{playerId: card}}
  card 含 15 項能力值、age、pos、MIN/GP、sample、e2（shot-origin）與 USG_PCT。
pass/rebound 的 pool 用 §1.1 的 box+team-games 公式重算（與 S1 的 bio 官方值同序、
REB 水平不同，見 season_attrs.pass_rebound_raw 的說明）；其餘屬性與 S1 完全相同。

用法：python reports/ovr-inseason-2026-27/tools/build_season_cards.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import DATA, ROOT, write_json
import season_attrs as SA

OUT = DATA / 'season-cards-2022-25.json'


def build(season):
    t0 = time.time()
    sd = SA.load_season(season)
    stats = SA.aggregate(sd)
    raw = SA.raw_with_box(sd, stats)
    mapping = SA.build_mapping(sd, stats, raw)
    cards = SA.compute_attrs(sd, stats, mapping)
    out = {'priors': mapping['priors'],
           'pools': {k: [round(float(v), 10) for v in vals] for k, vals in mapping['pools'].items()},
           'poolPlayerIds': mapping['pool'],
           'cards': {}}
    for pid, c in cards.items():
        c = dict(c)
        bio = sd['bio'][pid]
        c['usg'] = SA._f(bio['USG_PCT'])
        out['cards'][str(pid)] = c
    print(json.dumps({'season': season, 'players': len(cards), 'pool': len(mapping['pool']),
                      'seconds': round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)
    return out


def main():
    doc = {'note': 'S2/S3 用三季全季卡片；pass/rebound pool 由 box+team-games 公式重算。',
           'seasons': {}}
    for season in SA.SEASONS:
        doc['seasons'][season] = build(season)
    write_json(OUT, doc)
    print(json.dumps({'out': str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
