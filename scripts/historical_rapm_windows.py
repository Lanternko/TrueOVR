"""RAPM windows and minutes for the v5 extended backtest chain (targets 2014-15 .. 2021-22).

  python3 -I scripts/historical_rapm_windows.py --stints <dir with <season>/stints.jsonl> \
      --box <dir with NocturneBear box csvs> --out reports/ovr-inseason-2026-27/v5/history

For each target season T it fits pooled RAPM with reports/impact-rapm/rapm.py (same model,
same lambda grid, same game-grouped cross-validation) on two season sets:
  predictor  T-4 .. T-1   newest RAPM available at season start, at most four seasons
  answer     T-3 .. T     includes the target season, at most four seasons
These are the general "at most four seasons" rules; whether the extended chain may reach
back before 2021-22 is still open (preregistration-v5 section 10, Q1).

Also writes per-season official box totals (minutes summed across teams for traded players,
plus one row per team) and gzipped per-game box scores for in-season checkpoints.
"""
import argparse, csv, glob, gzip, json, os, re, sys, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reports/impact-rapm'))
import rapm  # noqa: E402

SEASONS = [f'{y}-{(y + 1) % 100:02d}' for y in range(2010, 2024)]
TARGETS = [f'{y}-{(y + 1) % 100:02d}' for y in range(2014, 2022)]
STATS = [('FGM', 'fieldGoalsMade'), ('FGA', 'fieldGoalsAttempted'), ('FG3M', 'threePointersMade'),
         ('FG3A', 'threePointersAttempted'), ('FTM', 'freeThrowsMade'), ('FTA', 'freeThrowsAttempted'),
         ('OREB', 'reboundsOffensive'), ('DREB', 'reboundsDefensive'), ('REB', 'reboundsTotal'),
         ('AST', 'assists'), ('STL', 'steals'), ('BLK', 'blocks'), ('TOV', 'turnovers'),
         ('PF', 'foulsPersonal'), ('PTS', 'points'), ('PLUS_MINUS', 'plusMinusPoints')]


def mmss(v):
    m = re.match(r'^(\d+):(\d+)$', v or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def shift(season, k):
    y = int(season[:4]) + k
    return f'{y}-{(y + 1) % 100:02d}'


def write_box(box_dir, out):
    rows = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(box_dir, 'regular_season_box_scores_*.csv'))):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['season_year'] in SEASONS:
                rows[r['season_year']].append(r)
    names = {}
    for season, rs in rows.items():
        with gzip.open(out / f'box-games-{season}.csv.gz', 'wt', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['season', 'gameId', 'gameDate', 'teamId', 'playerId', 'name', 'starter', 'seconds'] + [k for k, _ in STATS])
            for r in sorted(rs, key=lambda r: (r['game_date'], r['gameId'], r['teamId'])):
                if not r['minutes']:
                    continue  # DNP rows
                w.writerow([season, f"{int(r['gameId']):010d}", r['game_date'], r['teamId'], r['personId'], r['personName'],
                            int(bool(r['position'])), mmss(r['minutes'])] + [r[c] or 0 for _, c in STATS])
        tot = defaultdict(lambda: defaultdict(float))
        for r in rs:
            if not r['minutes']:
                continue
            pid = int(r['personId']); names[pid] = r['personName']
            for key in (('ALL', pid), (int(r['teamId']), pid)):
                t = tot[key]; t['GP'] += 1; t['MIN'] += mmss(r['minutes']) / 60
                for k, c in STATS:
                    t[k] += float(r[c] or 0)
        with open(out / f'box-totals-{season}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['season', 'playerId', 'name', 'teamId', 'GP', 'MIN'] + [k for k, _ in STATS])
            for (team, pid), t in sorted(tot.items(), key=lambda kv: (kv[0][1], str(kv[0][0]))):
                w.writerow([season, pid, names[pid], 'ALL' if team == 'ALL' else team, int(t['GP']), round(t['MIN'], 3)] + [int(t[k]) for k, _ in STATS])
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stints', required=True)
    ap.add_argument('--box', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = write_box(a.box, out)
    reader = lambda s: open(os.path.join(a.stints, s, 'stints.jsonl'), encoding='utf-8')
    windows = {}
    for t in TARGETS:
        windows[('predictor', t)] = [shift(t, k) for k in range(-4, 0)]
        windows[('answer', t)] = [shift(t, k) for k in range(-3, 1)]
    fitted, summary = {}, {'targets': {}, 'windows': {}, 'prep': {}}
    for s in SEASONS:
        p = json.load(open(os.path.join(a.stints, s, 'preparation.json')))
        summary['prep'][s] = {k: p[k] for k in ('boxGames', 'pbpGames', 'validLineupGames', 'stints', 'pointsPer100', 'possessionsPerTeamGame', 'sources')}
    for (kind, t), seasons in windows.items():
        key = f'{seasons[0]}_{seasons[-1]}'
        summary['targets'].setdefault(t, {})[kind] = key
        if key in fitted:
            continue
        t0 = time.time()
        obs = list(rapm.observations(seasons, reader))
        players = sorted({p for o in obs for p in o[2] + o[3]})
        fit, info = rapm.fit_rapm(obs, players)
        fitted[key] = True
        with open(out / f'rapm-{key}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['playerId', 'name', 'net', 'O', 'D', 'poss'])
            for p in sorted(fit, key=lambda p: -fit[p]['net']):
                v = fit[p]
                w.writerow([p, names.get(p, ''), round(v['net'], 3), round(v['O'], 3), round(v['D'], 3), round(v['poss'])])
        summary['windows'][key] = {'seasons': seasons, 'observations': len(obs), 'players': len(players), **info}
        print(key, len(obs), len(players), info['lambda'], f'{time.time() - t0:.0f}s', flush=True)
    (out / 'summary.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
