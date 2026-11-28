"""第 1 步查證：現有 prior 與答案卡的 MIN 是否跨隊加總。

對每季輸出：
  - 被交易球員人數（來源的分隊紀錄 >1）
  - 現有 prior MIN vs 來源整季合計 MIN 的差（中位、最大、前 10 名）
  - 現有 prior MIN vs「只取第一筆 roster 紀錄」的差（證明是不是只取第一隊）
  - 答案卡（v4 與 v5 卡）MIN 與來源合計的差
輸出 v5/data/minutes-audit.json、minutes-audit-prior.csv、minutes-audit-cards.csv。
"""
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
sys.path.insert(0, str(HERE.parents[2] / 'tools'))
import minutes_v5 as M  # noqa: E402
import v4_common as C  # noqa: E402
import build_prior_v5 as P  # noqa: E402

V5_DATA = C.REPORT / 'v5' / 'data'
V5_CARDS = C.REPORT / 'v5' / 'cards'


def stats(diffs):
    if not diffs:
        return {'n': 0}
    a = sorted(abs(d) for d in diffs)
    return {'n': len(diffs),
            'medianSigned': round(statistics.median(diffs), 4),
            'medianAbs': round(statistics.median(a), 4),
            'maxAbs': round(max(a), 4),
            'nAbsGt1': sum(1 for v in a if v > 1.0),
            'nAbsGt5': sum(1 for v in a if v > 5.0)}


def audit_prior(season):
    doc = json.load(open(P.PRIOR_SRC[season], encoding='utf-8'))
    by = {int(p['playerId']): p for p in doc['players']}
    mins = M.load_minutes(season)
    first = M.first_record_minutes(season)
    traded = sorted(pid for pid, m in mins.items() if m['teams'] > 1)
    rows = []
    for pid in sorted(by):
        m = mins.get(pid)
        if m is None:
            continue
        f = first.get(pid, {'MIN': None, 'GP': None, 'team': None})
        rows.append({
            'season': season, 'playerId': pid, 'name': by[pid].get('name', ''),
            'teams': m['teams'], 'traded': m['teams'] > 1,
            'priorMIN': round(float(by[pid]['observed']['MIN']), 4),
            'priorGP': float(by[pid]['observed'].get('GP', 0.0)),
            'sourceMIN': round(m['MIN'], 4), 'sourceGP': m['GP'],
            'dMIN': round(float(by[pid]['observed']['MIN']) - m['MIN'], 4),
            'firstRecordMIN': None if f['MIN'] is None else round(f['MIN'], 4),
            'firstRecordTeam': f['team'],
            'dFirstRecord': (round(float(by[pid]['observed']['MIN']) - f['MIN'], 4)
                             if f['MIN'] is not None else None),
        })
    traded_rows = [r for r in rows if r['traded']]
    all_d = [r['dMIN'] for r in rows]
    traded_d = [r['dMIN'] for r in traded_rows]
    first_d = [r['dFirstRecord'] for r in traded_rows if r['dFirstRecord'] is not None]
    return {
        'season': season, 'source': M.describe(season),
        'players': len(rows), 'tradedPlayers': len(traded_rows),
        'allPlayers': stats(all_d), 'tradedPlayersDiff': stats(traded_d),
        'tradedVsFirstRecordOnly': stats(first_d),
        'top10TradedAbsDiff': sorted(traded_rows, key=lambda r: -abs(r['dMIN']))[:10],
        'top10AllAbsDiff': sorted(rows, key=lambda r: -abs(r['dMIN']))[:10],
        '_rows': rows,
    }


def audit_card(season, path, label):
    if not path.exists():
        return {'season': season, 'card': label, 'missing': str(path)}
    rows = C.load_csv(path)
    by = {int(r['playerId']): r for r in rows}
    mins = M.load_minutes(season)
    traded = sorted(pid for pid, m in mins.items() if m['teams'] > 1)
    out = []
    for pid in sorted(by):
        if pid not in mins:
            continue
        card_min = float(by[pid]['MIN_season'])
        out.append({'season': season, 'card': label, 'playerId': pid,
                    'name': by[pid]['name'], 'teams': mins[pid]['teams'],
                    'traded': mins[pid]['teams'] > 1,
                    'cardMIN': round(card_min, 4), 'sourceMIN': round(mins[pid]['MIN'], 4),
                    'dMIN': round(card_min - mins[pid]['MIN'], 4)})
    t = [r for r in out if r['traded']]
    return {'season': season, 'card': label, 'file': str(path.relative_to(C.ROOT)),
            'players': len(out), 'tradedPlayers': len(t),
            'tradedPlayersDiff': stats([r['dMIN'] for r in t]),
            'allPlayersDiff': stats([r['dMIN'] for r in out]),
            'top10TradedAbsDiff': sorted(t, key=lambda r: -abs(r['dMIN']))[:10],
            '_rows': out}


def main():
    V5_DATA.mkdir(parents=True, exist_ok=True)
    priors, prior_rows = {}, []
    for s in M.SEASONS:
        a = audit_prior(s)
        prior_rows.extend(a.pop('_rows'))
        priors[s] = a
    cards = {}
    for season, v4, v5 in [('2023-24', C.V4_CARDS / '2023-24.csv', V5_CARDS / '2023-24-v5.csv'),
                           ('2024-25', C.V4_CARDS / '2024-25.csv', V5_CARDS / '2024-25-v5.csv')]:
        cards[season] = {'v4card': audit_card(season, v4, 'v4'),
                         'v5card': audit_card(season, v5, 'v5')}
    cross = {s: M.cross_check(s, 'player-games') for s in ('2022-23', '2023-24')}
    out = {
        'spec': 'preregistration-v5 §R.7 第 1 條查證（2026-10-28）',
        'question': '既有 prior 與答案卡的 MIN 是否跨隊加總？',
        'priors': priors,
        'answerCards': cards,
        'twoSourceCrossCheck': cross,
        'sourceNotes': {
            'box-totals': 'v5/history/box-totals-<season>.csv，teamId=ALL 已跨隊加總',
            '2024-25': 'player-games 逐場列按 (pid, team) 加總（player-games 無 box-totals）',
            '2025-26': 'season-league E2 roster 逐隊 +=',
        },
    }
    C.write_json(V5_DATA / 'minutes-audit.json', out)
    C.write_csv(V5_DATA / 'minutes-audit-prior.csv', prior_rows,
                head=['season', 'playerId', 'name', 'teams', 'traded', 'priorMIN', 'priorGP',
                      'sourceMIN', 'sourceGP', 'dMIN', 'firstRecordMIN', 'firstRecordTeam',
                      'dFirstRecord'])
    card_rows = []
    for c in cards.values():
        for k in ('v4card', 'v5card'):
            card_rows.extend(c[k].get('_rows', []))
    C.write_csv(V5_DATA / 'minutes-audit-cards.csv', card_rows,
                head=['season', 'card', 'playerId', 'name', 'teams', 'traded', 'cardMIN',
                      'sourceMIN', 'dMIN'])
    brief = {s: {k: v[k] for k in ('source', 'players', 'tradedPlayers',
                                   'tradedPlayersDiff', 'tradedVsFirstRecordOnly')}
             for s, v in priors.items()}
    print(json.dumps({'priors': brief, 'crossCheck': cross,
                      'cards': {s: {k: v[k]['tradedPlayersDiff'] for k in ('v4card', 'v5card')}
                                for s, v in cards.items()}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
