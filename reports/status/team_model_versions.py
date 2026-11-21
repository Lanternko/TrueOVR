"""E-273：球隊評分 T 各上線版本用同一批比賽重測準度（審查板折線圖用）。輸出 reports/status/team_model_versions.json。

版本（上線順序）：M0 舊引擎（基準）→ T0（R-160）→ T1（R-169，21 欄追蹤本季混合）→ T1+K10（R-171，殘差對凍結的賽前預期）→
T1+K10 today（R-172，殘差對「當天的 T」重算）。診斷列 T1·tovSkill 舊值（0.2.12 tovSkill 改動是否影響 T，不入折線，diagnostic=true）。
集合 A＝2026-27 開季至最新已完賽日（team-games.json 與 league.json 都有比分）；集合 B＝2025-26 整季（E-228 同資訊）。

階段（全部可重跑，本機子程序一律 CREATE_NO_WINDOW）：
  python reports/status/team_model_versions.py prep     # 本機：work/games.json、rots.json（輕量）
  python reports/status/team_model_versions.py fetch    # 本機：賽前快照 snap/<日期>（DateTo＝前一天，已有跳過）
  python reports/status/team_model_versions.py m0       # M0 模擬（可續跑；E-229b 已算且名單相同的場次沿用）
  python reports/status/team_model_versions.py remote   # 5090：deploy→launch→wait→pull（5 個抽樣種子的 T0／T1／T1tov／today）
  python reports/status/team_model_versions.py eval     # 彙整（預設）→ team_model_versions.json
重度部分在 5090 `~/side_projects/pure_ovr/experiments/team-model-versions/`（run_t.py）。"""
import collections, json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TMV = os.path.join(ROOT, 'reports', 'team-model-versions')
W = os.path.join(TMV, 'work')
SEEDS = (229, 230, 231, 232, 233)
CLEAN_AFTER = '2026-10-27'
H, SIG, K = 2.5, 12.0, 10.0
NOWIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def run(cmd, cwd=ROOT):
    r = subprocess.run(cmd, cwd=cwd, creationflags=NOWIN, stdin=subprocess.DEVNULL)
    if r.returncode:
        sys.exit(f'失敗：{cmd}')


def stage(name):
    py = [sys.executable, '-I', '-X', 'utf8']
    if name == 'prep':
        run(py + [os.path.join(TMV, 'prep.py')])
    elif name == 'fetch':
        run(['node', 'fetch_snap.mjs'], cwd=TMV)
    elif name == 'm0':
        run(py + [os.path.join(TMV, 'sim_m0.py'), '6'])
    elif name == 'remote':
        for step in ('deploy', 'launch', 'wait', 'pull'):
            run(['bash', os.path.join(TMV, 'remote_run.sh'), step])
    else:
        sys.exit('階段：prep|fetch|m0|remote|eval')


# ---------- 評分 ----------
def Phi(x):
    return 0.5 * (1 + np.vectorize(math.erf)(x / math.sqrt(2)))


def brier_acc(m, y):
    p = Phi((m + H) / SIG)
    return (p - y) ** 2, ((p > .5) == (y > .5)).astype(float), p


def boot_idx(n, seed=20261108, B=2000):
    return np.random.default_rng(seed).integers(0, n, (B, n))


def delta(a, b, idx):
    """per-game Brier 陣列 a、b 的差（a−b）：點估計與同場次 bootstrap 90% 區間。"""
    d = a - b; m = d[idx].mean(1)
    return float(d.mean()), float(np.percentile(m, 5)), float(np.percentile(m, 95))


def blend_frozen(g, mT, k):
    """E-253 blend（複製）：殘差＝實際分差−(賽前 mT＋H)，同日比賽結束後才更新，÷(場數＋k) 加回。g 需含 date, home, away, d。"""
    res = collections.defaultdict(list); m = np.zeros(len(g))
    by = collections.defaultdict(list)
    for i in sorted(range(len(g)), key=lambda i: g[i]['date']):
        by[g[i]['date']].append(i)
    for day in sorted(by):
        for i in by[day]:
            R = {t: (sum(res[t]) / (len(res[t]) + k) if res[t] else 0.0) for t in (g[i]['home'], g[i]['away'])}
            m[i] = mT[i] + R[g[i]['home']] - R[g[i]['away']]
        for i in by[day]:
            rh = g[i]['d'] - (mT[i] + H); res[g[i]['home']].append(rh); res[g[i]['away']].append(-rh)
    return m


