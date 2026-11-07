"""P1：2021-22 座標版先驗卡與 season-cards（preregistration-v4 §3.4、§9 P1）。
另建 2025-26 先驗卡（S* 的 x0，§5.1；來源＝正式卡 card-H1-m0 的屬性，揭露為同源）。

2021-22：season_load_v4 的座標分區（mid 補回），其餘缺層照 P0 降級
（onBall/help=70、creation 的 received=0.5 為 v3 既有處理、short=shortBase）。
輸出 v4/data/prior-2021-22.json、v4/data/season-cards-2021-22.json、v4/data/prior-2025-26.json。
P1 驗收：mid 至少 50 個相異值；midA 聯盟合計與 P0 的規則重算一致；prior 與 season-cards 屬性差 <1e-9。
"""
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import season_attrs_v4 as SA
from season_load_v4 import load_season_v4
from ovr_common import ATTRS, load_json

OUTDIR = C.V4_DATA


def src(path, **kw):
    path = Path(path)
    d = {'file': str(path.relative_to(C.ROOT)), 'sha256': C.sha256_file(path)}
    d.update(kw)
    return d


def build_2021_22():
    season = '2021-22'
    sd = load_season_v4(season)
    stats = SA.aggregate(sd)
    raw = SA.raw_with_box(sd, stats)
    mapping = SA.build_mapping(sd, stats, raw)
    cards = SA.compute_attrs(sd, stats, mapping)

    pbp_manifest = OUTDIR / f'pbp-{season}-sha256.txt'
    lines = [f'{p.stem} {C.sha256_file(p)}' for p in sorted(sd['paths']['pbp'].glob('*.json'))]
    pbp_manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    sources = {
        'player-games': src(sd['paths']['box']),
        'bio': src(sd['paths']['bio']),
        'team-games': src(sd['paths']['team_games']),
        'four-factors': src(sd['ffSource'], scope='season-only'),
        'pbp': {'dir': str(sd['paths']['pbp'].relative_to(C.ROOT)), 'files': len(lines),
                'manifest': str(pbp_manifest.relative_to(C.ROOT)),
                'manifestSha256': C.sha256_file(pbp_manifest),
                'gamesWithPbp': len(sd['pbpGames']),
                'gamesWithoutPbp': sorted(sd['allGames'] - sd['pbpGames']), 'badFiles': sd['badPbp']},
        'v3-league': {'absent': True, 'fallback': 'onBall/help=70 (P0: tracking unavailable)'},
        'shot-origin': {'absent': True, 'fallback': 'short=shortBase; e2=None (P0)'},
        'dependence-audit': {'absent': True, 'fallback': 'sourceReceived=0.5 (P0)'},
        'mid-zone': {'rule': 'coordinate rule (xLegacy/yLegacy, §3.2)',
                     'evidence': 'v4/data/feasibility-2021-22-v4.json'},
    }
    players = sorted(cards)
    coverage = {a: sum(1 for p in players if cards[p].get(a) is not None
                       and math.isfinite(float(cards[p][a]))) / len(players) for a in ATTRS}
    missing = {
        'shot (no PBP attempts)': sorted(p for p in players if not any(k[0] == p for k in sd['shots'])),
        'bio weight': sorted(p for p in players if not float(sd['bio'][p]['PLAYER_WEIGHT'] or 0) > 0),
        'v3 (onBall/help fallback)': sorted(p for p in players if p not in sd['v3']),
        'shot-origin (E2 skipped)': sorted(p for p in players if p not in sd['fed']),
        'four-factors (pressure=0)': sorted(p for p in players if p not in sd['ff']),
    }
    validation = {
        'uniquePlayers': len(players),
        'uniquePlayersPass500': len(players) >= 500,
        'poolPlayers': len(mapping['pool']),
        'coverage': coverage,
        'coveragePass': all(v >= 0.98 for v in coverage.values()),
        'missingCounts': {k: len(v) for k, v in missing.items()},
        'pass': bool(len(players) >= 500 and all(v >= 0.98 for v in coverage.values())),
    }
    out = {
        'schemaVersion': 1, 'season': season,
        'note': 'v4 座標版：mid 由 §3.2 座標規則補回；其餘缺層照 P0 降級。',
        'priors': mapping['priors'],
        'poolRule': 'GP>=30 and MIN/GP>=20',
        'poolPlayers': len(mapping['pool']),
        'mappingPools': {k: [round(float(v), 10) for v in vals] for k, vals in mapping['pools'].items()},
        'poolPlayerIds': mapping['pool'],
        'methodology': {
            'curves': 'src/constants.js; shooting = inverse((makes+100*leagueMean)/(attempts+100), curve)',
            'percentiles': 'scripts/build_season_league.js percentile()/attr()',
            'short': 'v58 E2-lambda0.4; shot-origin absent -> shortBase',
            'pass/rebound': 'bio AST_PCT/REB_PCT x100',
            'onBall/help': 'absent -> 70',
            'creation': '(1-sourceReceived)*FGA/MIN*36; dependence absent -> 0.5 default (v3 沿用)',
            'pressure': 'tovNonSteal_defense percentile, same-season four-factors only',
            'mid/short zone': '2021-22 無 area -> 座標規則（半寬 80、前緣 y=138、哨兵(0,0)->short）',
        },
        'shotOriginEB': sd['originMeta'],
        'sources': sources,
        'validation': validation,
        'missing': missing,
        'players': [cards[p] for p in players],
    }
    path = OUTDIR / f'prior-{season}.json'
    C.write_json(path, out)

    # season-cards（同源；W 的視窗映射）
    sc_out = {
        'season': season,
        'note': 'v4 座標版 W 起點用；pass/rebound pool 由 box+team-games 公式重算。',
        'priors': mapping['priors'],
        'pools': {k: [round(float(v), 10) for v in vals] for k, vals in mapping['pools'].items()},
        'poolPlayerIds': mapping['pool'],
        'cards': {},
    }
    for pid, c in cards.items():
        c = dict(c)
        c['usg'] = SA._f(sd['bio'][pid]['USG_PCT'])
        sc_out['cards'][str(pid)] = c
    sc_path = OUTDIR / f'season-cards-{season}.json'
    C.write_json(sc_path, sc_out)

    # ---- P1 驗收
    fe = load_json(OUTDIR / 'feasibility-2021-22-v4.json')
    mid_a_total = sum(s['midA'] for s in stats.values())
    mid_vals = sorted({round(cards[p]['mid'], 6) for p in players})
    diff_attr = max(abs(float(cards[p][a]) - float(sc_out['cards'][str(p)][a]))
                    for p in players for a in ATTRS)
    checks = {
        'midDistinct>=50': len(mid_vals) >= 50,
        'midDistinct': len(mid_vals),
        'midATotal': mid_a_total,
        'midATotalRule': round(fe['apply2021_22']['midShare_rule'] * fe['apply2021_22']['twoPointers']),
        'midATotalMatch': abs(mid_a_total - fe['apply2021_22']['midShare_rule']
                             * fe['apply2021_22']['twoPointers']) <= 1.0,
        'priorVsSeasonCardsMaxAttrDiff': diff_attr,
        'priorVsSeasonCardsSame': diff_attr < 1e-9,
    }
    checks['pass'] = bool(checks['midDistinct>=50'] and checks['midATotalMatch']
                          and checks['priorVsSeasonCardsSame']
                          and validation['pass'])
    report = {'season': season,
              'prior': src(path), 'seasonCards': src(sc_path),
              'validation': validation, 'checks': checks}
    C.write_json(OUTDIR / 'p1-2021-22-check.json', report)
    return report


