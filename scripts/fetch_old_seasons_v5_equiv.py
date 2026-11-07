"""v5 Path A 等價驗證：同一支轉換程式產生的 2021-22（v3+v2 路徑、cdn 路徑）對本機既有 2021-22。

用法：python -I scripts/fetch_old_seasons_v5_equiv.py --cand DIR[,DIR...] [--season 2021-22] --json OUT
比較 pbp 投籃分區（每球員 mid/short/3 的 M/A）、bio、player-games、team-games。
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def zone_of(a):   # 與 v4/tools/season_attrs_v4.zone_of 相同
    area = a.get('area')
    if area:
        return 'mid' if area == 'Mid-Range' else 'short'
    x, y = a.get('xLegacy'), a.get('yLegacy')
    if x is None or y is None or (x == 0 and y == 0):
        return 'short'
    return 'short' if (abs(x) <= 80 and y <= 138) else 'mid'


def zones(base):
    out = {}
    for p in sorted((base / 'pbp').glob('*.json')):
        for a in json.loads(p.read_text(encoding='utf-8'))['data']['game']['actions']:
            if a.get('isFieldGoal') != 1 or a.get('personId') in (None, 0):
                continue
            if a.get('shotResult') not in ('Made', 'Missed') or a.get('actionType') not in ('2pt', '3pt'):
                continue
            z = '3' if a['actionType'] == '3pt' else zone_of(a)
            s = out.setdefault(int(a['personId']), {k: 0 for k in ('midM', 'midA', 'shortM', 'shortA', '3M', '3A')})
            s[z + 'A'] += 1
            s[z + 'M'] += a['shotResult'] == 'Made'
    return out


def rs(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(d['headers'], r)) for r in d['rowSet']]


def corr(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if sx == 0 or sy == 0 else round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sx / sy, 6)


def compare(ref, cand, keys, tol=0):
    common = sorted(set(ref) & set(cand))
    res = {'refN': len(ref), 'candN': len(cand), 'common': len(common),
           'onlyRef': len(set(ref) - set(cand)), 'onlyCand': len(set(cand) - set(ref)), 'fields': {}}
    bad = set()
    for k in keys:
        xs, ys, mx, nbad = [], [], 0, 0
        for c in common:
            a, b = ref[c].get(k), cand[c].get(k)
            if a is None or b is None:
                if a != b:
                    nbad += 1
                    bad.add(c)
                continue
            a, b = float(a), float(b)
            xs.append(a)
            ys.append(b)
            d = abs(a - b)
            mx = max(mx, d)
            if d > tol:
                nbad += 1
                bad.add(c)
        res['fields'][k] = {'r': corr(xs, ys), 'maxDiff': round(mx, 6), 'mismatch': nbad}
    res['rowsAnyMismatch'] = len(bad)
    res['exampleMismatch'] = [str(c) for c in sorted(bad, key=str)[:5]]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', default='2021-22')
    ap.add_argument('--cand', required=True)
    ap.add_argument('--json', required=True)
    args = ap.parse_args()
    ref = ROOT / 'data/defense-seventh' / args.season
    rz = zones(ref)
    rbio = {int(r['PLAYER_ID']): r for r in rs(ref / 'bio.json')}
    rpg = {(int(r['PLAYER_ID']), r['GAME_ID']): r for r in rs(ref / 'player-games.json')}
    rtg = {(int(r['TEAM_ID']), r['GAME_ID']): r for r in rs(ref / 'team-games.json')}
    stats = ['MIN', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK',
             'TOV', 'PF', 'PTS', 'PLUS_MINUS']
    out = {'season': args.season, 'reference': str(ref), 'candidates': {}}
    for c in args.cand.split(','):
        base = Path(c) / args.season
        cb = {int(r['PLAYER_ID']): r for r in rs(base / 'bio.json')}
        cpg = {(int(r['PLAYER_ID']), r['GAME_ID']): r for r in rs(base / 'player-games.json')}
        ctg = {(int(r['TEAM_ID']), r['GAME_ID']): r for r in rs(base / 'team-games.json')}
        # 球員季合計（被交易球員跨隊加總）
        def season_tot(pg):
            t = {}
            for (p, _), r in pg.items():
                s = t.setdefault(p, {k: 0 for k in stats})
                for k in stats:
                    s[k] += float(r[k] or 0)
            return t
        out['candidates'][c] = {
            'pbpZones': compare(rz, zones(base), ['midM', 'midA', 'shortM', 'shortA', '3M', '3A']),
            'bio': compare(rbio, cb, ['PLAYER_HEIGHT_INCHES', 'PLAYER_WEIGHT', 'AGE', 'AST_PCT', 'OREB_PCT',
                                      'DREB_PCT', 'GP']),
            'playerGames': compare(rpg, cpg, stats),
            'playerSeason': compare(season_tot(rpg), season_tot(cpg), stats),
            'teamGames': compare(rtg, ctg, [k for k in stats if k != 'MIN'] + ['MIN']),
        }
    Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for c, v in out['candidates'].items():
        print(c)
        for layer, r in v.items():
            worst = {k: (f['r'], f['maxDiff'], f['mismatch']) for k, f in r['fields'].items()}
            print(f"  {layer}: common={r['common']} onlyRef={r['onlyRef']} onlyCand={r['onlyCand']} "
                  f"rowsBad={r['rowsAnyMismatch']} {worst}")


if __name__ == '__main__':
    main()