def blend_today(g, mT, today, k):
    """R-172：第 d 天用「當天的 T」重算過去已完賽場次的預期（today[d][gid]）算殘差；當天比賽的基底預測仍是賽前 mT。"""
    m = np.zeros(len(g)); by = collections.defaultdict(list)
    for i, x in enumerate(g):
        by[x['date']].append(i)
    pos = {x['gid']: i for i, x in enumerate(g)}
    for day in sorted(by):
        S = collections.defaultdict(float); N = collections.Counter()
        for gid, pm in today.get(day, {}).items():
            x = g[pos[gid]]; rh = x['d'] - (pm + H)
            S[x['home']] += rh; S[x['away']] -= rh; N[x['home']] += 1; N[x['away']] += 1
        R = lambda t: S[t] / (N[t] + k)
        for i in by[day]:
            m[i] = mT[i] + R(g[i]['home']) - R(g[i]['away'])
    return m


def wins_partial(p, y, g):
    """已賽部分各隊「預測勝場（逐場賽前勝率加總）−實際勝場」絕對值平均。"""
    pw = collections.defaultdict(float); aw = collections.defaultdict(float)
    for i, x in enumerate(g):
        pw[x['home']] += p[i]; pw[x['away']] += 1 - p[i]; aw[x['home']] += y[i]; aw[x['away']] += 1 - y[i]
    return float(np.mean([abs(pw[t] - aw[t]) for t in pw]))


META = {
    'M0': dict(order=0, date='11-04 前（被 T0 取代）', ruling='R-158／R-153', change='舊模擬引擎 sim 0.1.4（每場兩隊陣容對 E-224 梯度隊模擬 200 局），作基準'),
    'T0': dict(order=1, date='2026-11-04', ruling='R-160', change='球隊評分換成陣容 Transformer：15 項能力值＋box 五欄本季混合，21 欄追蹤統計只用 2025-26'),
    'T1': dict(order=2, date='2026-11-05', ruling='R-169', change='21 欄追蹤統計（hustle／rimthree／matchup／adv）改本季混合 w=min/(min+500)'),
    'T1+K10': dict(order=3, date='2026-11-07', ruling='R-171', change='再把本季實際表現殘差（實際−賽前預期）÷(場數+10) 加回預測，殘差對凍結的賽前預期算'),
    'T1+K10 today': dict(order=4, date='2026-11-07', ruling='R-172', change='殘差改成對「當天的 T」重算過去已完賽場次（避免和本季 OVR 更新重複計入）'),
    'T0+K10（代用）': dict(order=3, date='2026-11-07', ruling='R-171', change='代用列：2025-26 無法重現 T1，改在 T0 同資訊預測上套 K10 殘差混合（E-253 的 blend）'),
    'T1·tovSkill舊值': dict(order=90, date='（診斷）', ruling='R-139', change='診斷：10-31 起 live 夾的 tovSkill 換回 0.2.9 的值，量 0.2.12 tovSkill 改動對 T 的影響'),
}


def row(version, setname, n, br, acc, wmae, d, note, **extra):
    r = dict(version=version, order=META[version]['order'], date=META[version]['date'], change=META[version]['change'], ruling=META[version]['ruling'],
             set=setname, n=n, brier=br, acc=acc, winsMAE=wmae, dBrierPrev=None, dBrierLo=None, dBrierHi=None,
             nClean=None, brierClean=None, accClean=None, dBrierPrevClean=None, dBrierLoClean=None, dBrierHiClean=None, note=note)
    if d:
        r['dBrierPrev'], r['dBrierLo'], r['dBrierHi'] = d
    r.update(extra)
    return r


