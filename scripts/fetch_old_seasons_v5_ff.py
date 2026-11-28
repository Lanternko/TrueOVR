"""v5 Path A：逐季 four-factors（與 v3/tools/four_factors_seasonal.run_season 同一演算法與同一輸出格式）。

只把輸入 stints 與輸出路徑改成參數；ridge、5-fold CV、LAMBDAS 都直接用 tools/four_factors_2022_25。
用法：python -I scripts/fetch_old_seasons_v5_ff.py --season 2016-17 --stints PATH --out CSV
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/tools'))
import four_factors_2022_25 as FF   # noqa: E402


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', required=True)
    ap.add_argument('--stints', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    with open(args.stints, encoding='utf-8') as fh:
        lines = fh.readlines()
    rows = FF.sides([args.season], reader=lambda s: lines)
    players = sorted({p for r in rows for p in r[1] + r[2]})
    results, summary = {}, {'season': args.season, 'stintSides': len(rows), 'players': len(players), 'factors': {}}
    for factor in FF.FACTORS:
        coef, info = FF.fit(rows, players, factor)
        results[factor] = coef
        summary['factors'][factor] = info
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    head = (['playerId', 'name'] + [f'{f}_{s}' for f in FF.FACTORS for s in ('defense', 'offense')]
            + ['defensePossessions', 'season'])
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for p in players:
            w.writerow([p, ''] + [round(results[f][p][s], 4) for f in FF.FACTORS for s in ('defense', 'offense')]
                       + [round(results['steal'][p]['defenseWeight']), args.season])
    summary['stints'] = {'file': str(Path(args.stints).resolve()), 'sha256': sha256(args.stints)}
    summary['code'] = {'scripts/fetch_old_seasons_v5_ff.py': sha256(__file__),
                       'reports/ovr-inseason-2026-27/tools/four_factors_2022_25.py': sha256(FF.__file__)}
    summary['output'] = {'file': str(out.resolve()), 'sha256': sha256(out)}
    out.with_name(out.stem + '-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n',
                                                         encoding='utf-8')
    print(json.dumps({'season': args.season, 'stintSides': len(rows), 'players': len(players),
                      'lambdas': {k: v['lambda'] for k, v in summary['factors'].items()}}))


if __name__ == '__main__':
    main()
