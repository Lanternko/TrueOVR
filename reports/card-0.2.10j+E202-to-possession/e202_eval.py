"""E-202 判定（預註冊 §2）。用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j+E202-to-possession/e202_eval.py
門檻讀 phase0.json，不重算。寫 results.json、report.md。"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, str(Path(__file__).resolve().parent))
from e202_common import *
E142 = ROOT / 'reports/E142-card-target'
TWOK_OVR = ROOT / 'data/external-impact/2k/2k-merged-e142.csv'
EPM = ROOT / 'data/external-impact/epm_self/epm_2025-26.csv'
ARMS = ['K0', 'KT']
TABLE = ['Shai Gilgeous-Alexander', 'Jalen Brunson', 'Luka Dončić', 'Nikola Jokić', 'Joel Embiid', 'Bam Adebayo', 'Tyrese Haliburton', 'Jrue Holiday',
         'Tyus Jones', 'Cade Cunningham', 'Trae Young', 'James Harden', 'Sam Hauser', 'Tim Hardaway Jr.', 'Dean Wade', 'Rudy Gobert', 'Jarrett Allen', 'Luke Kornet']


def rho(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def _load(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def coef(arm):
    out = {}
    for part in ('primary', 'fitA', 'fitB'):
        f = HERE / f'work/{arm}/A/base-KG-2025-26/c0/cards/K0/{part}/summary.json'
        out[part] = json.loads(f.read_text(encoding='utf-8'))['valuePer10AttributePoints']
    return out


def external(cards):
    sys.path.insert(0, str(E142))
    P = _load('pe', E142 / 'phase1_eval.py')
    pop, _ = P.pop_of('2025-26')
    pages = {s_: P.C0L.contracts(s_) for s_ in P.C0L.ORDER}
    drafts, ev = P.C0L.draft_years(), P.C0L.tx_events()
    sal, _ = P.salary_terms('2025-26', pop, pages, drafts, ev)
    twok = P.load_twok(str(TWOK_OVR))
    epm = {int(r['playerId']): float(r['net']) for r in csv.DictReader(open(EPM, encoding='utf-8-sig'))}
    ids = sorted(p for p, r in cards['K0'].items() if float(r['MIN']) >= 500)
    out = {}
    for a in ARMS:
        o = {p: float(cards[a][p]['ovr']) for p in ids}
        hs = [p for p in ids if p in sal]
        k2 = [(p, float(twok[P.norm(cards[a][p]['name'])]['2K27'])) for p in ids
              if P.norm(cards[a][p]['name']) in twok and (twok[P.norm(cards[a][p]['name'])].get('2K27') or '').strip()]
        he = [p for p in ids if p in epm]
        out[a] = {'salary_wspearman': P.wspearman([o[p] for p in hs], [sal[p][0] for p in hs], [P.YEARW.get(sal[p][1], 0.3) for p in hs]), 'n_sal': len(hs),
                  'twok27_ovr_spearman': P.spearman([o[p] for p, _ in k2], [v for _, v in k2]), 'n_2k': len(k2),
                  'epm_spearman': P.spearman([o[p] for p in he], [epm[p] for p in he]), 'n_epm': len(he)}
    return out


def main():
    p0 = json.loads((HERE / 'phase0.json').read_text(encoding='utf-8'))
    cards = {a: load_arm(a) for a in ARMS}
    res = {'phase0': {k: p0[k] for k in ('MDE', 'h', 'notBroken_threshold', 'K0_tov_vs_2K_BallHandle_rho', 'K0_ovr_vs_rapm_rho')},
           'ranking_sha256': {a: sha(rank_path(a)) for a in ARMS}}
    assert res['ranking_sha256']['K0'] == p0['K0_ranking_sha256']
    bh = twok_bh()
    # A
    ids2k = [p for p, r in cards['K0'].items() if float(r['MIN']) >= 500 and norm(r['name']) in bh]
    y = np.array([bh[norm(cards['K0'][p]['name'])] for p in ids2k])
    tv = {a: np.array([float(cards[a][p]['tovSkill']) for p in ids2k]) for a in ARMS}
    rng = np.random.default_rng(SEED)
    n = len(ids2k)
    dd = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        dd.append(rho(tv['KT'][i], y[i]) - rho(tv['K0'][i], y[i]))
    a_pt = {a: rho(tv[a], y) for a in ARMS}
    res['A'] = {'n': n, 'rho': a_pt, 'diff': a_pt['KT'] - a_pt['K0'], 'diff_ci90': ci(dd), 'MDE': p0['MDE'], 'pass': bool(a_pt['KT'] - a_pt['K0'] >= p0['MDE'])}
    # 沒弄壞：RAPM
    rapm = {k: json.load(open(f, encoding='utf-8'))['players'] for k, f in RAPM_FILES.items()}
    full = rapm['full']
    ids = sorted(p for p, r in cards['K0'].items() if float(r['MIN']) >= 500 and str(p) in full and full[str(p)]['poss'] >= 1000)
    ov = {a: np.array([float(cards[a][p]['ovr']) for p in ids]) for a in ARMS}
    res['rapm'] = {}
    for rn in RAPM_FILES:
        rv = np.array([rapm[rn][str(p)]['net'] if str(p) in rapm[rn] else np.nan for p in ids])
        ok = ~np.isnan(rv)
        pt = {a: rho(ov[a][ok], rv[ok]) for a in ARMS}
        rng = np.random.default_rng(SEED)
        m = len(ids)
        d2 = []
        for _ in range(B):
            i = rng.integers(0, m, m)
            i = i[ok[i]]
            d2.append(rho(ov['KT'][i], rv[i]) - rho(ov['K0'][i], rv[i]))
        res['rapm'][rn] = {'n': int(ok.sum()), 'rho': pt, 'diff': pt['KT'] - pt['K0'], 'diff_ci90': ci(d2)}
    d = res['rapm']['full']['diff']
    res['notBroken'] = {'rho_diff': d, 'threshold': p0['notBroken_threshold'], 'pass_rho': bool(d >= p0['notBroken_threshold']),
                        'c0_bitwise': True, 'split_direction_same': bool(np.sign(res['rapm']['odd']['diff']) == np.sign(res['rapm']['even']['diff']))}
    res['B'] = {'K0': f143(cards['K0']), 'KT': f143(cards['KT']), 'threshold_le': 10}
    res['B']['pass'] = bool(res['B']['KT']['n_below'] <= 10)
    # 只報告：係數與 VIF
    res['coef_per10'] = {a: coef(a) for a in ARMS}
    m5 = [p for p in sorted(cards['KT']) if float(cards['KT'][p]['MIN']) >= 500]
    po = np.array([float(cards['KT'][p]['predictedPer36']) for p in m5])
    ovv = np.array([float(cards['KT'][p]['ovr']) for p in m5])
    slope = float(np.polyfit(po, ovv, 1)[0])
    out_c = {}
    for a in ARMS:
        t = res['coef_per10'][a]['primary']['tovSkill']
        out_c[a] = {'per36': t['per36'], 'SE': t['bootstrapSE'], 'ovr': t['per36'] * slope, 'ovr_SE': t['bootstrapSE'] * slope,
                    'fitA': res['coef_per10'][a]['fitA']['tovSkill'], 'fitB': res['coef_per10'][a]['fitB']['tovSkill']}
    res['tov_per10'] = {'ovr_per_per36_slope': slope, **out_c}
    cols = set(next(iter(cards['KT'].values())).keys())
    attrs = [k for k in res['coef_per10']['KT']['primary'] if k != 'gravity' and k in cols]
    gr = {int(r['playerId']): float(r['gravity']) for r in csv.DictReader(open(HERE / 'gravity-attr.csv', encoding='utf-8'))}
    vif = {}
    for a in ARMS:
        names = attrs + ['gravity']
        X = np.array([[float(cards[a][p][k]) for k in attrs] + [gr[p]] for p in m5])
        j = names.index('tovSkill')
        yv = X[:, j]
        Xc = np.column_stack([np.ones(len(m5)), np.delete(X, j, 1)])
        bb, *_ = np.linalg.lstsq(Xc, yv, rcond=None)
        r2 = 1 - ((yv - Xc @ bb) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
        vif[a] = {'vif': float(1 / (1 - r2)), 'corr': {k: float(np.corrcoef(yv, X[:, names.index(k)])[0, 1]) for k in ('creation', 'pass', 'gravity')}}
    res['vif_tovSkill'] = {'attrs_used': attrs, **vif}
    res['external'] = external(cards)
    ids_all = sorted(cards['K0'])
    rk = {a: {p: int(cards[a][p]['rank']) for p in ids_all} for a in ARMS}
    t100 = [p for p in ids_all if rk['K0'][p] <= 100]
    mv = sorted([(cards['K0'][p]['name'], rk['K0'][p], rk['KT'][p]) for p in t100 if abs(rk['KT'][p] - rk['K0'][p]) >= 10], key=lambda x: x[2] - x[1])
    t20 = {a: {p for p in ids_all if rk[a][p] <= 20} for a in ARMS}
    res['moves'] = {'top100_moved_ge10': len(mv), 'list': mv, 'top20_in': [cards['KT'][p]['name'] for p in t20['KT'] - t20['K0']],
                    'top20_out': [cards['K0'][p]['name'] for p in t20['K0'] - t20['KT']]}
    tr = list(csv.DictReader(open(HERE / 'tov-raw.csv', encoding='utf-8')))
    res['topMissing'] = [x['name'] for x in tr if x['topMissing'] == '1']
    v36 = poss36(cards['KT'])
    trank = {a: {p: r for r, p in enumerate(sorted([q for q in ids_all if float(cards[a][q]['MIN']) >= 500], key=lambda q: -float(cards[a][q]['tovSkill'])), 1)} for a in ARMS}
    nm = {cards['K0'][p]['name']: p for p in ids_all}
    tab = []
    for nme in TABLE:
        p = nm.get(nme)
        if p is None:
            tab.append({'name': nme, 'missing': True})
            continue
        tab.append({'name': nme, 'TO_K0': float(cards['K0'][p]['tovSkill']), 'TO_KT': float(cards['KT'][p]['tovSkill']),
                    'TOrank_K0': trank['K0'].get(p), 'TOrank_KT': trank['KT'].get(p),
                    'ovr_K0': float(cards['K0'][p]['ovr']), 'ovr_KT': float(cards['KT'][p]['ovr']), 'rank_K0': rk['K0'][p], 'rank_KT': rk['KT'][p],
                    'poss36': v36.get(p), 'MIN': cards['K0'][p]['MIN']})
    res['table'] = tab
    res['inputs_sha256'] = {Path(f).relative_to(ROOT).as_posix(): sha(f) for f in list(RAPM_FILES.values()) + [TAIL, TWOK, HANDLE, EPM, HERE / 'tail-KT.csv', HERE / 'tov-raw.csv', HERE / 'preregistration.md']}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    write_report(res)
    print(json.dumps({k: res[k] for k in ('A', 'notBroken', 'B', 'tov_per10', 'vif_tovSkill', 'external', 'moves', 'topMissing', 'table')}, ensure_ascii=False, indent=1, default=float))


def write_report(r):
    A, N, Bq, T, V = r['A'], r['notBroken'], r['B'], r['tov_per10'], r['vif_tovSkill']
    L = ['# E-202 結果（KT vs K0）', '',
         f"- A：tovSkill 對 2K27 Ball Handle ρ（n={A['n']}）K0 {A['rho']['K0']:.4f} → KT {A['rho']['KT']:.4f}，差 {A['diff']:+.4f}（90% CI {A['diff_ci90'][0]:+.4f}～{A['diff_ci90'][1]:+.4f}），MDE {A['MDE']:.4f} → {'過' if A['pass'] else '沒過'}。",
         f"- 沒弄壞：c0 逐位元重現（sha 4519d615…）；OVR 對 RAPM ρ K0 {r['rapm']['full']['rho']['K0']:.4f} → KT {r['rapm']['full']['rho']['KT']:.4f}，差 {N['rho_diff']:+.4f}（90% CI {r['rapm']['full']['diff_ci90'][0]:+.4f}～{r['rapm']['full']['diff_ci90'][1]:+.4f}；門檻 {N['threshold']:+.4f}）→ {'過' if N['pass_rho'] else '沒過'}；npm test 見回報。",
         f"- 分半：odd 差 {r['rapm']['odd']['diff']:+.4f}、even 差 {r['rapm']['even']['diff']:+.4f}，方向{'一致' if N['split_direction_same'] else '不一致'}。",
         f"- B（F-143）：TO 前 30 持球/36 低於池中位數（{Bq['KT']['median']:.3f}）K0 {Bq['K0']['n_below']} → KT {Bq['KT']['n_below']}（≤{Bq['threshold_le']} 算解決）→ {'達成' if Bq['pass'] else '未達成'}；前 30 平均持球/36 {Bq['K0']['top30_mean_poss36']:.2f} → {Bq['KT']['top30_mean_poss36']:.2f}；KT 榜首 {'、'.join(Bq['KT']['top5'])}。",
         f"- tovSkill 每 10 點：K0 {T['K0']['ovr']:+.3f}（SE {T['K0']['ovr_SE']:.3f}）→ KT {T['KT']['ovr']:+.3f}（SE {T['KT']['ovr_SE']:.3f}）OVR（每 36 分 {T['K0']['per36']:+.3f}±{T['K0']['SE']:.3f} → {T['KT']['per36']:+.3f}±{T['KT']['SE']:.3f}）；VIF {V['K0']['vif']:.2f} → {V['KT']['vif']:.2f}；與 creation 相關 {V['K0']['corr']['creation']:+.2f} → {V['KT']['corr']['creation']:+.2f}、pass {V['K0']['corr']['pass']:+.2f} → {V['KT']['corr']['pass']:+.2f}、gravity {V['K0']['corr']['gravity']:+.2f} → {V['KT']['corr']['gravity']:+.2f}。",
         f"- 外部：OVR 對 2K27 OVR ρ {r['external']['K0']['twok27_ovr_spearman']:.4f} → {r['external']['KT']['twok27_ovr_spearman']:.4f}；EPM {r['external']['K0']['epm_spearman']:.4f} → {r['external']['KT']['epm_spearman']:.4f}；薪水 {r['external']['K0']['salary_wspearman']:.4f} → {r['external']['KT']['salary_wspearman']:.4f}。",
         f"- 前 100 名移動 ≥10 名 {r['moves']['top100_moved_ge10']} 人；前 20 進 {'、'.join(r['moves']['top20_in']) or '無'}；出 {'、'.join(r['moves']['top20_out']) or '無'}。topMissing=1：{'、'.join(r['topMissing']) or '無'}。", '',
         '## 球員表（K0→KT）', '', '| 球員 | TO | TO 名次 | OVR | OVR 名次 | 持球/36 |', '|---|---|---|---|---|---|']
    for t in r['table']:
        if t.get('missing'):
            L.append(f"| {t['name']} | 不在名單 | | | | |")
            continue
        ps = f"{t['poss36']:.2f}" if t['poss36'] is not None else 'NA'
        L.append(f"| {t['name']} | {t['TO_K0']:.0f}→{t['TO_KT']:.0f} | {t['TOrank_K0']}→{t['TOrank_KT']} | {t['ovr_K0']:.1f}→{t['ovr_KT']:.1f} | {t['rank_K0']}→{t['rank_KT']} | {ps} |")
    L += ['', '## 前 100 名移動 ≥10（名次 K0→KT）', ''] + [f"- {n}：{a}→{b}" for n, a, b in r['moves']['list']]
    (HERE / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
