"""L-057 direction check on synthetic distributions only (no real data): gap scale (r99-r90)/1.044 vs full SD, and SD_top (E-097) vs SD."""
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
rng = np.random.default_rng(0)
N = 400_000
dists = {
    'normal': rng.normal(0, 1, N),
    'lognormal s=0.5 (右偏)': rng.lognormal(0, 0.5, N),
    'lognormal s=1.0 (很右偏)': rng.lognormal(0, 1.0, N),
    'beta(5,2) (左偏、頂端擠)': rng.beta(5, 2, N),
    'uniform (頂端截平)': rng.uniform(0, 1, N),
}
Z = 2.3263 - 1.2816
print(f'{"分布":<26}{"gap/1.044 ÷ SD":>16}{"SD_top ÷ SD":>14}')
for k, x in dists.items():
    r90, r99 = np.percentile(x, [90, 99])
    sd = x.std()
    print(f'{k:<26}{(r99 - r90) / Z / sd:>16.2f}{x[x >= r90].std() / sd:>14.2f}')
# 4 seasons pooled with season-mean shifts of 0.2 SD: pooled SD vs within-season SD
shift = rng.normal(0, 0.2, 4)
pool = np.concatenate([rng.normal(m, 1, N // 4) for m in shift])
print('4 季合併（季平均差 0.2 SD）：合併 SD ÷ 單季 SD =', round(pool.std(), 3))
