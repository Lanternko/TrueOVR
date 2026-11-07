"""E-142 第 1 階段評估（暫時版：2K 預設用 F-072 的 2k_yearly_ovr.csv，模擬項缺席；輸出檔名帶 -provisional）。
定義（preregistration ＋ errata-1 ＋ errata-2，後者優先）：
  人群  卡片 ranking 內 MIN>=500 的球員，且五張候選卡都有（同人群，G3）；ref 的百分位在 player-games MIN>=500 全體上算（與候選無關）。
  ref_i ＝ Σ w_ik·p_ik ÷ Σ w_ik，只加總 i 有的項；薪水 0.4×合約年次權重(1/1/0.7/0.5/0.3)、2K 0.3、下季 RAPM×W(mpg) 0.15、模擬 0.15；四項都沒有者剔除。
  薪水  t 季在約非新秀約的當季薪水（同季內百分位與「佔帽%」同序，故不需帽值）；合約年次邏輯同 c0l_check.py。
  RAPM  t+1 單季 RAPM net（poss>=1000）× W(t+1 mpg)；2025-26 原點沒有 t+1，故無此項。
  C ＝ Spearman(OVR, ref)；M_sal ＝ 加權 Spearman（名次後加權 Pearson，權重＝合約年次）；M_2k、M_rapm ＝ 一般 Spearman。
  候選目標＝t 季單季值（見報告的解讀聲明）。T* 在訓練季 2022-23 於 T1/T4/T5/T6 中選 C 最高者（平手取代號小的）。
  測試季 2023-24＋2024-25 合併＝人數加權平均；① 用球員層 bootstrap（兩季球員聯集重抽，2000 次，固定 seed），90% 下界＝第 5 百分位。
用法：python -I phase1_eval.py [--twok CSV] [--sim CSV] [--suffix -provisional]
  --twok  含 name 欄與 2K24/2K25/2K26/2K27 欄的 CSV（補齊版 2K 到位後換這個）
  --sim   模擬 WinImp：CSV 欄 season,playerId,value（越大越好）；不給＝所有人都沒有模擬項
"""
import argparse, csv, hashlib, importlib.util, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
HERE = Path(__file__).resolve().parent
R = HERE.parents[1]
PW = HERE / 'phase1-work'
CANDS = ['T0', 'T1', 'T4', 'T5', 'T6']
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
FOLDS = ['2022-23', '2023-24', '2024-25']   # errata-3 三折輪流
EDITION = {'2022-23': '2K24', '2023-24': '2K25', '2024-25': '2K26', '2025-26': '2K27'}
NEXT = {'2022-23': '2023-24', '2023-24': '2024-25', '2024-25': '2025-26'}
W_BASE = {'sal': 0.4, 'twok': 0.3, 'rapm': 0.15, 'sim': 0.15}
YEARW = {1: 1.0, 2: 1.0, 3: 0.7, 4: 0.5}
SEED, B = 20261031, 2000
TOL = {'sal': 0.02, 'twok': 0.02, 'rapm': 0.05}
E126 = R / 'reports/card-0.2.7+E126-tank-next-season'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _c0l():
    s = importlib.util.spec_from_file_location('c0l', HERE / 'c0l_check.py')
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


C0L = _c0l()
norm = C0L.norm


def wfun(m):
    return (1 - math.exp(-m / 15)) / (1 - math.exp(-36 / 15))


def table(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(d['headers'], r)) for r in d['rowSet']]


def pg_path(s):
    return R / ('data/season-source/player-games.json' if s == '2025-26' else f'data/defense-seventh/{s}/player-games.json')


def pop_of(s):
    mins, names, games, gp = defaultdict(float), {}, defaultdict(lambda: defaultdict(int)), defaultdict(int)
    for r in table(pg_path(s)):
        if r['MIN']:
            p = r['PLAYER_ID']
            mins[p] += r['MIN']
            gp[p] += 1
            names[p] = r['PLAYER_NAME']
            games[p][r['TEAM_ABBREVIATION']] += 1
    pop = {p: {'name': names[p], 'team': max(games[p], key=games[p].get), 'min': m} for p, m in mins.items() if m >= 500}
    mpg = {p: mins[p] / gp[p] for p in mins}
    return pop, mpg


