"""E-069 步驟 1：從 PBP 抽出每場每人的失誤 subType 計數（含全部取值，供附錄與歸類）。
輸出 pbp-tov-<季>.csv.gz：gameId, playerId, ctl, pass, other（補充 1 歸類）；team 失誤 playerId=0。另寫 pbp-tov-subtypes.json。
用法（repo 根目錄）：python reports/handle-E069/extract_tov.py
"""
import json, multiprocessing, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
from lib import write_gz_csv, sha256, MANIFEST_A  # noqa

SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def files(season):
    if season == '2025-26':
        return [(s['id'], ROOT / s['file']) for s in json.loads(MANIFEST_A.read_text(encoding='utf-8'))['sources']]
    return [(p.stem, p) for p in sorted((ROOT / 'data/defense-seventh' / season / 'pbp').glob('*.json'))]


CTL_ST = {'lost ball', 'traveling', 'double dribble', 'discontinued dribble', 'backcourt', 'palming'}


def parse(a):
    """回傳 (gid, {pid: [ctl, pass, other]}, subType 次數, 細分統計)。分類依預註冊 §2.1 + 補充 1。"""
    gid, path = a
    acts = json.loads(Path(path).read_text(encoding='utf-8'))['data']['game']['actions']
    charge_keys = set()
    foul_keys = set()
    for x in acts:
        if x['actionType'] == 'foul':
            k = (x.get('period'), x.get('clock'), x.get('personId') or 0)
            foul_keys.add(k)
            if (x.get('descriptor') or '').strip().lower() == 'charge':
                charge_keys.add(k)
    per = {}
    st_cnt = Counter()
    det = Counter()
    for x in acts:
        if x['actionType'] != 'turnover':
            continue
        st = ' '.join((x.get('subType') or '').lower().split())
        desc = ' '.join((x.get('description') or '').lower().split())
        pid = x.get('personId') or 0
        st_cnt[st] += 1
        cls = 'other'
        if st == 'bad pass':
            cls = 'pass'
        elif st in CTL_ST:
            cls = 'ctl'
        elif st == 'out-of-bounds':
            det['oob_total'] += 1
            if 'bad pass out-of-bounds' in desc:
                cls = 'pass'
            elif 'lost ball out-of-bounds' in desc or 'step out-of-bounds' in desc:
                cls = 'ctl'
            else:
                det['oob_unmatched'] += 1
        elif st == 'offensive foul':
            det['of_total'] += 1
            k = (x.get('period'), x.get('clock'), pid)
            if k in charge_keys:
                cls = 'ctl'
                det['of_charge'] += 1
            elif k not in foul_keys:
                det['of_nofoul'] += 1
        det['cls_' + cls] += 1
        r = per.setdefault(pid, [0, 0, 0])
        r[{'ctl': 0, 'pass': 1, 'other': 2}[cls]] += 1
    return gid, per, st_cnt, det


def main():
    exe = Path(sys.executable).with_name('pythonw.exe')
    if exe.exists():
        multiprocessing.set_executable(str(exe))
    man = {}
    for_stats = {}
    with multiprocessing.Pool(6) as pool:
        for s in SEASONS:
            fl = files(s)
            res = sorted(pool.imap_unordered(parse, fl, chunksize=8), key=lambda r: r[0])
            rows = []
            st_tot, det_tot = Counter(), Counter()
            for gid, per, stc, det in res:
                st_tot.update(stc)
                det_tot.update(det)
                for pid, (c, p, o) in sorted(per.items()):
                    rows.append([gid, pid, c, p, o])
            out = HERE / f'pbp-tov-{s}.csv.gz'
            write_gz_csv(out, ['gameId', 'playerId', 'ctl', 'pass', 'other'], rows)
            man[s] = {'games': len(fl), 'rows': len(rows), 'sha256': sha256(out)}
            for_stats[s] = {'subType': dict(st_tot), 'detail': dict(det_tot)}
            print(s, man[s], dict(det_tot), flush=True)
    for name, obj in (('pbp-tov-manifest.json', man), ('pbp-tov-subtypes.json', for_stats)):
        (HERE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
