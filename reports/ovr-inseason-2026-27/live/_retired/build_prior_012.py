raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-107 retired guard
"""由 card 0.1.2 的 ranking.csv 產生賽中用的 2025-26 先驗卡（inseason 0.1.2）。

只換屬性欄（x0）：v5 先驗卡 prior-2025-26-v5.json 的 playerId／observed／sample／usg 等原樣保留，
17 個 card 0.1.2 屬性（含 foulDraw）依姓名（兩邊各 582 人、無同名）覆寫。不重擬合、不改任何公式。
用法：python -I reports/ovr-inseason-2026-27/live/build_prior_012.py
"""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'reports/ovr-inseason-2026-27/v5/data/prior-2025-26-v5.json'
CARD = ROOT / 'reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv'
OUT = HERE / 'prior-2025-26-card012.json'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall',
         'help', 'stamina', 'heightInches', 'creation', 'pressure']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    doc = json.loads(OLD.read_text(encoding='utf-8'))
    rows = {r['name']: r for r in csv.DictReader(CARD.open(encoding='utf-8'))}
    assert len(rows) == 582 == len(doc['players'])
    for p in doc['players']:
        r = rows[p['name']]
        assert r['pos'] == p['pos'], p['name']
        for a in ATTRS:
            p[a] = float(r[a])
    doc['note'] = ('S* 的 x0：2025-26 card 0.1.2 屬性（含 foulDraw）。attrs 取自 '
                   'reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv；其餘欄位沿用 prior-2025-26-v5.json。')
    doc['sources'] = {
        'formalCard': {'file': CARD.relative_to(ROOT).as_posix(), 'sha256': sha(CARD)},
        'baseV5Prior': {'file': OLD.relative_to(ROOT).as_posix(), 'sha256': sha(OLD)},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote', OUT, len(doc['players']))


if __name__ == '__main__':
    main()
