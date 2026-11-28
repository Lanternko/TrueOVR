"""E-306 資料準備（本機，純 Python、不開子程序）。輸出到 ./ship/（整包上傳 5090）：
  stints-2627.csv.gz        2026-27 全部可重建 stint（split=train、fold=1、加 date 欄）
  feat-full.npz／feat-cut.npz  2026-27 球員特徵（e229_live.build；full＝截至 11-21 線上同款，cut＝截至 11-07、box＋matchup 混本季）
  stints-2526-first.csv.gz  2025-26 依日期前 235 場的 stint（測試 M）
  mock-games.json           2025-26 場次序號、主客、是否在前 235 場（不含比分）
用法：python -I -X utf8 reports/E306-team-model-r3/prep.py"""
import csv, gzip, hashlib, io, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SHIP = os.path.join(HERE, 'ship'); os.makedirs(SHIP, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E225-lineup-transformer'))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np
import actual_blend as ab
import build_dataset as bd
import e229_live

FULL_TODAY, CUT_TODAY, CUT_LAST = '2026-11-21', '2026-11-07', '2026-11-06'
LIVE = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')
COLS = ['season', 'gid', 'date', 'period', 'sec', 'split', 'fold'] + [f'{X}{j}' for X in 'ab' for j in range(5)] + [f'p{X}{j}' for X in 'ab' for j in range(5)] + ['teama', 'teamb'] + [f'{c}{X}' for X in 'ab' for c in bd.SIDE]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def write_rows(name, rows):
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=COLS, extrasaction='ignore', lineterminator='\n'); w.writeheader()
    for r in rows:
        w.writerow(r)
    p = os.path.join(SHIP, name)
    with gzip.open(p, 'wt', encoding='utf-8') as f:
        f.write(buf.getvalue())
    return p


def save_feat(name, today, ldir, blend, names):
    B, tab, info = e229_live.build(today, ldir, names, blend)
    pids = sorted(B)
    p = os.path.join(SHIP, name)
    np.savez_compressed(p, pids=np.array(pids), vals=np.stack([B[q][0] for q in pids]), mask=np.stack([B[q][1] for q in pids]))
    return p, info


man = {}
# 1. 2026-27 stints
G = ab.played_games()
players = bd.load_players('2026-27')[0]
rows = []
for r in bd.stint_rows('2026-27', bd.STINTS['2026-27'], players):
    if r['gid'] not in G:
        continue
    r['split'], r['fold'], r['date'] = 'train', 1, G[r['gid']]['date']
    rows.append(r)
gids = {r['gid'] for r in rows}
p = write_rows('stints-2627.csv.gz', rows)
man['stints2627'] = dict(rows=len(rows), games=len(gids), played=len(G), missing=sorted(set(G) - gids),
                         cutGames=len({r['gid'] for r in rows if r['date'] <= CUT_LAST}), sha256=sha(p), liveRanking=os.path.basename(os.path.dirname(bd.live_ranking())))
names = {str(r[f'{X}{j}']): 1 for r in rows for X in 'ab' for j in range(5)}
# 2. 特徵
p, info = save_feat('feat-full.npz', FULL_TODAY, os.path.join(LIVE, '2026-11-20'), None, names); man['featFull'] = dict(info=info, sha256=sha(p))
p, info = save_feat('feat-cut.npz', CUT_TODAY, os.path.join(LIVE, CUT_LAST), ('matchup',), names); man['featCut'] = dict(info=info, sha256=sha(p))
# 3. 2025-26 前 235 場
inp = json.load(open(os.path.join(ROOT, 'reports', 'E208-team-rating', 'inputs.json'), encoding='utf-8'))
gs = sorted(inp['games'], key=lambda g: (g['date'], g['id']))
first = {g['id'] for g in gs[:235]}; date = {g['id']: g['date'] for g in gs}
rows = []
with gzip.open(os.path.join(ROOT, 'reports', 'E225-lineup-transformer', 'data', 'stints-2025-26.csv.gz'), 'rt', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['gid'] in first:
            r['split'], r['fold'], r['date'] = 'train', 1, date[r['gid']]
            rows.append(r)
p = write_rows('stints-2526-first.csv.gz', rows)
man['stints2526first'] = dict(rows=len(rows), games=len({r['gid'] for r in rows}), lastDate=gs[234]['date'], sha256=sha(p))
json.dump([dict(i=g['i'], id=g['id'], date=g['date'], home=g['home'], away=g['away'], first=g['id'] in first) for g in inp['games']],
          open(os.path.join(SHIP, 'mock-games.json'), 'w'))
shutil.copy(os.path.join(ROOT, 'reports', 'E223-team-rating', 'work', 'lineups-2526.json'), os.path.join(SHIP, 'lineups-2526.json'))
json.dump(man, open(os.path.join(HERE, 'prep-manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(man, ensure_ascii=False)[:1500])
