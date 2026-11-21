raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-124 retired guard（0.2.10j 換 build_prior_0210j.py；加 gravity）
"""inseason 0.2.10i 先驗卡：prior-2025-26-card0210d.json（已退到 _retired/）的 drive、creation 換成 card 0.2.10i 的值
（reports/card-0.2.10i/tail-U.csv：drive_D、creationJ 的 2025-26 季末四季窗口值，以 playerId 配對）；其餘欄位原樣。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_prior_0210i.py"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = HERE / '_retired/prior-2025-26-card0210d.json'
TAIL = ROOT / 'reports/card-0.2.10i/tail-U.csv'
OUT = HERE / 'prior-2025-26-card0210i.json'
A2 = ['drive', 'creation']
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    d = json.loads(SRC.read_text(encoding='utf-8'))
    tail = {int(r['playerId']): r for r in csv.DictReader(TAIL.open(encoding='utf-8'))}
    n = miss = 0
    for p in d['players']:
        t = tail.get(int(p['playerId']))
        if t is None:
            miss += 1
            continue
        for a in A2:
            p[a] = float(t[a])
        n += 1
    d['note'] = 'card 0.2.10i 先驗：' + d['note'] + ' ／ drive、creation 換 card-0.2.10i/tail-U.csv（R-130：drive_D、creationJ，四季滑動窗口，2025-26 季末）。'
    d['sources']['card0210iTailU'] = {'file': 'reports/card-0.2.10i/tail-U.csv', 'sha256': sha(TAIL)}
    d['sources']['basePrior0210d'] = {'file': 'reports/ovr-inseason-2026-27/live/_retired/prior-2025-26-card0210d.json', 'sha256': sha(SRC)}
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'replaced': n, 'noTail': miss}, ensure_ascii=False))
    return 0 if miss == 0 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