# ---------- 集合 A ----------
def set_a():
    g = json.load(open(os.path.join(W, 'games.json')))
    m0 = json.load(open(os.path.join(W, 'm0.json')))
    y = np.array([1.0 if x['pts_home'] > x['pts_away'] else 0.0 for x in g]); n = len(g)
    gg = [dict(gid=x['gid'], date=x['date'], home=x['home'], away=x['away'], d=x['pts_home'] - x['pts_away']) for x in g]
    last = max(x['date'] for x in g)
    setname = f'2026-27 開季至 {last[5:]}'
    mM = np.array([m0[f"{x['gid']}|home"] - m0[f"{x['gid']}|away"] for x in g])
    per = {s: json.load(open(os.path.join(W, f'seed_{s}.json'))) for s in SEEDS}
    arms = collections.defaultdict(dict)        # arm -> seed -> margin 陣列
    for s, D in per.items():
        for a in ('T0', 'T1', 'T1tov'):
            arms[a][s] = np.array([D[a][x['gid']] for x in g])
        arms['K10'][s] = blend_frozen(gg, arms['T1'][s], K)
        arms['K10t'][s] = blend_today(gg, arms['T1'][s], D['today'], K)
    names = {'M0': 'M0', 'T0': 'T0', 'T1': 'T1', 'K10': 'T1+K10', 'K10t': 'T1+K10 today', 'T1tov': 'T1·tovSkill舊值'}
    stats = {}
    bM, aM, pM = brier_acc(mM, y); stats['M0'] = dict(b=[bM], a=[aM], w=[wins_partial(pM, y, gg)], sd=0.0)
    for a in ('T0', 'T1', 'K10', 'K10t', 'T1tov'):
        bs, as_, ws = [], [], []
        for s in SEEDS:
            b, ac, p = brier_acc(arms[a][s], y); bs.append(b); as_.append(ac); ws.append(wins_partial(p, y, gg))
        stats[a] = dict(b=bs, a=as_, w=ws, sd=float(np.std([x.mean() for x in bs], ddof=1)))
    idx = boot_idx(n)
    pg = {a: np.mean(v['b'], axis=0) for a, v in stats.items()}          # 5 種子平均的逐場 Brier
    # 無偷看子集：prep.folder_for 對比賽日 ≤ 第一個 live 夾（10-27）的場次退回 10-27 夾（含當天結果），故只留比賽日 > CLEAN_AFTER 的場次
    clean = np.array([x['date'] > CLEAN_AFTER for x in g]); nc = int(clean.sum()); idxc = boot_idx(nc)
    pa = {a: np.mean(v['a'], axis=0) for a, v in stats.items()}
    prev = {'T0': 'M0', 'T1': 'T0', 'K10': 'T1', 'K10t': 'K10', 'T1tov': 'T1'}
    notes = {
        'M0': 'E-229b 做法：每場實際上場名單×比賽日前自己的平均分鐘，屬性用比賽日前最新 live 夾；無抽樣種子（200 局模擬）。',
        'T0': '追蹤欄全用 2025-26；box 五欄本季混合。',
        'T1': '追蹤欄用比賽日前一天的官網整季累計快照（DateTo）與逐場 matchup 加總。',
        'K10': '殘差用各場當時賽前預期（T1 值）算，同日比賽結束後才更新。',
        'K10t': '殘差用當天的 T 重算過去場次（當天 live 夾＋當天追蹤混合）。與 R-171 逐場預測不同（殘差約縮兩成），非同一點。',
        'T1tov': '診斷列：只換 tovSkill 欄（舊夾沒有的人保留新值），其餘同 T1；用來看 0.2.12 tovSkill 改動（10-31 起進 live 夾）對 T 的影響。',
    }
    rows = []
    for a in ('M0', 'T0', 'T1', 'K10', 'K10t', 'T1tov'):
        v = stats[a]; br = float(np.mean([x.mean() for x in v['b']])); ac = float(np.mean([x.mean() for x in v['a']]))
        d = delta(pg[a], pg[prev[a]], idx) if a in prev else None
        dc = delta(pg[a][clean], pg[prev[a]][clean], idxc) if a in prev else (None, None, None)
        extra = dict(brierSeedSD=v['sd'], nSeeds=len(v['b']) if a != 'M0' else 1, nClean=nc, brierClean=float(pg[a][clean].mean()), accClean=float(pa[a][clean].mean()),
                     dBrierPrevClean=dc[0], dBrierLoClean=dc[1], dBrierHiClean=dc[2])
        if a == 'T1tov':
            extra['diagnostic'] = True
        note = notes[a] + ('' if a == 'M0' else f' 5 個抽樣種子平均（Brier 種子 SD {v["sd"]:.4f}）；ΔBrier 對 {names[prev[a]]}，同場次 bootstrap 90%。') + \
            ' winsMAE＝只含已賽部分的各隊「預測勝場−實際勝場」（非全季）。'             f' *Clean 欄＝無偷看子集（比賽日 > {CLEAN_AFTER[5:]}，n={nc}）：{n - nc} 場比賽日 ≤ {CLEAN_AFTER[5:]} 的場次用了含當天結果的 {CLEAN_AFTER[5:]} live 夾，主結論以 Clean 欄為準。'
        rows.append(row(names[a], setname, n, br, ac, float(np.mean(v['w'])), d, note, **extra))
    return rows, dict(n=n, last=last, games=gg, arms=arms, per=per)


