"""E-065 判準 V1／V2（lead 自算，照凍結預註冊 sha256 01ff0b67…）。

答案：A→B＝RAPM_B pooledNet × MPG_B，B→A 反之（同 E-064 §3.2）。
人群：winimp.csv（2025-26 MIN≥500 有卡）∩ 評估半 pooledPoss≥2500 ∩ A、B 兩半各 ≥5 場。
V1：ρ(WinImp, 答案) − ρ(OVR 0.1.2, 答案)，球員 bootstrap 2000（seed 1），兩方向；90% 下界 > −0.02 不輸、> 0 較好。
V2：card 0.1.2 全域名次 ≤60 且在人群內者；殘差＝答案名次 − OVR 名次（人群內排名，正＝OVR 高估）；
    defenseBonus ≥ 1.0 組平均殘差，bootstrap 90% 下界 > 0 → 高估。另列其餘組供對照。
用法：python -I reports/card-0.1.2+E065-inout-wins/verdict_e065.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
RAPM = {h: {r['name']: r for r in csv.DictReader((ROOT / f'reports/ovr-v58-holdout-2025-26/rapm-{h}.csv').open(encoding='utf-8'))} for h in 'AB'}
MPG = {h: {r['playerId']: r for r in csv.DictReader((E064 / f'mpg-{h}.csv').open(encoding='utf-8'))} for h in 'AB'}
W = list(csv.DictReader((HERE / 'winimp.csv').open(encoding='utf-8-sig')))
THR, MIN_G, B, SEED = 2500, 5, 2000, 1


def pid(name):
    for h in 'AB':
        if name in RAPM[h]:
            return RAPM[h][name]['playerId']


def pool(ev):
    out = []
    for r in W:
        n, p = r['name'], pid(r['name'])
        if n not in RAPM[ev] or float(RAPM[ev][n]['pooledPoss']) < THR or p is None:
            continue
        if not all(p in MPG[h] and int(MPG[h][p]['gp']) >= MIN_G for h in 'AB'):
            continue
        out.append((r, float(RAPM[ev][n]['pooledNet']) * float(MPG[ev][p]['mpg'])))
    return out


def ci(x):
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]


def main():
    rng = np.random.default_rng(SEED)
    res = {'preregSha256': (HERE / 'preregistration.sha256').read_text().split()[0], 'directions': {}}
    for d, ev in (('AB', 'B'), ('BA', 'A')):
        P = pool(ev)
        ans = np.array([a for _, a in P])
        wi = np.array([float(r['winsPer82']) for r, _ in P])
        ov = np.array([float(r['ovr012']) for r, _ in P])
        diff = []
        for _ in range(B):
            i = rng.integers(0, len(P), len(P))
            diff.append(spearmanr(wi[i], ans[i])[0] - spearmanr(ov[i], ans[i])[0])
        rw, ro = spearmanr(wi, ans)[0], spearmanr(ov, ans)[0]
        # V2
        ans_rank = rankdata(-ans, method='average')
        ovr_rank = rankdata(-ov, method='average')
        top = [k for k, (r, _) in enumerate(P) if int(r['ovrRank']) <= 60]
        hi = [k for k in top if float(P[k][0]['defenseBonus']) >= 1.0]
        lo = [k for k in top if float(P[k][0]['defenseBonus']) < 1.0]
        resid = ans_rank - ovr_rank
        boot = lambda ks: [float(resid[rng.choice(ks, len(ks))].mean()) for _ in range(B)]
        bh, bl = boot(hi), boot(lo)
        res['directions'][d] = {
            'n': len(P), 'rhoWinImp': float(rw), 'rhoOVR': float(ro), 'diff': float(rw - ro), 'diffCI90': ci(diff),
            'V2': {'nTop60InPool': len(top), 'nHighBonus': len(hi), 'meanResidHigh': float(resid[hi].mean()), 'ciHigh': ci(bh),
                   'nLowBonus': len(lo), 'meanResidLow': float(resid[lo].mean()), 'ciLow': ci(bl),
                   'highBonus': sorted([(P[k][0]['name'], int(P[k][0]['ovrRank']), float(resid[k])) for k in hi], key=lambda t: -t[2])},
        }
    D = res['directions']
    lo1 = min(D[d]['diffCI90'][0] for d in D)
    res['V1'] = {'pass_notWorse': all(D[d]['diffCI90'][0] > -0.02 for d in D), 'pass_better': all(D[d]['diffCI90'][0] > 0 for d in D), 'minLower': lo1}
    res['V2'] = {'pass_overrated': all(D[d]['V2']['ciHigh'][0] > 0 for d in D)}
    (HERE / 'verdict.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    for d in D:
        x = D[d]
        print(d, 'n', x['n'], 'rhoW %.3f rhoO %.3f diff %+.3f CI %s' % (x['rhoWinImp'], x['rhoOVR'], x['diff'], [round(v, 3) for v in x['diffCI90']]))
        v = x['V2']
        print('   V2 high n=%d mean %+.1f CI %s | low n=%d mean %+.1f CI %s' % (v['nHighBonus'], v['meanResidHigh'], [round(t, 1) for t in v['ciHigh']],
              v['nLowBonus'], v['meanResidLow'], [round(t, 1) for t in v['ciLow']]))
        print('   ', v['highBonus'])
    print('V1', res['V1'], 'V2', res['V2'])


if __name__ == '__main__':
    main()
