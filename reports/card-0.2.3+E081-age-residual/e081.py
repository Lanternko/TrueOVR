"""E-081：card 0.2.3 樣本外年齡偏差診斷（預註冊 preregistration.md，sha256 見 preregistration.sha256）。

輸入（都在本資料夾，先跑 e081_cards.py、rapm1.py）：cards.json（卡片 g_c、答案 Q、年齡、MPG）、rapm1-A.csv／rapm1-B.csv（答案 N 的 RAPM）。
輸出：results.json、report.md。不改任何已凍結的東西。

  python e081.py
"""
import csv, hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NBOOT = 2000
GROUPS = [('<=23', lambda a: a <= 23), ('24-27', lambda a: 24 <= a <= 27), ('28-30', lambda a: 28 <= a <= 30), ('>=31', lambda a: a >= 31)]
NAMED = ['Paolo Banchero', 'Jalen Williams', 'Jalen Johnson']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(x):
    """0-1 百分位名次，同分取平均名次：(avg_rank - 1) / (n - 1)。"""
    return (rankdata(x) - 1.0) / (len(x) - 1.0)


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return float('nan')
    return float(np.corrcoef(ra, rb)[0, 1])


def read_rapm1(h):
    return {int(r['playerId']): {k: float(r[k]) for k in ('net', 'O', 'D', 'poss')} | {'name': r['name']}
            for r in csv.DictReader(open(HERE / f'rapm1-{h}.csv', encoding='utf-8'))}


