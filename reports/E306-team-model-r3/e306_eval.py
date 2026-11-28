"""E-306 評估（本機、輕量）：A 前向檢討、測試 F、測試 M、C1、C2、選 K。輸出 work/eval.json。
  python -I -X utf8 e306_eval.py"""
import collections, csv, glob, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import numpy as np
import actual_blend as ab
import team_ratings_daily as M

H, SIG = 2.5, 12.0
KS = {'none': None, 'K5': 5.0, 'K10': 10.0, 'K20': 20.0, 'K40': 40.0}
WORK = os.path.join(HERE, 'work')
rng = np.random.default_rng(306); NB = 2000
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))
J = lambda p: json.load(open(p, encoding='utf-8'))
out = {}


def brier(m, d):
    return (np.clip(Phi((np.asarray(m) + H) / SIG), 1e-6, 1 - 1e-6) - (np.asarray(d) > 0)) ** 2


def boot(x):
    x = np.asarray(x, float); n = len(x)
    b = x[rng.integers(0, n, (NB, n))].mean(1)
    return [float(np.percentile(b, 5)), float(np.percentile(b, 95))]


def summ(m, d):
    m, d = np.asarray(m), np.asarray(d); p = Phi((m + H) / SIG); r = d - (m + H)
    return dict(n=len(d), brier=float(brier(m, d).mean()), acc=float(((p > .5) == (d > 0)).mean()), mae=float(np.abs(r).mean()),
                bias=float(r.mean()), homeAdvImplied=float((d - m).mean()), residSd=float(r.std()), slope=float(np.polyfit(m, d, 1)[0]))


def roll(games, k):
    """逐日滾動：每場只用該場日期之前的殘差（同日賽後才更新）。games: dict(date,home,away,mT,d)。"""
    res = collections.defaultdict(list); m = np.zeros(len(games)); byd = collections.defaultdict(list)
    for i, g in enumerate(games):
        byd[g['date']].append(i)
    for day in sorted(byd):
        for i in byd[day]:
            g = games[i]; R = {t: (0.0 if k is None or not res[t] else sum(res[t]) / (len(res[t]) + k)) for t in (g['home'], g['away'])}
            m[i] = g['mT'] + R[g['home']] - R[g['away']]
        for i in byd[day]:
            g = games[i]; r = g['d'] - (g['mT'] + H); res[g['home']].append(r); res[g['away']].append(-r)
    return m


def shr_at(games, k):
    acc = collections.defaultdict(list)
    for g in games:
        r = g['d'] - (g['mT'] + H); acc[g['home']].append(r); acc[g['away']].append(-r)
    return collections.defaultdict(float, {t: (0.0 if k is None else sum(v) / (len(v) + k)) for t, v in acc.items()})


# ---------- 資料 ----------
G = ab.played_games()
abbr = {str(r['TEAM_ID']): r['TEAM_ABBREVIATION'] for r in ab._tab('team-games.json')}
for g in G.values():
    g['d'] = g['pts_home'] - g['pts_away']
pre = J(os.path.join(WORK, 'pred-pregame.json'))
gl = sorted(G.values(), key=lambda g: (g['date'], g['gid']))
for g in gl:
    g['mT'] = pre[g['gid']]['p']['online']['mT']
d_all = np.array([g['d'] for g in gl]); m_all = np.array([g['mT'] for g in gl])

# ---------- A1 勝負／分差 ----------
A1 = dict(known=summ(m_all, d_all), homeWinRate=float((d_all > 0).mean()), brierCoin=0.25,
          brierHomeOnly=float(brier(np.zeros(len(gl)), d_all).mean()))
p = Phi((m_all + H) / SIG); fav = np.maximum(p, 1 - p); hit = ((p > .5) == (d_all > 0))
A1['calib'] = [dict(lo=lo, hi=hi, n=int(s.sum()), pred=float(fav[s].mean()), actual=float(hit[s].mean()))
               for lo, hi in ((.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)) for s in [(fav >= lo) & (fav < hi)] if s.any()]
