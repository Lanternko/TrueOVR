"""card 0.2.6 = card 0.2.5 + E-101（PBP 補籃改歸近距離、四季合併錨點、頂端差距尺只壓縮；R-055、R-056）。
ranking.csv：與 E-101 主版本（cards/e101/e084/ranking.csv）逐位元相同，欄位與順序同 card 0.2.5。
  E-101 改的是能力值本身（mid、short 等的歷史收縮與 99 以上的尾巴），所以能力值欄、pred、OVR 全部取自 E-101。
OVR 錨點（PR1／PR50／PR99，名單頁換算 OVR 傾向用）取自 E-101 e084 results.json 的 card.anchors。
版號：使用者 2026-10-30 G5「A」通過，PATCH（照 R-019：樣本外只證明不變差）。
用法：python -I -X utf8 reports/card-0.2.6/build_card_026.py
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C025 = ROOT / 'reports/card-0.2.5/ranking.csv'
C025_SHA = '73b1d6353142dd86327a022a19e939833c42a0aa0c69f3377201ffe411c0050a'
E101D = ROOT / 'reports/card-0.2.5+E101-crossera'
E101 = E101D / 'cards/e101/e084/ranking.csv'
E101_SHA = 'a0a81ecb2d591497bc1d6680573e6fbf71a11124c4d33ba60df3e4d412f16c91'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C025) == C025_SHA, 'card 0.2.5 ranking.csv sha256 不符'
    assert sha(E101) == E101_SHA, 'E-101 ranking.csv sha256 不符'
    a, b = rd(C025), rd(E101)
    cols = list(a[0].keys())
    assert list(b[0].keys()) == cols and len(a) == len(b) == 582
    assert {r['name'] for r in a} == {r['name'] for r in b}, '姓名對不上'
    assert [int(r['rank']) for r in b] == list(range(1, 583))
    shutil.copyfile(E101, OUT / 'ranking.csv')
    assert sha(OUT / 'ranking.csv') == E101_SHA
    A = {r['name']: r for r in a}
    diff = {c: sum(A[r['name']][c] != r[c] for r in b) for c in cols}
    res = json.loads((E101D / 'results.json').read_text(encoding='utf-8'))
    anchors = json.loads((E101D / 'cards/e101/e084/results.json').read_text(encoding='utf-8'))['card']['anchors']
    top20_025 = {r['name'] for r in a if int(r['rank']) <= 20}
    top20_026 = {r['name'] for r in b if int(r['rank']) <= 20}
    srcs = [C025, E101, E101D / 'results.json', E101D / 'preregistration.md', E101D / 'report.md', E101D / 'audit/audit.md',
            E101D / 'cards/e101/e084/results.json']
    out = {
        'version': 'card 0.2.6',
        'baseVersion': 'card 0.2.5',
        'change': 'E-101：PBP 把補籃、補扣標成 Mid-Range 的出手（shotDistance < 8）改歸近距離，mid／short 收縮向聯盟平均；'
                  '百分位與 99 錨點改對 2022-23～2025-26 四季合併池；頂端的尺 S = max((PR99−PR90)/1.044, SD_pool)，只壓縮不放大（R-055、R-056）',
        'players': 582,
        'columns': cols,
        'columnsDifferentFromCard025': {c: n for c, n in diff.items() if n},
        'anchors': anchors,
        'top20Changes': {'out': sorted(top20_025 - top20_026), 'in': sorted(top20_026 - top20_025)},
        'verdict_E101': f"預註冊判定 {res['verdict']}；role-audit 重算成立；G5 使用者 2026-10-30「A」；樣本外只證明不變差，版號 PATCH（R-019）",
        'gates_E101': {k: {f: v[f] for f in ('point', 'ci90', 'value', 'pass') if f in v} for k, v in res['checks'].items()},
        'nextRound': '新賽季頁（inseason）先驗仍是 card 0.2.5（inseason 0.2.5a），要跟上 0.2.6 另走 inseason 實驗',
        'audit': 'role-audit 重算成立（reports/card-0.2.5+E101-crossera/audit/audit.md）',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.6/build_card_026.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; top20 out/in:', out['top20Changes'], 'anchors', anchors, 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
