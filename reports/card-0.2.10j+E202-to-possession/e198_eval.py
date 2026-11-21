"""E-198 判定（預註冊 §2）。
用法（repo root）：
  python -I -B -X utf8 reports/card-0.2.10j+E198-gravity/e198_eval.py phase0   # 只用 KAU；寫 phase0.json／phase0.md（跑 KG 前）
  python -I -B -X utf8 reports/card-0.2.10j+E198-gravity/e198_eval.py eval     # KAU vs KG；寫 results.json（門檻讀 phase0.json，不重算）
定義（phase0 寫檔前固定）：
  人群 P  ＝卡片 ranking.csv MIN≥500，且 2025-26 本季 RAPM（E-126 rapm-2025-26.json）poss≥1000；分半（單雙場）沿用同一人群。
  名次     ＝人群內 rankdata 平均名次 → (r−1)/(n−1)×100（越大越好）；名次殘差＝pct(RAPM net) − pct(OVR)（正＝卡片低估）。
  價值殘差 ＝ z(RAPM) − b·z(OVR)，b＝人群內 OLS 斜率（L-112）；單位＝RAPM 的 SD。
  接球射手組 S ＝ KAU 的 long≥75 且 creation≤60（人群內；兩臂同一組人）。
  bootstrap：人群內球員層有放回重抽 2000 次，seed 20261102；每次在重抽樣本內重算名次／z／b；90% 半寬＝(q95−q05)/2。
  h ＝ KAU Spearman(OVR, RAPM) 的半寬；MDE_rank／MDE_value ＝ KAU 的 S 組平均名次殘差／價值殘差的半寬。
  A：縮小量＝sign(KAU 組平均)·(KAU 組平均 − KG 組平均) ≥ MDE。主口徑見 phase0 的假象規則。
  沒弄壞：ρ_KG − ρ_KAU ≥ −2h（全季 RAPM）；c0、npm test 另記。"""
import csv, hashlib, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
E142 = ROOT / 'reports/E142-card-target'
TAIL = ROOT / 'reports/card-0.2.10i/tail-U.csv'
TWOK = ROOT / 'data/external-impact/2k/2k-merged-e142.csv'
EPM = ROOT / 'data/external-impact/epm_self/epm_2025-26.csv'
SEED, B = 20261102, 2000
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TABLE = ['Klay Thompson', 'Stephen Curry', 'Buddy Hield', 'Luke Kennard', 'Duncan Robinson', 'Sam Hauser', 'Michael Porter Jr.',
         'Shai Gilgeous-Alexander', 'Kevin Durant', 'Luka Dončić', 'Nikola Jokić', 'Rudy Gobert', 'Jalen Williams',
         'Giannis Antetokounmpo', 'Josh Giddey']
RAPM_FILES = {'full': E126 / 'rapm-2025-26.json', 'odd': HERE / 'work/rapm-2025-26-odd.json', 'even': HERE / 'work/rapm-2025-26-even.json'}


def rank_path(arm):
    return HERE / f'work/{arm}-final/out/ranking.csv'


def load_arm(arm):
    pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(TAIL, encoding='utf-8'))}
    rows = list(csv.DictReader(open(rank_path(arm), encoding='utf-8')))
    return {pid[r['name']]: r for r in rows}


def pctr(x):
    r = rankdata(x)
    return (r - 1) / (len(x) - 1) * 100


def zs(x):
    return (x - x.mean()) / x.std()


def stats(ovr, rapm, grp):
    """ovr、rapm：同序向量；grp：布林。回 ρ、組平均名次殘差、組平均價值殘差、組平均 pct(OVR)。"""
    po, pr = pctr(ovr), pctr(rapm)
    rho = float(np.corrcoef(rankdata(ovr), rankdata(rapm))[0, 1])
    zo, zr = zs(ovr), zs(rapm)
    b = float((zo * zr).mean() / (zo * zo).mean())
    rr = pr - po
    vr = zr - b * zo
    return {'rho': rho, 'rank_resid': float(rr[grp].mean()), 'value_resid': float(vr[grp].mean()), 'grp_pct_ovr': float(po[grp].mean()), 'b': b}


def setup(arms):
    cards = {a: load_arm(a) for a in arms}
    k = cards['KAU']
    rapm = {n: json.load(open(f, encoding='utf-8'))['players'] for n, f in RAPM_FILES.items()}
    full = rapm['full']
    ids = sorted(p for p, r in k.items() if float(r['MIN']) >= 500 and str(p) in full and full[str(p)]['poss'] >= 1000)
    assert all(set(ids) <= set(cards[a]) for a in arms)
    grp = np.array([float(k[p]['long']) >= 75 and float(k[p]['creation']) <= 60 for p in ids])
    ovr = {a: np.array([float(cards[a][p]['ovr']) for p in ids]) for a in arms}
    rv = {n: np.array([rapm[n][str(p)]['net'] if str(p) in rapm[n] else np.nan for p in ids]) for n in rapm}
    return {'cards': cards, 'ids': ids, 'grp': grp, 'ovr': ovr, 'rapm': rv}


