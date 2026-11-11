"""E-296 A 部分：卡片池 S2–S5（2025-26 card 0.2.14a）＋樣本外 2026-27 實際分鐘。"""
import sys, csv, json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP)); from armlib import *
R = list(csv.DictReader(open(ROOT / 'reports/card-0.2.14a/ranking.csv', encoding='utf8')))
live = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08/ranking.csv', encoding='utf8'))}
# 隊伍：2025-26 卡沒有隊欄，用 bio25 TEAM
bio = json.load(open(ROOT / 'data/benchmark-source/bio.json', encoding='utf8'))
rs = bio['resultSets'][0] if 'resultSets' in bio else bio['data']['resultSets'][0]
H = rs['headers']; team = {r[H.index('PLAYER_NAME')]: r[H.index('TEAM_ABBREVIATION')] for r in rs['rowSet']}
P = []
for r in R:
    m = float(r['mpg']); g0 = float(r['gRepl'])
    D = g0 / W(m) if m > 0 else float(r['predictedPer36']) - R_REPL
    P.append(dict(name=r['name'], m=m, D=D, mix=float(r['mixBonus'] or 0), team=team.get(r['name']), ovr0=float(r['ovr'])))
out = {}
for arm in ARMS:
    gs = [g_arm(p['D'], p['m'], arm) for p in P]
    for anc_kind in ('F', 'R'):
        a = dict(ANC0)
        if anc_kind == 'R': a['PR1'] = pr1(gs)
        ov = np.array([omap(g, a) + p['mix'] for g, p in zip(gs, P)])
        key = f'{arm}-{anc_kind}'
        if arm == 'A0' and anc_kind == 'R': continue
        # S2：同隊配對，MPG 多 ≥10 卻 OVR 低 ≥3
        viol = 0
        for i, p in enumerate(P):
            for j, q in enumerate(P):
                if p['team'] and p['team'] == q['team'] and p['m'] >= q['m'] + 10 and ov[i] < ov[j] - 3: viol += 1
        # S3：對 2026-27 MPG（N≥3）
        idx = [i for i, p in enumerate(P) if p['name'] in live and float(live[p['name']]['N']) >= 3]
        mpg26 = np.array([float(live[P[i]['name']]['MIN26']) / float(live[P[i]['name']]['N']) for i in idx])
        rho = spearmanr(ov[idx], mpg26).correlation
        neg = [k for k, i in enumerate(idx) if P[i]['D'] < 0]
        rho_neg = spearmanr(ov[idx][neg], mpg26[neg]).correlation
        # S4：D<0 子群，2026-27 有沒有上場
        ng = [i for i, p in enumerate(P) if p['D'] < 0]
        y = [1 if (P[i]['name'] in live and float(live[P[i]['name']]['N']) > 0) else 0 for i in ng]
        auc = roc_auc_score(y, ov[ng])
        top = np.argsort(-ov)[:100]; base = out.get('A0-F', {}).get('_ov')
        s5 = {}
        if base is not None:
            d = ov - base
            s5 = dict(top100_maxabs=float(np.abs(d[np.argsort(-base)[:100]]).max()), median_all=float(np.median(d)),
                      negN=int(sum(p['D'] < 0 for p in P)), neg_mean=float(np.mean([d[i] for i in ng])),
                      pos_below50_mean=float(np.mean([d[i] for i, p in enumerate(P) if p['D'] >= 0 and ov[i] < 70])))
        out[key] = dict(PR1=a['PR1'], S2_viol=viol, S3_rho=rho, S3_rho_negD=rho_neg, S3_n=len(idx), S4_auc=auc, S4_n=len(ng), S4_pos=sum(y), **s5, _ov=ov)
base = out['A0-F']['_ov']; print('重建 vs 卡片 ovr 最大差', float(np.abs(base - np.array([p['ovr0'] for p in P])).max()))
for k, v in out.items():
    print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != '_ov'})
# 代表球員
names = ['Yang Hansen', 'Payton Sandfort', 'Andre Drummond', 'Reed Sheppard', 'Ryan Kalkbrenner', 'Adem Bona']
order0 = {i: r for r, i in enumerate(np.argsort(-base))}
for n in names:
    i = next((k for k, p in enumerate(P) if p['name'] == n), None)
    if i is None: continue
    print(n, f"mpg {P[i]['m']:.1f} D {P[i]['D']:+.2f}", {k: round(float(v['_ov'][i]), 1) for k, v in out.items()})
json.dump({k: {kk: vv for kk, vv in v.items() if kk != '_ov'} for k, v in out.items()}, open(EXP / 'part_a.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
np.save(EXP / 'part_a_ovr.npy', np.array([out[k]['_ov'] for k in out])); json.dump([p['name'] for p in P], open(EXP / 'part_a_names.json', 'w', encoding='utf8'))
