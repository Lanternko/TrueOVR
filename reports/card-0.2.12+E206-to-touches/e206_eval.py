"""E-206 判定（預註冊 §2）；自 E-202 e202_eval.py 複本。用法（repo root）：python -I -B -X utf8 reports/card-0.2.12+E206-to-touches/e206_eval.py
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
ARMS = ['K0', 'K12', 'KC']
MDE_E202 = 0.0879   # 預註冊 §2：E-202 的 MDE
TABLE = ['Austin Reaves', 'Kevin Porter Jr.', 'Shai Gilgeous-Alexander', 'Jalen Brunson', 'Luka Dončić', 'Nikola Jokić', 'Cade Cunningham', 'James Harden',
         'LaMelo Ball', 'Tyrese Maxey', 'Ty Jerome', 'Trae Young', 'Sam Hauser', 'Tim Hardaway Jr.', 'Luke Kornet', 'Jarrett Allen', 'Rudy Gobert']


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
        f = (E202 if arm == 'K0' else HERE) / f'work/{arm}/A/base-KG-2025-26/c0/cards/K0/{part}/summary.json'
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
    res = {'phase0': {k: p0[k] for k in ('A_subgroup', 'conversion_rho_touch_per_possmin', 'h', 'notBroken_threshold', 'K12_tov_vs_2K_BallHandle_rho', 'K12_ovr_vs_rapm_rho', 'K12_vif', 'F143')},
           'ranking_sha256': {a: sha(rank_path(a)) for a in ARMS}}
    assert res['ranking_sha256']['K12'] == p0['K12_ranking_sha256'] == '29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5'
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
        dd.append(rho(tv['KC'][i], y[i]) - rho(tv['K0'][i], y[i]))
    a_pt = {a: rho(tv[a], y) for a in ARMS}
    res['keepE202'] = {'n': n, 'rho': a_pt, 'diff_KC_minus_K0': a_pt['KC'] - a_pt['K0'], 'diff_ci90': ci(dd), 'MDE_E202': MDE_E202, 'pass': bool(a_pt['KC'] - a_pt['K0'] >= MDE_E202)}
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
            d2.append(rho(ov['KC'][i], rv[i]) - rho(ov['K12'][i], rv[i]))
        res['rapm'][rn] = {'n': int(ok.sum()), 'rho': pt, 'diff': pt['KC'] - pt['K12'], 'diff_ci90': ci(d2)}
    d = res['rapm']['full']['diff']
    res['notBroken'] = {'rho_diff': d, 'threshold': p0['notBroken_threshold'], 'pass_rho': bool(d >= p0['notBroken_threshold']),
                        'c0_bitwise': bool(json.loads((HERE / 'work/K12/final/result.json').read_text(encoding='utf-8'))['c0_equal_0212']), 'split_direction_same': bool(np.sign(res['rapm']['odd']['diff']) == np.sign(res['rapm']['even']['diff']))}
    res['B'] = {'K0': f143(cards['K0']), 'K12': f143(cards['K12']), 'KC': f143(cards['KC']), 'threshold_le': 10}
    res['B']['pass'] = bool(res['B']['KC']['n_below'] <= 10)
    # 只報告：係數與 VIF
    res['coef_per10'] = {a: coef(a) for a in ARMS}
    m5 = [p for p in sorted(cards['KC']) if float(cards['KC'][p]['MIN']) >= 500]
    po = np.array([float(cards['KC'][p]['predictedPer36']) for p in m5])
    ovv = np.array([float(cards['KC'][p]['ovr']) for p in m5])
    slope = float(np.polyfit(po, ovv, 1)[0])
    out_c = {}
    for a in ARMS:
        t = res['coef_per10'][a]['primary']['tovSkill']
        out_c[a] = {'per36': t['per36'], 'SE': t['bootstrapSE'], 'ovr': t['per36'] * slope, 'ovr_SE': t['bootstrapSE'] * slope,
                    'fitA': res['coef_per10'][a]['fitA']['tovSkill'], 'fitB': res['coef_per10'][a]['fitB']['tovSkill']}
    res['tov_per10'] = {'ovr_per_per36_slope': slope, **out_c}
    cols = set(next(iter(cards['KC'].values())).keys())
    attrs = [k for k in res['coef_per10']['KC']['primary'] if k != 'gravity' and k in cols]
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
    # A：持球者子群 tovSkill vs AVG_SEC_PER_TOUCH
    dj = json.loads((ROOT / 'reports/handle-E069/raw/2025-26/Possessions-FULL.json').read_text(encoding='utf-8'))['data']['resultSets']
    rs = dj[0] if isinstance(dj, list) else dj
    ip_, ia_ = rs['headers'].index('PLAYER_ID'), rs['headers'].index('AVG_SEC_PER_TOUCH')
    ast = {r_[ip_]: r_[ia_] for r_ in rs['rowSet']}
    p36 = poss36(cards['K12'])
    subA = sorted(p for p, r_ in cards['K12'].items() if float(r_['MIN']) >= 1000 and p in p36 and p36[p] >= 5 and p in ast)
    sa = np.array([ast[p] for p in subA])
    ta = {a: np.array([float(cards[a][p]['tovSkill']) for p in subA]) for a in ARMS}
    rhoA = {a: rho(ta[a], sa) for a in ARMS}
    rng = np.random.default_rng(SEED); na = len(subA); dA = []
    for _ in range(B):
        i = rng.integers(0, na, na); dA.append(rho(ta['K12'][i], sa[i]) - rho(ta['KC'][i], sa[i]))
    mdeA = p0['A_subgroup']['MDE_A']; dpt = rhoA['K12'] - rhoA['KC']
    res['A'] = {'n': na, 'rho': rhoA, 'diff_K12_minus_KC': dpt, 'diff_ci90': ci(dA), 'MDE_A': mdeA, 'pass': bool(dpt >= mdeA),
                'vif_KC': vif['KC']['vif'], 'vif_K12': vif['K12']['vif']}
    res['external'] = external(cards)
    ids_all = sorted(cards['K0'])
    rk = {a: {p: int(cards[a][p]['rank']) for p in ids_all} for a in ARMS}
    t100 = [p for p in ids_all if rk['K12'][p] <= 100]
    mv = sorted([(cards['K12'][p]['name'], rk['K12'][p], rk['KC'][p]) for p in t100 if abs(rk['KC'][p] - rk['K12'][p]) >= 10], key=lambda x: x[2] - x[1])
    t20 = {a: {p for p in ids_all if rk[a][p] <= 20} for a in ARMS}
    res['moves'] = {'top100_moved_ge10': len(mv), 'list': mv, 'top20_in': [cards['KC'][p]['name'] for p in t20['KC'] - t20['K12']],
                    'top20_out': [cards['K12'][p]['name'] for p in t20['K12'] - t20['KC']]}
    tr = list(csv.DictReader(open(HERE / 'tov-raw-KC.csv', encoding='utf-8')))
    res['topMissing'] = [x['name'] for x in tr if x['topMissing'] == '1']
    v36 = poss36(cards['KC'])
    trank = {a: {p: r for r, p in enumerate(sorted([q for q in ids_all if float(cards[a][q]['MIN']) >= 500], key=lambda q: -float(cards[a][q]['tovSkill'])), 1)} for a in ARMS}
    nm = {cards['K0'][p]['name']: p for p in ids_all}
    tab = []
    for nme in TABLE:
        p = nm.get(nme)
        if p is None:
            tab.append({'name': nme, 'missing': True})
            continue
        tab.append({'name': nme, **{f'TO_{a}': float(cards[a][p]['tovSkill']) for a in ARMS}, **{f'TOrank_{a}': trank[a].get(p) for a in ARMS},
                    **{f'ovr_{a}': float(cards[a][p]['ovr']) for a in ARMS}, **{f'rank_{a}': rk[a][p] for a in ARMS},
                    'poss36': v36.get(p), 'MIN': cards['K0'][p]['MIN']})
    res['table'] = tab
    res['inputs_sha256'] = {Path(f).relative_to(ROOT).as_posix(): sha(f) for f in list(RAPM_FILES.values()) + [TAIL, TWOK, HANDLE, EPM, HERE / 'tail-KC.csv', HERE / 'tov-raw-KC.csv', HERE / 'tov-raw-K12.csv', HERE / 'preregistration.md', HERE / 'phase0.json']}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    write_report(res)
    print(json.dumps({k: res[k] for k in ('A', 'keepE202', 'notBroken', 'B', 'tov_per10', 'vif_tovSkill', 'external', 'moves', 'topMissing', 'table')}, ensure_ascii=False, indent=1, default=float))


def write_report(r):
    A, KP, N, Bq, T, V, X = r['A'], r['keepE202'], r['notBroken'], r['B'], r['tov_per10'], r['vif_tovSkill'], r['external']
    ok = lambda b: '過' if b else '沒過'
    L = ['# E-206 結果（KC＝TO 分母改觸球次數 vs K12＝card 0.2.12）', '',
         f"- A（機制）：持球者子群（n={A['n']}）tovSkill 對 AVG_SEC_PER_TOUCH Spearman K12 {A['rho']['K12']:.4f} → KC {A['rho']['KC']:.4f}（K0 {A['rho']['K0']:.4f}），K12−KC = {A['diff_K12_minus_KC']:+.4f}（90% CI {A['diff_ci90'][0]:+.4f}～{A['diff_ci90'][1]:+.4f}），門檻 MDE_A {A['MDE_A']:.4f} → {ok(A['pass'])}。（只報告：tovSkill 對其他能力值 VIF K12 {A['vif_K12']:.2f} → KC {A['vif_KC']:.2f}。）",
         f"- 保住 E-202：tovSkill 對 2K27 Ball Handle ρ（n={KP['n']}）K0(0.2.11) {KP['rho']['K0']:.4f}、K12 {KP['rho']['K12']:.4f}、KC {KP['rho']['KC']:.4f}；KC − K0 = {KP['diff_KC_minus_K0']:+.4f}（90% CI {KP['diff_ci90'][0]:+.4f}～{KP['diff_ci90'][1]:+.4f}），門檻 {KP['MDE_E202']} → {ok(KP['pass'])}。",
         f"- 沒弄壞：c0 逐位元重現 K12（{'是' if N['c0_bitwise'] else '否'}）；OVR 對 RAPM ρ K12 {r['rapm']['full']['rho']['K12']:.4f} → KC {r['rapm']['full']['rho']['KC']:.4f}，差 {N['rho_diff']:+.4f}（90% CI {r['rapm']['full']['diff_ci90'][0]:+.4f}～{r['rapm']['full']['diff_ci90'][1]:+.4f}；門檻 {N['threshold']:+.4f}）→ {ok(N['pass_rho'])}；npm test 見回報。",
         f"- 分半：odd 差 {r['rapm']['odd']['diff']:+.4f}、even 差 {r['rapm']['even']['diff']:+.4f}，方向{'一致' if N['split_direction_same'] else '不一致'}。",
         f"- B（F-143，不擋採用）：TO 前 30 持球/36 低於池中位數（{Bq['KC']['median']:.3f}）K0 {Bq['K0']['n_below']} → K12 {Bq['K12']['n_below']} → KC {Bq['KC']['n_below']}（≤{Bq['threshold_le']}）→ {ok(Bq['pass'])}；前 30 平均持球/36 {Bq['K12']['top30_mean_poss36']:.2f} → {Bq['KC']['top30_mean_poss36']:.2f}；KC 榜首 {'、'.join(Bq['KC']['top5'])}。",
         f"- tovSkill 每 10 點 OVR：K12 {T['K12']['ovr']:+.3f}（SE {T['K12']['ovr_SE']:.3f}）→ KC {T['KC']['ovr']:+.3f}（SE {T['KC']['ovr_SE']:.3f}）；與 creation 相關 {V['K12']['corr']['creation']:+.2f} → {V['KC']['corr']['creation']:+.2f}、pass {V['K12']['corr']['pass']:+.2f} → {V['KC']['corr']['pass']:+.2f}、gravity {V['K12']['corr']['gravity']:+.2f} → {V['KC']['corr']['gravity']:+.2f}。",
         f"- 外部（K0 / K12 / KC）：2K27 OVR ρ {X['K0']['twok27_ovr_spearman']:.4f} / {X['K12']['twok27_ovr_spearman']:.4f} / {X['KC']['twok27_ovr_spearman']:.4f}；EPM {X['K0']['epm_spearman']:.4f} / {X['K12']['epm_spearman']:.4f} / {X['KC']['epm_spearman']:.4f}；薪水 {X['K0']['salary_wspearman']:.4f} / {X['K12']['salary_wspearman']:.4f} / {X['KC']['salary_wspearman']:.4f}。",
         f"- RAPM 分半 OVR ρ（K12→KC）：odd {r['rapm']['odd']['rho']['K12']:.4f}→{r['rapm']['odd']['rho']['KC']:.4f}；even {r['rapm']['even']['rho']['K12']:.4f}→{r['rapm']['even']['rho']['KC']:.4f}。",
         f"- 前 100 名移動 ≥10 名（KC 對 K12）{r['moves']['top100_moved_ge10']} 人；前 20 進 {'、'.join(r['moves']['top20_in']) or '無'}；出 {'、'.join(r['moves']['top20_out']) or '無'}。topMissing=1：{'、'.join(r['topMissing']) or '無'}。", '',
         '## 球員表（0.2.11→K12→KC）', '', '| 球員 | TO | TO 名次 | OVR | OVR 名次 | 持球/36 |', '|---|---|---|---|---|---|']
    for t in r['table']:
        if t.get('missing'):
            L.append(f"| {t['name']} | 不在名單 | | | | |")
            continue
        ps = f"{t['poss36']:.2f}" if t['poss36'] is not None else 'NA'
        j = lambda k, f: '→'.join(f.format(t[f'{k}_{a}']) for a in ARMS)
        L.append(f"| {t['name']} | {j('TO', '{:.0f}')} | {j('TOrank', '{}')} | {j('ovr', '{:.1f}')} | {j('rank', '{}')} | {ps} |")
    L += ['', '## 前 100 名移動 ≥10（名次 K12→KC）', ''] + [f"- {n}：{a}→{b}" for n, a, b in r['moves']['list']]
    L += ['', '## 與預註冊不同或自行詮釋之處', '',
          '- 「保住 E-202」的 KC − 0.0798：0.0798 取自 E-202 phase0（0.2.11 的 K0），本次評估由 E-202 的 K0 ranking.csv（唯讀）重算，數值相同；門檻 0.0879 取預註冊文字。',
          '- 「沒弄壞」的 h 取 phase0 用 K12 算出的值，RAPM 人群與 phase0 同（MIN≥500 且 RAPM poss≥1000）。',
          '- A 子群：2025-26 卡片 MIN≥1000 且持球/36≥5（handle.csv 持球分鐘÷卡片 MIN×36）且在 Possessions-FULL 有 AVG_SEC_PER_TOUCH（n=64，與 F-144 同）；MDE_A 取 phase0。換算係數 ρ 取卡片池（582 人）2025-26 ΣTOUCHES÷ΣTIME_OF_POSS＝15.593（預註冊「卡片池」未指明是 582 人名單或 252 人 z 池；z 池值 15.012，未使用）。',
          '- VIF 的自變數＝卡片 8 項屬性（不含 gravity）加 gravity，同 E-202 算法。',
          '- 每 10 點 OVR 係數＝primary 擬合每 36 分係數 × OVR 對 predictedPer36 的斜率（同 E-202）。',
          '- 持球/36 取 handle.csv 2025-26 TIME_OF_POSS÷卡片 MIN×36，中位數同 E-202（MIN≥500 人群）。',
          '- 分母改觸球時 r 的單位變成每觸球失誤；v（用球量）、z 池、topMissing 規則不變（本次 topMissing 人數 0）。',
          '- 評估腳本由 E-202 e202_eval.py 複製改寫；跑之前未改門檻；看到 KC 結果後未改權重或定義。']
    (HERE / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
