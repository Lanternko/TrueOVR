"""inseason 0.2.10j 先驗卡：_retired/prior-2025-26-card0210i.json 加一欄 gravity＝card 0.2.10j 的值
（reports/card-0.2.10j/gravity-attr.csv，未四捨五入，以 playerId 配對）；其餘欄位原樣。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_prior_0210j.py"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = HERE / '_retired/prior-2025-26-card0210i.json'
GA = ROOT / 'reports/card-0.2.10j/gravity-attr.csv'
OUT = HERE / 'prior-2025-26-card0210j.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    d = json.loads(SRC.read_text(encoding='utf-8'))
    g = {int(r['playerId']): r for r in csv.DictReader(GA.open(encoding='utf-8'))}
    n = miss = 0
    for p in d['players']:
        t = g.get(int(p['playerId']))
        if t is None:
            miss += 1
            continue
        p['gravity'] = float(t['gravity'])
        p['gravityImputed'] = int(t['gravityImputed'])
        n += 1
    d['note'] = 'card 0.2.10j 先驗：' + d['note'] + ' ／ 加 gravity（card-0.2.10j/gravity-attr.csv；R-134 無球外線引力）。'
    d['sources']['card0210jGravity'] = {'file': 'reports/card-0.2.10j/gravity-attr.csv', 'sha256': sha(GA)}
    d['sources']['basePrior0210i'] = {'file': 'reports/ovr-inseason-2026-27/live/_retired/prior-2025-26-card0210i.json', 'sha256': sha(SRC)}
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'added': n, 'noGravity': miss}, ensure_ascii=False))
    return 0 if miss == 0 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
