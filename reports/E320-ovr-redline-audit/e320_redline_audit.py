"""E-320 本機完整紅線驗收：對照現行 OVR 與雙核滾動 OVR（ADAPT_CT_k300 / HYB_CT_r35）在
1. 跨季樣本外下季 EPM*W（24-25 → 25-26，n=319）
2. 2025-26 2K27 OVR Spearman
3. 人類直覺硬紅線（Durant > VanVleet、前 30 名護框長人數）
4. 2026-27 本季前 15 名實際排名對照。"""
import csv, importlib.util, json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

_sp = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X269 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(X269)
P269 = X269.P


def z_map(d):
    vals = np.array(list(d.values()), float)
    mu, sd = float(vals.mean()), float(vals.std() + 1e-6)
    return {k: (v - mu) / sd for k, v in d.items()}


def load_t_net(season):
    sw = json.load(open(ROOT / f'reports/E314-multiseason-decomposed/work/swap-D_add-{season}.json', encoding='utf-8'))
    return {int(p): float(sw['ownPts100'][p]) - float(sw['oppPts100'][p]) for p in sw['ownPts100']}


def main():
    sn = json.load(open(HERE / 'e320_snaps.json', encoding='utf-8'))
    ref_mu, ref_sd = sn['ref_mu'], sn['ref_sd']

    # ===== 1. 跨季樣本外 EPM*W（2024-25 季末 → 2025-26 EPM*W，n=319） =====
    cur24 = json.load(open(ROOT / 'reports/E287-offdef-align-t/cur-2024-25.json', encoding='utf-8'))
    t24 = z_map(load_t_net('2024-25'))
    c24 = z_map({int(p): float(v['ovr']) for p, v in cur24.items()})
    sn24 = sn['snaps']['2024-25']
    _, mp25 = P269.pop_of('2025-26')
    epm25 = {}
    for r in csv.DictReader(open(ROOT / 'data/external-impact/epm_self/epm_2025-26.csv', encoding='utf-8-sig')):
        p = int(r['playerId'])
        if float(r['stintPoss']) >= 1000 and p in mp25:
            epm25[p] = (float(r['O']) + float(r['D'])) * P269.wfun(mp25[p])

    def score_player(pid, c_z, t_z, sn_d, mode):
        cz = c_z.get(pid, -0.5); tz = t_z.get(pid, cz)
        base = 0.5 * cz + 0.5 * tz
        rec = sn_d.get(str(pid))
        rz = ((rec['nn_raw'] - ref_mu) / ref_sd) if rec else base
        cm = rec['c_min'] if rec else 0.0
        if mode == 'CUR': return cz
        if mode == 'BASE_CT': return base
        if mode == 'ADAPT':
            w = (0.55 if pid in t_z else 0.75) * cm / (cm + (300.0 if pid in t_z else 150.0))
            return (1.0 - w) * base + w * rz
        if mode == 'HYB35': return 0.65 * base + 0.35 * rz
        raise ValueError(mode)

    print('=== 1. 嚴格樣本外下季 EPM*W（2024-25 → 2025-26） ===')
    pids24 = [int(p) for p in cur24 if int(p) in epm25]
    y25 = np.array([epm25[p] for p in pids24])
    for mode in ('CUR', 'BASE_CT', 'ADAPT', 'HYB35'):
        x = np.array([score_player(p, c24, t24, sn24, mode) for p in pids24])
        print(f'  {mode:8s}: rho = {spearmanr(x, y25)[0]:.4f} (n={len(pids24)})')

    # ===== 2 & 3. 2025-26 2K27 OVR 與人類直覺紅線（Durant > VanVleet、前30護框長人） =====
    card25 = list(csv.DictReader(open(ROOT / 'reports/card-0.3.0/ranking.csv', encoding='utf-8-sig')))
    # 讀 2K27 OVR（檔內欄位確認）
    k2_rows = list(csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')))
    k2_col = next((c for c in k2_rows[0] if c.lower() in ('ovr', 'overall', 'rating', '2k27')), None)
    k2_ovr = {P269.norm(r['name']): float(r[k2_col]) for r in k2_rows if k2_col and r.get(k2_col)}

    # 讀 2025-26 playerId 對應
    cur25 = json.load(open(ROOT / 'reports/E287-offdef-align-t/cur-2025-26.json', encoding='utf-8'))
    nm2pid = {P269.norm(v['name']): int(p) for p, v in cur25.items()}
    t25 = z_map(load_t_net('2025-26'))
    c25 = z_map({nm2pid[P269.norm(r['name'])]: float(r['ovr']) for r in card25 if P269.norm(r['name']) in nm2pid})
    sn25 = sn['snaps']['2025-26']

    # 護框長人定義（同 E-310）：pos C/PF 且 help >= MIN>=500 人群第 75 百分位
    helps = [float(r['help']) for r in card25 if float(r.get('MIN') or 0) >= 500 and r.get('help')]
    help_p75 = float(np.percentile(helps, 75))

    print(f'\n=== 2 & 3. 2025-26 2K27({k2_col}) 與人類直覺紅線 ===')
    for mode in ('CUR', 'BASE_CT', 'ADAPT', 'HYB35'):
        scored = []
        for r in card25:
            nm = P269.norm(r['name'])
            pid = nm2pid.get(nm)
            if pid is None: continue
            sc = score_player(pid, c25, t25, sn25, mode)
            is_rim_big = (r['pos'] in ('C', 'PF')) and (float(r.get('help') or 0) >= help_p75)
            scored.append((sc, r['name'], nm, float(r.get('MIN') or 0), is_rim_big))
        scored.sort(key=lambda x: -x[0])
        rk = {x[1]: i + 1 for i, x in enumerate(scored)}
        rim30 = sum(1 for x in scored[:30] if x[4])
        xk = [x[0] for x in scored if x[3] >= 500 and x[2] in k2_ovr]
        yk = [k2_ovr[x[2]] for x in scored if x[3] >= 500 and x[2] in k2_ovr]
        r_2k = spearmanr(xk, yk)[0] if xk else float('nan')
        kd, fvv = rk.get('Kevin Durant'), rk.get('Fred VanVleet')
        print(f'  {mode:8s}: 2K_OVR={r_2k:.4f} (n={len(xk)}) | KD=#{kd} vs FVV=#{fvv} (pass={kd is not None and fvv is not None and kd < fvv}) | RimBigsTop30={rim30}')

    # ===== 4. 2026-27 最新本季前 15 名實際排名對照（現行 inseason 0.3.0 vs ADAPT） =====
    live26 = list(csv.DictReader(open(ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-25/ranking.csv', encoding='utf-8-sig')))
    c26 = z_map({int(r['playerId']): float(r['ovr']) for r in live26})
    sn26 = sn['snaps']['2026-27']
    print('\n=== 4. 2026-27 本季前 15 名（ADAPT_CT_k300 vs 現行名次） ===')
    live_sc = []
    for r in live26:
        pid = int(r['playerId'])
        sc = score_player(pid, c26, t25, sn26, 'ADAPT')
        live_sc.append((sc, r['name'], r['team'], r['pos'], int(r['rank']), float(r['ovr'])))
    live_sc.sort(key=lambda x: -x[0])
    # 映射到與現行同均值/標準差方便直觀對照
    cur_ovrs = np.array([x[5] for x in live_sc]); new_raws = np.array([x[0] for x in live_sc])
    mapped = cur_ovrs.mean() + (new_raws - new_raws.mean()) * (cur_ovrs.std() / (new_raws.std() + 1e-6))
    for i, (sc, nm, tm, pos, old_rk, old_ov) in enumerate(live_sc[:15], 1):
        print(f'  {i:2d}. {nm:24s} {tm:3s} {pos:2s} | New~{mapped[i-1]:5.1f} (Old #{old_rk:2d}, {old_ov:5.1f})')


if __name__ == '__main__':
    main()
