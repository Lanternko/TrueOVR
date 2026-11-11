"""v5 §R.7：建 v5 版先驗卡（只換 MIN/GP，能力值不動）。

輸入：v4/v3 的既有 prior（不改原檔）
  v4/data/prior-2021-22.json、v3/data/prior-2022-23..2024-25.json、v4/data/prior-2025-26.json
輸出：v5/data/prior-<season>-v5.json + v5/data/priors-v5.json（SHA、來源、變動統計）

MIN/GP 來源見 minutes_v5.py：2021-22..2023-24 用 box-totals 的 teamId=ALL；
2024-25 用 player-games 逐隊加總；2025-26 用 season-league roster 逐隊 +=。
其餘欄位逐位不變（程式檢查 canonical hash 相同）。
"""
import copy
import hashlib
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

V5_DATA = C.REPORT / 'v5' / 'data'
PRIOR_SRC = {
    '2021-22': C.V4_DATA / 'prior-2021-22.json',
    '2022-23': C.V3_DATA / 'prior-2022-23.json',
    '2023-24': C.V3_DATA / 'prior-2023-24.json',
    '2024-25': C.V3_DATA / 'prior-2024-25.json',
    '2025-26': C.V4_DATA / 'prior-2025-26.json',
}


def canonical_without_minutes(doc):
    """把 MIN/GP/sample.min/sample.gp 歸零後的正規化 JSON（用來證明其他欄位沒動）。"""
    d = copy.deepcopy(doc)
    d.pop('v5Minutes', None)
    d.pop('note', None)
    for p in d.get('players', []):
        if 'observed' in p:
            p['observed']['MIN'] = 0
            p['observed']['GP'] = 0
        if p.get('sample') is not None:
            p['sample']['min'] = 0
            p['sample']['gp'] = 0
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def build(season):
    src = PRIOR_SRC[season]
    doc = json.load(open(src, encoding='utf-8'))
    before_hash = canonical_without_minutes(doc)
    mins = M.load_minutes(season)
    missing, changed = [], []
    for p in doc['players']:
        pid = int(p['playerId'])
        m = mins.get(pid)
        if m is None:
            missing.append(pid)
            continue
        old_min = float(p['observed']['MIN'])
        old_gp = float(p['observed'].get('GP', 0.0))
        p['observed']['MIN'] = m['MIN']
        p['observed']['GP'] = m['GP']
        if p.get('sample') is not None:
            p['sample']['min'] = m['MIN']
            p['sample']['gp'] = m['GP']
        if abs(old_min - m['MIN']) > 1e-9 or abs(old_gp - m['GP']) > 1e-9:
            changed.append({'playerId': pid, 'name': p.get('name', ''),
                            'oldMIN': old_min, 'newMIN': round(m['MIN'], 4),
                            'dMIN': round(m['MIN'] - old_min, 4),
                            'oldGP': old_gp, 'newGP': m['GP'],
                            'teams': m['teams']})
    after_hash = canonical_without_minutes(doc)
    desc = M.describe(season)
    doc['note'] = (doc.get('note', '') +
                   ' | v5 §R.7：MIN/GP 改為跨隊加總（' + desc['kind'] + '）。能力值未動。')
    doc['v5Minutes'] = {
        'rule': 'preregistration-v5 §R.7 第 1 條（2026-10-28 定案）：被交易球員分鐘數跨隊加總',
        'source': desc,
        'sourceSha256': C.sha256_file(M.SOURCE[season][1]),
        'playersUpdated': len(doc['players']) - len(missing),
        'playersMissingFromSource': missing,
        'changedPlayers': len(changed),
        'changedTradedPlayers': sum(1 for c in changed if c['teams'] > 1),
        'attrsUnchanged': before_hash == after_hash,
        'attrsHashBefore': before_hash,
        'attrsHashAfter': after_hash,
    }
    out = V5_DATA / f'prior-{season}-v5.json'
    C.write_json(out, doc)
    diffs = [c['dMIN'] for c in changed]
    return {
        'season': season,
        'source': desc,
        'sourceSha256': doc['v5Minutes']['sourceSha256'],
        'original': {'file': str(src.relative_to(C.ROOT)), 'sha256': C.sha256_file(src)},
        'output': {'file': str(out.relative_to(C.ROOT)), 'sha256': C.sha256_file(out)},
        'players': len(doc['players']),
        'changedPlayers': len(changed),
        'changedTradedPlayers': sum(1 for c in changed if c['teams'] > 1),
        'missing': missing,
        'attrsUnchanged': before_hash == after_hash,
        'dMIN': {'median': round(statistics.median(diffs), 4) if diffs else 0.0,
                 'max': round(max(diffs), 4) if diffs else 0.0,
                 'min': round(min(diffs), 4) if diffs else 0.0,
                 'maxAbs': round(max(abs(d) for d in diffs), 4) if diffs else 0.0},
        'changedPlayersDetail': sorted(changed, key=lambda c: -abs(c['dMIN'])),
    }


def main():
    V5_DATA.mkdir(parents=True, exist_ok=True)
    out = {s: build(s) for s in M.SEASONS}
    summary = {
        'spec': 'preregistration-v5 §R.7 第 1 條（跨隊加總）',
        'sourceNotes': {
            '2021-22..2023-24': 'v5/history/box-totals-<season>.csv 的 teamId=ALL',
            '2024-25': ('沒有 box-totals；整季 season-league roster 不存在'
                        '（calendar-82 v3-league 的 observed 只到約 60-69 場），'
                        '改用 data/defense-seventh/2024-25/player-games.json 逐場列按 (pid, team) 加總'),
            '2025-26': 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json 逐隊 +=',
        },
        'seasons': {s: {k: v[k] for k in ('source', 'sourceSha256', 'original', 'output',
                                          'players', 'changedPlayers', 'changedTradedPlayers',
                                          'missing', 'attrsUnchanged', 'dMIN')}
                    for s, v in out.items()},
        'changedTop10': {s: v['changedPlayersDetail'][:10] for s, v in out.items()},
        'pass': bool(all(v['attrsUnchanged'] and not v['missing'] for v in out.values())),
    }
    C.write_json(V5_DATA / 'priors-v5.json', summary)
    print(json.dumps({s: {k: v[k] for k in ('source', 'players', 'changedPlayers',
                                            'changedTradedPlayers', 'attrsUnchanged', 'dMIN')}
                      for s, v in out.items()}, ensure_ascii=False, indent=1))
    return 0 if summary['pass'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
