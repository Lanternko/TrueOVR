"""card 0.2.0：每場 OVR（含上場時間，相對替補水準；R-028，E-064 副版）。

由 card 0.1.2 ranking.csv（每 36 分鐘 OVR）與 E-064 副版輸出 pergame-repl.csv（以姓名對上）產生：
  ranking.csv = card 0.1.2 全部欄位，ovr 換成副版每場 OVR（小數 1 位），依新 ovr 重排 rank，
                另加 mpg、gRepl（g_r = (pred - r_repl) * MPG / 36）、ovr36（原每 36 分鐘 OVR）。
  summary.json = 版本、r_repl、錨點、來源檔 sha256（G2）。
能力值（long, mid, ... 等欄）一律不動。用法：python -I reports/card-0.2.0+E070-foul-volume/build_card.py
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
TAG = sys.argv[1]
SRC = Path(__file__).resolve().parent / f'cards-{TAG}' / 'primary'
OUT = Path(__file__).resolve().parent / ('primary' if TAG == 'w075' else f'cards-{TAG}/card')
OUT.mkdir(parents=True, exist_ok=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    base = list(csv.DictReader((SRC / 'ranking.csv').open(encoding='utf-8')))
    repl = {r['name']: r for r in csv.DictReader((SRC / 'pergame-repl.csv').open(encoding='utf-8'))}
    summ = json.loads((SRC / 'pergame-summary.json').read_text(encoding='utf-8'))
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
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore', lineterminator='\n')
        w.writeheader()
        for i, o in enumerate(rows, 1):
            o['rank'] = i
            w.writerow(o)
    srcs = {(SRC / n).relative_to(ROOT).as_posix(): sha(SRC / n)
            for n in ('ranking.csv', 'pergame-repl.csv', 'pergame-summary.json')}
    out = {
        'version': 'card 0.2.0+E070' if TAG == 'w075' else 'card 0.2.0 (w_vol=0 re-run)',
        'definition': 'OVR = 每場，含上場時間，相對替補水準：g_r = (pred - r_repl) * MPG / 36；'
                      '兩段映射錨點 g_r 的 PR1/PR50/PR99（MIN>=500 池）。能力值與 card 0.1.2 相同。',
        'rRepl_PR10_of_pred': summ['rRepl_PR10_of_pred'],
        'anchors': summ['anchors']['repl'],
        'poolSize': summ['poolSize'],
        'players': len(rows),
        'sources_sha256': srcs,
        'ruling': 'R-028（E-064 副版）',
        'generator': 'reports/card-0.2.0+E070-foul-volume/build_card.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('wrote', len(rows), 'rows; top ovr:', [o['ovr'] for o in rows[:5]])


if __name__ == '__main__':
    main()