def pct(vals):
    ks = list(vals)
    if len(ks) < 2:
        return {k: 0.5 for k in ks}
    r = rankdata([vals[k] for k in ks])
    return {k: (x - 1) / (len(ks) - 1) for k, x in zip(ks, r)}


def salary_terms(t, pop, pages, drafts, ev):
    ORDER = C0L.ORDER
    ti = ORDER.index(t)
    out, stat = {}, defaultdict(int)
    for pid, info in pop.items():
        k = norm(info['name'])
        dy, rd = drafts.get(pid, (None, None))
        try:
            D = int(dy)
        except Exception:
            D = None
        if D is not None and str(rd) == '1' and 0 <= int(t[:4]) - D <= 3:
            stat['rookie_no_salary_term'] += 1
            continue
        row = C0L.pick(pages[t].get(k), info['team'])
        if row is None:
            stat['no_salary_row'] += 1
            continue
        cur, j, censored = row['sched'], ti, False
        while True:
            if j == 0:
                censored = True
                break
            nxt = next((c for c in pages[ORDER[j - 1]].get(k, []) if C0L.same_contract(c['sched'], cur)), None)
            if nxt is None:
                break
            cur, j = nxt['sched'], j - 1
        if not censored:
            year = ti - j + 1
        else:
            evs = [e for e in ev.get(k, []) if e[0].year >= 2020]
            fa = [e for e in evs if e[1] == 'fa']
            if not evs:
                stat['undated_censored_no_salary_term'] += 1
                continue
            year = ti + 1
            if fa:
                ss = C0L.start_year_of_fa(fa[-1][0])
                if ss > 2021:
                    stat['fa_start_after_2021_ignored(leak-guard)'] += 1
                else:
                    year = int(t[:4]) - ss + 1
            stat['year_via_tx'] += 1
        out[pid] = (row['sched'][0], max(1, year))
    return out, dict(stat)


def load_twok(path):
    d = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        d.setdefault(norm(r['name']), r)
    return d


def load_sim(path):
    out = defaultdict(dict)
    if path:
        for r in csv.DictReader(open(path, encoding='utf-8-sig')):
            out[r['season']][int(r['playerId'])] = float(r['value'])
    return out


def build_ref(t, pop, mpg_cache, sal, twok, sim):
    s = {p: v[0] for p, v in sal.items()}
    ps = pct(s)
    t_sal = {p: (ps[p], W_BASE['sal'] * YEARW.get(sal[p][1], 0.3)) for p in sal}
    col = EDITION[t]
    k2 = {}
    for p, info in pop.items():
        r = twok.get(norm(info['name']))
        if r and (r.get(col) or '').strip():
            try:
                k2[p] = float(r[col])
            except ValueError:
                pass
    pk = pct(k2)
    t_2k = {p: (pk[p], W_BASE['twok']) for p in k2}
    rv, t_rapm = {}, {}
    if t in NEXT:
        n = NEXT[t]
        d = json.loads((E126 / f'rapm-{n}.json').read_text(encoding='utf-8'))
        assert d['season'] == n
        mp = mpg_cache[n]
        rv = {int(p): v['net'] * wfun(mp[int(p)]) for p, v in d['players'].items() if int(p) in pop and v['poss'] >= 1000 and int(p) in mp}
        pr = pct(rv)
        t_rapm = {p: (pr[p], W_BASE['rapm']) for p in rv}
    sv = {p: v for p, v in sim.get(t, {}).items() if p in pop}
    psim = pct(sv)
    t_sim = {p: (psim[p], W_BASE['sim']) for p in sv}
    ref, excl = {}, 0
    for p in pop:
        num = den = 0.0
        for tt in (t_sal, t_2k, t_rapm, t_sim):
            if p in tt:
                v, w = tt[p]
                num += w * v
                den += w
        if den > 0:
            ref[p] = num / den
        else:
            excl += 1
    raw = {'sal': dict(sal), 'twok': k2, 'rapm': rv, 'sim': sv}
    return ref, raw, excl


