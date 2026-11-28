"""P1b：把 RAPM 集擴到 2024-25（S* 的預測用；preregistration-v4 §5.1）。

演算法與 v3/tools/rapm_expanding.py 相同（沿用 tools/rapm_2022_25.py 的 ridge/CV，不改原檔）：
  v4/data/rapm-2021-22_2024-25.csv   for S*（最大季 2024-25，不含 2026-27）
驗收：
  1. 檔名最大季 = 2024-25；
  2. 用同一支工具重算 v3 既有的 rapm-2021-22_2023-24.csv，係數差 <1e-9（可重現、不是新算法）；
  3. SHA 記錄。
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import rapm_2022_25 as R

HEAD = ['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss',
        'lastSeasonNet', 'lastSeasonO', 'lastSeasonD', 'lastSeasonPoss']
SETS = {
    '2021-22_2023-24': ['2021-22', '2022-23', '2023-24'],        # 只為重現性檢查
    '2021-22_2024-25': ['2021-22', '2022-23', '2023-24', '2024-25'],
}


def lines(season):
    path = (C.V3_DATA / 'derived-2021-22/stints/stints.jsonl' if season == '2021-22'
            else R.stint_path(season))
    with open(path, encoding='utf-8') as fh:
        return fh.readlines()


def build(tag, seasons, outdir=C.V4_DATA):
    obs = list(R.observations(seasons, reader=lambda s: lines(s)))
    players = sorted({p for o in obs for p in o[2] + o[3]})
    pooled, info = R.fit_rapm(obs, players)
    last = [o for o in obs if o[0] == seasons[-1]]
    single, sinfo = R.fit_rapm(last, sorted({p for o in last for p in o[2] + o[3]}))
    out = outdir / f'rapm-{tag}.csv'
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        for p in sorted(pooled, key=lambda p: -pooled[p]['net']):
            a, s = pooled[p], single.get(p, {})
            w.writerow([p, '', round(a['net'], 3), round(a['O'], 3), round(a['D'], 3), round(a['poss']),
                        round(s.get('net', 0), 3), round(s.get('O', 0), 3),
                        round(s.get('D', 0), 3), round(s.get('poss', 0))])
    meta = {'file': str(out.relative_to(C.ROOT)), 'seasons': seasons, 'maxSeason': max(seasons),
            'observations': len(obs), 'players': len(players), 'pooled': info,
            'lastSeason': sinfo, 'sha256': C.sha256_file(out)}
    return out, meta


def compare(path_a, path_b):
    """逐 playerId 比較 4 個係數欄的最大絕對差。"""
    def load(p):
        return {int(r['playerId']): r for r in C.load_csv(p)}
    a, b = load(path_a), load(path_b)
    common = sorted(set(a) & set(b))
    cols = ['pooledNet', 'pooledO', 'pooledD', 'lastSeasonNet', 'lastSeasonO', 'lastSeasonD']
    mx = 0.0
    for pid in common:
        for c in cols:
            mx = max(mx, abs(float(a[pid][c]) - float(b[pid][c])))
    return {'n': len(common), 'onlyA': len(set(a) - set(b)), 'onlyB': len(set(b) - set(a)),
            'maxAbsDiff': mx, 'identical': bool(mx < 1e-9 and set(a) == set(b))}


def main():
    C.V4_DATA.mkdir(parents=True, exist_ok=True)
    tmp = C.V4_DATA / '_repro'
    tmp.mkdir(exist_ok=True)
    _, repro = build('2021-22_2023-24', SETS['2021-22_2023-24'], outdir=tmp)
    chk = compare(tmp / 'rapm-2021-22_2023-24.csv', C.V3_DATA / 'rapm-2021-22_2023-24.csv')
    if chk['identical']:
        (tmp / 'rapm-2021-22_2023-24.csv').unlink()
        tmp.rmdir()
    out, meta = build('2021-22_2024-25', SETS['2021-22_2024-25'])
    report = {
        'spec': 'preregistration-v4 §5.1 / P1b',
        'reproducibilityVsV3': {**chk, 'ref': 'v3/data/rapm-2021-22_2023-24.csv',
                                'refSha256': C.sha256_file(C.V3_DATA / 'rapm-2021-22_2023-24.csv'),
                                'recomputedSha256': repro['sha256']},
        'maxSeasonIs2024_25': meta['maxSeason'] == '2024-25',
        'set': meta,
        'inputs': {'stints-2021-22': C.sha256_file(C.V3_DATA / 'derived-2021-22/stints/stints.jsonl'),
                   **{f'stints-{s}': C.sha256_file(R.stint_path(s))
                      for s in SETS['2021-22_2024-25'] if s != '2021-22'}},
    }
    report['pass'] = bool(chk['identical'] and report['maxSeasonIs2024_25'])
    C.write_json(C.V4_DATA / 'rapm-v4.json', report)
    print(json.dumps({'repro': {k: chk[k] for k in ('n', 'maxAbsDiff', 'identical')},
                      'new': {k: meta[k] for k in ('file', 'maxSeason', 'players', 'observations',
                                                   'sha256')}, 'pass': report['pass']},
                     ensure_ascii=False, indent=1))
    return 0 if report['pass'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
