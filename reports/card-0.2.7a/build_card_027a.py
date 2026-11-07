"""card 0.2.7a = card 0.2.7 + E-125 pass 量率各半（0.5·zs(AST/36)＋0.5·zs(AST%)；R-074）。
ranking.csv：與 E-125 P50 經 e094 pipeline 的輸出（work/P50/ranking.csv）逐位元相同，欄位與順序同 card 0.2.7。
  同一流程的 P0 與 card 0.2.7 逐位元相同（c0），所以兩版差異只來自 pass 欄。
OVR 錨點（PR1／PR50／PR99，名單頁換算 OVR 傾向用）取自 E-125 results-e125.json 的 reportOnly.anchors.P50。
版號：使用者 2026-10-30「0,2,7a」，字母小版本（R-064 影響小：前 20 換 1 人、移動 ≥ 10 名 4 人、evaluate 18/19 不減）。
用法：python -I -X utf8 reports/card-0.2.7a/build_card_027a.py
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'
C027_SHA = 'aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6'
E125D = ROOT / 'reports/card-0.2.7+E125-pass-volume'
E125 = E125D / 'work/P50/ranking.csv'
E125_P0 = E125D / 'work/P0/ranking.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C027) == C027_SHA, 'card 0.2.7 ranking.csv sha256 不符'
    assert sha(E125_P0) == C027_SHA, 'E-125 P0 和 card 0.2.7 不同（c0）'
    res = json.loads((E125D / 'results-e125.json').read_text(encoding='utf-8'))
    p50 = res['arms']['P50']
    assert sha(E125) == p50['ranking_sha256'], 'E-125 P50 ranking.csv sha256 和 results-e125.json 不符'
    a, b = rd(C027), rd(E125)
    cols = list(a[0].keys())
    assert list(b[0].keys()) == cols and len(a) == len(b) == 582
    assert {r['name'] for r in a} == {r['name'] for r in b}, '姓名對不上'
    assert [int(r['rank']) for r in b] == list(range(1, 583))
    shutil.copyfile(E125, OUT / 'ranking.csv')
    assert sha(OUT / 'ranking.csv') == p50['ranking_sha256']
    A = {r['name']: r for r in a}
    diff = {c: sum(A[r['name']][c] != r[c] for r in b) for c in cols}
    top20_027 = {r['name'] for r in a if int(r['rank']) <= 20}
    top20_027a = {r['name'] for r in b if int(r['rank']) <= 20}
    srcs = [C027, E125, E125D / 'results-e125.json', E125D / 'preregistration.md', E125D / 'report.txt', E125D / 'evaluation.json']
    out = {
        'version': 'card 0.2.7a',
        'baseVersion': 'card 0.2.7',
        'change': 'E-125 pass 量率各半：每季 pass 原始值改成 0.5·zs(AST/36，E-055 (c) 收縮)＋0.5·zs(AST%)，四季池與 S 錨點照 E-101 重算（R-074）；'
                  '其他屬性、OVR 迴歸、用人回歸、防守 UL 不動；模擬 per36 沿用（新 pass 沒進模擬）',
        'players': 582,
        'columns': cols,
        'columnsDifferentFromCard027': {c: n for c, n in diff.items() if n},
        'anchors': res['reportOnly']['anchors']['P50'],
        'top20Changes': {'out': sorted(top20_027 - top20_027a), 'in': sorted(top20_027a - top20_027)},
        'verdict_E125': f"預註冊判定 {p50['verdict']}；evaluate 18/19（card 0.2.7 18/19）；使用者 2026-10-30「0,2,7a」；"
                        '樣本外只證明不變差，看過 Giannis 才選方向（不算盲測，L-026），字母小版本（R-064 影響小）',
        'gates_E125': {k: {f: v[f] for f in ('point', 'ci90', 'value', 'pass') if f in v}
                       for k, v in json.loads((E125D / 'results.json').read_text(encoding='utf-8'))['results']['checks'].items() if isinstance(v, dict)},
        'nextRound': '新賽季頁（inseason）先驗不跟著改，要跟上 0.2.7a 另走 inseason 實驗（R-050）；pass 進模擬另立實驗',
        'audit': '未做 role-audit 重算；lead 從 attributes／results.json 重算 c0a、c0、m1–m3、p1',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.7a/build_card_027a.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; top20 out/in:', out['top20Changes'], 'anchors', out['anchors'], 'diff', out['columnsDifferentFromCard027'], 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
