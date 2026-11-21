"""card 0.2.3 = card 0.2.2 + E-075（用人當能力證據：分鐘、出賽率、年齡、練兵隊；DNP 與輪休分開；R-040）。
ranking.csv：欄位與順序同 card 0.2.2（含 foulDisc、presDisplay）。
  取自 E-075 ranking.csv（依姓名）：rank、ovr、mpg、gRepl（E-075 有改的衍生欄；mpg = E-075 的可出賽修正後場均，等於其 mpgAvail 欄）。
  取自 card 0.2.2（依姓名）：其餘全部（能力值欄、pr、ovr36、foulDisc、presDisplay…）。
  列序 = E-075 名次序。
用法：python -I reports/card-0.2.3/build_card_023.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C022 = ROOT / 'reports/card-0.2.2/ranking.csv'
E075D = ROOT / 'reports/card-0.2.2+E073-usage-evidence'
E075 = E075D / 'ranking.csv'
E075_SHA = '01aab81a56bca96888df95845a9adfc466be065787810e80708e3635c7452215'
FROM_E075 = ['rank', 'ovr', 'mpg', 'gRepl']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(E075) == E075_SHA, 'E-075 ranking.csv sha256 不符'
    a, b = rd(C022), rd(E075)
    cols = list(a[0].keys())
    A = {r['name']: r for r in a}
    assert len(A) == len(a) == len(b) == 582 and len({r['name'] for r in b}) == 582 and set(A) == {r['name'] for r in b}, '姓名對不上或重名'
    for r in b:
        assert r['mpg'] == r['mpgAvail'], r['name']
    shared = [c for c in cols if c not in FROM_E075]
    rows = []
    for r in b:
        o = dict(A[r['name']])
        for c in FROM_E075:
            o[c] = r[c]
        rows.append(o)
    assert [int(o['rank']) for o in rows] == list(range(1, 583))
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    # 驗證
    new = {r['name']: r for r in rd(OUT / 'ranking.csv')}
    assert list(rd(OUT / 'ranking.csv')[0].keys()) == cols
    diff = {c: sum(new[k][c] != A[k][c] for k in A) for c in cols}
    assert all(diff[c] == 0 for c in shared), diff
    assert all(new[r['name']]['ovr'] == r['ovr'] and new[r['name']]['rank'] == r['rank'] for r in b)
    res = json.loads((E075D / 'results.json').read_text(encoding='utf-8'))
    ev = json.loads((E075D / 'evaluation.json').read_text(encoding='utf-8'))
    cand = {c['label']: c for c in ev['candidates']}
    gates = {k: {'value': v['value'], 'threshold': v['threshold'], 'pass': v['pass']} for k, v in res['checks'].items()}
    srcs = [C022, E075, E075D / 'results.json', E075D / 'evaluation.json', E075D / 'preregistration.md', E075D / 'e075.py', E075D / 'audit/audit.md']
    out = {
        'version': 'card 0.2.3',
        'baseVersion': 'card 0.2.2',
        'change': 'E-075：用人當能力證據（分鐘、出賽率、年齡、練兵隊；DNP 與輪休分開）進入 OVR 的能力估計（R-040）。能力值欄、foulDisc、presDisplay 與 card 0.2.2 逐欄相同',
        'players': 582,
        'columns': cols,
        'columnsFromE075': FROM_E075,
        'columnsFromCard022': shared,
        'columnsDifferentFromCard022': {c: n for c, n in diff.items() if n},
        'mpgNote': 'mpg = E-075 可出賽修正後場均（等於 E-075 mpgAvail 欄）；與 card 0.2.2 不同者 %d 人。名單頁「MPG」欄仍是 MIN/出賽場數，不是此欄' % diff['mpg'],
        'verdict_E075': '語意版（只有 c4 不過），使用者於 R-040 裁定採用，G5 已過',
        'gates_E075': gates,
        'rho2k_perGame': {'card-0.2.2': cand['card-0.2.2']['rho2k'], 'card-0.2.3(E075)': cand['E075']['rho2k']},
        'evaluate_mjs': {'card-0.2.2': cand['card-0.2.2']['gates']['pass'], 'card-0.2.3(E075)': cand['E075']['gates']['pass'], 'of': 19},
        'audit': 'role-audit 重算成立（reports/card-0.2.2+E073-usage-evidence/audit/audit.md）；浮點最大差 2.7e-15，582 列 OVR 差 0.0',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.3/build_card_023.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote 582 rows; differing cols vs 0.2.2:', out['columnsDifferentFromCard022'], 'sha', out['ranking_csv_sha256'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