def boot(D, arms, rname='full'):
    rng = np.random.default_rng(SEED)
    n = len(D['ids'])
    out = {a: defaultdict(list) for a in arms}
    r = D['rapm'][rname]
    for _ in range(B):
        idx = rng.integers(0, n, n)
        for a in arms:
            s = stats(D['ovr'][a][idx], r[idx], D['grp'][idx])
            for kk, v in s.items():
                out[a][kk].append(v)
    return {a: {kk: np.array(v) for kk, v in d.items()} for a, d in out.items()}


def hw(x):
    return float((np.percentile(x, 95) - np.percentile(x, 5)) / 2)


def ci(x):
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]


def phase0():
    D = setup(['KAU'])
    pt = {n: stats(D['ovr']['KAU'], D['rapm'][n], D['grp']) for n in RAPM_FILES if not np.isnan(D['rapm'][n]).any()}
    bt = boot(D, ['KAU'])['KAU']
    h, mde_r, mde_v = hw(bt['rho']), hw(bt['rank_resid']), hw(bt['value_resid'])
    artifact = abs(pt['full']['grp_pct_ovr'] - 50) > 10
    names = [D['cards']['KAU'][p]['name'] for p, g in zip(D['ids'], D['grp']) if g]
    res = {'n_pop': len(D['ids']), 'n_group': int(D['grp'].sum()), 'group_names': names,
           'KAU_point': pt, 'h': h, 'MDE_rank': mde_r, 'MDE_value': mde_v, 'KAU_ci90': {k: ci(v) for k, v in bt.items()},
           'artifact_rule': 'S 組在 KAU 上的平均 pct(OVR) 偏離 50 超過 10 點 → 名次殘差有均值回歸假象（L-112），A 以價值殘差判；否則以名次殘差判（價值殘差只報告）',
           'artifact': bool(artifact), 'A_primary': 'value_resid' if artifact else 'rank_resid',
           'seed': SEED, 'draws': B, 'kau_ranking_sha256': sha(rank_path('KAU')),
           'rapm_sha256': {n: sha(f) for n, f in RAPM_FILES.items()}}
    (HERE / 'phase0.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    f = pt['full']
    md = f"""# E-198 phase0（跑 KG 前；只用 KAU）

- 人群：卡片 MIN≥500 且 2025-26 本季 RAPM poss≥1000，{res['n_pop']} 人；接球射手組（KAU long≥75 且 creation≤60）{res['n_group']} 人。
- KAU ranking.csv sha256 `{res['kau_ranking_sha256']}`（＝card-0.2.10i）。bootstrap 球員層 {B} 次，seed {SEED}。
- KAU 全體 Spearman(OVR, 本季 RAPM) = {f['rho']:.4f}，90% 半寬 **h = {h:.4f}** → 沒弄壞門檻：ρ_KG − ρ_KAU ≥ **{-2*h:.4f}**。
- 接球射手組平均名次殘差（pct RAPM − pct OVR，正＝低估）= {f['rank_resid']:+.2f} 點，**MDE_rank = {mde_r:.2f}** 點。
- 接球射手組平均價值殘差（z RAPM − b·z OVR，b={f['b']:.3f}）= {f['value_resid']:+.4f} SD，**MDE_value = {mde_v:.4f}** SD。
- 組平均 pct(OVR) = {f['grp_pct_ovr']:.1f}。假象規則（寫檔前定）：偏離 50 超過 10 點 → 名次殘差有均值回歸假象，A 以價值殘差判；
  否則以名次殘差判（價值殘差只報告）。本次：**{'有假象，A 主口徑＝價值殘差' if artifact else '無假象，A 主口徑＝名次殘差'}**。
- A 判定式：縮小量＝sign(KAU 組平均)·(KAU − KG) ≥ MDE（主口徑）。
- 分半（單雙場）KAU 點估計：odd ρ {pt['odd']['rho']:.4f}、組名次殘差 {pt['odd']['rank_resid']:+.2f}、價值殘差 {pt['odd']['value_resid']:+.4f}；
  even ρ {pt['even']['rho']:.4f}、組名次殘差 {pt['even']['rank_resid']:+.2f}、價值殘差 {pt['even']['value_resid']:+.4f}。
- 組員：{'、'.join(names)}
"""
    (HERE / 'phase0.md').write_text(md, encoding='utf-8')
    print(md)


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def external(D, arms):
    sys.path.insert(0, str(E142))
    P = _load('pe', E142 / 'phase1_eval.py')
    pop, _ = P.pop_of('2025-26')
    pages = {s_: P.C0L.contracts(s_) for s_ in P.C0L.ORDER}
    drafts, ev = P.C0L.draft_years(), P.C0L.tx_events()
    sal, sstat = P.salary_terms('2025-26', pop, pages, drafts, ev)
    twok = P.load_twok(str(TWOK))
    epm = {int(r['playerId']): float(r['net']) for r in csv.DictReader(open(EPM, encoding='utf-8-sig'))}
    cards = D['cards']
    ids = sorted(p for p, r in cards['KAU'].items() if float(r['MIN']) >= 500)
    out = {}
    for a in arms:
        o = {p: float(cards[a][p]['ovr']) for p in ids}
        hs = [p for p in ids if p in sal]
        k2 = [(p, float(twok[P.norm(cards[a][p]['name'])]['2K27'])) for p in ids
              if P.norm(cards[a][p]['name']) in twok and (twok[P.norm(cards[a][p]['name'])].get('2K27') or '').strip()]
        he = [p for p in ids if p in epm]
        out[a] = {'salary_wspearman': P.wspearman([o[p] for p in hs], [sal[p][0] for p in hs], [P.YEARW.get(sal[p][1], 0.3) for p in hs]), 'n_sal': len(hs),
                  'twok27_spearman': P.spearman([o[p] for p, _ in k2], [v for _, v in k2]), 'n_2k': len(k2),
                  'epm_spearman': P.spearman([o[p] for p in he], [epm[p] for p in he]), 'n_epm': len(he)}
    out['salary_stats'] = sstat
    return out


def coef_info(arm):
    d = {}
    for part in ('primary', 'fitA', 'fitB'):
        sm = json.loads((HERE / f'work/A/base-{arm}-2025-26/c0/cards/K0/{part}/summary.json').read_text(encoding='utf-8'))
        d[part] = sm['valuePer10AttributePoints']
    return d


def evaluate():
    p0 = json.loads((HERE / 'phase0.json').read_text(encoding='utf-8'))
    arms = ['KAU', 'KG']
    D = setup(arms)
    res = {'phase0': {k: p0[k] for k in ('h', 'MDE_rank', 'MDE_value', 'artifact', 'A_primary', 'n_pop', 'n_group')},
           'ranking_sha256': {a: sha(rank_path(a)) for a in arms}}
    assert res['ranking_sha256']['KAU'] == p0['kau_ranking_sha256']
    for rn in RAPM_FILES:
        pt = {a: stats(D['ovr'][a], D['rapm'][rn], D['grp']) for a in arms}
        bt = boot(D, arms, rn)
        dd = {k: bt['KG'][k] - bt['KAU'][k] for k in ('rho', 'rank_resid', 'value_resid')}
        res[rn] = {'point': pt, 'diff_point': {k: pt['KG'][k] - pt['KAU'][k] for k in dd}, 'diff_ci90': {k: ci(v) for k, v in dd.items()},
                   'ci90': {a: {k: ci(bt[a][k]) for k in ('rho', 'rank_resid', 'value_resid')} for a in arms}}
    f = res['full']['point']
    shrink = {k: math.copysign(1, f['KAU'][k]) * (f['KAU'][k] - f['KG'][k]) for k in ('rank_resid', 'value_resid')}
    passA = {'rank_resid': shrink['rank_resid'] >= p0['MDE_rank'], 'value_resid': shrink['value_resid'] >= p0['MDE_value']}
    A = passA[p0['A_primary']]   # phase0 假象規則決定主口徑
    drho = f['KG']['rho'] - f['KAU']['rho']
    res['judge'] = {'A_shrink': shrink, 'A_pass_each': passA, 'A_pass': bool(A),
                    'notBroken_rho': {'drho': drho, 'threshold': -2 * p0['h'], 'pass': bool(drho >= -2 * p0['h'])},
                    'split_direction': {rn: {k: res[rn]['diff_point'][k] for k in ('rho', 'rank_resid', 'value_resid')} for rn in ('odd', 'even')}}
    # 只報告
    res['coef_per10'] = {a: coef_info(a) for a in arms}
    cards = D['cards']
    ids_all = sorted(cards['KAU'])
    grav = {int(r['playerId']): (float(r['gravity']), int(r['gravityImputed'])) for r in csv.DictReader(open(HERE / 'gravity-attr.csv', encoding='utf-8'))}
    m5 = [p for p in ids_all if float(cards['KAU'][p]['MIN']) >= 500]
    attrs = [k for k in res['coef_per10']['KAU']['primary']]
    X = np.array([[float(cards['KAU'][p][k]) for k in attrs] for p in m5])
    g = np.array([grav[p][0] for p in m5])
    Xc = np.column_stack([np.ones(len(m5)), X])
    bb, *_ = np.linalg.lstsq(Xc, g, rcond=None)
    r2 = 1 - ((g - Xc @ bb) ** 2).sum() / ((g - g.mean()) ** 2).sum()
    res['vif_gravity'] = {'r2_on_other_attrs': float(r2), 'vif': float(1 / (1 - r2)), 'n': len(m5),
                          'corr': {k: float(np.corrcoef(g, X[:, i])[0, 1]) for i, k in enumerate(attrs)}}
    # OVR 換算：MIN≥500 人群 OVR 對 predictedPer36 的 OLS 斜率（KG）
    po = np.array([float(cards['KG'][p]['predictedPer36']) for p in m5]); ov = np.array([float(cards['KG'][p]['ovr']) for p in m5])
    slope = float(np.polyfit(po, ov, 1)[0])
    gp = res['coef_per10']['KG']['primary']['gravity']
    res['gravity_per10'] = {'per36': gp['per36'], 'per36_SE': gp['bootstrapSE'], 'ovr_per_per36_slope': slope,
                            'ovr': gp['per36'] * slope, 'ovr_SE': gp['bootstrapSE'] * slope,
                            'fitA': res['coef_per10']['KG']['fitA']['gravity'], 'fitB': res['coef_per10']['KG']['fitB']['gravity']}
    res['external'] = external(D, arms)
    rk = {a: {p: int(cards[a][p]['rank']) for p in ids_all} for a in arms}
    top100 = [p for p in ids_all if rk['KAU'][p] <= 100]
    mv = [(cards['KAU'][p]['name'], rk['KAU'][p], rk['KG'][p]) for p in top100 if abs(rk['KG'][p] - rk['KAU'][p]) >= 10]
    t20 = {a: {p for p in ids_all if rk[a][p] <= 20} for a in arms}
    res['moves'] = {'top100_moved_ge10': len(mv), 'list': sorted(mv, key=lambda x: x[2] - x[1]),
                    'top20_in': [cards['KG'][p]['name'] for p in t20['KG'] - t20['KAU']],
                    'top20_out': [cards['KAU'][p]['name'] for p in t20['KAU'] - t20['KG']],
                    'rho_rank_KAU_KG_min500': float(np.corrcoef(rankdata([rk['KAU'][p] for p in m5]), rankdata([rk['KG'][p] for p in m5]))[0, 1])}
    imp = [p for p in m5 if grav[p][1]]
    dr = [rk['KAU'][p] - rk['KG'][p] for p in imp]
    res['imputed'] = {'n_min500': len(imp), 'mean_rank_up': float(np.mean(dr)), 'mean_abs': float(np.mean(np.abs(dr))),
                      'top_up': sorted([(cards['KAU'][p]['name'], rk['KAU'][p], rk['KG'][p], round(grav[p][0], 1)) for p in imp], key=lambda x: x[2] - x[1])[:10],
                      'top_down': sorted([(cards['KAU'][p]['name'], rk['KAU'][p], rk['KG'][p], round(grav[p][0], 1)) for p in imp], key=lambda x: x[1] - x[2])[:10]}
    nm = {cards['KAU'][p]['name']: p for p in ids_all}
    # S 組成員變化
    gi = [p for p, x in zip(D['ids'], D['grp']) if x]
    res['group_rank_change'] = {'mean_rank_up': float(np.mean([rk['KAU'][p] - rk['KG'][p] for p in gi])),
                                'members': [(cards['KAU'][p]['name'], rk['KAU'][p], rk['KG'][p], cards['KAU'][p]['ovr'], cards['KG'][p]['ovr'], round(grav[p][0], 1)) for p in gi]}
    tab = []
    for n in TABLE:
        p = nm.get(n)
        if p is None:
            tab.append({'name': n, 'missing': True}); continue
        tab.append({'name': n, 'rank_KAU': rk['KAU'][p], 'rank_KG': rk['KG'][p], 'ovr_KAU': cards['KAU'][p]['ovr'], 'ovr_KG': cards['KG'][p]['ovr'],
                    'gravity': round(grav[p][0], 1), 'imputed': grav[p][1], 'MIN': cards['KAU'][p]['MIN']})
    res['table'] = tab
    res['inputs_sha256'] = {**{str(Path(f).relative_to(ROOT).as_posix()): sha(f) for f in list(RAPM_FILES.values()) + [TAIL, TWOK, EPM, HERE / 'gravity-attr.csv', HERE / 'gravity-raw.csv']},
                            'reports/card-0.2.10i/ranking.csv': sha(ROOT / 'reports/card-0.2.10i/ranking.csv'),
                            'preregistration(HEAD,LF)': '52013c06f5c597b0d3e2e965054ca8b61f039b02e435698d5baed968de0950dc'}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('judge', 'gravity_per10', 'moves', 'external', 'table')}, ensure_ascii=False, indent=1, default=float))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    phase0() if sys.argv[1] == 'phase0' else evaluate()
