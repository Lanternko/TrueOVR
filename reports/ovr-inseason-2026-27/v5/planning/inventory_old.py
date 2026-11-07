"""v5 pre-registration: feasibility inventory for 2015-16 .. 2020-21 (read-only).

The first-round inventory.py covered 2021-22 .. 2025-26 only.  This script
answers the v5 question "can the start chain be extended backwards?" without
any network access: it checks the local archive, the fetch tools, and the
old-season aggregate references.

Output: reports/ovr-inseason-2026-27/v5/planning/inventory-old-seasons.json
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = Path(__file__).resolve().parent
SEASONS = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21']


def exists(rel):
    return (ROOT / rel).exists()


def count(rel, suffix='.json'):
    p = ROOT / rel
    if not p.exists():
        return 0
    return sum(1 for f in p.iterdir() if f.name.endswith(suffix))


def json_seasons(rel, key):
    try:
        doc = json.loads((ROOT / rel).read_text(encoding='utf-8'))
    except Exception:
        return None
    try:
        if key == 'teams':
            return sorted({v.get('season') for v in doc['teams'].values() if isinstance(v, dict)})
        if key == 'contexts':
            return [c.get('season') for c in doc['contexts']]
    except Exception:
        return None
    return None


def tool_info(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    text = p.read_text(encoding='utf-8')
    return {
        'seasonLiterals': sorted(set(re.findall(r"'20\d\d-\d\d'", text))),
        'argvSeason': bool(re.search(r'process\.argv', text)),
        'hardCoded1230': '1230' in text,
        'requiresV4Freeze': 'v4-freeze.json' in text,
    }


def repo_hits(season):
    """Files under data/ and reports/ whose text/name mentions the season."""
    hits = []
    for base in ('data', 'reports/impact-rapm', 'reports/ovr-inseason-2026-27'):
        root = ROOT / base
        if not root.exists():
            continue
        for f in root.rglob('*'):
            if not f.is_file():
                continue
            parts = set(f.parts)
            if parts & {'pbp', 'boxes', 'stints', '.git'}:
                continue
            if season in f.name:
                hits.append(str(f.relative_to(ROOT)))
                continue
            if f.suffix.lower() in ('.json', '.csv', '.md', '.py', '.js') \
                    and f.stat().st_size < 2_000_000:
                try:
                    if season in f.read_text(encoding='utf-8', errors='ignore'):
                        hits.append(str(f.relative_to(ROOT)))
                except Exception:
                    pass
    return sorted(hits)


out = {
    'generatedBy': 'reports/ovr-inseason-2026-27/v5/planning/inventory_old.py',
    'scope': 'local archive + tool source only; no network calls; no 2026-27 data',
    'seasons': {},
    'references': {
        'data/reference-seasons.json': json_seasons('data/reference-seasons.json', 'teams'),
        'data/league-context.json': json_seasons('data/league-context.json', 'contexts'),
        'data/benchmark-source': '2025-26 only (see inventory.json)',
    },
    'fetchTools': {
        rel: tool_info(rel) for rel in (
            'scripts/fetch_defense_seventh_season.js',
            'scripts/fetch_season_games.js',
            'scripts/fetch_benchmark_league.js',
            'scripts/fetch_league_context.js',
            'scripts/fetch_defense_a_pbp.js',
        )
    },
}

for s in SEASONS:
    d = f'data/defense-seventh/{s}'
    mentions = repo_hits(s)
    out['seasons'][s] = {
        'dirExists': exists(d),
        'pbp': count(f'{d}/pbp'),
        'boxes': count(f'{d}/boxes'),
        'bio': exists(f'{d}/bio.json'),
        'playerGames': exists(f'{d}/player-games.json'),
        'teamGames': exists(f'{d}/team-games.json'),
        'leagueSchedule': exists(f'{d}/league.json'),
        'gameExposure': exists(f'{d}/game-exposure.json'),
        'manifest': exists(f'{d}/manifest.json'),
        'stintsJsonl': count(f'reports/defense-seventh/{s}/stints', '.jsonl'),
        'shotOrigin': exists(f'reports/defense-seventh/{s}/shot-origin.json'),
        'dependenceAudit': exists(f'reports/defense-seventh/{s}/dependence-audit.json'),
        'seasonCards': exists(f'reports/ovr-inseason-2026-27/data/season-cards-{s}.json'),
        'v3OrV4Card': exists(f'reports/ovr-inseason-2026-27/v4/cards/{s}.csv')
                        or exists(f'reports/ovr-inseason-2026-27/v3/cards/{s}.csv'),
        'repoMentions': mentions[:12],
        'repoMentionCount': len(mentions),
    }

(PLAN / 'inventory-old-seasons.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=2)[:5000])
