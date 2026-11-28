"""E-333（gpu5090）：訓練 E-321 冠軍 4 異質家族（SetPool_age, Ridge_age, D_add_age, M2_age）全 5 季正式上線權重。
每家族 5-fold × 4 seeds = 20 模型，共 80 個正式 .pt 權重，可直接接管線上球隊評分（4 季 LOSO 驗證 Brier 0.21270→0.20897 C0 / 0.20302 C2）。"""
import argparse, json, os, sys, time
import numpy as np
import torch

ALL_SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--e227', required=True); ap.add_argument('--e315', required=True)
    ap.add_argument('--e321', required=True); ap.add_argument('--dob', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--seeds', type=int, default=4)
    args = ap.parse_args()

    sys.path.insert(0, args.e227); sys.path.insert(0, args.e315); sys.path.insert(0, args.e321)
    import e227_common, e227_model, e315_lib, e321_scaleup_loso as e321

    os.makedirs(args.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    dob = e321.load_dob(args.dob)
    feat_cache = {s: e321.build_features_age(s, e227_model, e227_common, e315_lib, dob) for s in ALL_SEASONS}
    F_dim = len(next(iter(feat_cache['2025-26'].values()))[0])
    rows = e227_common.load_rows(ALL_SEASONS)
    print(f'E-333 PROD dev={dev} seasons=5 rows={len(rows)} F={F_dim} seeds_per_fold={args.seeds}', flush=True)

    fams = ('SetPool_age', 'Ridge_age', 'D_add_age', 'M2_age')
    t0 = time.time()
    meta = {'seasons': ALL_SEASONS, 'F': F_dim, 'fams': list(fams), 'models_per_fam': 5 * args.seeds}
    for fold in range(5):
        tr = [r for r in rows if r['fold'] != fold]; va = [r for r in rows if r['fold'] == fold]
        means = e227_model.season_means(tr); s2 = e227_model.sigma2_of(tr, means)
        Tt = e321.swap_augment(e321.build_tensors(tr, feat_cache, means, F_dim))
        Tv = e321.build_tensors(va, feat_cache, means, F_dim)
        for s_i in range(args.seeds):
            sd = fold * args.seeds + s_i + 100
            for fam in fams:
                net = e321.train_one(fam, sd, Tt, Tv, s2, dev, e315_lib)
                torch.save(net.state_dict(), os.path.join(args.out, f'{fam}_f{fold}_s{s_i}.pt'))
        print(f'  fold {fold} done ({4 * args.seeds} models) elapsed {round(time.time()-t0)}s', flush=True)
    json.dump(meta, open(os.path.join(args.out, 'meta.json'), 'w'), indent=2)
    print(f'ALL_DONE_E333_PROD total {round(time.time()-t0)}s', flush=True)


if __name__ == '__main__':
    main()