A1['byPeriod'] = {lab: summ(m_all[s], d_all[s]) for lab, s in (('10-20~11-06', np.array([g['date'] < '2026-11-07' for g in gl])),
                                                              ('11-07~11-20', np.array([g['date'] >= '2026-11-07' for g in gl])))}
recs = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward', 'log', '2026-*.json'))):
    for r in J(f)['records']:
        if not r.get('smoke') and r['game_id'] in G:
            recs[r['game_id']] = r
if recs:
    ids = sorted(recs); dd = np.array([G[i]['d'] for i in ids]); pT = np.array([recs[i]['pT'] for i in ids]); mT = np.array([recs[i]['marginT'] for i in ids])
    pM = np.array([recs[i]['pM0'] for i in ids]); kn = np.array([G[i]['mT'] for i in ids])
    A1['published'] = dict(n=len(ids), first=min(recs[i]['date'] for i in ids), brierT=float(((pT - (dd > 0)) ** 2).mean()), accT=float(((pT > .5) == (dd > 0)).mean()),
                           maeT=float(np.abs(dd - mT).mean()), brierM0=float(((pM - (dd > 0)) ** 2).mean()),
                           brierKnownLineupSameGames=float(brier(kn, dd).mean()), maeKnownSameGames=float(np.abs(dd - kn - H).mean()))
out['A1'] = A1

# ---------- A2 名單／分鐘 ----------
rows = [r for r in ab._tab('player-games.json') if r['MIN'] and r['MIN'] > 0]
tot = collections.Counter()
for r in rows:
    tot[(r['GAME_ID'], r['TEAM_ID'])] += r['MIN']
name = {}; pg = collections.defaultdict(dict); plog = collections.defaultdict(list)
for r in sorted(rows, key=lambda r: (r['GAME_DATE'], r['GAME_ID'])):
    m = r['MIN'] * 240.0 / tot[(r['GAME_ID'], r['TEAM_ID'])]
    name[r['PLAYER_ID']] = r.get('PLAYER_NAME'); pg[(r['GAME_ID'], str(r['TEAM_ID']))][r['PLAYER_ID']] = m
    plog[r['PLAYER_ID']].append((r['GAME_DATE'], m))
ab._rotations(G)
tg = collections.defaultdict(list)
for g in gl:
    for s in ('home', 'away'):
        tg[g[s]].append((g['date'], g['gid'], s))
st = collections.defaultdict(list)
for t, lst in tg.items():
    for j, (d, gid, s) in enumerate(lst):
        act = pg[(gid, t)]
        if j < 3 or not act:
            continue
        prior = [[[p_, m_] for p_, m_ in pg[(g2, t)].items()] for _, g2, _ in lst[max(0, j - 10):j]]
        logs = {p_: [m_ for dd_, m_ in plog[p_] if dd_ < d] for r_ in prior for p_, _ in r_}
        for lab, rot in (('blind', dict(M.rotation(prior, [], logs=logs))), ('known', dict(G[gid]['rot_' + s]))):
            u = set(rot) | set(act); err = sum(abs(rot.get(q, 0) - act.get(q, 0)) for q in u)
            st[lab + 'Mis'].append(err / 2)
            st[lab + 'MaeRot'].append(np.mean([abs(rot.get(q, 0) - act.get(q, 0)) for q in u if rot.get(q, 0) >= 10 or act.get(q, 0) >= 10]))
            if lab == 'blind':
                st['predNoShowMin'].append(sum(v for q, v in rot.items() if q not in act)); st['unpredMin'].append(sum(v for q, v in act.items() if q not in rot))
                st['predNoShowN'].append(sum(1 for q, v in rot.items() if q not in act and v >= 10)); st['rotN'].append(sum(1 for v in rot.values() if v >= 10))
                top = sorted(rot.items(), key=lambda x: -x[1])[:5]
                st['starterOut'].append(sum(1 for q, _ in top if q not in act))
