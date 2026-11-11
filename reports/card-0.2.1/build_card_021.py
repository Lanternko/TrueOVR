"""card 0.2.1：pressure 來源換成事件式 force（E-071 P1，含勘誤 1；R-019 升 PATCH）。

由 E-071 P1 卡片與 force-2025-26.csv 產生：
  ranking.csv = P1 card ranking.csv 全部欄位不變，另加 foulDisc（犯規紀律）、presDisplay（顯示用 PRES = force − 0.25·z(pf)）。
                以姓名對上 force-2025-26.csv；對不到的人兩欄留空。
  summary.json = 版本、基準 card 0.2.0、變更、r_repl 與錨點（同 P1 card summary）、來源檔 sha256（G2）。
用法：python -I reports/card-0.2.1/build_card_021.py
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E071 = ROOT / 'reports/card-0.2.0+E071-pressure'
SRC = E071 / 'cards/P1/card'
FORCE = E071 / 'force-2025-26.csv'
OUT = Path(__file__).resolve().parent
NEW_COLS = ['foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    base = list(csv.DictReader((SRC / 'ranking.csv').open(encoding='utf-8')))
    force_rows = list(csv.DictReader(FORCE.open(encoding='utf-8')))
    force = {}
    for r in force_rows:
        assert r['name'] not in force, f"force 重名：{r['name']}"
        force[r['name']] = r
    summ = json.loads((SRC / 'summary.json').read_text(encoding='utf-8'))
    cols = list(base[0].keys()) + NEW_COLS
    missing = []
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        for r in base:
            o = dict(r)
            fr = force.get(r['name'])
            if fr is None or fr['foulDisc'] == '' or fr['presDisplay'] == '':
                missing.append(r['name'])
                o['foulDisc'] = o['presDisplay'] = ''
            else:
                o['foulDisc'] = fr['foulDisc']
                o['presDisplay'] = fr['presDisplay']
            w.writerow(o)
    srcs = {p.relative_to(ROOT).as_posix(): sha(p)
            for p in (SRC / 'ranking.csv', SRC / 'summary.json', FORCE, E071 / 'preregistration.md', E071 / 'errata.md',
                      E071 / 'verdict.json', E071 / 'report.md')}
    out = {
        'version': 'card 0.2.1',
        'baseVersion': 'card 0.2.0',
        'change': 'pressure 來源 tovNonSteal_defense → 事件式 force（E-071 P1，含勘誤 1）；新增顯示欄 foulDisc、presDisplay（不進 OVR）',
        'ruling': 'R-019（沒有變準，升 PATCH）；使用者 2026-10-29 裁定採用 P1',
        'rRepl_PR10_of_pred': summ['rRepl_PR10_of_pred'],
        'anchors': summ['anchors'],
        'poolSize': summ['poolSize'],
        'players': len(base),
        'newColumns': NEW_COLS,
        'newColumnsMissing': missing,
        'sources_sha256': srcs,
        'generator': 'reports/card-0.2.1/build_card_021.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', len(base), 'rows; new columns missing for', len(missing), missing[:10])


if __name__ == '__main__':
    main()
