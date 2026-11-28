"""0.2.10i 步驟 1：每季逐場 creationJ 計數表。分類照 E-190 errata-1（extract_classes.classify），只留 J 類。
輸出 work/history/crJ-{季}.csv.gz：gameId, playerId, cls, madeUn（進球沒被助攻）, madeAst（進球被助攻）, miss。
creationJ 分子＝madeUn＋miss×pu[cls]（pu＝該季 J 類進球中沒被助攻比例；build_drive.py 的加權），分母＝分鐘。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/extract_j.py [季…]"""
import multiprocessing, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E190 = ROOT / 'reports/card-0.2.10c+E190-creation-jumper'
sys.path.insert(0, str(E190))
import extract_classes as X  # noqa: E402
from lib import write_gz_csv  # noqa: E402

OUT = HERE / 'work/history'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']


def one(args):
    gid, old, dd, al = X.parse_game(args)
    c = Counter()
    for pid, made, ast, typ, k, cls in al:
        if k != 'J':
            continue
        c[(pid, cls, 'madeUn' if made and not ast else 'madeAst' if made else 'miss')] += 1
    return gid, c


def main():
    exe = Path(sys.executable).with_name('pythonw.exe')
    if exe.exists():
        multiprocessing.set_executable(str(exe))
    OUT.mkdir(parents=True, exist_ok=True)
    seasons = sys.argv[1:] or SEASONS
    with multiprocessing.Pool(6) as pool:
        for s in seasons:
            files = sorted(X.game_files(s))
            res = sorted(pool.imap_unordered(one, files, chunksize=8), key=lambda r: r[0])
            rows = []
            for gid, c in res:
                keys = sorted({(p, cl) for p, cl, _ in c})
                rows += [[gid, p, cl, c[(p, cl, 'madeUn')], c[(p, cl, 'madeAst')], c[(p, cl, 'miss')]] for p, cl in keys]
            write_gz_csv(OUT / f'crJ-{s}.csv.gz', ['gameId', 'playerId', 'cls', 'madeUn', 'madeAst', 'miss'], rows)
            print(s, len(files), 'games', len(rows), 'rows', flush=True)


if __name__ == '__main__':
    main()