out['A2'] = dict(teamGames=len(st['blindMis']), note='blind＝不知道誰缺陣、只看該隊前 ≤10 場；known＝已知該場誰上場（T 評估用的名單）。Mis＝每隊每場放錯人的分鐘（240 分鐘裡）',
                 **{k: float(np.mean(v)) for k, v in st.items()},
                 predNoShowShare=float(np.sum(st['predNoShowN']) / np.sum(st['rotN'])), gamesWithTop5Out=float(np.mean(np.array(st['starterOut']) > 0)))

# ---------- A3 球員：季初預期 vs 現在 ----------
fl = ab._folders()
rk = lambda f: {int(r['playerId']): r for r in csv.DictReader(open(ab.LIVE / f / 'ranking.csv', encoding='utf-8'))}
R0, R1 = rk(fl[0]), rk(fl[-1])
gp = {p_: (len(v), float(np.mean([m_ for _, m_ in v]))) for p_, v in plog.items()}
tgames = {t: len(v) for t, v in tg.items()}
pl = []
for p_, r1 in R1.items():
    if p_ in R0 and p_ in gp and gp[p_][0] >= 6:
        pl.append(dict(pid=p_, name=r1['name'], team=r1['team'], g=gp[p_][0], ovr0=float(R0[p_]['ovr']), ovr1=float(r1['ovr']), dOvr=float(r1['ovr']) - float(R0[p_]['ovr']),
                       mpgHat0=float(R0[p_]['MPGhat']), mpg=gp[p_][1], dMpg=gp[p_][1] - float(R0[p_]['MPGhat'])))
big = [x for x in pl if x['mpg'] >= 20 or x['mpgHat0'] >= 20]
out['A3'] = dict(base=fl[0], now=fl[-1], n=len(pl), ovrMae=float(np.mean([abs(x['dOvr']) for x in pl])), mpgMae=float(np.mean([abs(x['dMpg']) for x in pl])),
                 mpgMaeRot=float(np.mean([abs(x['dMpg']) for x in big])), ovrCorr=float(np.corrcoef([x['ovr0'] for x in pl], [x['ovr1'] for x in pl])[0, 1]),
                 ovrUp=sorted(big, key=lambda x: -x['dOvr'])[:8], ovrDown=sorted(big, key=lambda x: x['dOvr'])[:8],
                 mpgUp=sorted(pl, key=lambda x: -x['dMpg'])[:8], mpgDown=sorted(pl, key=lambda x: x['dMpg'])[:8])
# 缺陣：先驗 MPGhat ≥ 24 但出賽不到球隊場次一半
out['A3']['missing'] = sorted([dict(name=r['name'], team=r['team'], mpgHat0=float(r['MPGhat']), ovr0=float(r['ovr']), g=gp.get(p_, (0, 0))[0])
                               for p_, r in R0.items() if float(r['MPGhat']) >= 24 and gp.get(p_, (0, 0))[0] < 0.5 * np.mean(list(tgames.values()))], key=lambda x: -x['ovr0'])[:15]

# ---------- A4 球隊：實際 − T 預期 ----------
acc = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
for g in gl:
    for t, sgn in ((g['home'], 1), (g['away'], -1)):
        a = acc[t]; a[0] += 1; a[1] += sgn * g['d']; a[2] += sgn * (g['mT'] + H); a[3] += (sgn * g['d'] > 0)
out['A4'] = sorted([dict(team=abbr[t], n=a[0], w=a[3], actual=a[1] / a[0], expT=a[2] / a[0], resid=(a[1] - a[2]) / a[0]) for t, a in acc.items()], key=lambda x: -x['resid'])

