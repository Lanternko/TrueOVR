"""E-196（R-133）SP 臂的 production 能力值。spec：reports/card-0.2.10g+E196-production/spec.md（凍結）。
  原始值 prod = (PTS + 0.25·SELF_FG_PTS) / MIN × 36 × (TS / lgTS)
    SELF_FG_PTS＝creation 分子所計入出手的投籃得分。0.2.10g 的 creation 分子是 (1−dep)·FGA（dep＝creationDependence／sourceDependence，
    球員層級的「依賴他人出手」比例），同一套分類套到投籃得分就是 (1−dep)·(PTS−FTM)。
    TS＝PTS／(2·(FGA＋0.44·FTA))（同窗口）；lgTS＝同季聯盟 TS（player-games 全部列）。
  窗口、季權重、池、映射全部照 0.2.10g 的 creation（window10 HEAD 版 Win10：四季 E-175 U 臂權重、2025-26 季末 c=82；
  池＝2025-26 窗口值（U 鏈 poolPids）＋過去三季（2022-23～2024-25）單季值（GP>=30、MPG>=20）；PctMapper＋E-101 尾巴旗標同 creation）。
  步驟 0（L-105）：先用同一段程式重算 creation，與 card-0.2.12/tail-U.csv（2025-26 窗口版）及 E-125 raw-<季>.json（過去季池值）對上才往下。
  歷史原點（A 線）：E-181 的歷史卡能力值層是 2025-26 單季靜態值（L-091，tail-e123a.csv）；production 照同一取法（單季 2025-26，聯盟 JSON observed），
    步驟 0 同樣先重現 tail-e123a.csv 的 creation。
輸出：tail-U-SP.csv（tail-U.csv 只把 creation 欄換成 production）、tail-e123a-SP.csv（tail-e123a.csv 只換 creation 欄）、prod-raw.csv、work/prod.json。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10g+E196-production/e196_prod.py"""
import csv, hashlib, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / 'lib'))
import w10h as W10  # noqa: E402
L, C = W10.L, W10.C
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
TAIL_U = ROOT / 'reports/card-0.2.12/tail-U.csv'
TAIL_H = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv'
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
DEP_AUDIT = ROOT / 'reports/player-impact-v30/dependence-audit.json'
W_SELF = 0.25


def rows_of(path):
    return W10.W8._rows(path)


def ts(pts, fga, fta):
    den = 2 * (np.asarray(fga, float) + 0.44 * np.asarray(fta, float))
    return np.where(den > 0, np.asarray(pts, float) / np.where(den > 0, den, 1), 0.0)


def lg_ts(s):
    rs = rows_of(W10.season_path(s))
    p = sum(float(r['PTS'] or 0) for r in rs if r['MIN']); a = sum(float(r['FGA'] or 0) for r in rs if r['MIN']); f = sum(float(r['FTA'] or 0) for r in rs if r['MIN'])
    return float(ts(p, a, f))


def prod_raw(pts, ftm, fga, fta, mn, dep, lgts):
    pts, ftm = np.asarray(pts, float), np.asarray(ftm, float)
    return (pts + W_SELF * (1 - np.asarray(dep, float)) * (pts - ftm)) / np.maximum(np.asarray(mn, float), 1.0) * 36 * ts(pts, fga, fta) / lgts


def past_season(s):
    """過去季單季值（同 E-125 pool_data_p.seventh_season：player-games 季總、dep＝dependence-audit 該季 sourceDependence）。回 {pid: (creation, production)}。"""
    dep = {int(r['playerId']): r['sourceDependence'] for se in json.loads(DEP_AUDIT.read_text(encoding='utf-8'))['seasons'] if se['season'] == s for r in se['rows']}
    tot = defaultdict(lambda: defaultdict(float))
    for r in rows_of(ROOT / f'data/defense-seventh/{s}/player-games.json'):
        t = tot[int(r['PLAYER_ID'])]
        for k in ('FGA', 'MIN', 'PTS', 'FTM', 'FTA'):
            t[k] += float(r[k] or 0)
    lg = lg_ts(s)
    out = {}
    for p, t in tot.items():
        if dep.get(p) is None:
            continue
        d = float(dep[p])
        cr = (1 - d) * t['FGA'] / max(t['MIN'], 1) * 36
        out[p] = (cr, float(prod_raw(t['PTS'], t['FTM'], t['FGA'], t['FTA'], t['MIN'], d, lg)))
    return out, lg


