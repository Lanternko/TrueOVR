"""E-069 m3 copy of reports/bias-check-E067/bias_check.py: only the WinImp csv input path (E065 -> handle-E069/sim) and the output/prereg paths differ.
E-067 長人偏袒檢查（照凍結預註冊 sha256 2dc53916…）。

S = mean(殘差 | C) − mean(殘差 | PG/SG)，殘差 = rankdata(−答案) − rankdata(−模型)（正＝高估）。
答案、人群同 E-064 §3.2／verdict_e065.pool()。兩方向 AB（評 B）、BA（評 A）；bootstrap 2000、seed 1。
判定：兩方向 90% 下界 > 0 → 偏袒長人；上界 < 0 → 偏袒後衛；其餘未偵測到。

模型以 (名稱, 函式) 註冊；函式收評估半 ev（'A'/'B'），回傳 {name: (score, pos, heightInches|None)}。
用法：python -I reports/bias-check-E067/bias_check.py
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
E067 = ROOT / 'reports/bias-check-E067'
WINIMP_DIR = ROOT / 'reports/handle-E069/sim'
E064 = ROOT / 'reports/card-0.1.2+E064-pergame'
E065 = ROOT / 'reports/card-0.1.2+E065-inout-wins'
_spec = importlib.util.spec_from_file_location('v065', E065 / 'verdict_e065.py')
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)
B, SEED = 2000, 1
K2 = {r['name']: float(r['overall2k']) for r in csv.DictReader((ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv').open(encoding='utf-8-sig'))}


def answers(ev):
    """{name: 答案}，人群同 E-065。"""
    return {r['name']: a for r, a in V.pool(ev)}


def fit_card(ev):
    fit = 'A' if ev == 'B' else 'B'
    rows = csv.DictReader((E064 / f'fit{fit}/ranking.csv').open(encoding='utf-8'))
    return {r['name']: (float(r['ovr']), r['pos'], float(r['heightInches'])) for r in rows}


def winimp(col):
    rows = list(csv.DictReader((WINIMP_DIR / 'winimp.csv').open(encoding='utf-8-sig')))
    return lambda ev: {r['name']: (float(r[col]), r['pos'], None) for r in rows}


MODELS = [('card 0.1.2 fit 卡', fit_card), ('WinImp 主版', winimp('winsPer82')), ('WinImp 位置版', winimp('winsPer82_pos'))]


def ci(x):
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]


def measure(model, ev, rng, answer=None):
    ans = answer or answers(ev)
    m = model(ev)
    names = [n for n in ans if n in m]
    a = np.array([ans[n] for n in names])
    s = np.array([m[n][0] for n in names])
    pos = np.array([m[n][1] for n in names])
    res = rankdata(-a) - rankdata(-s)
    c, g = np.where(pos == 'C')[0], np.where(np.isin(pos, ['PG', 'SG']))[0]
    boot = [res[rng.choice(c, len(c))].mean() - res[rng.choice(g, len(g))].mean() for _ in range(B)]
    out = {'n': len(names), 'nC': len(c), 'nG': len(g), 'S': float(res[c].mean() - res[g].mean()), 'CI90': ci(boot),
           'rho': float(spearmanr(s, a)[0]),
           'groupMean': {p: float(res[pos == p].mean()) for p in ['PG', 'SG', 'SF', 'PF', 'C'] if (pos == p).any()},
           'top20C_model': int(sum(pos[np.argsort(-s)[:20]] == 'C')), 'top20C_answer': int(sum(pos[np.argsort(-a)[:20]] == 'C')),
           'over10': [(names[k], float(res[k])) for k in np.argsort(-res)[:10]],
           'under10': [(names[k], float(res[k])) for k in np.argsort(res)[:10]]}
    h = np.array([m[n][2] if m[n][2] is not None else np.nan for n in names], dtype=float)
    if not np.isnan(h).all():
        q = np.nanpercentile(h, [100 / 3, 200 / 3])
        out['heightTercileMean'] = [float(res[h <= q[0]].mean()), float(res[(h > q[0]) & (h <= q[1])].mean()), float(res[h > q[1]].mean())]
    return out


def verdict(d):
    if all(d[k]['CI90'][0] > 0 for k in d):
        return '偏袒長人'
    if all(d[k]['CI90'][1] < 0 for k in d):
        return '偏袒後衛'
    return '未偵測到偏袒'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rng = np.random.default_rng(SEED)
    res = {'preregSha256': (E067 / 'preregistration.sha256').read_text().split()[0], 'models': {}}
    for name, model in MODELS:
        d = {dr: measure(model, ev, rng) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        # 第二答案：2K27（只列不判）
        k2 = {dr: measure(model, ev, rng, answer={n: K2[n] for n in answers(ev) if n in K2}) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        res['models'][name] = {'verdict': verdict(d), 'directions': d, 'vs2K27': {k: {'S': v['S'], 'CI90': v['CI90'], 'n': v['n']} for k, v in k2.items()}}
        print(f'## {name}：{verdict(d)}')
        for dr, x in d.items():
            print(f"  {dr} n={x['n']} (C {x['nC']}, G {x['nG']}) S={x['S']:+.1f} CI {[round(t, 1) for t in x['CI90']]} ρ={x['rho']:.3f} "
                  f"組平均 {({p: round(v, 1) for p, v in x['groupMean'].items()})} 前20 C 模型{x['top20C_model']}/答案{x['top20C_answer']}")
            print(f"     2K27 答案 S={k2[dr]['S']:+.1f} CI {[round(t, 1) for t in k2[dr]['CI90']]}")
    (HERE / 'bias-check-e069.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
