"""v5 wrapper：把轉換後的 2021-22 目錄餵 v4 的 season_attrs（不改 v4 檔），比較 15 項屬性與 v4/data/prior-2021-22.json。

做法：暫時把 SA.season_paths('2021-22') 的 data 根換成 --data（其餘路徑不變），呼叫和 build_prior_v4.build_2021_22
相同的 load_season_v4 → aggregate → raw_with_box → build_mapping → compute_attrs。
用法：python -I scripts/fetch_old_seasons_v5_attrs.py --data DIR [--ff CSV] --label NAME --json OUT
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/ovr-inseason-2026-27'
sys.path.insert(0, str(REPORT / 'tools'))
sys.path.insert(0, str(REPORT / 'v4/tools'))
import season_attrs_v4 as SA          # noqa: E402
import season_load_v4 as SL           # noqa: E402
from ovr_common import ATTRS          # noqa: E402


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if not sx or not sy else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sx / sy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True, help='含 2021-22/ 的根目錄')
    ap.add_argument('--ff')
    ap.add_argument('--label', required=True)
    ap.add_argument('--json', required=True)
    args = ap.parse_args()
    orig = SA.season_paths
    base = Path(args.data) / '2021-22'

    def patched(season):
        P = orig(season)
        if season == '2021-22':
            P.update(box=base / 'player-games.json', bio=base / 'bio.json', pbp=base / 'pbp',
                     team_games=base / 'team-games.json')
        return P
    SA.season_paths = patched
    sd = SL.load_season_v4('2021-22', ff_path=Path(args.ff) if args.ff else None)
    stats = SA.aggregate(sd)
    raw = SA.raw_with_box(sd, stats)
    mapping = SA.build_mapping(sd, stats, raw)
    cards = SA.compute_attrs(sd, stats, mapping)
    prior = {p['playerId']: p for p in
             json.loads((REPORT / 'v4/data/prior-2021-22.json').read_text(encoding='utf-8'))['players']}
    common = sorted(set(cards) & set(prior))
    rows = {}
    for a in ATTRS:
        xs, ys, diffs = [], [], []
        for p in common:
            x, y = prior[p].get(a), cards[p].get(a)
            if x is None or y is None:
                continue
            x, y = float(x), float(y)
            xs.append(x)
            ys.append(y)
            diffs.append(abs(x - y))
        diffs.sort()
        rows[a] = {'n': len(xs), 'r': round(corr(xs, ys), 6) if corr(xs, ys) is not None else None,
                   'maxAbsDiff': round(diffs[-1], 4) if diffs else None,
                   'medianAbsDiff': round(diffs[len(diffs) // 2], 4) if diffs else None,
                   'nDiffGt0.01': sum(d > 0.01 for d in diffs), 'nDiffGt1': sum(d > 1 for d in diffs)}
    out = {'label': args.label, 'data': str(base), 'ff': sd['ffSource'], 'players': len(cards),
           'priorPlayers': len(prior), 'common': len(common), 'poolPlayers': len(mapping['pool']),
           'attrs': rows}
    Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(args.label, 'players', len(cards), 'common', len(common), 'pool', len(mapping['pool']))
    for a, r in rows.items():
        print(f"  {a:12s} r={r['r']} max={r['maxAbsDiff']} med={r['medianAbsDiff']} n>0.01={r['nDiffGt0.01']} n>1={r['nDiffGt1']}")


if __name__ == '__main__':
    main()