def past_pool(W, ps):
    """同 Win10._past(a, 'pool')：C.MAIN 各季、poolInfo GP>=30 且 MPG>=20 的人；回 (creation 池重算, creation 池原值, production 池)。"""
    cre_re, cre_ref, prd = [], [], []
    for s in C.MAIN:
        d, info = W.inp['seas'][s]['attrs'].get('creation', {}), W.inp['seas'][s]['poolInfo']
        for k, x in d.items():
            i = info.get(k)
            if i is not None and i['GP'] > 0 and i['GP'] >= L.POOL_GP and i['MIN'] / i['GP'] >= L.POOL_MPG:
                c_, p_ = ps[s][int(k)]
                cre_ref.append(x); cre_re.append(c_); prd.append(p_)
    return cre_re, cre_ref, prd


def season_extra_tabs(W, s):
    """2025-26 逐場表多加 (PTS, MIN)、(FTM, FTA)：場次序號、球員索引與 window10.season_tabs 相同。"""
    D = W.D
    rows = rows_of(W10.season_path(s))
    gi_of = {g: i for i, g in enumerate(D.gids[s])}
    rows = [r for r in rows if r['MIN'] and r['GAME_ID'] in gi_of]
    sel = [r for r in rows if r['PLAYER_ID'] in D.pidx]
    f = lambda k: [W10._num(r, k) for r in sel]
    gi, pi = [gi_of[r['GAME_ID']] for r in sel], [D.pidx[r['PLAYER_ID']] for r in sel]
    return {'pts': L.Tab(gi, pi, f('PTS'), f('MIN'), D.NP), 'ft': L.Tab(gi, pi, f('FTM'), f('FTA'), D.NP)}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    W = W10.Win10()
    PRIOR = W10.PRIOR
    info = {'spec_sha256': sha(HERE / 'spec.md')}
    # ---------- 過去季池值
    ps, lgs = {}, {}
    for s in C.MAIN:
        ps[s], lgs[s] = past_season(s)
    cre_re, cre_ref, prd_pool_past = past_pool(W, ps)
    info['past_pool_creation_maxdiff'] = float(np.max(np.abs(np.array(cre_re) - np.array(cre_ref))))
    info['past_pool_n'] = len(cre_ref)
    assert info['past_pool_creation_maxdiff'] < 1e-9, info['past_pool_creation_maxdiff']
    # ---------- 2025-26 窗口（卡片端，c=82）
    for s in W10.SEASONS10:
        W.T10[s].update(season_extra_tabs(W, s))
    cur, G = W.season_cur(PRIOR)
    n_fga, mn = (x[W.ix] for x in W.sums10('cr', G, cur, G, PRIOR))
    pts, _ = (x[W.ix] for x in W.sums10('pts', G, cur, G, PRIOR))
    ftm, fta = (x[W.ix] for x in W.sums10('ft', G, cur, G, PRIOR))
    cre_r = (1 - W.dep) * n_fga / np.maximum(mn, 1.0) * 36
    assert np.array_equal(cre_r, W._creation_r(G, cur, G, PRIOR))
    lg26 = lg_ts(PRIOR)
    lgs[PRIOR] = lg26
    prd_r = prod_raw(pts, ftm, n_fga, fta, mn, W.dep, lg26)
    top, bot = W._flags('creation')
    cmap = L.PctMapper(list(cre_r[W.pool_i]) + cre_ref, top, bot)
    pmap = L.PctMapper(list(prd_r[W.pool_i]) + prd_pool_past, top, bot)
    cre_v, prd_v = cmap(cre_r), pmap(prd_r)
    tu = list(csv.DictReader(open(TAIL_U, encoding='utf-8')))
    pid_i = {int(p): i for i, p in enumerate(W.pids)}
    info['tailU_creation_maxdiff'] = max(abs(float(r['creation']) - cre_v[pid_i[int(r['playerId'])]]) for r in tu)
    assert info['tailU_creation_maxdiff'] < 1e-9, info['tailU_creation_maxdiff']
    keys = list(tu[0].keys())
    with open(HERE / 'tail-U-SP.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(keys)
        for r in tu:
            o = dict(r, creation=repr(float(prd_v[pid_i[int(r['playerId'])]])))
            w.writerow([o[k] for k in keys])
    # ---------- 歷史原點用的單季 2025-26 版（tail-e123a 的 creation 取法：聯盟 JSON observed）
    lg = json.loads(LEAGUE.read_text(encoding='utf-8'))
    tot = {}
    for team in lg['teams']:
        for p in team['roster']:
            t_ = tot.setdefault(p['name'], {'FGA': 0.0, 'MIN': 0.0, 'GP': 0, 'PTS': 0.0, 'FTM': 0.0, 'FTA': 0.0})
            for k in t_:
                t_[k] += p['observed'][k]
    nm = [W.inp['cards'][p]['name'] for p in W.pids]
    T = {k: np.array([tot[n][k] for n in nm], float) for k in ('FGA', 'MIN', 'GP', 'PTS', 'FTM', 'FTA')}
    lg_json = float(ts(sum(t['PTS'] for t in tot.values()), sum(t['FGA'] for t in tot.values()), sum(t['FTA'] for t in tot.values())))
    c2 = (1 - W.dep) * T['FGA'] / np.maximum(T['MIN'], 1) * 36
    p2 = prod_raw(T['PTS'], T['FTM'], T['FGA'], T['FTA'], T['MIN'], W.dep, lg_json)
    pool = [i for i, n in enumerate(nm) if tot[n]['GP'] >= 30 and tot[n]['MIN'] / tot[n]['GP'] >= 20]
    c2v = L.PctMapper(list(c2[pool]) + cre_ref, top, bot)(c2)
    p2v = L.PctMapper(list(p2[pool]) + prd_pool_past, top, bot)(p2)
    th = list(csv.DictReader(open(TAIL_H, encoding='utf-8')))
    info['tailH_creation_maxdiff'] = max(abs(float(r['creation']) - c2v[pid_i[int(r['playerId'])]]) for r in th)
    assert info['tailH_creation_maxdiff'] < 1e-9, info['tailH_creation_maxdiff']
    keys = list(th[0].keys())
    with open(HERE / 'tail-e123a-SP.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(keys)
        for r in th:
            o = dict(r, creation=repr(float(p2v[pid_i[int(r['playerId'])]])))
            w.writerow([o[k] for k in keys])
    with open(HERE / 'prod-raw.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['playerId', 'name', 'winMIN', 'winPTS', 'winFTM', 'winFGA', 'winFTA', 'dep', 'winTS', 'creationRaw', 'creation', 'prodRaw', 'production', 'prodRaw1', 'production1'])
        for i, p in enumerate(W.pids):
            w.writerow([int(p), nm[i], repr(float(mn[i])), repr(float(pts[i])), repr(float(ftm[i])), repr(float(n_fga[i])), repr(float(fta[i])), repr(float(W.dep[i])),
                        repr(float(ts(pts[i], n_fga[i], fta[i]))), repr(float(cre_r[i])), repr(float(cre_v[i])), repr(float(prd_r[i])), repr(float(prd_v[i])),
                        repr(float(p2[i])), repr(float(p2v[i]))])
    info.update({'lgTS': lgs, 'lgTS_json_2025-26': lg_json, 'flags_top_bot': [top, bot], 'pool_window_n': int(len(W.pool_i)),
                 'tail-U-SP.csv': sha(HERE / 'tail-U-SP.csv'), 'tail-e123a-SP.csv': sha(HERE / 'tail-e123a-SP.csv'), 'prod-raw.csv': sha(HERE / 'prod-raw.csv'),
                 'inputs': {'tail-U.csv': sha(TAIL_U), 'tail-e123a.csv': sha(TAIL_H), 'w10h.py': sha(HERE / 'lib/w10h.py'), 'w8h.py': sha(HERE / 'lib/w8h.py')}})
    (HERE / 'work').mkdir(exist_ok=True)
    (HERE / 'work/prod.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
