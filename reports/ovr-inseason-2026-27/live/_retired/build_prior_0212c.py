"""inseason 0.2.12c 先驗卡（R-144，E-207）：_retired/prior-2025-26-card0210j.json 的 tovSkill 換成 card 0.2.12c 的值
（reports/card-0.2.12c-w246/tov-raw.csv 的 tovSkill，未四捨五入，以 playerId 配對）；其餘欄位原樣。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_prior_0212tov.py"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = HERE / '_retired/prior-2025-26-card0210j.json'
TR = ROOT / 'reports/card-0.2.12c-w246/tov-raw.csv'
OUT = HERE / 'prior-2025-26-card0212c.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    d = json.loads(SRC.read_text(encoding='utf-8'))
    g = {int(r['playerId']): r for r in csv.DictReader(TR.open(encoding='utf-8'))}
    n = miss = 0
    for p in d['players']:
        t = g.get(int(p['playerId']))
        if t is None:
            miss += 1
            continue
        p['tovSkill'] = float(t['tovSkill'])
        p['topMissing'] = int(t['topMissing'])
        n += 1
    d['note'] = 'card 0.2.12c 先驗：' + d['note'] + ' ／ tovSkill 換成觸球分母定義（card-0.2.12c-w246/tov-raw.csv；R-144）。'
    d['sources']['card0212c'] = {'file': 'reports/card-0.2.12c-w246/tov-raw.csv', 'sha256': sha(TR)}
    d['sources']['basePrior0210j'] = {'file': 'reports/ovr-inseason-2026-27/live/_retired/prior-2025-26-card0210j.json', 'sha256': sha(SRC)}
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'replaced': n, 'missing': miss}, ensure_ascii=False))
    return 0 if miss == 0 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
