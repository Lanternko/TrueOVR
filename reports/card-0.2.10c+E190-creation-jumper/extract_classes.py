"""E-190 errata-1 步驟 2–3：從原始 PBP 抽出（a）舊 drive 候選（逐行照 ovr-v61 extract_pbp.py，用來證明抽取與 V61 history/pbp-drive-*.csv.gz 相同）、
（b）errata-1 分類後的切入 D 候選（同欄位格式，餵同一條 drive 管線）、（c）2025-26 全部出手的分類（creation 用）。
分類（errata-1 表，一筆只進一類，順序固定）：
  1. descriptor 含 tip／putback／alley-oop／cutting → 'R'（補籃／空接／空切，都不計）
  2. 2pt、descriptor 含 driving、qualifier 無 2ndchance／fastbreak → 'D'（drive_D）
  3. 其餘 → 'J'（creationJ；三分、pullup、hook、turnaround、無 descriptor…，不限距離）
and-one 偵測照 extract_pbp.py。輸出只寫本目錄 work/history/。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10c+E190-creation-jumper/extract_classes.py"""
import json, multiprocessing, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
from lib import write_gz_csv, sha256, MANIFEST_A, SEVENTH, TEST_SEASON  # noqa: E402

OUT = HERE / 'work/history'
DRIVE_SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
DIST_MAX = 10.0
EXCLUDE_DESC = ('tip', 'putback', 'alley-oop', 'cutting')


def andone(acts, i, a):
    for n in acts[i + 1:i + 8]:
        if n['period'] != a['period'] or n['clock'] != a['clock']:
            break
        if n['actionType'] == 'freethrow' and n.get('subType') == '1 of 1' and n['personId'] == a['personId']:
            return 1 if n.get('shotResult') == 'Made' else 0
    return 0


def classify(a):
    desc = a.get('descriptor') or ''
    quals = tuple(a.get('qualifiers') or ())
    if any(x in desc for x in EXCLUDE_DESC):
        return 'R'
    if a['actionType'] == '2pt' and 'driving' in desc and '2ndchance' not in quals and 'fastbreak' not in quals:
        return 'D'
    return 'J'


def parse_game(args):
    gid, path = args
    acts = json.loads(Path(path).read_text(encoding='utf-8'))['data']['game']['actions']
    old, dd, allshots = [], [], []
    for i, a in enumerate(acts):
        if a['actionType'] not in ('2pt', '3pt'):
            continue
        made = a.get('shotResult') == 'Made'
        desc = a.get('descriptor') or ''
        quals = tuple(a.get('qualifiers') or ())
        dist = a.get('shotDistance') or 0.0
        assisted = int(a.get('assistPersonId') is not None)
        cls = (a.get('subType') or '') + '|' + (desc or '(none)')
        k = classify(a)
        allshots.append((a['personId'], int(made), assisted, a['actionType'], k, cls))
        if a['actionType'] != '2pt':
            continue
        is_old = not (dist > DIST_MAX or '2ndchance' in quals or 'fastbreak' in quals or any(x in desc for x in EXCLUDE_DESC))
        if is_old or k == 'D':
            ft = andone(acts, i, a) if made else 0
            row = (a['personId'], int(made), assisted, ft, cls)
            if is_old:
                old.append(row)
            if k == 'D':
                dd.append(row)
    return gid, old, dd, allshots


def game_files(season):
    if season == TEST_SEASON:
        return [(s['id'], ROOT / s['file']) for s in json.loads(MANIFEST_A.read_text(encoding='utf-8'))['sources']]
    return [(p.stem, p) for p in sorted((SEVENTH / season / 'pbp').glob('*.json'))]


def main():
    exe = Path(sys.executable).with_name('pythonw.exe')
    if exe.exists():
        multiprocessing.set_executable(str(exe))   # 工作程序不開黑窗
    OUT.mkdir(parents=True, exist_ok=True)
    man = {}
    H = ['gameId', 'playerId', 'made', 'assisted', 'ftmade', 'cls']
    with multiprocessing.Pool(6) as pool:
        for season in DRIVE_SEASONS:
            files = sorted(game_files(season))
            res = sorted(pool.imap_unordered(parse_game, files, chunksize=8), key=lambda r: r[0])
            orows, drows, arows = [], [], []
            for gid, old, dd, al in res:
                orows += [[gid] + list(x) for x in sorted(old)]
                drows += [[gid] + list(x) for x in sorted(dd)]
                if season == TEST_SEASON:
                    arows += [[gid] + list(x) for x in al]
            write_gz_csv(OUT / f'pbp-drive-OLD-{season}.csv.gz', H, orows)
            write_gz_csv(OUT / f'pbp-drive-D-{season}.csv.gz', H, drows)
            ref = V61 / 'history' / f'pbp-drive-{season}.csv.gz'
            man[season] = {'games': len(files), 'oldShots': len(orows), 'dShots': len(drows),
                           'old_sha256': sha256(OUT / f'pbp-drive-OLD-{season}.csv.gz'), 'v61_sha256': sha256(ref),
                           'D_sha256': sha256(OUT / f'pbp-drive-D-{season}.csv.gz')}
            man[season]['old_equals_v61'] = man[season]['old_sha256'] == man[season]['v61_sha256']
            if season == TEST_SEASON:
                write_gz_csv(OUT / f'shots-all-{season}.csv.gz', ['gameId', 'playerId', 'made', 'assisted', 'type', 'klass', 'cls'], arows)
                man[season]['allShots'] = len(arows)
                man[season]['all_sha256'] = sha256(OUT / f'shots-all-{season}.csv.gz')
            print(season, json.dumps(man[season]), flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