# ---------- 測試 F ----------
tf = [g for g in gl if g['date'] >= '2026-11-07' and all(k in pre[g['gid']]['p'] for k in ('cut', 'cutw3'))]
if tf:
    d = np.array([g['d'] for g in tf]); F = {'n': len(tf)}
    mm = {k: np.array([pre[g['gid']]['p'][k]['mT'] for g in tf]) for k in ('online', 'cut', 'cutw3')}
    for k, m in mm.items():
        F[k] = summ(m, d)
        if k != 'online':
            db = brier(m, d) - brier(mm['online'], d); da = np.abs(d - m - H) - np.abs(d - mm['online'] - H)
            F[k].update(dBrier=float(db.mean()), dBrierCI=boot(db), dMae=float(da.mean()), dMaeCI=boot(da), corrWithOnline=float(np.corrcoef(m, mm['online'])[0, 1]),
                        meanAbsShift=float(np.abs(m - mm['online']).mean()))
    out['F'] = F

# ---------- 2025-26 資料（測試 M、C1） ----------
inp = J(os.path.join(ROOT, 'reports', 'E208-team-rating', 'inputs.json'))['games']
byi = {g['i']: g for g in inp}
order = sorted(inp, key=lambda g: (g['date'], g['id'])); first = {g['i'] for g in order[:235]}
pm = os.path.join(HERE, 'results', 'pred-mock.json')
if os.path.exists(pm):
    P = J(pm); idx = [j for j, i in enumerate(P['games']) if i not in first]
    d = np.array([byi[P['games'][j]]['hs'] - byi[P['games'][j]]['as'] for j in idx]); Mo = {'n': len(idx)}
    mm = {k: np.array(v).mean(0)[idx] for k, v in P['margin_seed'].items()}
    for k, m in mm.items():
        Mo[k] = summ(m, d)
        if k != 'T2425':
            db = brier(m, d) - brier(mm['T2425'], d); da = np.abs(d - m - H) - np.abs(d - mm['T2425'] - H)
            Mo[k].update(dBrier=float(db.mean()), dBrierCI=boot(db), dMae=float(da.mean()), dMaeCI=boot(da), corrWithBase=float(np.corrcoef(m, mm['T2425'])[0, 1]),
                         meanAbsShift=float(np.abs(m - mm['T2425']).mean()))
    out['M'] = Mo

# ---------- C1：2025-26 模擬 235 場檢查點 ----------
PT = J(os.path.join(ROOT, 'reports', 'E228-transformer-team-rating', 'work', 'pred-T-2526.json'))
mT26 = dict(zip(PT['games'], np.array(PT['margin_seed']).mean(0)))
g26 = [dict(date=g['date'], home=g['home'], away=g['away'], mT=float(mT26[g['i']]), d=g['hs'] - g['as'], first=g['i'] in first) for g in order]
fg = [g for g in g26 if g['first']]; rg = [g for g in g26 if not g['first']]
teams26 = sorted({g['home'] for g in g26})
won_first = collections.Counter(); won_all = collections.Counter(); act_rest = collections.defaultdict(list)
for g in g26:
    for t, sgn in ((g['home'], 1), (g['away'], -1)):
        won_all[t] += sgn * g['d'] > 0
        if g['first']:
            won_first[t] += sgn * g['d'] > 0
        else:
            act_rest[t].append(sgn * g['d'])
C1 = {}; C1t = {}
def c1_eval(m):
    pw = collections.Counter(won_first); pm_ = collections.defaultdict(list)
    ph = Phi((m + H) / SIG)
    for g, mi, pi in zip(rg, m, ph):
        pw[g['home']] += pi; pw[g['away']] += 1 - pi; pm_[g['home']].append(mi + H); pm_[g['away']].append(-(mi + H))
    we = np.array([abs(pw[t] - won_all[t]) for t in teams26]); me = np.array([abs(np.mean(pm_[t]) - np.mean(act_rest[t])) for t in teams26])
    ws = np.array([pw[t] - won_all[t] for t in teams26])
    return dict(winsMae=float(we.mean()), winsRmse=float(np.sqrt((ws ** 2).mean())), winsP90=float(np.percentile(we, 90)), marginMae=float(me.mean()),
                brier=float(brier(m, [g['d'] for g in rg]).mean())), we, me
