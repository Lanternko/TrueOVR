"""E-101 改動一（預註冊 §1）：PBP 投籃區重產。複製自 reports/ovr-v61-shrink-history-2025-26/extract_pbp.py，只保留 zones 部分（drive 不動）。

規則（唯一改動）：actionType=='2pt'、isFieldGoal==1、area=='Mid-Range'，但 shotDistance < 8 的出手改歸 short。其他照 V61：
  area == 'Mid-Range' → mid；'Restricted Area' 或 'In The Paint (Non-RA)' → short；其餘（含 corner／above-the-break 的 2pt 罕見值）不計。
  shotDistance 缺值：照 diag/area_count.py 的 `a.get('shotDistance') or 0.0`（缺值視為 0 呎），以便和 area-count.txt 的 lt8 對得上；缺值筆數另記。
同一趟同時產出：
  - 未修正版（work/tmp/pbp-zones-<季>-v61repro.csv.gz）：必須和 V61 history/pbp-zones-<季>.csv.gz 逐位元相同（sha256），列數與合計另記。
  - 修正版（history/pbp-zones-<季>.csv.gz，欄位同原檔：gameId, playerId, midA, midM, shortA, shortM）。
  - 每季被移走的出手（attempts／made），和 diag/area-count.txt 的 lt8 比對。
單程序依序讀檔（不開子程序，不閃窗）。決定性：依 (gameId, playerId) 排序，gzip mtime=0。
輸出：zones-check.json。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/extract_pbp_e101.py
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
from lib import write_gz_csv, read_gz_csv, sha256, ZONE_SEASONS, TEST_SEASON, MANIFEST_A, SEVENTH, HIST  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FIX_DIST = 8.0
HEADER = ['gameId', 'playerId', 'midA', 'midM', 'shortA', 'shortM']


def parse_game(path):
    acts = json.loads(Path(path).read_text(encoding='utf-8'))['data']['game']['actions']
    zo = defaultdict(lambda: [0, 0, 0, 0])   # 未修正（V61）
    zf = defaultdict(lambda: [0, 0, 0, 0])   # 修正
    moved = [0, 0]
    missing = 0
    for a in acts:
        if a['actionType'] != '2pt':
            continue
        made = a.get('shotResult') == 'Made'
        if a.get('isFieldGoal') == 1:
            area = a.get('area')
            z = 0 if area == 'Mid-Range' else 2 if area in ('Restricted Area', 'In The Paint (Non-RA)') else None
            if z is None:
                continue
            zo[a['personId']][z] += 1
            zo[a['personId']][z + 1] += made
            zf_ = z
            if area == 'Mid-Range':
                if a.get('shotDistance') is None:
                    missing += 1
                if (a.get('shotDistance') or 0.0) < FIX_DIST:
                    zf_ = 2
                    moved[0] += 1
                    moved[1] += made
            zf[a['personId']][zf_] += 1
            zf[a['personId']][zf_ + 1] += made
    return zo, zf, moved, missing


def game_files(season):
    if season == TEST_SEASON:
        return [(s['id'], ROOT / s['file']) for s in json.loads(MANIFEST_A.read_text(encoding='utf-8'))['sources']]
    return [(p.stem, p) for p in sorted((SEVENTH / season / 'pbp').glob('*.json'))]


def totals(rows):
    t = [0, 0, 0, 0]
    for r in rows:
        for i in range(4):
            t[i] += int(r[2 + i])
    return dict(zip(HEADER[2:], t))


def parse_area_count():
    out = {}
    for line in (ROOT / 'reports/card-0.2.5+E097-topscale/diag/area-count.txt').read_text(encoding='utf-8').splitlines():
        s = line.split()[0]
        i = line.index("'lt8': '") + len("'lt8': '")
        m, a = line[i:].split(' ')[0].split('/')
        out[s] = {'made': int(m), 'att': int(a)}
    return out


def main():
    (HERE / 'tmp').mkdir(exist_ok=True)
    (OUT / 'history').mkdir(exist_ok=True)
    ref_lt8 = parse_area_count()
    check = {'rule': "actionType=='2pt' 且 isFieldGoal==1 且 area=='Mid-Range' 且 (shotDistance or 0) < 8 → short", 'seasons': {}}
    for season in ZONE_SEASONS:
        files = sorted(game_files(season))
        rows_o, rows_f = [], []
        mv = [0, 0]
        miss = 0
        for gid, path in files:
            zo, zf, moved, missing = parse_game(path)
            for pid in sorted(zo):
                rows_o.append([gid, pid] + list(zo[pid]))
            for pid in sorted(zf):
                rows_f.append([gid, pid] + list(zf[pid]))
            mv[0] += moved[0]; mv[1] += moved[1]
            miss += missing
        p_o = HERE / 'tmp' / f'pbp-zones-{season}-v61repro.csv.gz'
        p_f = OUT / 'history' / f'pbp-zones-{season}.csv.gz'
        write_gz_csv(p_o, HEADER, rows_o)
        write_gz_csv(p_f, HEADER, rows_f)
        v61 = HIST / f'pbp-zones-{season}.csv.gz'
        v61rows = read_gz_csv(v61)
        v61tot = totals([[r[k] for k in HEADER] for r in v61rows])
        to, tf = totals(rows_o), totals(rows_f)
        c = {
            'games': len(files),
            'unfixed': {'rows': len(rows_o), 'totals': to, 'sha256': sha256(p_o)},
            'v61': {'rows': len(v61rows), 'totals': v61tot, 'sha256': sha256(v61)},
            'unfixedReproducesV61': {'rows': len(rows_o) == len(v61rows), 'totals': to == v61tot, 'sha256Identical': sha256(p_o) == sha256(v61)},
            'fixed': {'rows': len(rows_f), 'totals': tf, 'sha256': sha256(p_f), 'file': f'history/pbp-zones-{season}.csv.gz'},
            'moved': {'att': mv[0], 'made': mv[1]},
            'areaCountLt8': ref_lt8.get(season),
            'movedMatchesAreaCount': ref_lt8.get(season) == {'made': mv[1], 'att': mv[0]},
            'shotDistanceMissingAmongMidRange': miss,
            'conservation': {'midA': to['midA'] - tf['midA'] == mv[0], 'shortA': tf['shortA'] - to['shortA'] == mv[0],
                             'midM': to['midM'] - tf['midM'] == mv[1], 'shortM': tf['shortM'] - to['shortM'] == mv[1]},
            'leagueRates': {'unfixed': {'mid': to['midM'] / to['midA'], 'short': to['shortM'] / to['shortA']},
                            'fixed': {'mid': tf['midM'] / tf['midA'], 'short': tf['shortM'] / tf['shortA']}},
        }
        check['seasons'][season] = c
        print(season, json.dumps({k: c[k] for k in ('unfixedReproducesV61', 'moved', 'areaCountLt8', 'movedMatchesAreaCount', 'conservation')}, ensure_ascii=False), flush=True)
    s = check['seasons']
    check['pass'] = all(all(v['unfixedReproducesV61'].values()) and v['movedMatchesAreaCount'] and all(v['conservation'].values()) for v in s.values())
    (OUT / 'zones-check.json').write_text(json.dumps(check, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('pass', check['pass'])


if __name__ == '__main__':
    main()
