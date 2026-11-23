"""E-312 資料準備（本機、不讀比分、不開子程序）：重建 E-306 feat-cut（逐位元核對），再換 AG → ship/feat-cut-tg.npz。
  python -X utf8 reports/E312-tg-r3-retrain/prep.py"""
import hashlib, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tg_live as TL
MAIN = TL.MAIN
sys.path.insert(0, os.path.join(MAIN, 'scripts')); sys.path.insert(0, os.path.join(MAIN, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np
import actual_blend as ab
import e229_live

SHIP = os.path.join(HERE, 'ship'); WORK = os.path.join(HERE, 'work')
os.makedirs(SHIP, exist_ok=True); os.makedirs(WORK, exist_ok=True)
E306S = os.path.join(MAIN, 'reports', 'E306-team-model-r3', 'ship')
CUT_TODAY, CUT_DIR = '2026-11-07', '2026-11-06'
BLK_J = len(e229_live.ATTRS) + e229_live.STATS.index('blk36')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()

z = np.load(os.path.join(E306S, 'feat-cut.npz'))
pids = [str(p) for p in z['pids']]
import csv, gzip      # names 同 E-306 prep：2026-27 全部 stint 上場者
with gzip.open(os.path.join(E306S, 'stints-2627.csv.gz'), 'rt', encoding='utf-8') as f:
    names = {r[f'{X}{j}']: 1 for r in csv.DictReader(f) for X in 'ab' for j in range(5)}
B, tab, info = e229_live.build(CUT_TODAY, os.path.join(e229_live.LIVE_ROOT, CUT_DIR), names, ('matchup',))
bad = [p for i, p in enumerate(pids) if p not in B or not (np.array_equal(B[p][0], z['vals'][i]) and np.array_equal(B[p][1], z['mask'][i]))]
same = not bad and set(B) == set(pids)
print('rebuild mismatch', len(bad), len(set(B) ^ set(pids)), bad[:5])
assert same, 'feat-cut 重建與 E-306 不一致'
G = ab.played_games(); dates = {k: v['date'] for k, v in G.items()}
per_game = TL.pbp_by_game(cache=os.path.join(WORK, 'pbp-per-game.json'))
prior = e229_live.load_player_table('2025-26')
agm, ainf = TL.ag_mixed(e229_live.season_box(CUT_TODAY), per_game, dates, CUT_TODAY)
Bt, pinf = TL.patch(B, set(prior), agm, BLK_J)
p = os.path.join(SHIP, 'feat-cut-tg.npz')
np.savez_compressed(p, pids=z['pids'], vals=np.stack([Bt[q][0] for q in pids]), mask=np.stack([Bt[q][1] for q in pids]))
m = np.array([B[q][1][BLK_J] == 1 for q in pids])
corr = float(np.corrcoef([B[q][0][BLK_J] for q, k in zip(pids, m) if k], [Bt[q][0][BLK_J] for q, k in zip(pids, m) if k])[0, 1])
x307 = os.path.join(SHIP, 'x307'); os.makedirs(os.path.join(x307, 'data'), exist_ok=True)
shutil.copy(os.path.join(TL.E307, 'x_lib.py'), x307)
for s in ('2021-22', '2022-23', '2023-24', '2024-25', '2025-26'):
    shutil.copy(os.path.join(TL.E307, 'data', f'feat-{s}.csv'), os.path.join(x307, 'data'))
played_cut = [g for g, d in dates.items() if d < CUT_TODAY]
man = dict(featCutRebuildIdentical=same, featCutE306sha=sha(os.path.join(E306S, 'feat-cut.npz')), featCutTG=dict(sha256=sha(p), **pinf),
           ag=dict(leagueR=ainf['leagueR'], nCur=ainf['nCur'], nEvGames=ainf['nEvGames'], playedBeforeCut=len(played_cut),
                   pbpMissing=sorted(g for g in dates if g not in per_game)),
           corrBlk36VsAG=corr, nPids=len(pids), blkJ=BLK_J)
json.dump(man, open(os.path.join(HERE, 'prep-manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(man, ensure_ascii=False))
