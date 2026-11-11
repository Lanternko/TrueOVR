# star-overlap 分析（預註冊規則寫死）。python -I -X utf8 reports/star-overlap/analyze.py  ->  analysis.json
import json, glob, os, csv, math
import numpy as np
from scipy.stats import rankdata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..')); E = f'{ROOT}/reports/E208-team-rating'
BOOT, BSEED, CREATOR_Q = 5000, 20261102, 0.70
names = json.load(open(f'{HERE}/names.json', encoding='utf-8')); LU = json.load(open(f'{HERE}/lineups.json', encoding='utf-8'))
def spearman(a, b): ra, rb = rankdata(a), rankdata(b); return float(np.corrcoef(ra, rb)[0, 1])
def boot_ci(f, n, rng):
    v = []
    for _ in range(BOOT):
        idx = rng.integers(0, n, n); x = f(idx)
        if x == x: v.append(x)
    return [float(np.percentile(v, 5)), float(np.percentile(v, 95))], len(v)
def load(tag):
    out = {}
    for fn in sorted(glob.glob(f'{HERE}/results/{tag}-*.json')):
        for o in json.load(open(fn, encoding='utf-8'))['res']: out[o['id']] = o
    return out
def actual(season):
    if season == '2025-26':
        adv = json.load(open(f'{ROOT}/data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets']; adv = adv[0] if isinstance(adv, list) else adv
        h = {k: i for i, k in enumerate(adv['headers'])}; return {str(r[h['TEAM_ID']]): r[h['NET_RATING']] for r in adv['rowSet']}
    inp = json.load(open(f'{E}/inputs-2425.json', encoding='utf-8')); return {t: v['net'] for t, v in inp['actual2425'].items()}   # 2024-25：箱分數推算（advanced-teams 只有 2025-26）
selfopp = sorted(v['selfOpp'] for v in names.values() if v['selfOpp'] is not None); creator_cut = float(np.quantile(selfopp, CREATOR_Q))
def season_table(season, tag):
    R = load(tag); act = actual(season); ids = sorted(R)
    rows = []
    for t in ids:
        o = R[t]; m = {k: np.array(v, float) for k, v in o['m'].items()}; poss = {k: np.array(v, float) for k, v in o['poss'].items()}
        base = m['v0'].mean(); g = [m[f'v{j}'].mean() - base for j in (1, 2, 3, 4)]; g4 = m['v4all'].mean() - base
        per_seed = m['v1'] + m['v2'] + m['v3'] + m['v4'] - m['v4all'] - 3 * m['v0']; S = len(per_seed)
        half = lambda sl: float((m['v1'][sl] + m['v2'][sl] + m['v3'][sl] + m['v4'][sl] - m['v4all'][sl] - 3 * m['v0'][sl]).mean())
        full = m['full'].mean(); full100 = 100 * m['full'].mean() / (poss['full'].mean() / 2)
        st = o['stars']; ncre = sum(1 for p in st if (names[str(p)]['selfOpp'] or 0) >= creator_cut)
        rows.append(dict(id=t, abbr=o['abbr'], season=season, stars=[names[str(p)]['name'] for p in st], gains=g, sumSingle=sum(g), gain4=g4, OL=sum(g) - g4,
                         OLse=float(per_seed.std(ddof=1) / math.sqrt(S)), OLodd=half(slice(0, None, 2)), OLeven=half(slice(1, None, 2)), full=float(full), full100=float(full100), nCreators=ncre,
                         actualNet=float(act[t]), S=S))
    mf = np.mean([r['full'] for r in rows]); mf1 = np.mean([r['full100'] for r in rows]); ma = np.mean([r['actualNet'] for r in rows])
    for r in rows:
        r['OLr'] = r['OL'] / r['sumSingle'] if r['sumSingle'] > 1.0 else None
        r['model'] = r['full'] - mf; r['model100'] = r['full100'] - mf1; r['actual'] = r['actualNet'] - ma
        r['R'] = r['actual'] - r['model']; r['R100'] = r['actual'] - r['model100']
    return rows
def per_season(rows, rng):
    OL = np.array([r['OL'] for r in rows]); Rr = np.array([r['R'] for r in rows]); n = len(rows)
    rho = spearman(OL, Rr); ci, nb = boot_ci(lambda i: spearman(OL[i], Rr[i]), n, rng)
    o = dict(n=n, rho_OL_R=rho, ci90=ci, nBoot=nb)
    ok = [r for r in rows if r['OLr'] is not None]
    if len(ok) >= 10:
        a = np.array([r['OLr'] for r in ok]); b = np.array([r['R'] for r in ok]); o['OLr'] = dict(n=len(ok), rho=spearman(a, b), ci90=boot_ci(lambda i: spearman(a[i], b[i]), len(ok), rng)[0])
    M = np.array([r['model'] for r in rows]); o['rho_OL_R_per100'] = spearman(OL, np.array([r['R100'] for r in rows]))
    o['rho_model_R'] = spearman(M, Rr); o['rho_OL_model'] = spearman(OL, M)
    # 偏相關（描述）：OL、R 各自對 model 做秩殘差後的 Pearson
    def resid(y):
        ry, rm = rankdata(y), rankdata(M); b = np.polyfit(rm, ry, 1); return ry - np.polyval(b, rm)
    o['partial_OL_R_given_model'] = float(np.corrcoef(resid(OL), resid(Rr))[0, 1])
    o['rho_nCreators_OL'] = spearman(np.array([r['nCreators'] for r in rows], float), OL)
    o['meanOL'] = float(OL.mean()); o['sdOL'] = float(OL.std(ddof=1)); o['medianOLse'] = float(np.median([r['OLse'] for r in rows]))
    o['splitHalf_rho_OL'] = spearman(np.array([r['OLodd'] for r in rows]), np.array([r['OLeven'] for r in rows]))
    o['slope_actual_on_model'] = float(np.polyfit(M, np.array([r['actual'] for r in rows]), 1)[0])
    o['meanOLr'] = float(np.mean([r['OLr'] for r in ok])) if ok else None
    return o
def pooled(rows, rng):
    OL = np.array([r['OL'] for r in rows]); Rr = np.array([r['R'] for r in rows]); n = len(rows)
    def f(i):
        o = OL[i]; r = Rr[i]; od = np.argsort(-o, kind='stable'); return float(r[od[:10]].mean() - r[od[-10:]].mean())
    d = f(np.arange(n)); ci, _ = boot_ci(f, n, rng)
    od = np.argsort(-OL, kind='stable')
    return dict(n=n, top10_meanR=float(Rr[od[:10]].mean()), bottom10_meanR=float(Rr[od[-10:]].mean()), diff=d, ci90=ci)
def main():
    rng = np.random.default_rng(BSEED)
    A = season_table('2024-25', 'S2425'); B = season_table('2025-26', 'S2526')
    out = dict(creatorCut=creator_cut, seasons={'2024-25': per_season(A, rng), '2025-26': per_season(B, rng)}, pooled=pooled(A + B, rng))
    s24, s25 = out['seasons']['2024-25'], out['seasons']['2025-26']
    out['H1_pass'] = bool(s24['rho_OL_R'] > 0 and s24['ci90'][0] > 0 and s25['rho_OL_R'] > 0)
    rows = sorted(A + B, key=lambda r: -r['OL']); out['top5OL'] = rows[:5]; out['rows'] = A + B
    # 描述：proxy 球星與 card 0.2.12c 排名對照（2025-26，名字比對）
    card = {}
    with open(f'{ROOT}/reports/card-0.2.12c/ranking.csv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh): card[r['name']] = float(r['ovr'])
    hit = tot = 0
    for t, v in LU['2025-26'].items():
        el = [p for p, m in v['rotation'] if m >= 20 and names[str(p)]['name'] in card]
        top = set(sorted(el, key=lambda p: -card[names[str(p)]['name']])[:4]); hit += len(top & set(v['stars'])); tot += 4
    out['proxyVsCardTop4_2526'] = dict(overlap=hit, of=tot)
    json.dump(out, open(f'{HERE}/analysis.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k in ('2024-25', '2025-26'): print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in out['seasons'][k].items()})
    print('pooled', out['pooled']); print('H1_pass', out['H1_pass'], 'proxyVsCard', out['proxyVsCardTop4_2526'])
    for r in rows[:5]: print(r['season'], r['abbr'], round(r['OL'], 2), 'model', round(r['model'], 2), 'actual', round(r['actual'], 2), r['stars'])
if __name__ == '__main__': main()
