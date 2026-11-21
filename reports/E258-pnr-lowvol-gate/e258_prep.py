"""E-258 前置：E-255 擋拆 pnr 欄的「率」改三種低回合處理，各輸出一份 players json（量 ṽ 不變）。
- G50 ：率百分位只在 POSS≥50 的球員裡排，其餘 ã=0（＝聯盟平均，只看量）
- G100：同上，門檻 POSS≥100
- REL ：率百分位照全部排，再乘可信度 POSS/(POSS+k) 後重新 z（低回合自然趨近 0）
用法：python -I -B -X utf8 reports/E258-pnr-lowvol-gate/e258_prep.py [--check]
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E255-pnr-handler-lineup-tf'))
import e255_prep as P  # noqa: E402

VARIANTS = ['G50', 'G100', 'REL']


def rate_z(variant, rate, poss, k):
    if variant in ('G50', 'G100'):
        g = 50 if variant == 'G50' else 100
        ok = poss >= g
        za = np.zeros(len(rate))
        za[ok] = P.zscore(P.pct(rate[ok]))
        return za, int(ok.sum())
    rel = poss / (poss + k)
    return P.zscore(P.zscore(P.pct(rate)) * rel), int((poss >= 50).sum())


def build(variant, season, base_tb):
    pids = base_tb['pids']
    c_min = P.season_minutes(season)
    poss_c, pts_c, score_c = P.synergy(season)
    k, mu, s2, vt = P.est_k(poss_c, pts_c, score_c)
    idx = np.where(np.array([c_min[p] > 0 for p in pids]))[0]
    poss = np.array([poss_c[pids[i]] for i in idx])
    vol = np.array([poss_c[pids[i]] / c_min[pids[i]] * 36.0 for i in idx])
    rate = np.array([(pts_c[pids[i]] + k * mu) / (poss_c[pids[i]] + k) for i in idx])
    zv = P.zscore(P.pct(vol))
    za, n_rate = rate_z(variant, rate, poss, k)
    rho = float(np.mean(zv * za) / (np.std(za) + 1e-12))  # za 有可能變異 <1（門檻版），ρ 以相關係數計
    rho = float(np.corrcoef(zv, za)[0, 1]) if np.std(za) > 0 else 0.0
    N = len(pids)
    ZV = np.zeros(N); ZA = np.zeros(N); M = np.zeros(N); PV = np.zeros(N); PA = np.zeros(N)
    ZV[idx] = zv; ZA[idx] = za; M[idx] = 1.0
    md = {'kf': round(k, 3), 'mu': round(mu, 5), 'rho': round(rho, 5), 'n_valid': int(len(idx)), 'n_rate': n_rate,
          'zv': [round(float(x), 6) for x in ZV], 'za': [round(float(x), 6) for x in ZA], 'zval': [0.0] * N,
          'pv': [0.0] * N, 'pa': [0.0] * N, 'mask3': [float(x) for x in M]}
    tb = dict(base_tb)
    tb['fallback'] = False
    tb['modes'] = {'train': md, 'full': md}
    tb['pnr_raw'] = {pids[i]: [round(float(vol[j]), 4), round(float(rate[j]), 4), round(float(poss[j]), 1)] for j, i in enumerate(idx)}
    tb['base_z'] = dict(tb['base_z']); tb['base_z']['pnr'] = [0.0] * N
    tb['base_m'] = dict(tb['base_m']); tb['base_m']['pnr'] = [0.0] * N
    return tb


def main():
    check = '--check' in sys.argv
    base = json.loads(P.E245.read_text(encoding='utf-8'))
    pre_ok = (not check) and P.sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip()
    for v in VARIANTS:
        tabs = {}
        for s in P.SEASONS:
            tabs[s] = build(v, s, base['player_tables'][s])
            m = tabs[s]['modes']['full']
            if s in ('2022-23', '2024-25'):
                print(v, s, 'n_rate', m['n_rate'], 'rho', m['rho'])
        if check:
            # 低回合診斷：2024-25 POSS<50 球員在 w=0.6 下的擋拆分數中位數
            from scipy.stats import rankdata
            md = tabs['2024-25']['modes']['full']; raw = tabs['2024-25']['pnr_raw']; pids = tabs['2024-25']['pids']
            ok = np.array(md['mask3']) > 0; w = 0.6; rho = md['rho']
            z = (w * np.array(md['zv']) + (1 - w) * np.array(md['za'])) / np.sqrt(w * w + (1 - w) ** 2 + 2 * w * (1 - w) * rho)
            sc = np.zeros(len(z)); sc[ok] = rankdata(z[ok], method='average') / ok.sum() * 99
            low = [sc[i] for i, p in enumerate(pids) if ok[i] and raw.get(p, [0, 0, 0])[2] < 50]
            nm = {n: round(float(sc[i]), 1) for i, n in enumerate(base['player_tables']['2024-25']['names']) if n in ('Jeremy Sochan', 'John Collins', 'Cam Thomas', 'Deni Avdija')}
            print(v, 'POSS<50 n', len(low), 'median score', round(float(np.median(low)), 1), 'p90', round(float(np.percentile(low, 90)), 1), nm)
            continue
        out = {'prereg_sha256_ok': pre_ok, 'variant': v, 'seasons': P.SEASONS, 'attrs': base['attrs'] + ['pnr'],
               'player_tables': tabs, 'e179': base['e179'], 'e179_base_attr': base['e179_base_attr'], 'e179_pos': base['e179_pos']}
        d = HERE / v; d.mkdir(exist_ok=True)
        (d / 'e255_players.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
        print('wrote', v, 'prereg_ok', pre_ok)


if __name__ == '__main__':
    main()
