"""E-306 本機逐場 T 預測（不寫線上快取；結果存 work/）。同 actual_blend 的做法：實際上場者＋比賽日前自己的平均分鐘、
N=2000、rng [229, gid]、主隊當 A／B 各算一次。同一場各權重共用同一組抽樣。
  python -I -X utf8 e306_pred.py pregame online[,cut,cutw3]      234 場賽前 T（統一規則：比賽日前最新 live 夾、box＋matchup 混本季）
  python -I -X utf8 e306_pred.py today online[,full,fullw3]      今天的 T（11-21、live/2026-11-20、線上四類混合）對所有已完賽場次
  python -I -X utf8 e306_pred.py ckpt:2026-11-07 online          檢查點當天的 T，場次到檢查點後 7 天
"""
import collections, datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
import numpy as np, torch
import actual_blend as ab
import e229_live
from t_lib import F
from e227_model import LineupNet, predict

torch.set_num_threads(4)
DRAWS = 2000; LIVE = str(ab.LIVE); CUT = '2026-11-07'
WORK = os.path.join(HERE, 'work'); os.makedirs(WORK, exist_ok=True)
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)


def load_nets(tag):
    pat = (os.path.join(ROOT, 'reports', 'E227-lineup-transformer-r2', 'results', 'weights', 'R2-stats-{}.pt') if tag == 'online'
           else os.path.join(HERE, 'results', 'weights', tag + '-{}.pt'))
    out = []
    for sd in range(5):
        n = LineupNet(F); n.load_state_dict(torch.load(pat.format(sd), map_location='cpu')); n.eval(); out.append(n)
    return out


def one(C, g, nets):
    Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
    rng = np.random.default_rng([229, int(g['gid'])])
    A, B = C.draw(Rh, lh, rh, rng, DRAWS), C.draw(Ra, la, ra, rng, DRAWS)
    X = torch.from_numpy(np.concatenate([np.concatenate([A, B], 1), np.concatenate([B, A], 1)], 0))
    T = [X, POS.expand(2 * DRAWS, -1), SIDE.expand(2 * DRAWS, -1)]; sc = C.avg_poss / 100; res = {}
    for tag, ns in nets.items():
        pf = pa = 0.0
        for m in ns:
            o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy()
            pf += 100.0 * 0.5 * (o[:DRAWS, 0].mean() + o[DRAWS:, 1].mean()) / len(ns)
            pa += 100.0 * 0.5 * (o[:DRAWS, 1].mean() + o[DRAWS:, 0].mean()) / len(ns)
        res[tag] = dict(pf=float(pf * sc), pa=float(pa * sc), mT=float((pf - pa) * sc))
    return res


def main():
    mode, tags = sys.argv[1], sys.argv[2].split(',')
    out_f = os.path.join(WORK, 'pred-' + mode.replace(':', '-') + '.json')
    doc = json.load(open(out_f, encoding='utf-8')) if os.path.exists(out_f) else {}
    nets = {t: load_nets(t) for t in tags}
    G = ab.played_games(); fl = ab._folders()
    if mode == 'pregame':
        ab._rotations(G)
        groups = collections.defaultdict(list)
        for g in G.values():
            groups[(g['date'], os.path.join(LIVE, g['folder']), ('matchup',))].append(g)
    else:
        if mode == 'today':
            today, folder, blend = '2026-11-21', '2026-11-20', None
            G = {k: v for k, v in G.items() if v['date'] < today}
        else:
            today = mode.split(':')[1]; folder = [f for f in fl if f < today][-1]; blend = ('matchup',)
            end = (dt.date.fromisoformat(today) + dt.timedelta(days=7)).isoformat()
            G = {k: v for k, v in G.items() if v['date'] < end}
        ab._rotations(G, folder=folder)
        groups = {(today, os.path.join(LIVE, folder), blend): list(G.values())}
    n = 0
    for (d, ldir, blend), gs in sorted(groups.items(), key=lambda x: x[0][0]):
        def want(g, t):
            return not (mode == 'pregame' and t != 'online' and g['date'] < CUT)
        todo = [g for g in gs if any(want(g, t) and t not in doc.get(g['gid'], {}).get('p', {}) for t in tags)]
        if not todo:
            continue
        names = {p: 1 for g in todo for s in ('home', 'away') for p, _ in g['rot_' + s]}
        C, info = e229_live.make_ctx(d, ldir, names, blend, None)
        for g in todo:
            use = {t: nets[t] for t in tags if want(g, t) and t not in doc.get(g['gid'], {}).get('p', {})}
            e = doc.setdefault(g['gid'], dict(date=g['date'], home=g['home'], away=g['away'], folder=os.path.basename(ldir), p={}))
            e['p'].update(one(C, g, use)); n += 1
        json.dump(doc, open(out_f, 'w', encoding='utf-8'))
        print(d, os.path.basename(ldir), len(todo), flush=True)
    print('done', mode, tags, n, 'games ->', out_f)


if __name__ == '__main__':
    main()