def build_2025_26():
    """S* 的 x0＝2025-26 全季卡；來源用正式卡 card-H1-m0/ranking.csv 的屬性（§6 參考卡同源）。

    playerId 由 v55 season-league 的 roster 以 name 對回；sample 用 roster 的 observed box
    可算的部分（midA/shortA/defensePossessions 無來源 → 0，僅供人員過濾與報告，不用於擬合）。
    """
    season = '2025-26'
    rank_path = C.ROOT / 'reports/ovr-v58-card-2025-26/card-H1-m0/ranking.csv'
    rows = C.load_csv(rank_path)
    league_path = C.ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
    league = load_json(league_path)
    roster = [p for t in league['teams'] for p in t['roster']]
    by_name = {}
    for p in roster:
        by_name.setdefault(p['name'], set()).add(int(p['playerId']))
    ambiguous = {k: sorted(v) for k, v in by_name.items() if len(v) > 1}
    players = []
    unmatched = []
    for r in rows:
        ids = by_name.get(r['name'])
        if not ids:
            unmatched.append(r['name'])
            continue
        pid = sorted(ids)[0]
        obs = next(p['observed'] for p in roster if int(p['playerId']) == pid)
        fga, fta = float(obs.get('FGA', 0)), float(obs.get('FTA', 0))
        ast, tov = float(obs.get('AST', 0)), float(obs.get('TOV', 0))
        players.append({
            'playerId': pid, 'name': r['name'], 'pos': r['pos'],
            'heightInches': float(r['heightInches']),
            'age': None,
            **{a: float(r[a]) for a in ATTRS},
            'shortBase': None, 'e2': None,
            'sample': {'fg3a': float(obs.get('FG3A', 0)), 'midA': 0.0, 'shortA': 0.0,
                       'fta': fta, 'fga': fga, 'possDen': fga + 0.44 * fta + ast + tov,
                       'min': float(obs.get('MIN', 0)), 'gp': float(obs.get('GP', 0)),
                       'defensePossessions': 0.0},
            'observed': {k: float(v) for k, v in obs.items()} | {'GP': float(obs.get('GP', 0))},
        })
    out = {
        'schemaVersion': 1, 'season': season,
        'note': 'S* 的 x0＝2025-26 正式卡屬性（card-H1-m0/ranking.csv，同源；揭露於 §6 與報告）。'
                'playerId/observed 由 v55 season-league roster 以 name 對回。'
                'sample 的 midA/shortA/defensePossessions 無來源（2025-26 的 zone/防守回合未在該檔），記 0，'
                '不參與任何擬合。',
        'sources': {'formalCard': src(rank_path), 'seasonLeague': src(league_path)},
        'priors': None,
        'mappingPools': None,
        'validation': {'rows': len(players), 'pass500': len(players) >= 500,
                       'unmatched': unmatched, 'ambiguousNames': ambiguous},
        'players': players,
    }
    path = OUTDIR / f'prior-{season}.json'
    C.write_json(path, out)
    return {'prior': src(path), 'validation': out['validation']}


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    a = build_2021_22()
    b = build_2025_26()
    print(json.dumps({'2021-22': {'checks': a['checks'], 'validation': a['validation']['pass']},
                      '2025-26': b['validation']}, ensure_ascii=False, indent=1))
    return 0 if a['checks']['pass'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
