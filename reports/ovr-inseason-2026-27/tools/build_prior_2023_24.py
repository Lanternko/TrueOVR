"""P1：重建 2023-24 先驗卡片能力值（preregistration-v2.md §1.2 P1）。

build_prior_2024_25.py 的複本：只改 SEASON、OUT、PBP_MANIFEST 與 sanity 參考檔／校準季
（2023-24 參考卡是 defense-tenth/step3-a2 的 calibrate(cards, prior="2022-23") 產物，
因此撤校準要用 reports/defense-seventh/2022-23/calendar-55/calibration-v3.json）。

公式在 tools/season_attrs.py（S1/S2/S4 共用）；本檔負責 2023-24 的輸入、SHA 記錄、
覆蓋率與 personal-cards sanity 驗收，輸出 data/prior-2023-24.json。

資料來源限定 2023-24（與 2022-25 的四因子）：
  data/defense-seventh/<season>/player-games.json   逐場 boxscore
  data/defense-seventh/<season>/bio.json            身高/體重/AGE/AST_PCT/REB_PCT/USG_PCT
  data/defense-seventh/<season>/pbp/*.json          投籃區（mid/short）
  reports/defense-seventh/<season>/calendar-55/v3-league.json   onBall/help
  reports/player-impact-v30/dependence-audit.json   sourceReceived（creation；多季檔，按季取值）
  reports/ovr-v55-finisher-fix-2025-26/shot-origin.json  sTilde（E2；多季檔，按季取值）
  reports/ovr-inseason-2026-27/data/four-factors-2022-25.csv  tovNonSteal_defense（pressure）

用法：python reports/ovr-inseason-2026-27/tools/build_prior_2023_24.py
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import ATTRS, CURVES, DATA, ROOT, load_json, sha256_file, write_json
import season_attrs as SA

SEASON = '2023-24'
OUT = DATA / 'prior-2023-24.json'
PBP_MANIFEST = DATA / 'pbp-2023-24-sha256.txt'
SANITY_REF = ROOT / 'reports/defense-tenth/step3-a2/personal-cards/2023-24.json'
SANITY_CAL = ROOT / 'reports/defense-seventh/2022-23/calendar-55/calibration-v3.json'


def sanity_check(cards):
    """與 personal-cards/2023-24.json 比對（preregistration-v2 §6.2 P1 驗收）。

    參考檔是 prepare.mjs 的 calibrate(buildCards(target), prior) 產物，pairs=(2022-23, 2023-24)；
    參考卡的 long/mid/short 多套了一層 2022-23 的 shotDelta logistic 偏移。
    本先驗沒有這層；先把參考檔的 shotDelta 撤掉（等同對參考值再套 calibrate(·, −shotDelta)）再比。
    """
    from scipy.stats import spearmanr
    from diagnose_sanity_2024_25 import CURVE_OF, calibrate
    ref = {int(c['playerId']): c for c in load_json(SANITY_REF)['cards']}
    cal = load_json(SANITY_CAL)['selected']
    shot_delta = float(cal.get('shotDelta', 0.0))
    common = sorted(p for p in cards if p in ref)
    attrs = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'stamina']

    def med(xs):
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

    raw, uncal = {}, {}
    sp_ok = mad_ok = True
    for a in attrs:
        ours = [cards[p][a] for p in common]
        theirs_raw = [float(ref[p][a]) for p in common]
        if a in CURVE_OF:
            curve = CURVES[CURVE_OF[a]]
            theirs = [calibrate(v, curve, -shot_delta) for v in theirs_raw]
        else:
            theirs = theirs_raw
        raw[a] = {'spearman': round(float(spearmanr(ours, theirs_raw).statistic), 6),
                  'medianAbsDiff': round(med([abs(o - t) for o, t in zip(ours, theirs_raw)]), 6)}
        rho = float(spearmanr(ours, theirs).statistic)
        diff = med([abs(o - t) for o, t in zip(ours, theirs)])
        uncal[a] = {'spearman': round(rho, 6), 'medianAbsDiff': round(diff, 6)}
        sp_ok &= rho >= 0.90
        mad_ok &= diff <= 5.0
    return {'reference': str(SANITY_REF.relative_to(ROOT)),
            'referenceTransform': {
                'source': 'reports/defense-tenth/step3-a2/prepare.mjs::calibrate(cards, prior="2022-23")',
                'shotDelta': shot_delta,
                'shotDeltaFile': str(SANITY_CAL.relative_to(ROOT)),
                'appliesTo': ['long', 'mid', 'short'],
                'undo': 'calibrate(reference, -shotDelta) before comparison (v1 §9 rule)',
            },
            'n': len(common),
            'raw': raw,
            'attributes': uncal,
            'spearmanPass': bool(sp_ok), 'medianAbsDiffPass': bool(mad_ok)}


def main():
    sd = SA.load_season(SEASON)
    stats = SA.aggregate(sd)
    mapping = SA.build_mapping(sd, stats)
    cards = SA.compute_attrs(sd, stats, mapping)

    pbp_manifest_lines = [f'{p.stem} {sha256_file(p)}' for p in sorted(sd['paths']['pbp'].glob('*.json'))]
    PBP_MANIFEST.write_text('\n'.join(pbp_manifest_lines) + '\n', encoding='utf-8')

    sources = {
        'player-games': {'file': str(sd['paths']['box'].relative_to(ROOT)), 'sha256': sha256_file(sd['paths']['box'])},
        'bio': {'file': str(sd['paths']['bio'].relative_to(ROOT)), 'sha256': sha256_file(sd['paths']['bio'])},
        'team-games': {'file': str(sd['paths']['team_games'].relative_to(ROOT)),
                       'sha256': sha256_file(sd['paths']['team_games']),
                       'used': False, 'note': 'AST%/REB% 直接取 bio 官方欄位；逐場團隊量留給視窗公式'},
        'v3-league': {'file': str(sd['paths']['v3'].relative_to(ROOT)), 'sha256': sha256_file(sd['paths']['v3']),
                      'onBallHelpSource': 'defense-seventh-v3'},
        'dependence-audit': {'file': str(sd['paths']['dependence'].relative_to(ROOT)),
                             'sha256': sha256_file(sd['paths']['dependence']), 'season': SEASON,
                             'note': '多季檔；只取 season==2023-24 的列'},
        'shot-origin': {'file': str(sd['paths']['shot_origin'].relative_to(ROOT)),
                        'sha256': sha256_file(sd['paths']['shot_origin']), 'season': SEASON,
                        'note': '多季檔；只取 seasons["2023-24"]'},
        'four-factors': {'file': str(sd['paths']['four_factors'].relative_to(ROOT)),
                         'sha256': sha256_file(sd['paths']['four_factors']),
                         'seasons': SA.SEASONS},
        'pbp': {'dir': str(sd['paths']['pbp'].relative_to(ROOT)), 'files': len(pbp_manifest_lines),
                'manifest': str(PBP_MANIFEST.relative_to(ROOT)), 'manifestSha256': sha256_file(PBP_MANIFEST),
                'gamesWithPbp': len(sd['pbpGames']),
                'gamesWithoutPbp': sorted(sd['allGames'] - sd['pbpGames']), 'badFiles': sd['badPbp']},
        'upstream-scripts': {
            'four-factors.py': {'file': 'reports/impact-rapm/four-factors.py',
                                'sha256': sha256_file(ROOT / 'reports/impact-rapm/four-factors.py')},
            'rapm.py': {'file': 'reports/impact-rapm/rapm.py',
                        'sha256': sha256_file(ROOT / 'reports/impact-rapm/rapm.py')}},
    }

    players = sorted(cards)
    coverage = {}
    for a in ATTRS:
        vals = [cards[p].get(a) for p in players]
        coverage[a] = sum(1 for v in vals if v is not None and math.isfinite(float(v))) / len(vals)
    sanity = sanity_check(cards)
    missing = {
        'shot (no PBP attempts)': sorted(p for p in players if not any(k[0] == p for k in sd['shots'])),
        'bio weight': sorted(p for p in players if not float(sd['bio'][p]['PLAYER_WEIGHT'] or 0) > 0),
        'v3 (onBall/help fallback)': sorted(p for p in players if p not in sd['v3']),
        'shot-origin (E2 skipped)': sorted(p for p in players if p not in sd['fed']),
        'four-factors (pressure=0)': sorted(p for p in players if p not in sd['ff']),
    }
    validation = {
        'uniquePlayers': len(players),
        'uniquePlayersPass': len(players) >= 550,
        'poolPlayers': len(mapping['pool']),
        'coverage': coverage,
        'coveragePass': all(v >= 0.98 for v in coverage.values()),
        'missingCounts': {k: len(v) for k, v in missing.items()},
        'sanityVsPersonalCards': sanity,
        'pass': bool(len(players) >= 550 and all(v >= 0.98 for v in coverage.values())
                     and sanity['spearmanPass'] and sanity['medianAbsDiffPass']),
    }
    out = {
        'schemaVersion': 1,
        'season': SEASON,
        'note': '2023-24 v58 式先驗卡片（不含任何目標季資料），供 v2 跨季漂移與 S3 驗證季使用。',
        'priors': mapping['priors'],
        'poolRule': 'GP>=30 and MIN/GP>=20',
        'poolPlayers': len(mapping['pool']),
        'mappingPools': {k: [round(float(v), 10) for v in vals] for k, vals in mapping['pools'].items()},
        'poolPlayerIds': mapping['pool'],
        'methodology': {
            'curves': 'src/constants.js CURVE_3PT/CURVE_MID/CURVE_SHORT/CURVE_FT; '
                      'shooting = inverse((makes+100*leagueMean)/(attempts+100), curve)',
            'percentiles': 'scripts/build_season_league.js percentile()/attr()',
            'short': 'base short then v58 E2-lambda0.4: short = 70 + (base-70)*(sTilde + effLambda*(1-sTilde)); '
                     'sTilde = EB fed-share (shot-origin 2023-24, pseudoAttempts=25); '
                     'effLambda = 0.4+0.6*exempt, exempt=clip((creation-55)/10,0,1) for PF/C; '
                     'players absent from shot-origin keep base short (build-card-E.mjs behaviour)',
            'pass/rebound': 'bio AST_PCT/REB_PCT x100 (percentile mapping is invariant to the scale change)',
            'onBall/help': 'reports/defense-seventh/2023-24/calendar-55/v3-league.json (different model; '
                           'excluded from backtest main metrics per v1 §4.3)',
            'creation': '(1-sourceReceived)*FGA/MIN*36 percentile (dependence-audit 2023-24)',
            'pressure': 'tovNonSteal_defense percentile (four-factors-2022-25, same factor/algorithm)',
        },
        'shotOriginEB': sd['originMeta'],
        'sources': sources,
        'validation': validation,
        'missing': missing,
        'players': [cards[p] for p in players],
    }
    write_json(OUT, out)
    print(json.dumps({'out': str(OUT.relative_to(ROOT)), 'validation': validation,
                      'pbpGames': len(sd['pbpGames']),
                      'gamesWithoutPbp': sources['pbp']['gamesWithoutPbp']}, ensure_ascii=False, indent=2))
    return 0 if validation['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
