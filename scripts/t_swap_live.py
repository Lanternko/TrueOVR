"""R-xxx（E-287 上線）：本季 Transformer 換人值 → <live_dir>/t-swap.json，給 build_inseason_viewer 的 OFF／DEF 欄混合用。
T＝上線球隊評分同一套（E-227 R2-stats 五個 seed，e229_live.make_ctx 的 live 混合特徵表）。
抽樣同 E-274／E-287：3000 組、seed 20261108，每組 10 人（4 隊友＋5 對手＋1 備用）從「名次人群」（sn.mpg_pool）抽，所有人共用同一批陣容；
x 換進隊友第 5 人（x 已在組裡就用備用補），位置依 hkey 排，主客兩向平均。
輸出 ownPts100（本隊每 100 回合得分，進攻）、oppPts100（對手每 100 回合得分，防守，越低越好）、pool（z 分數的人群）。
用法（repo root）：python -I -X utf8 scripts/t_swap_live.py <live_dir>"""
import csv, datetime as dt, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reports/E229-transformer-vs-m0-forward'))
sys.path.insert(0, str(ROOT / 'reports/E228-transformer-team-rating'))
sys.path.insert(0, str(ROOT / 'scripts'))
N_DRAWS, SEED = 3000, 20261108


def main(ldir: Path, threads: int = 4) -> int:
    import numpy as np
    import torch
    import e229_live
    from e227_model import predict
    import season_nav as sn
    torch.set_num_threads(threads)
    t0 = time.time()
    meta = json.loads((ldir / 'meta.json').read_text(encoding='utf-8'))
    today = (dt.date.fromisoformat(meta['dataCutoff']) + dt.timedelta(days=1)).isoformat()   # season_box 取 GAME_DATE < today
    rows = list(csv.DictReader(open(ldir / 'ranking.csv', encoding='utf-8')))
    C, _ = e229_live.make_ctx(today, str(ldir))
    pool = sn.mpg_pool({r['playerId']: float(r['MIN26'] or 0) / int(r['N']) for r in rows if int(r['N'])})
    pool = sorted(p for p in pool if p in C.B)
    ev = sorted({r['playerId'] for r in rows if r['playerId'] in C.B} | set(pool))
    rng = np.random.default_rng(SEED)
    draws = [list(rng.choice(pool, 10, replace=False)) for _ in range(N_DRAWS)]
    V = {p: C.vec(p) for p in ev}
    order = lambda l: sorted(l, key=C.hkey)
    A = np.stack([np.stack([V[p] for p in order(d[4:9])]) for d in draws])
    pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    N = N_DRAWS
    own, opp = {}, {}
    for x in ev:
        H = [[d[9] if q == x else q for q in d[:4]] for d in draws]
        Ao = A.copy()
        for i, d in enumerate(draws):
            if x in d[4:9]:
                Ao[i] = np.stack([V[p] for p in order([d[9] if q == x else q for q in d[4:9]])])
        Hs = np.stack([np.stack([V[p] for p in order(m + [x])]) for m in H])
        X = torch.from_numpy(np.concatenate([np.concatenate([Hs, Ao], 1), np.concatenate([Ao, Hs], 1)], 0))
        T = [X, pos.expand(2 * N, -1), side.expand(2 * N, -1)]
        o_, d_ = [], []
        for m in C.nets:
            o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy() * 100
            o_.append(0.5 * (o[:N, 0] + o[N:, 1])); d_.append(0.5 * (o[:N, 1] + o[N:, 0]))
        own[x] = round(float(np.mean(o_)), 4); opp[x] = round(float(np.mean(d_)), 4)
    out = {'dataCutoff': meta['dataCutoff'], 'version': meta.get('version'), 'model': 'E227-R2-stats (e229_live)', 'draws': N, 'seed': SEED,
           'pool': pool, 'ownPts100': own, 'oppPts100': opp, 'seconds': round(time.time() - t0, 1)}
    (ldir / 't-swap.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f't-swap：{len(ev)} 人（名次人群 {len(pool)}），{out["seconds"]} 秒')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(Path(sys.argv[1]).resolve()))
