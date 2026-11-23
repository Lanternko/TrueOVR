"""E-312 測試 F 逐場賽前預測（本機；不讀比分）。同 E-306 e306_pred.py pregame：比賽日前最新 live 夾、box＋matchup 混本季、
實際上場者＋賽前平均分鐘、N=2000、rng [229, gid]、主隊當 A／B 各算一次；TG 另把 blk36 欄換成當日 AG（tg_live）。
臂：B-cut、TG-cut（各 10 seed，逐 seed 存 mT）＋E-306 舊 cut 5 seed（重現對照）。場次＝2026-11-07～11-22 已完賽。
  python -X utf8 reports/E312-tg-r3-retrain/e312_pred_f.py      （權重先從 5090 拷回 results/weights/）"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tg_live as TL
MAIN = TL.MAIN
sys.path.insert(0, os.path.join(MAIN, 'scripts')); sys.path.insert(0, os.path.join(MAIN, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np, torch
import actual_blend as ab
import e229_live
from e227_model import LineupNet, predict

torch.set_num_threads(4)
DRAWS = 2000; LIVE = str(ab.LIVE); LO, HI = '2026-11-07', '2026-11-22'
BLK_J = len(e229_live.ATTRS) + e229_live.STATS.index('blk36'); FN = len(e229_live.ATTRS) + len(e229_live.STATS)
WORK = os.path.join(HERE, 'work'); OUT = os.path.join(WORK, 'pred-f.json')
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
ARMS = {'B': (os.path.join(HERE, 'results', 'weights', 'B-cut-{}.pt'), 10, False),
        'TG': (os.path.join(HERE, 'results', 'weights', 'TG-cut-{}.pt'), 10, True),
        'E306cut': (os.path.join(MAIN, 'reports', 'E306-team-model-r3', 'results', 'weights', 'cut-{}.pt'), 5, False)}


def load(pat, n):
    out = []
    for sd in range(n):
        m = LineupNet(FN); m.load_state_dict(torch.load(pat.format(sd), map_location='cpu')); m.eval(); out.append(m)
    return out


def seed_margins(C, g, nets, B):
    C.B = B
    Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
    rng = np.random.default_rng([229, int(g['gid'])])
    A, Bb = C.draw(Rh, lh, rh, rng, DRAWS), C.draw(Ra, la, ra, rng, DRAWS)
    X = torch.from_numpy(np.concatenate([np.concatenate([A, Bb], 1), np.concatenate([Bb, A], 1)], 0))
    T = [X, POS.expand(2 * DRAWS, -1), SIDE.expand(2 * DRAWS, -1)]; sc = C.avg_poss / 100; res = []
    for m in nets:
        o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy()
        pf = 100.0 * 0.5 * (o[:DRAWS, 0].mean() + o[DRAWS:, 1].mean()); pa = 100.0 * 0.5 * (o[:DRAWS, 1].mean() + o[DRAWS:, 0].mean())
        res.append(float((pf - pa) * sc))
    return res


def main():
    doc = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    nets = {k: load(p, n) for k, (p, n, _) in ARMS.items()}
    G = ab.played_games(); dates = {k: v['date'] for k, v in G.items()}
    G = {k: v for k, v in G.items() if LO <= v['date'] <= HI}
    ab._rotations(G)
    per_game = TL.pbp_by_game(cache=os.path.join(WORK, 'pbp-per-game.json'))
    prior = set(e229_live.load_player_table('2025-26')); pag = TL.prior_ag()
    groups = collections.defaultdict(list)
    for g in G.values():
        groups[(g['date'], os.path.join(LIVE, g['folder']))].append(g)
    for (d, ldir), gs in sorted(groups.items()):
        todo = [g for g in gs if g['gid'] not in doc]
        if not todo:
            continue
        names = {p: 1 for g in todo for s in ('home', 'away') for p, _ in g['rot_' + s]}
        C, info = e229_live.make_ctx(d, ldir, names, ('matchup',), None)
        B0 = C.B
        agm, ainf = TL.ag_mixed(e229_live.season_box(d), per_game, dates, d, pag)
        Bt, pinf = TL.patch(B0, prior, agm, BLK_J)
        for g in todo:
            e = dict(date=g['date'], home=g['home'], away=g['away'], folder=os.path.basename(ldir), agPatch=pinf, nEvGames=ainf['nEvGames'], seeds={})
            for k, (_, _, tg) in ARMS.items():
                e['seeds'][k] = seed_margins(C, g, nets[k], Bt if tg else B0)
            doc[g['gid']] = e
        json.dump(doc, open(OUT + '.tmp', 'w', encoding='utf-8')); os.replace(OUT + '.tmp', OUT)
        print(d, os.path.basename(ldir), len(todo), flush=True)
    print('done', len(doc), 'games ->', OUT)


if __name__ == '__main__':
    main()
