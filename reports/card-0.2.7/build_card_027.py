"""card 0.2.7 = card 0.2.6 + E-107 防守 UL（防守加成不打折 max(0, centeredD)、防守 D 用 E-104 逐場線性遞減、回合門檻 × 1/2；R-061）。
ranking.csv：與 E-107 UL6 經 e094 pipeline 的輸出（work/UL6/ranking.csv）逐位元相同，欄位與順序同 card 0.2.6。
  同一流程的 B6 與 card 0.2.6 逐位元相同（c0b），所以兩版差異只來自 UL 的兩個開關。
OVR 錨點（PR1／PR50／PR99，名單頁換算 OVR 傾向用）取自 E-107 phase2.json 的 reportOnly.anchors.UL6。
版號：使用者 2026-10-30「發布2.7」，PATCH（R-064：改了公式且影響大；樣本外只證明不變差，R-019）。
用法：python -I -X utf8 reports/card-0.2.7/build_card_027.py
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C026 = ROOT / 'reports/card-0.2.6/ranking.csv'
C026_SHA = 'a0a81ecb2d591497bc1d6680573e6fbf71a11124c4d33ba60df3e4d412f16c91'
E107D = ROOT / 'reports/card-0.2.6+E107-defense-UL'
E107 = E107D / 'work/UL6/ranking.csv'
E107_B6 = E107D / 'work/B6/ranking.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C026) == C026_SHA, 'card 0.2.6 ranking.csv sha256 不符'
    assert sha(E107_B6) == C026_SHA, 'E-107 B6 和 card 0.2.6 不同（c0b）'
    ph = json.loads((E107D / 'phase2.json').read_text(encoding='utf-8'))
    ul = ph['arms']['UL6']
    assert sha(E107) == ul['ranking_sha256'], 'E-107 UL6 ranking.csv sha256 和 phase2.json 不符'
    a, b = rd(C026), rd(E107)
    cols = list(a[0].keys())
    assert list(b[0].keys()) == cols and len(a) == len(b) == 582
    assert {r['name'] for r in a} == {r['name'] for r in b}, '姓名對不上'
    assert [int(r['rank']) for r in b] == list(range(1, 583))
    shutil.copyfile(E107, OUT / 'ranking.csv')
    assert sha(OUT / 'ranking.csv') == ul['ranking_sha256']
    A = {r['name']: r for r in a}
    diff = {c: sum(A[r['name']][c] != r[c] for r in b) for c in cols}
    top20_026 = {r['name'] for r in a if int(r['rank']) <= 20}
    top20_027 = {r['name'] for r in b if int(r['rank']) <= 20}
    srcs = [C026, E107, E107D / 'phase2.json', E107D / 'preregistration.md', E107D / 'report.md', E107D / 'evaluation.json']
    ev = ph['evaluate_gates']
    out = {
        'version': 'card 0.2.7',
        'baseVersion': 'card 0.2.6',
        'change': 'E-107 防守 UL：防守加成改成不打折 max(0, centeredD)（原本屬性分前 4% 歸 0）；防守 D 改用 E-104 逐場線性遞減版、回合門檻 × 1/2；'
                  'RAPM 名次封頂、align、gamma 不動（R-061）',
        'players': 582,
        'columns': cols,
        'columnsDifferentFromCard026': {c: n for c, n in diff.items() if n},
        'anchors': ph['reportOnly']['anchors']['UL6'],
        'top20Changes': {'out': sorted(top20_026 - top20_027), 'in': sorted(top20_027 - top20_026)},
        'verdict_E107': f"預註冊判定 {ul['verdict']}；evaluate {ev['E107-UL6']['pass']}/{ev['E107-UL6']['of']}（card 0.2.6 {ev['card-0.2.6']['pass']}/{ev['card-0.2.6']['of']}）；"
                        '使用者 2026-10-30「發布2.7」；樣本外只證明不變差，看過 E-106 才選（不算盲測，L-026），版號 PATCH',
        'gates_E107': {k: {f: v[f] for f in ('point', 'ci90', 'value', 'pass') if f in v} for k, v in ul['checks'].items() if isinstance(v, dict)},
        'nextRound': '新賽季頁（inseason）先驗不跟著改，要跟上 0.2.7 另走 inseason 實驗（R-050）',
        'audit': '未做 role-audit 重算（使用者直接發布）',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.7/build_card_027.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; top20 out/in:', out['top20Changes'], 'anchors', out['anchors'], 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
