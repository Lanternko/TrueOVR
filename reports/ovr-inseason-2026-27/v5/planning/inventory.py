"""v5 preregistration data-feasibility inventory (read-only).

Scans the local archive for every layer the v4 spec depended on, per season
2021-22 .. 2025-26, and records fetch-tool hard-coded seasons.  No network.

Output: reports/ovr-inseason-2026-27/v5/planning/inventory.json
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = Path(__file__).resolve().parent
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return None


def count(dirpath, suffix='.json'):
    p = ROOT / dirpath
    if not p.exists():
        return 0
    return sum(1 for f in p.iterdir() if f.name.endswith(suffix))


def pbp_shot_fields(prefix):
    """Per-season coverage of the shot fields v4 used (area, xLegacy/yLegacy)."""
    p = ROOT / f'data/defense-seventh/{prefix}/pbp'
    if not p.exists():
        return None
    games = sorted(p.iterdir())
    n2, area, xy, sentinel = 0, 0, 0, 0
    sample = games[0].name if games else None
    for f in games:
        doc = load(f)
        if not doc:
            continue
        for a in doc['data']['game']['actions']:
            if a.get('actionType') not in ('2pt', '3pt'):
                continue
            n2 += 1
            if a.get('area'):
                area += 1
            x = a.get('xLegacy')
            y = a.get('yLegacy')
            if x is not None and y is not None:
                xy += 1
                if abs(x) <= 1e-9 and abs(y) <= 1e-9:
                    sentinel += 1
    return {'pbpGames': len(games), 'sampleGame': sample, 'shotActions': n2,
            'withArea': area, 'withXY': xy, 'sentinelXY': sentinel,
            'areaRate': round(area / n2, 6) if n2 else None,
            'xyRate': round(xy / n2, 6) if n2 else None}


def bio_columns(prefix):
    p = ROOT / f'data/defense-seventh/{prefix}/bio.json'
    doc = load(p)
    if not doc:
        return None
    sets = doc.get('data', {}).get('resultSets') or []
    if isinstance(sets, list) and sets:
        return {'headers': sets[0].get('headers'), 'rows': len(sets[0].get('rowSet', []))}
    return {'headers': None, 'rows': None}


def tool_seasons(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8')
    seasons = sorted(set(re.findall(r"'20\d\d-\d\d'", text)))
    hard = re.findall(r"(?:const|let|var)\s+season\s*=\s*'([^']+)'", text)
    return {'hardCodedSeasonVar': hard[:3], 'seasonLiterals': seasons}


out = {'generatedBy': 'reports/ovr-inseason-2026-27/v5/planning/inventory.py',
       'scope': 'local archive only; no network calls', 'seasons': {}}

for s in SEASONS:
    d = f'data/defense-seventh/{s}'
    out['seasons'][s] = {
        'pbp': count(f'{d}/pbp'),
        'boxes': count(f'{d}/boxes'),
        'stints_local': count(f'reports/defense-seventh/{s}/stints', '.jsonl'),
        'bio': (ROOT / f'{d}/bio.json').exists(),
        'bioColumns': bio_columns(s),
        'playerGames': (ROOT / f'{d}/player-games.json').exists(),
        'teamGames': (ROOT / f'{d}/team-games.json').exists(),
        'leagueSchedule': (ROOT / f'{d}/league.json').exists(),
        'gameExposure': (ROOT / f'{d}/game-exposure.json').exists(),
        'manifest': (ROOT / f'{d}/manifest.json').exists(),
        'shotFields': pbp_shot_fields(s),
        'shotOrigin': (ROOT / f'reports/defense-seventh/{s}/shot-origin.json').exists(),
        'dependenceAudit': (ROOT / f'reports/defense-seventh/{s}/dependence-audit.json').exists(),
        'cards': (ROOT / f'reports/ovr-inseason-2026-27/v4/cards/c_{s}.csv').exists(),
    }

# Layer-level files independent of season directories.
out['globalLayers'] = {
    'benchmarkSourceFiles': sorted(f.name for f in (ROOT / 'data/benchmark-source').glob('*.json')),
    'benchmarkSourcePlayerLevel': [n for n in ('base.json', 'advanced.json', 'bio.json', 'shots.json',
                                               'defense-long.json', 'defense-rim.json', 'teams.json')
                                   if (ROOT / 'data/benchmark-source' / n).exists()],
    'seasonSourceFiles': sorted(f.name for f in (ROOT / 'data/season-source').glob('*.json'))[:8],
    'defenseASourcePbp': count('data/defense-a-source/pbp'),
    'defenseFifthSource': sorted(x.name for x in (ROOT / 'data/defense-fifth-source').iterdir())
    if (ROOT / 'data/defense-fifth-source').exists() else [],
    'v4RapmOutputs': sorted(f.name for f in (ROOT / 'reports/ovr-inseason-2026-27/v4/data').glob('rapm*')),
    'v4Cards': sorted(f.name for f in (ROOT / 'reports/ovr-inseason-2026-27/v4/cards').glob('*.csv')),
    'v4PriorFiles': sorted(f.name for f in (ROOT / 'reports/ovr-inseason-2026-27/v4').rglob('prior*')),
}

out['fetchTools'] = {
    'scripts/fetch_defense_a_pbp.js': tool_seasons('scripts/fetch_defense_a_pbp.js'),
    'scripts/fetch_season_games.js': tool_seasons('scripts/fetch_season_games.js'),
    'scripts/fetch_defense_seventh_season.js': tool_seasons('scripts/fetch_defense_seventh_season.js'),
    'scripts/fetch_benchmark_league.js': tool_seasons('scripts/fetch_benchmark_league.js'),
    'scripts/fetch_league_context.js': tool_seasons('scripts/fetch_league_context.js'),
}

(PLAN / 'inventory.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
