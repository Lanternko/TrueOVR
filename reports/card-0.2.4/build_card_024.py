"""card 0.2.4 = card 0.2.3 + E-084（用人回歸的訓練目標改成 2025-26 單季 RAPM，修正年輕被低估；R-042）。
ranking.csv：欄位與順序同 card 0.2.3。
  取自 E-084 ranking.csv（依姓名）：rank、ovr、mpg、gRepl（E-084 有改的衍生欄）。
  取自 card 0.2.3（依姓名）：其餘全部（能力值欄、pr、ovr36、foulDisc、presDisplay…）。
  列序 = E-084 名次序。
版號：使用者 2026-10-29 定為 PATCH（R-044；照 R-019 原為 MINOR 候選）。
用法：python -I reports/card-0.2.4/build_card_024.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C023 = ROOT / 'reports/card-0.2.3/ranking.csv'
C023_SHA = '933797d84f6c411b57f3caadcf26a898c203858b4808cf97b461717a9c3ebc64'
E084D = ROOT / 'reports/card-0.2.3+E084-current-target'
E084 = E084D / 'ranking.csv'
E084_SHA = 'af37ce25169c64b5e747afe066b42747c187b5d2ef20ffb3cc454e3ba95b7203'
FROM_E084 = ['rank', 'ovr', 'mpg', 'gRepl']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C023) == C023_SHA, 'card 0.2.3 ranking.csv sha256 不符'
    assert sha(E084) == E084_SHA, 'E-084 ranking.csv sha256 不符'
    a, b = rd(C023), rd(E084)
    cols = list(a[0].keys())
    A = {r['name']: r for r in a}
    assert len(A) == len(a) == len(b) == 582 and set(A) == {r['name'] for r in b}, '姓名對不上或重名'
    assert list(b[0].keys()) == cols
    shared = [c for c in cols if c not in FROM_E084]
    rows = []
    for r in b:
        o = dict(A[r['name']])
        for c in FROM_E084:
            o[c] = r[c]
        rows.append(o)
    assert [int(o['rank']) for o in rows] == list(range(1, 583))
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    # 驗證
    new = {r['name']: r for r in rd(OUT / 'ranking.csv')}
    diff = {c: sum(new[k][c] != A[k][c] for k in A) for c in cols}
    assert all(diff[c] == 0 for c in shared), diff
    assert all(new[r['name']][c] == r[c] for r in b for c in cols), 'E-084 ranking.csv 其他欄與 card 0.2.3 不同'
    res = json.loads((E084D / 'results.json').read_text(encoding='utf-8'))
    ev = json.loads((E084D / 'evaluation.json').read_text(encoding='utf-8'))
    cand = {c['label']: c for c in ev['candidates']}
    gates = {k: {f: v[f] for f in ('value', 'threshold', 'pass') if f in v} for k, v in res['checks'].items()}
    srcs = [C023, E084, E084D / 'results.json', E084D / 'evaluation.json', E084D / 'preregistration.md', E084D / 'e084.py', E084D / 'audit/audit.md']
    out = {
        'version': 'card 0.2.4',
        'baseVersion': 'card 0.2.3',
        'change': 'E-084：E-075 用人回歸的訓練目標由四季合併 RAPM 改成 2025-26 單季 RAPM（修正年輕被低估、老將被高估）。能力值欄、foulDisc、presDisplay 與 card 0.2.3 逐欄相同',
        'players': 582,
        'columns': cols,
        'columnsFromE084': FROM_E084,
        'columnsFromCard023': shared,
        'columnsDifferentFromCard023': {c: n for c, n in diff.items() if n},
        'verdict_E084': '機械判定只差 (c3)（evaluate 16/19，參考名次與偏差同源）；使用者依機會成本裁定通過（R-042），G5 已過，版號 PATCH（R-044）',
        'gates_E084': gates,
        'rho2k_perGame': {'card-0.2.3': cand['card-0.2.3']['rho2k'], 'card-0.2.4(E084)': cand['E084']['rho2k']},
        'evaluate_mjs': {'card-0.2.3': cand['card-0.2.3']['gates']['pass'], 'card-0.2.4(E084)': cand['E084']['gates']['pass'], 'of': 19},
        'nextRound': 'R-042／R-043：四季量尺 ρ −0.017、分鐘權重改遞減（pred 標準差 1.65 → 1.01）、老將、p_B 間接路徑、p 上限、mpg-A/B 出賽數',
        'audit': 'role-audit（Opus）重算成立（reports/card-0.2.3+E084-current-target/audit/audit.md）；ranking 與稽核重算逐位元相同',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.4/build_card_024.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; differing cols vs 0.2.3:', out['columnsDifferentFromCard023'], 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
