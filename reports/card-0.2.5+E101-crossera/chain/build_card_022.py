"""E-101 複本（自 reports/card-0.2.5+E097-topscale/chain/build_card_022.py，只改 generator 字串）。E-097 原說明：E-097 複本（自 reports/card-0.2.5+E096-tail150/chain/build_card_022.py，只改 generator 字串）。E-096 原說明：E-096 複本（自 reports/card-0.2.4+E090-onball-tail/chain/build_card_022.py，只改 generator 字串）。原說明：E-090 複本（自 reports/card-0.2.2/build_card_022.py）：只跑 P1，輸入／輸出改到 E-090 的 cards/<variant>/；ranking 寫 cards/<variant>/ranking022.csv（= card 0.2.2 ranking.csv 格式）。邏輯不改。
用法：python -I -B reports/card-0.2.4+E090-onball-tail/chain/build_card_022.py <cur|e090>
以下為原說明：
card 0.2.2 = card 0.2.0 + E-070（foulDraw 以量為主，w075）+ E-071 P1（pressure 換成事件式 force，含勘誤 1）。
1) 把 cards/{base,P1}/primary 轉成 card 格式（每場 OVR，替補水準基準；邏輯同 E-071 build_cards.py 的 build()）→ cards/<v>/card/
2) ranking.csv = P1 card ranking.csv + foulDisc、presDisplay（依姓名取自 E-071 force-2025-26.csv，方法同 card-0.2.1/build_card_021.py）
3) summary.json
用法：python -I reports/card-0.2.2/build_card_022.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parents[1]
OUT = HERE / 'cards' / sys.argv[1]
E071 = ROOT / 'reports/card-0.2.0+E071-pressure'
E070 = ROOT / 'reports/card-0.2.0+E070-foul-volume'
FORCE = E071 / 'force-2025-26.csv'
NEW_COLS = ['foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    base = list(csv.DictReader((src / 'ranking.csv').open(encoding='utf-8')))
    repl = {r['name']: r for r in csv.DictReader((src / 'pergame-repl.csv').open(encoding='utf-8'))}
    summ = json.loads((src / 'pergame-summary.json').read_text(encoding='utf-8'))
    names = [r['name'] for r in base]
    assert len(set(names)) == len(names) == len(repl) and set(names) == set(repl), '姓名對不上或重名'
    rows = []
    for r in base:
        p = repl[r['name']]
        assert r['MIN'] == p['MIN'] and r['pos'] == p['pos'], r['name']
        o = {k: v for k, v in r.items()}
        o['ovr36'] = r['ovr']
        o['ovr'] = f"{float(p['ovr']):.1f}"
        o['mpg'] = f"{float(p['mpg']):.2f}"
        o['gRepl'] = f"{float(p['g']):.4f}"
        o['_sort'] = float(p['ovr'])
        rows.append(o)
    rows.sort(key=lambda o: -o['_sort'])
    cols = list(base[0].keys()) + ['mpg', 'gRepl', 'ovr36']
    with (out / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        for i, o in enumerate(rows, 1):
            o['rank'] = i
            w.writerow(o)
    (out / 'summary.json').write_text(json.dumps({
        'rRepl_PR10_of_pred': summ['rRepl_PR10_of_pred'], 'anchors': summ['anchors']['repl'], 'poolSize': summ['poolSize'],
        'players': len(rows), 'columns': cols, 'ranking_csv_sha256': sha(out / 'ranking.csv')}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    build(OUT / 'P1/primary', OUT / 'P1/card')
    src = OUT / 'P1/card'
    base = list(csv.DictReader((src / 'ranking.csv').open(encoding='utf-8')))
    force = {}
    for r in csv.DictReader(FORCE.open(encoding='utf-8')):
        assert r['name'] not in force, f"force 重名：{r['name']}"
        force[r['name']] = r
    summ = json.loads((src / 'summary.json').read_text(encoding='utf-8'))
    cols = list(base[0].keys()) + NEW_COLS
    missing = []
    with (OUT / 'ranking022.csv').open('w', encoding='utf-8', newline='') as f:
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
    srcfiles = [src / 'ranking.csv', src / 'summary.json', FORCE, E071 / 'force-pressure-source.csv', E071 / 'calibrate-wing.py',
                E071 / 'preregistration.md', E071 / 'errata.md', E070 / 'attributes-w075/attributes-new.csv', E070 / 'preregistration.md',
                HERE / 'chain/run_cards.py', HERE / 'calibrate-wing.py', OUT / 'P1/primary/ranking.csv']
    out = {
        'version': 'card 0.2.2',
        'baseVersion': 'card 0.2.0',
        'change': 'foulDraw 以量為主（E-070 w075）+ pressure 來源 tovNonSteal_defense → 事件式 force（E-071 P1，含勘誤 1）；新增顯示欄 foulDisc、presDisplay（不進 OVR）',
        'components': {'E-070': 'foulDraw w075（reports/card-0.2.0+E070-foul-volume/attributes-w075）', 'E-071': 'P1 pressure=force（含勘誤 1）'},
        'rRepl_PR10_of_pred': summ['rRepl_PR10_of_pred'],
        'anchors': summ['anchors'],
        'poolSize': summ['poolSize'],
        'players': len(base),
        'newColumns': NEW_COLS,
        'newColumnsMissing': missing,
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcfiles},
        'generator': 'reports/card-0.2.5+E101-crossera/chain/build_card_022.py',
        'ranking_csv_sha256': sha(OUT / 'ranking022.csv'),
    }
    (OUT / 'summary022.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', len(base), 'rows; new columns missing for', len(missing), missing[:10])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