def main():
    # ---- 唯讀目錄：before（先前已算好，這裡只讀）
    ro_before = json.loads((HERE / 'work/ro_before.json').read_text(encoding='utf-8'))
    pre_sha_before = sha(HERE / 'preregistration.md')
    pre_expected = (HERE / 'preregistration.sha256').read_text(encoding='utf-8').split()[0]
    assert pre_sha_before == pre_expected, '預註冊 sha256 與凍結值不同'

    C = json.loads((HERE / 'cards.json').read_text(encoding='utf-8'))
    k0 = C['k0']
    k1 = json.loads((HERE / 'rapm1-summary.json').read_text(encoding='utf-8'))['k1']
    rapm1 = {'A': read_rapm1('A'), 'B': read_rapm1('B')}
    master_all = C['master']

    # ---- 每個方向：N、Q、卡片、年齡；排除沒有年齡的人（先排除再排名）
    dirs, excl = {}, {}
    for dn in ('AB', 'BA'):
        d = C['dirs'][dn]
        ev = dn[1]
        n_pool = len(d['names'])
        keep, no_age, no_rapm = [], [], []
        N = []
        for i, pid in enumerate(d['pid']):
            if d['age'][i] is None:
                no_age.append(d['names'][i]); continue
            if pid not in rapm1[ev]:
                no_rapm.append(d['names'][i]); continue
            keep.append(i)
        keep = np.array(keep)
        names = [d['names'][i] for i in keep]
        pids = [d['pid'][i] for i in keep]
        age = np.array([d['age'][i] for i in keep], dtype=float)
        cand = np.array([d['cand'][i] for i in keep])
        ansQ = np.array([d['ans'][i] for i in keep])
        mpg = np.array([d['mpg_ev'][i] for i in keep])
        net1 = np.array([rapm1[ev][p]['net'] for p in pids])
        ansN = net1 * mpg
        pc, pN, pQ = pct(cand), pct(ansN), pct(ansQ)
        dirs[dn] = {'names': names, 'pids': pids, 'age': age, 'cand': cand, 'ansN': ansN, 'ansQ': ansQ, 'pc': pc, 'pN': pN, 'pQ': pQ,
                    'uN': pN - pc, 'uQ': pQ - pc, 'netN': net1, 'mpg': mpg}
        excl[dn] = {'pool': n_pool, 'used': len(keep), 'excluded_no_age': no_age, 'excluded_no_rapm1': no_rapm}

    # ---- 點估計
    def S_of(u_key, sub=None):
        return float(np.mean([spearman(dirs[dn]['age'], dirs[dn][u_key]) for dn in dirs]))

    S_N, S_Q = S_of('uN'), S_of('uQ')
    S_dir = {dn: {'N': spearman(dirs[dn]['age'], dirs[dn]['uN']), 'Q': spearman(dirs[dn]['age'], dirs[dn]['uQ'])} for dn in dirs}

    def group_stats(u_key, dn_list=('AB', 'BA')):
        out = {}
        for g, f in GROUPS:
            per = {}
            for dn in dn_list:
                m = np.array([f(a) for a in dirs[dn]['age']])
                per[dn] = (float(dirs[dn][u_key][m].mean()) if m.any() else float('nan'), int(m.sum()))
            out[g] = per
        return out

    gN, gQ = group_stats('uN'), group_stats('uQ')

    def g_point(gs):
        return {g: float(np.nanmean([gs[g][dn][0] for dn in gs[g]])) for g in gs}

    gN_pt, gQ_pt = g_point(gN), g_point(gQ)

    # ---- bootstrap：以球員重抽，master 名單聯集，兩個方向共用同一組抽樣（照 E-075 b2）
    master = sorted(set(C['dirs']['AB']['names']) | set(C['dirs']['BA']['names']))
    assert master == sorted(master_all)
    NN = len(master)
    mp_ = {dn: np.array([{n: i for i, n in enumerate(dirs[dn]['names'])}.get(n, -1) for n in master]) for dn in dirs}
    rng = np.random.default_rng(1)
    bN, bQ, bDiff, bN_rerank = [], [], [], []
    bgN = {g: [] for g, _ in GROUPS}
    bgQ = {g: [] for g, _ in GROUPS}
    for _ in range(NBOOT):
        ix = rng.integers(0, NN, NN)
        sN, sQ, sR = [], [], []
        gdN = {g: [] for g, _ in GROUPS}
        gdQ = {g: [] for g, _ in GROUPS}
        for dn, d in dirs.items():
            s = mp_[dn][ix]
            s = s[s >= 0]
            sN.append(spearman(d['age'][s], d['uN'][s]))
            sQ.append(spearman(d['age'][s], d['uQ'][s]))
            # 僅供參考：在重抽樣本內重新排名
            uR = pct(d['ansN'][s]) - pct(d['cand'][s])
            sR.append(spearman(d['age'][s], uR))
            for g, f in GROUPS:
                m = np.array([f(a) for a in d['age'][s]])
                gdN[g].append(float(d['uN'][s][m].mean()) if m.any() else np.nan)
                gdQ[g].append(float(d['uQ'][s][m].mean()) if m.any() else np.nan)
        bN.append(float(np.mean(sN))); bQ.append(float(np.mean(sQ))); bDiff.append(bN[-1] - bQ[-1]); bN_rerank.append(float(np.mean(sR)))
        for g, _ in GROUPS:
            bgN[g].append(float(np.nanmean(gdN[g]))); bgQ[g].append(float(np.nanmean(gdQ[g])))

    def ci(b):
        b = np.array(b, dtype=float)
        return float(np.nanpercentile(b, 5)), float(np.nanpercentile(b, 95))

    S_N_ci, S_Q_ci, D_ci, R_ci = ci(bN), ci(bQ), ci(bDiff), ci(bN_rerank)
    if S_N_ci[1] < 0:
        verdict = '年輕被低估'
    elif S_N_ci[0] > 0:
        verdict = '老將被低估'
    else:
        verdict = '沒有可偵測的偏差'

    groups = {}
    for g, _ in GROUPS:
        groups[g] = {'N': {'mean_u': gN_pt[g], 'lo90': ci(bgN[g])[0], 'hi90': ci(bgN[g])[1],
                           'n_AB': gN[g]['AB'][1], 'n_BA': gN[g]['BA'][1], 'mean_u_AB': gN[g]['AB'][0], 'mean_u_BA': gN[g]['BA'][0]},
                     'Q': {'mean_u': gQ_pt[g], 'lo90': ci(bgQ[g])[0], 'hi90': ci(bgQ[g])[1],
                           'n_AB': gQ[g]['AB'][1], 'n_BA': gQ[g]['BA'][1], 'mean_u_AB': gQ[g]['AB'][0], 'mean_u_BA': gQ[g]['BA'][0]}}

    # ---- 指名球員（只報告）
    named = {}
    for nm in NAMED:
        named[nm] = {}
        for dn, d in dirs.items():
            if nm in d['names']:
                i = d['names'].index(nm)
                named[nm][dn] = {'age': int(d['age'][i]), 'pct_card': float(d['pc'][i]), 'pct_N': float(d['pN'][i]), 'pct_Q': float(d['pQ'][i]),
                                 'u_N': float(d['uN'][i]), 'u_Q': float(d['uQ'][i]), 'rapm1_net': float(d['netN'][i]), 'mpg_ev': float(d['mpg'][i])}
            else:
                named[nm][dn] = None

    # ---- 唯讀目錄 after（所有計算與輸入讀取完成後；子程序無視窗）
    subprocess.run([sys.executable, str(HERE / 'ro_sha.py'), str(HERE / 'work/ro_after.json')], check=True, cwd=str(HERE),
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                   env={**__import__('os').environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    ro_after = json.loads((HERE / 'work/ro_after.json').read_text(encoding='utf-8'))
    ro = {}
    for dname in ro_before:
        b, a = ro_before[dname], ro_after[dname]
        ro[dname] = {'n_files_before': b['n_files'], 'n_files_after': a['n_files'], 'aggregate_sha256_before': b['aggregate_sha256'],
                     'aggregate_sha256_after': a['aggregate_sha256'], 'unchanged': bool(b['files'] == a['files'])}
    ro_all_ok = all(v['unchanged'] for v in ro.values())
    pre_sha_after = sha(HERE / 'preregistration.md')

    results = {
        'experiment': 'E-081', 'purpose': 'card 0.2.3 樣本外年齡偏差診斷（不改卡）',
        'verdict': verdict,
        'verdict_rule': 'S_N 的 90% 區間上界 < 0 → 年輕被低估；下界 > 0 → 老將被低估；其他 → 沒有可偵測的偏差',
        'S_N': {'point': S_N, 'lo90': S_N_ci[0], 'hi90': S_N_ci[1], 'per_direction': {dn: S_dir[dn]['N'] for dn in dirs}},
        'S_Q': {'point': S_Q, 'lo90': S_Q_ci[0], 'hi90': S_Q_ci[1], 'per_direction': {dn: S_dir[dn]['Q'] for dn in dirs}, 'note': '只報告，不作判準'},
        'S_N_minus_S_Q': {'point': S_N - S_Q, 'lo90': D_ci[0], 'hi90': D_ci[1], 'note': '同一組 bootstrap，只報告'},
        'S_N_rerank_in_resample': {'point': S_N, 'lo90': R_ci[0], 'hi90': R_ci[1], 'note': '僅供參考：重抽樣本內重新排名 u（主分析 u 固定為全人群排名）'},
        'groups': groups, 'age_groups': [g for g, _ in GROUPS],
        'players': {dn: {'pool': excl[dn]['pool'], 'used': excl[dn]['used'], 'excluded_no_age': len(excl[dn]['excluded_no_age']),
                         'excluded_no_rapm1': len(excl[dn]['excluded_no_rapm1'])} for dn in dirs},
        'excluded_names': {dn: {'no_age': excl[dn]['excluded_no_age'], 'no_rapm1': excl[dn]['excluded_no_rapm1']} for dn in dirs},
        'master_size': NN, 'n_boot': NBOOT, 'seed': 1,
        'k0': k0, 'k1': k1,
        'named_players': named,
        'readonly_sha256': {'dirs': ro, 'all_unchanged': ro_all_ok, 'manifest_before': 'work/ro_before.json', 'manifest_after': 'work/ro_after.json'},
        'preregistration_sha256': {'frozen': pre_expected, 'before': pre_sha_before, 'after': pre_sha_after, 'unchanged': pre_sha_before == pre_sha_after == pre_expected},
        'inputs_sha256': {'cards.json': sha(HERE / 'cards.json'), 'rapm1-A.csv': sha(HERE / 'rapm1-A.csv'), 'rapm1-B.csv': sha(HERE / 'rapm1-B.csv')},
    }
    (HERE / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    write_report(results)
    print(json.dumps({k: results[k] for k in ('verdict', 'S_N', 'S_Q', 'S_N_minus_S_Q', 'S_N_rerank_in_resample', 'players')}, ensure_ascii=False, indent=1))
    print('ro_all_unchanged', ro_all_ok, 'prereg_unchanged', results['preregistration_sha256']['unchanged'])


def f3(x):
    return f'{x:+.3f}'


def write_report(r):
    L = []
    L.append('# E-081 報告：card 0.2.3 樣本外年齡偏差診斷\n')
    L.append('- 性質：診斷，不改卡。預註冊 `preregistration.md`（sha256 `%s`，執行前後相同）。' % r['preregistration_sha256']['frozen'])
    L.append('- 產生：`e081_cards.py`（複製 e075.py，只加輸出）→ `cards.json`；`rapm1.py` → `rapm1-A.csv`、`rapm1-B.csv`；`e081.py` → `results.json`、本檔。\n')
    L.append('## 判定\n')
    L.append(f"**{r['verdict']}**（答案 N，S 的 90%% 區間 [%s, %s]；判定規則：上界 < 0 年輕被低估、下界 > 0 老將被低估、其他無可偵測偏差）。\n" % (f3(r['S_N']['lo90']), f3(r['S_N']['hi90'])))
    L.append('## S = Spearman(年齡, u)，兩方向平均（u = pct(答案) − pct(卡片)，u > 0 = 卡片低估；S < 0 = 年輕被低估）\n')
    L.append('| 答案 | S 點估計 | 90% 區間 | AB | BA | 角色 |\n|---|---|---|---|---|---|')
    L.append(f"| N（2025-26 單季分半 RAPM × MPG） | {f3(r['S_N']['point'])} | [{f3(r['S_N']['lo90'])}, {f3(r['S_N']['hi90'])}] | {f3(r['S_N']['per_direction']['AB'])} | {f3(r['S_N']['per_direction']['BA'])} | 主（判準） |")
    L.append(f"| Q（四季合併 pooledNet × MPG，E-064 舊量尺） | {f3(r['S_Q']['point'])} | [{f3(r['S_Q']['lo90'])}, {f3(r['S_Q']['hi90'])}] | {f3(r['S_Q']['per_direction']['AB'])} | {f3(r['S_Q']['per_direction']['BA'])} | 只報告 |")
    d = r['S_N_minus_S_Q']
    L.append(f"| N − Q（同一組 bootstrap） | {f3(d['point'])} | [{f3(d['lo90'])}, {f3(d['hi90'])}] | | | 只報告 |")
    d = r['S_N_rerank_in_resample']
    L.append(f"| N（參考：重抽樣本內重新排名 u） | {f3(d['point'])} | [{f3(d['lo90'])}, {f3(d['hi90'])}] | | | 僅供參考，不作判準 |\n")
    L.append('## 年齡分組的 u 平均（兩方向平均；90% 區間為同一組 bootstrap；人數為 AB／BA）\n')
    L.append('| 年齡組 | 人數 AB／BA | N：u 平均 | N：90% 區間 | Q：u 平均 | Q：90% 區間 |\n|---|---|---|---|---|---|')
    for g in r['age_groups']:
        a = r['groups'][g]
        L.append(f"| {g} | {a['N']['n_AB']}／{a['N']['n_BA']} | {f3(a['N']['mean_u'])} | [{f3(a['N']['lo90'])}, {f3(a['N']['hi90'])}] | {f3(a['Q']['mean_u'])} | [{f3(a['Q']['lo90'])}, {f3(a['Q']['hi90'])}] |")
    L.append('')
    L.append('分方向的組平均（N）：' + '；'.join(f"{g} AB {f3(r['groups'][g]['N']['mean_u_AB'])}／BA {f3(r['groups'][g]['N']['mean_u_BA'])}" for g in r['age_groups']) + '\n')
    L.append('## 人數與排除\n')
    p = r['players']
    L.append('| 方向 | 人群（E-075 pools） | 納入分析 | 排除：沒有年齡 | 排除：評估半季 RAPM1 沒有此人 |\n|---|---|---|---|---|')
    for dn in ('AB', 'BA'):
        L.append(f"| {dn} | {p[dn]['pool']} | {p[dn]['used']} | {p[dn]['excluded_no_age']} | {p[dn]['excluded_no_rapm1']} |")
    L.append(f"\n兩方向聯集（bootstrap 的 master 名單）{r['master_size']} 人；排除合計 {sum(p[dn]['excluded_no_age'] + p[dn]['excluded_no_rapm1'] for dn in p)} 人次。\n")
    L.append('## 自檢\n')
    k0, k1 = r['k0'], r['k1']
    L.append(f"- (k0) 重算的 c2 與 E-075 `results.json` 比對（delta、ci90 兩端、rho_cand／rho_base 的 AB／BA）：最大絕對差 {k0['maxAbsDiff']:.3g}（門檻 < 1e-9）→ **{'通過' if k0['pass'] else '失敗'}**。")
    L.append(f"- (k1) `rapm1.py` 對 2025-26 全季（λ 3000）擬合，與 `reports/impact-rapm/rapm.csv` 的 lastSeasonNet／O／D（csv 為 3 位小數，我方也四捨五入後比）最大絕對差 {k1['maxAbsDiff']:.3g}（門檻 < 1e-6）→ **{'通過' if k1['pass'] else '失敗'}**。比對 {k1['compared_present']} 人，csv 中 {k1['ref_players_absent_in_season(csv=0)']} 人不在本季（csv 填 0，同樣納入比對且相符）；另 lastSeasonPoss 四捨五入後最大差 {k1['poss_maxAbsDiff_rounded']:.3g}。\n")
    L.append('## 唯讀目錄 sha256（L-037；before 為開工後、跑任何程式前，after 為全部計算完成後；逐檔相同才算 unchanged）\n')
    L.append('| 目錄 | 檔數（前／後） | 彙總 sha256 前 | 彙總 sha256 後 | 逐檔相同 |\n|---|---|---|---|---|')
    for dname, v in r['readonly_sha256']['dirs'].items():
        L.append(f"| `{dname}/` | {v['n_files_before']}／{v['n_files_after']} | `{v['aggregate_sha256_before']}` | `{v['aggregate_sha256_after']}` | {'是' if v['unchanged'] else '**否**'} |")
    L.append(f"\n全部唯讀目錄未變：**{'是' if r['readonly_sha256']['all_unchanged'] else '否'}**。逐檔清單：`work/ro_before.json`、`work/ro_after.json`。預註冊 sha256 前後皆 `{r['preregistration_sha256']['after']}`，與凍結值{'相同' if r['preregistration_sha256']['unchanged'] else '**不同**'}。\n")
    L.append('## 指名球員（只報告；pct = 方向內百分位，u = pct(答案) − pct(卡片)）\n')
    L.append('| 球員 | 方向 | 年齡 | pct 卡片 | pct N | pct Q | u（N） | u（Q） |\n|---|---|---|---|---|---|---|---|')
    for nm, v in r['named_players'].items():
        for dn in ('AB', 'BA'):
            x = v[dn]
            if x is None:
                L.append(f'| {nm} | {dn} | 不在此方向人群 | | | | | |')
            else:
                L.append(f"| {nm} | {dn} | {x['age']} | {x['pct_card']:.3f} | {x['pct_N']:.3f} | {x['pct_Q']:.3f} | {f3(x['u_N'])} | {f3(x['u_Q'])} |")
    L.append('')
    L.append('## 預註冊沒寫死、我採用的解讀（最字面讀法）\n')
    for s in INTERP:
        L.append('- ' + s)
    L.append('\n## 範圍與限制\n')
    L.append('- 只跑 E-075 主規格那一輪（敏感度 s1–s3 與卡片輸出略過，不影響主規格的半季評估：`dirs` 與 c2 在那些步驟之前已算完；k0 已證實相同）。')
    L.append('- 這是對 card 0.2.3 在半季擬合下的診斷，不是對正式卡 ranking 的直接評估；不改卡、不下採用結論，後續是否修正由 lead 另寫預註冊。')
    (HERE / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


INTERP = [
    '卡片 g_c：取 E-075 `pipeline` 主規格「半季評估」裡的 `dirs[dn]["cand"]`（程式只加輸出、演算法一字不改，`e081_cards.py` 對 e075.py 的差異只有：檔頭說明、`half_only` 提前輸出、`main()` 改成只跑主規格並做 k0）。',
    '答案 N 的 MPG：`D["mpgh"][評估半季][pid][1]`（與 E-075 `ans` 用的相同欄位）；N = rapm1-{評估半季}.net × 該 MPG。rapm1 的 net = O + D（同 rapm.py 的 pooledNet 口徑）。',
    '分半 RAPM：2025-26 stint 以 `int(gameId) % 2` 分 A／B，各半 λ 固定 3000（不做 CV），截距不罰；與 rapm.py 的 `normal_equations`／`solve` 同式（直接匯入，原檔不改）。方向 AB 的評估半季為 B（用 rapm1-B.csv），BA 為 A。',
    '百分位 = (平均名次 − 1) / (n − 1)，n 為該方向納入分析的人數；沒有年齡（或評估半季 RAPM1 沒有）的人先排除再排名，N 與 Q 用同一批人。',
    'Spearman 用平均名次處理同分（年齡同分很多）。S = 兩方向各算一次後取平均。',
    'bootstrap：master = 兩方向 `pools` 名單的聯集（排序後），每次 `ix = rng.integers(0, NN, NN)`（`default_rng(1)`），兩方向共用；把 ix 對映到各方向名單後丟掉不在該方向的人，重複抽到的人保留重複（同 E-075 b2）。主分析中 u 固定為全人群排名下的殘差、只對 (年齡, u) 重抽；「重抽樣本內重新排名」另列為參考欄，不作判準。',
    '年齡分組 ≤23、24–27、28–30、≥31；組平均在各方向先算，再取兩方向平均（某方向某組在重抽中為空時以另一方向代表，`nanmean`）。90% 區間 = bootstrap 5%／95% 百分位。',
    '判定只看答案 N 的 S 的 90% 區間；N − Q、Q、重新排名版都不作判準。',
]


if __name__ == '__main__':
    main()
