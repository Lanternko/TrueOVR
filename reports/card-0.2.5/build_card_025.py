"""card 0.2.5 = card 0.2.4 + E-089（卡片 g 的分鐘權重 mpg/36 → 飽和 W(m)=(1−e^(−m/15))/(1−e^(−36/15))；R-047）。
ranking.csv：欄位與順序同 card 0.2.4。
  取自 E-089 ranking.csv（依姓名）：rank、ovr、mpg、gRepl（E-089 有改的衍生欄）。
  取自 card 0.2.4（依姓名）：其餘全部（能力值欄、pr、ovr36、foulDisc、presDisplay…）。
  列序 = E-089 名次序。
版號：使用者 2026-10-29 定為 PATCH（R-048；照 R-019）。
用法：python -I -X utf8 reports/card-0.2.5/build_card_025.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C024 = ROOT / 'reports/card-0.2.4/ranking.csv'
C024_SHA = 'af37ce25169c64b5e747afe066b42747c187b5d2ef20ffb3cc454e3ba95b7203'
E089D = ROOT / 'reports/card-0.2.4+E089-minutes-saturation'
E089 = E089D / 'ranking.csv'
E089_SHA = '73b1d6353142dd86327a022a19e939833c42a0aa0c69f3377201ffe411c0050a'
FROM_E089 = ['rank', 'ovr', 'mpg', 'gRepl']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C024) == C024_SHA, 'card 0.2.4 ranking.csv sha256 不符'
    assert sha(E089) == E089_SHA, 'E-089 ranking.csv sha256 不符'
    a, b = rd(C024), rd(E089)
    cols = list(a[0].keys())
    A = {r['name']: r for r in a}
    assert len(A) == len(a) == len(b) == 582 and set(A) == {r['name'] for r in b}, '姓名對不上或重名'
    assert list(b[0].keys()) == cols
    shared = [c for c in cols if c not in FROM_E089]
    rows = []
    for r in b:
        o = dict(A[r['name']])
        for c in FROM_E089:
            o[c] = r[c]
        rows.append(o)
    assert [int(o['rank']) for o in rows] == list(range(1, 583))
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    assert sha(OUT / 'ranking.csv') == E089_SHA, '產出 ranking.csv 與 E-089 不是逐位元相同'
    # 驗證
    new = {r['name']: r for r in rd(OUT / 'ranking.csv')}
    diff = {c: sum(new[k][c] != A[k][c] for k in A) for c in cols}
    assert all(diff[c] == 0 for c in shared), diff
    assert all(new[r['name']][c] == r[c] for r in b for c in cols), 'E-089 ranking.csv 其他欄與 card 0.2.4 不同'
    res = json.loads((E089D / 'results.json').read_text(encoding='utf-8'))
    ev = json.loads((E089D / 'evaluation.json').read_text(encoding='utf-8'))
    cand = {c['label']: c for c in ev['candidates']}
    gates = {k: {f: v[f] for f in ('value', 'threshold', 'pass') if f in v} for k, v in res['checks'].items()}
    srcs = [C024, E089, E089D / 'results.json', E089D / 'evaluation.json', E089D / 'preregistration.md', E089D / 'e089.py', E089D / 'audit/audit.md']
    out = {
        'version': 'card 0.2.5',
        'baseVersion': 'card 0.2.4',
        'change': 'E-089：卡片 g 的分鐘權重由 mpg/36 改為飽和 W(m)=(1−e^(−m/15))/(1−e^(−36/15))（R-047）。能力值欄、foulDisc、presDisplay 與 card 0.2.4 逐欄相同',
        'players': 582,
        'columns': cols,
        'columnsFromE089': FROM_E089,
        'columnsFromCard024': shared,
        'columnsDifferentFromCard024': {c: n for c, n in diff.items() if n},
        'verdict_E089': f"預註冊判定 {res['verdict']}（失敗關卡 {res['failed_checks']}）；G5 使用者「還行 可以接受」；樣本外只證明不變差，2K27 ρ 小降，版號 PATCH（R-048）",
        'gates_E089': gates,
        'rho2k_perGame': {'card-0.2.4': cand['card-0.2.4']['rho2k'], 'card-0.2.5(E089)': cand['E089']['rho2k']},
        'evaluate_mjs': {'card-0.2.4': cand['card-0.2.4']['gates']['pass'], 'card-0.2.5(E089)': cand['E089']['gates']['pass'], 'of': cand['E089']['gates']['of']},
        'nextRound': 'R-048：賽中先驗仍是 card 0.2.4（inseason 0.2.2a），賽中要不要改用 W 另走 inseason 實驗',
        'audit': 'role-audit 重算成立（reports/card-0.2.4+E089-minutes-saturation/audit/audit.md）',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.5/build_card_025.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; differing cols vs 0.2.4:', out['columnsDifferentFromCard024'], 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
