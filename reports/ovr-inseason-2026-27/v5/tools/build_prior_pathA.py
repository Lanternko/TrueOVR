"""Path A 先驗卡、season-cards、答案卡（preregistration-v5 §4.7、§5.2、errata-c4 §6 第 2 步）。

先驗卡 prior-<S>：照 build_prior_v4.build_2021_22 的流程，逐季通用（pathA_common.load_season_pa）。
缺層照 §5.6：onBall/help=70、creation 的 received 用 v3 既有預設、short=shortBase、mid 座標規則。
沒有 bio 的球員 compute_attrs 直接略過（不用現代身高體重回填）。

答案卡 cards/<target>.csv：凍結 v58 H1-m0 管線吃 prior-<target> 的全季能力值，RAPM 用 §5.2 表的答案窗口
（含目標季）。2015-16 的答案卡是 Y0 的，只為完整記錄；Y0 沒有先驗卡、不出預測。

輸出 v5/pathA/data/{prior,season-cards}-<S>.json、v5/pathA/cards/<S>.csv、v5/pathA/data/build-check.json。
驗收（只記錄，人數 <500 不停）：屬性覆蓋率 ≥0.98、prior 與 season-cards 屬性差 <1e-9、答案卡人數＝先驗卡人數。
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
from ovr_common import ATTRS, load_json  # noqa: E402
from ovr_pipeline import OVRPipeline  # noqa: E402

ANSWER_TAG = {v['target']: v['ans'] for v in PA.CHAIN_Y.values()}


def src(path, **kw):
    path = Path(path)
    d = {'file': str(path.relative_to(C.ROOT)), 'sha256': C.sha256_file(path)}
    d.update(kw)
    return d


def build_prior(season):
    sd = PA.load_season_pa(season)
    stats = SA.aggregate(sd)
    raw = SA.raw_with_box(sd, stats)
    mapping = SA.build_mapping(sd, stats, raw)
    cards = SA.compute_attrs(sd, stats, mapping)

    manifest = PA.PA_DATA / f'pbp-{season}-sha256.txt'
    lines = [f'{p.stem} {C.sha256_file(p)}' for p in sorted(sd['paths']['pbp'].glob('*.json'))]
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    sources = {
        'player-games': src(sd['paths']['box']),
        'bio': src(sd['paths']['bio']),
        'team-games': src(sd['paths']['team_games']),
        'four-factors': src(sd['ffSource'], scope='season-only'),
        'pbp': {'dir': str(sd['paths']['pbp'].relative_to(C.ROOT)), 'files': len(lines),
                'manifest': str(manifest.relative_to(C.ROOT)),
                'manifestSha256': C.sha256_file(manifest),
                'gamesWithPbp': len(sd['pbpGames']),
                'gamesWithoutPbp': sorted(sd['allGames'] - sd['pbpGames']), 'badFiles': sd['badPbp']},
        'v3-league': {'absent': True, 'fallback': 'onBall/help=70 (§5.6 tracking missing)'},
        'shot-origin': {'absent': True, 'fallback': 'short=shortBase; e2=None (§5.6)'},
        'dependence-audit': {'absent': True, 'fallback': 'v3 default received (§5.6); window creation=x0'},
        'mid-zone': {'rule': 'coordinate rule (xLegacy/yLegacy), same as v4 2021-22'},
    }
    players = sorted(cards)
    box_pids = set(sd['box'])
    coverage = {a: sum(1 for p in players if cards[p].get(a) is not None
                       and math.isfinite(float(cards[p][a]))) / len(players) for a in ATTRS}
    missing = {
        'no bio (skipped, no card)': sorted(p for p in box_pids if p not in sd['bio']),
        'shot (no PBP attempts)': sorted(p for p in players if not any(k[0] == p for k in sd['shots'])),
        'bio weight': sorted(p for p in players if not float(sd['bio'][p]['PLAYER_WEIGHT'] or 0) > 0),
        'four-factors (pressure=0)': sorted(p for p in players if p not in sd['ff']),
    }
    validation = {
        'uniquePlayers': len(players),
        'uniquePlayersPass500': len(players) >= 500,
        'poolPlayers': len(mapping['pool']),
        'coverage': coverage,
        'coveragePass': all(v >= 0.98 for v in coverage.values()),
        'missingCounts': {k: len(v) for k, v in missing.items()},
        'fallbackAllPlayers': ['onBall=70', 'help=70', 'short=shortBase', 'creation received=v3 default'],
    }
    pools = {k: [round(float(v), 10) for v in vals] for k, vals in mapping['pools'].items()}
    out = {
        'schemaVersion': 1, 'season': season,
        'note': 'v5 Path A：v4 座標版流程逐季通用；缺層照 §5.6 降級。',
        'priors': mapping['priors'], 'poolRule': 'GP>=30 and MIN/GP>=20',
        'poolPlayers': len(mapping['pool']), 'mappingPools': pools, 'poolPlayerIds': mapping['pool'],
        'shotOriginEB': sd['originMeta'], 'sources': sources, 'validation': validation,
        'missing': missing, 'players': [cards[p] for p in players],
    }
    path = PA.PA_DATA / f'prior-{season}.json'
    C.write_json(path, out)

    sc = {'season': season, 'note': 'Path A 視窗映射（同源）', 'priors': mapping['priors'],
          'pools': pools, 'poolPlayerIds': mapping['pool'], 'cards': {}}
    for pid, c in cards.items():
        c = dict(c)
        c['usg'] = SA._f(sd['bio'][pid]['USG_PCT'])
        sc['cards'][str(pid)] = c
    sc_path = PA.PA_DATA / f'season-cards-{season}.json'
    C.write_json(sc_path, sc)
    diff = max(abs(float(cards[p][a]) - float(sc['cards'][str(p)][a])) for p in players for a in ATTRS)
    return {'prior': src(path), 'seasonCards': src(sc_path), 'validation': validation,
            'priorVsSeasonCardsMaxAttrDiff': diff, 'midDistinct': len({round(cards[p]['mid'], 6) for p in players})}


def build_answer(season):
    doc = load_json(PA.PA_DATA / f'prior-{season}.json')
    by_pid = {int(c['playerId']): c for c in doc['players']}
    rapm = PA.PA_RAPM / f'pipe-{ANSWER_TAG[season]}.csv'
    pipe = OVRPipeline(str(C.V2.FROZEN_SUMMARY), str(rapm), by_pid)
    attrs = {pid: {a: float(c[a]) for a in ATTRS} for pid, c in by_pid.items()}
    pred = pipe.predict(attrs)
    rows = []
    for pid in sorted(by_pid):
        r = pred[pid]
        rows.append({
            'playerId': pid, 'name': by_pid[pid].get('name', ''), 'pos': by_pid[pid]['pos'],
            'ovr': round(r['ovr'], 4), 'pred': round(r['pred'], 6), 'pred0': round(r['pred0'], 6),
            'bonus': round(r['bonus'], 6), 'align': round(r['align'], 6),
            'MIN_season': round(float(by_pid[pid]['observed']['MIN']), 1),
            'attrSource': 'pathA-prior', 'rapm': ANSWER_TAG[season],
            **{a: round(attrs[pid][a], 4) for a in ATTRS},
        })
    out = PA.PA_CARDS / f'{season}.csv'
    C.write_csv(out, rows)
    ovrs = sorted(r['ovr'] for r in rows)
    return {'card': src(out), 'rapm': src(rapm), 'rows': len(rows),
            'ovrMedian': ovrs[len(ovrs) // 2], 'ovrMin': ovrs[0], 'ovrMax': ovrs[-1]}


def main():
    PA.PA_DATA.mkdir(parents=True, exist_ok=True)
    PA.PA_CARDS.mkdir(parents=True, exist_ok=True)
    seasons = sys.argv[1:] or PA.PA_SEASONS
    report = {}
    for s in seasons:
        rep = build_prior(s)
        rep['answer'] = build_answer(s)
        rep['answerRowsMatchPrior'] = rep['answer']['rows'] == rep['validation']['uniquePlayers']
        report[s] = rep
        v = rep['validation']
        print(s, v['uniquePlayers'], 'cov', v['coveragePass'], 'mid', rep['midDistinct'],
              'diff', rep['priorVsSeasonCardsMaxAttrDiff'], 'ans', rep['answer']['rows'],
              rep['answer']['ovrMedian'], flush=True)
    check_path = PA.PA_DATA / 'build-check.json'
    old = {}
    if check_path.exists():
        old = load_json(check_path)
    old.update(report)
    C.write_json(check_path, old)
    return 0


if __name__ == '__main__':
    sys.exit(main())