# ---------- 集合 B ----------
def set_b():
    sys.path.insert(0, os.path.join(ROOT, 'reports', 'E223-team-rating'))
    from e223_lib import CARDS, SEASONS, load_card, wins_mae
    from fit_train import features
    zmap, zmiss, _ = load_card(CARDS / SEASONS['2526']['card'])
    F = features('2526', zmap, zmiss)
    P = json.load(open(os.path.join(ROOT, 'reports', 'E228-transformer-team-rating', 'work', 'pred-T-2526-same.json')))
    y, ids, home, away = F['y'], F['ids'], F['home'], F['away']; n = len(y)
    assert P['games'] == list(range(n)) and P['home'] == list(home) and P['away'] == list(away)
    mT = np.array(P['margin_seed']).mean(0); mM = F['m0']
    G = [dict(date=x['date'], home=str(x['home']), away=str(x['away']), d=x['hs'] - x['as']) for x in F['S']['games']]
    assert [x['home'] for x in G] == [str(h) for h in home]
    mK = blend_frozen(G, mT, K)
    idx = boot_idx(n, 20261102)       # E-228 的 rng
    out = {}
    for a, m in (('M0', mM), ('T0', mT), ('K10', mK)):
        b, ac, p = brier_acc(m, y); out[a] = dict(b=b, a=ac, w=wins_mae(p, y, home, away, ids))
    setname = '2025-26 整季'
    rows = [
        row('M0', setname, n, float(out['M0']['b'].mean()), float(out['M0']['a'].mean()), out['M0']['w'], None,
            'E-228 同資訊重比：M0 用 2025-26 同季屬性（含 E-208 污染，對 M0 有利）。'),
        row('T0', setname, n, float(out['T0']['b'].mean()), float(out['T0']['a'].mean()), out['T0']['w'], delta(out['T0']['b'], out['M0']['b'], idx),
            'E-228 同資訊重比（T2425 權重、2025-26 整季特徵＝與 M0 同資訊，單一抽樣種子、5 個 net 平均）；ΔBrier 對 M0。winsMAE＝全季預測勝場誤差。'),
        row('T1', setname, None, None, None, None, None,
            '無法量測：T1 的本季追蹤混合需要賽前逐日的官網快照與逐場 matchup，2025-26 沒有（E-228 同資訊特徵是整季累計，已含全季，混合無意義）。'),
        row('T1+K10', setname, None, None, None, None, None,
            '無法量測：需要 T1 的逐日特徵。K10 本身在 2025-26 的效果見下一列（以 T0 代用）與 E-253（季前特徵 T0 0.2175→K10 0.2008）。'),
        row('T1+K10 today', setname, None, None, None, None, None,
            '無法量測：2025-26 同資訊特徵整季固定，「當天的 T」＝賽前 T，R-172 在此與 R-171 定義重合（逐場預測相同），故不另算。'),
        {**row('T0+K10（代用）', setname, n, float(out['K10']['b'].mean()), float(out['K10']['a'].mean()), out['K10']['w'], delta(out['K10']['b'], out['T0']['b'], idx),
               '代用列（version 為 T0+K10（代用），標 substitute=true，不與 T1+K10 同 key；繪圖請用 2026-27 的點）：在 T0 同資訊預測上套 K10（E-253 的 blend），ΔBrier 對 T0。'
               'winsMAE＝逐場賽前預測（含季內殘差更新）的全季加總，資訊量比 M0／T0 的季初預測多，不可直接比。'), 'substitute': True},
    ]
    return rows


def main():
    global np
    import numpy as np
    rows_a, info = set_a()
    rows_b = set_b()
    out = rows_a + rows_b
    json.dump(out, open(os.path.join(HERE, 'team_model_versions.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in out:
        print(f"{r['set']:<22}{r['version']:<18}n={r['n']}  brier={r['brier'] if r['brier'] is None else round(r['brier'], 4)}  acc={r['acc'] if r['acc'] is None else round(r['acc'], 3)}  "
              f"clean n={r['nClean']} b={r['brierClean'] if r['brierClean'] is None else round(r['brierClean'], 4)} acc={r['accClean'] if r['accClean'] is None else round(r['accClean'], 3)} "
              f"dC={None if r['dBrierPrevClean'] is None else (round(r['dBrierPrevClean'], 4), round(r['dBrierLoClean'], 4), round(r['dBrierHiClean'], 4))}  "
              f"wins={r['winsMAE'] if r['winsMAE'] is None else round(r['winsMAE'], 2)}  d={None if r['dBrierPrev'] is None else (round(r['dBrierPrev'], 4), round(r['dBrierLo'], 4), round(r['dBrierHi'], 4))}")
    return info


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else 'eval'
    if a == 'eval':
        main()
    else:
        stage(a)
