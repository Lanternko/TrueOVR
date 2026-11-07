"""E-082：把 cards/{off,on}/primary 轉成 card 格式，並加上 foulDisc、presDisplay。
邏輯逐字取自 reports/card-0.2.2/build_card_022.py 的 build() 與 main()（只把路徑換成本資料夾的 cards/<mode>，且兩個 mode 都做）。
輸出：cards/<mode>/card/{ranking.csv,summary.json}（e075.py 讀）、cards/<mode>/ranking.csv（card 0.2.2 格式的最終 ranking，含兩個顯示欄）。
用法（repo 根目錄）：python -I reports/card-0.2.3+E082-position-shares/build_card.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E071 = ROOT / 'reports/card-0.2.0+E071-pressure'
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


def final(mode):
    base_dir = OUT / 'cards' / mode
    build(base_dir / 'primary', base_dir / 'card')
    src = base_dir / 'card'
    base = list(csv.DictReader((src / 'ranking.csv').open(encoding='utf-8')))
    force = {}
    for r in csv.DictReader(FORCE.open(encoding='utf-8')):
        assert r['name'] not in force, f"force 重名：{r['name']}"
        force[r['name']] = r
    cols = list(base[0].keys()) + NEW_COLS
    missing = []
    with (base_dir / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
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
    print(mode, 'wrote', len(base), 'rows; new columns missing for', len(missing), missing[:10], 'sha', sha(base_dir / 'ranking.csv'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for m in ('off', 'on'):
        final(m)