for lab, k in KS.items():
    s = shr_at(fg, k); m = np.array([g['mT'] + s[g['home']] - s[g['away']] for g in rg])
    C1[lab], we, me = c1_eval(m); C1t[lab] = we
acc2 = collections.defaultdict(list)
for g in fg:
    acc2[g['home']].append(g['d']); acc2[g['away']].append(-g['d'])
rt = {t: sum(v) / (len(v) + 10.0) for t, v in acc2.items()}
C1['actualOnlyK10'], _, _ = c1_eval(np.array([rt[g['home']] - rt[g['away']] for g in rg]))
for lab in KS:
    if lab != 'K10':
        C1[lab]['dWinsMaeVsK10'] = float((C1t[lab] - C1t['K10']).mean()); C1[lab]['dWinsMaeCI'] = boot(C1t[lab] - C1t['K10'])
C1['nFirst'] = len(fg); C1['nRest'] = len(rg)
out['C1'] = C1

# ---------- C2：2026-27 逐日滾動＋檢查點 ----------
C2 = {}; br = {}
for lab, k in KS.items():
    m = roll(gl, k); br[lab] = brier(m, d_all); C2[lab] = dict(brier=float(br[lab].mean()), mae=float(np.abs(d_all - m - H).mean()), acc=float((((m + H) > 0) == (d_all > 0)).mean()))
for lab in KS:
    if lab != 'K10':
        C2[lab]['dBrierVsK10'] = float((br[lab] - br['K10']).mean()); C2[lab]['dBrierCI'] = boot(br[lab] - br['K10'])
ck = {lab: [[], []] for lab in KS}; nck = {}
for c in ('2026-10-31', '2026-11-07', '2026-11-14'):
    f = os.path.join(WORK, f'pred-ckpt-{c}.json')
    if not os.path.exists(f):
        continue
    D = J(f); gs = [dict(G[i], mT=D[i]['p']['online']['mT']) for i in D if i in G]
    past = [g for g in gs if g['date'] < c]; fut = [g for g in gs if g['date'] >= c]; nck[c] = len(fut)
    for lab, k in KS.items():
        s = shr_at(past, k)
        ck[lab][0] += [g['mT'] + s[g['home']] - s[g['away']] for g in fut]; ck[lab][1] += [g['d'] for g in fut]
C2['checkpoints'] = dict(n=nck, **{lab: dict(brier=float(brier(v[0], v[1]).mean()), mae=float(np.abs(np.array(v[1]) - np.array(v[0]) - H).mean())) for lab, v in ck.items() if v[0]})
out['C2'] = C2

# ---------- 選 K（事前規則） ----------
labs = list(KS); r1 = {l: r for r, l in enumerate(sorted(labs, key=lambda l: C1[l]['winsMae']))}; r2 = {l: r for r, l in enumerate(sorted(labs, key=lambda l: C2[l]['brier']))}
tot_r = {l: r1[l] + r2[l] for l in labs}; best = min(tot_r.values()); cand = [l for l in labs if tot_r[l] == best]
pick = 'K10'; why = 'tie'
if len(cand) == 1:
    b = cand[0]
    if b == 'K10':
        why = 'K10 名次和最小'
    else:
        clear = C1[b]['dWinsMaeCI'][1] < 0 and C2[b]['dBrierCI'][1] < 0
        pick, why = (b, '名次和最小且兩項差距都在重抽區間外') if clear else ('K10', f'{b} 名次和最小但差距在重抽區間內')
out['pickK'] = dict(rankSum=tot_r, pick=pick, why=why)

json.dump(out, open(os.path.join(WORK, 'eval.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
show = lambda k: print(k, json.dumps(out.get(k), ensure_ascii=False, default=float)[:2500])
for k in ('A1', 'A2', 'F', 'M', 'C1', 'C2', 'pickK'):
    show(k)