def spearman(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def wspearman(x, y, w):
    a, b, w = rankdata(x), rankdata(y), np.asarray(w, float)
    w = w / w.sum()
    ma, mb = (w * a).sum(), (w * b).sum()
    return float((w * (a - ma) * (b - mb)).sum() / math.sqrt((w * (a - ma) ** 2).sum() * (w * (b - mb) ** 2).sum()))


def read_rank(cand, t):
    f = PW / cand / ('c0/ranking.csv' if t == '2025-26' else f'{t}/out/K0/ranking.csv')
    return list(csv.DictReader(open(f, encoding='utf-8-sig'))), f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--twok', default=str(R / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv'))
    ap.add_argument('--sim', default=None)
    ap.add_argument('--suffix', default='-provisional')
    ap.add_argument('--out', default=str(HERE))
    a = ap.parse_args()
    suf, outd = a.suffix, Path(a.out)
    twok, sim = load_twok(a.twok), load_sim(a.sim)
    pages = {s: C0L.contracts(s) for s in C0L.ORDER}
    drafts, ev = C0L.draft_years(), C0L.tx_events()
    pops, mpgs = {}, {}
    for s in SEASONS:
        pops[s], mpgs[s] = pop_of(s)
    chk = {'twok_file': a.twok, 'twok_sha256': sha(a.twok), 'sim_file': a.sim, 'seed': SEED, 'bootstrap_draws': B, 'seasons': {}}
    data = {}
    for t in SEASONS:
        pop = pops[t]
        sal, sstat = salary_terms(t, pop, pages, drafts, ev)
        ref, raw, excl = build_ref(t, pop, mpgs, sal, twok, sim)
        n2 = defaultdict(list)
        for p, i in pop.items():
            n2[norm(i['name'])].append(p)
        ranks, unmatched, minbad = {}, {}, {}
        for c in CANDS:
            rows, f = read_rank(c, t)
            m, um, mb = {}, [], 0
            for r in rows:
                if float(r['MIN']) < 500:
                    continue
                ids = n2.get(norm(r['name'])) or []
                if len(ids) != 1:
                    um.append(r['name'])
                    continue
                if abs(pop[ids[0]]['min'] - float(r['MIN'])) > 1.5:
                    mb += 1
                m[ids[0]] = float(r['ovr'])
            ranks[c], unmatched[c], minbad[c] = m, um, mb
        common = set.intersection(*[set(ranks[c]) for c in CANDS])
        ids = sorted(p for p in common if p in ref)
        data[t] = {'ids': ids, 'ovr': {c: np.array([ranks[c][p] for p in ids]) for c in CANDS}, 'ref': np.array([ref[p] for p in ids]), 'raw': raw}
        avail = {k: sum(1 for p in ids if p in raw[k]) for k in raw}
        chk['seasons'][t] = {
            'playerGamesPop_MIN>=500': len(pop), 'cardRows_MIN>=500_matched': {c: len(ranks[c]) for c in CANDS},
            'unmatchedRankingNames_first10': {c: unmatched[c][:10] for c in CANDS},
            'unmatchedCount': {c: len(unmatched[c]) for c in CANDS}, 'rankingMinMismatch>1.5': minbad, 'evalPop(common_and_ref)': len(ids),
            'inCommonButNoRef(excluded)': len([p for p in common if p not in ref]),
            'refExcludedInPop(no_term_at_all)': excl, 'availableInEvalPop': avail,
            'availableInPlayerGamesPop': {k: len(raw[k]) for k in raw}, 'salaryStats': sstat,
            'leak': {'salaryPage': C0L.PAGE[t], 'rapmFile': f'card-0.2.7+E126-tank-next-season/rapm-{NEXT[t]}.json' if t in NEXT else None,
                     'rapmUsesOnlySeason': NEXT.get(t), 'twokEdition': EDITION[t], 'simSeasonPresent': t in sim}}
    p0 = {t: json.loads((HERE / (f'build-{t}.json' if t != '2025-26' else 'build-c0.json')).read_text(encoding='utf-8'))['ranking_sha256'] for t in SEASONS}
    p1 = {t: sha(PW / 'T0' / ('c0/ranking.csv' if t == '2025-26' else f'{t}/out/K0/ranking.csv')) for t in SEASONS}
    rep = {t: {'phase0_sha': p0[t], 'phase1_sha': p1[t], 'equal': p0[t] == p1[t]} for t in SEASONS}
    rep['all_equal'] = all(v['equal'] for v in rep.values())
    rep['c0_want_99466f36'] = p1['2025-26'] == '99466f369d53316a260f2b6d91ee056e2da8048e65d8283a68cec1322fef1655'
    chk['T0_reproduction'] = rep

    def metrics(t, c, idx=None):
        d = data[t]
        idx = np.arange(len(d['ids'])) if idx is None else idx
        o, rf = d['ovr'][c][idx], d['ref'][idx]
        out = {'n': int(len(idx)), 'C': spearman(o, rf)}
        for k in ('sal', 'twok', 'rapm'):
            have = [i for i in idx if d['ids'][i] in d['raw'][k]]
            out['n_' + k] = len(have)
            if len(have) < 10:
                out[k] = None
                continue
            oo = d['ovr'][c][have]
            if k == 'sal':
                y = [d['raw'][k][d['ids'][i]][0] for i in have]
                w = [YEARW.get(d['raw'][k][d['ids'][i]][1], 0.3) for i in have]
                out[k] = wspearman(oo, y, w)
            else:
                out[k] = spearman(oo, [d['raw'][k][d['ids'][i]] for i in have])
        return out

    res = {'per_season': {t: {c: metrics(t, c) for c in CANDS} for t in SEASONS}}
    ps = res['per_season']

    def pick(seasons):
        cc = {c: sum(ps[t][c]['n'] * ps[t][c]['C'] for t in seasons) / sum(ps[t][c]['n'] for t in seasons) for c in CANDS if c != 'T0'}
        return sorted(cc, key=lambda c: (-cc[c], c))[0], cc
    # errata-3：三折輪流，第 k 折用另外兩季選 T*_k、在第 k 季測試
    folds = {}
    for t in FOLDS:
        ts, cc = pick([s for s in FOLDS if s != t])
        folds[t] = {'train': [s for s in FOLDS if s != t], 'trainC': cc, 'Tstar': ts}
    tstar, ccall = pick(FOLDS)
    res['folds'], res['final'] = folds, {'Tstar': tstar, 'C_allFolds': ccall}

    def pooled_diff(key):
        num = den = 0.0
        for t, f in folds.items():
            a, b0 = ps[t][f['Tstar']], ps[t]['T0']
            if a.get(key) is None or b0.get(key) is None:
                continue
            nn = a['n'] if key == 'C' else a['n_' + key]
            num += nn * (a[key] - b0[key])
            den += nn
        return num / den if den else None
    res['oof_diff'] = {k: pooled_diff(k) for k in ('C', 'sal', 'twok', 'rapm')}
    rng = np.random.default_rng(SEED)
    allids = sorted(set().union(*[data[t]['ids'] for t in FOLDS]))
    pos = {t: {p: i for i, p in enumerate(data[t]['ids'])} for t in FOLDS}
    diffs = np.empty(B)
    for b in range(B):
        mult = np.bincount(rng.integers(0, len(allids), len(allids)), minlength=len(allids))
        num = den = 0.0
        for t in FOLDS:
            sel = [j for j in range(len(allids)) if mult[j] and allids[j] in pos[t]]
            idx = np.repeat(np.array([pos[t][allids[j]] for j in sel]), np.array([mult[j] for j in sel]))
            d = data[t]
            cs = spearman(d['ovr'][folds[t]['Tstar']][idx], d['ref'][idx]) - spearman(d['ovr']['T0'][idx], d['ref'][idx])
            num += len(idx) * cs
            den += len(idx)
        diffs[b] = num / den
    lo = float(np.percentile(diffs, 5))
    od = res['oof_diff']
    j1 = lo > 0
    j2 = od['sal'] >= -TOL['sal']
    j22 = od['twok'] >= -TOL['twok']
    j3 = od['rapm'] >= -TOL['rapm']
    res['bootstrap'] = {'diffC_point': od['C'], 'lower90': lo, 'upper90': float(np.percentile(diffs, 95)), 'draws': B, 'seed': SEED}
    prov = suf != ''
    res['judgement'] = {'1': bool(j1), '2_sal': bool(j2), '2-2_2k': bool(j22), '3_rapm': bool(j3),
                        'verdict': 'adopt' if (j1 and j2 and j22 and j3) else ('side_effect' if j1 else 'no_improvement'), 'PROVISIONAL': prov}
    res['note'] = ('暫時版：不可作判定或結論（errata-2 §4）。' if prov else '正式版（errata-3 三折）') + f" 2K={a.twok}；sim={a.sim}"
    (outd / f'phase1{suf}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    (outd / f'phase1-checks{suf}.json').write_text(json.dumps(chk, ensure_ascii=False, indent=1), encoding='utf-8')
    f4 = lambda v: 'NA' if v is None else f'{v:.4f}'
    L = ([f'# E-142 第 1 階段報告（暫時版 {suf}）', '', '**暫時版：以下數字不得當判定或結論（errata-2 §4）。**', '']
         if prov else ['# E-142 第 1 階段報告（正式版，errata-3 三折）', '']) + [f'- 2K：`{a.twok}`；模擬：`{a.sim}`', '',
         '## 口徑', '- 候選目標＝t 季單季值（T0 窗口含 2021-22，該季無候選資料，故候選一律只用 t 季；這是對 pooled 的解讀）。',
         '- T6：T4、T5 的 O、D 各自季內 z 分數平均後轉回每百回合單位，net＝O＋D（見 phase1_build.py t6）。',
         '- 薪水以同季內百分位進 ref，與佔帽 % 同序，所以不需帽值。',
         '- 人群＝五張卡都有且 MIN≥500 且 ref 有項目者；測試合併＝人數加權平均。T* 只從 T1/T4/T5/T6 選。',
         '- 2025-26 原點無下季，沒有 RAPM 項；只報告。', '', '## 各季各候選']
    for t in SEASONS:
        L += [f'### {t}', '| 候選 | n | C | M_sal | M_2k | M_rapm |', '|---|---|---|---|---|---|']
        for c in CANDS:
            m = res['per_season'][t][c]
            L.append(f"| {c} | {m['n']} | {f4(m['C'])} | {f4(m['sal'])} (n={m['n_sal']}) | {f4(m['twok'])} (n={m['n_twok']}) | {f4(m['rapm'])} (n={m['n_rapm']}) |")
        L.append('')
    L += ['## 三折（errata-3）', '| 測試季 | 訓練季 | T*_k | 訓練 C |', '|---|---|---|---|']
    for t, f in folds.items():
        L.append(f"| {t} | {'、'.join(f['train'])} | {f['Tstar']} | {json.dumps({k: round(v, 4) for k, v in f['trainC'].items()})} |")
    L += ['', f"上線候選 T*（三季合併選）＝{tstar}：{json.dumps({k: round(v, 4) for k, v in ccall.items()})}", '',
          '## 樣本外差值（T*_k − T0，三折依人數加權）', f"C {f4(od['C'])}｜M_sal {f4(od['sal'])}｜M_2k {f4(od['twok'])}｜M_rapm {f4(od['rapm'])}",
          '', f"① 90% 下界＝{lo:.4f} → {'過' if j1 else '不過'}",
          f"② 薪水 {'過' if j2 else '不過'}；②之二 2K {'過' if j22 else '不過'}；③ RAPM {'過' if j3 else '不過'}",
          f"判定：{res['judgement']['verdict']}" + ('（暫時版，無效）' if prov else '')]
    (outd / f'report{suf}.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('done', tstar)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
