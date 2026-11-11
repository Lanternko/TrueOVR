"""E-226 診斷（只讀，不調參，L-026）：同一個 stint ridge 套在 2025-26 實測 stints 與模擬回合帳本，比 ≥1000 分鐘球員的單人淨值。
ridge：每邊球員進攻欄＋防守欄（λ3000，權重＝回合，每 100 回合）＋每邊「場上中鋒人數」「場上後衛人數」輕懲罰欄（λ=1）。
單人值＝進攻係數−防守係數（＋所屬位置欄），+＝讓球隊淨分變好。拆分：得分＝籃下(2·shortM)＋中距(2·midM)＋三分(3·longM)＋罰球(ftm)，逐項加總＝總值；
另列計數通道（進攻籃板、對手進攻籃板、失誤、出手數）當機制指標，不可加總。
半數：實測＝game id 奇偶；模擬＝帳本檔案奇偶。模擬帳本：sim 0.1.1 兩個 seed＋sim 0.1.2（E-166 k1）四個 seed（與 F-114 同一組）。
用法（repo 根目錄）：python -I -X utf8 reports/E226-sim-player-value/diag.py [--sim012]"""
import json, sys, hashlib
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as sl
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'reports/E226-sim-player-value/'
ONLY012 = '--sim012' in sys.argv
REAL = 'reports/defense-b1/stints.jsonl'
SIMF = ([] if ONLY012 else [('reports/sim-0.1.1-wing-diag/poss-sim-%d.json' % s) for s in (20261101, 20261102)]) + \
       [('reports/sim-0.1.2+E166-ft-defense/possk/possk-%sk1-%d.json' % (pre, s)) for pre, s in (('', 20261103), ('judge-', 20261028), ('', 20261104), ('judge-', 20261029))]
RR = json.load(open('reports/sim-0.1.1-oreb-diag/rr-20261101.json', encoding='utf-8'))['real']
INFO = {p['id']: p for p in RR}
ATT = json.load(open('reports/E208-team-rating/players-attrs.json', encoding='utf-8'))['players']
POS = lambda i: INFO[i]['pos'] if i in INFO else ({-3004: 'C', -3005: 'C'}.get(i) or (ATT.get(str(i), {}).get('pos') or ''))
isC = lambda i: POS(i) == 'C'
isG = lambda i: POS(i) in ('PG', 'SG')
PARTS = ('pts', 'rim', 'mid', 'three', 'ftm', 'oreb', 'tov', 'fga')

def part(o):
    return {'rim': 2 * o['shortM'], 'mid': 2 * o['midM'], 'three': 3 * o['longM'], 'ftm': o['ftm'], 'oreb': o['oreb'], 'tov': o['tov'], 'fga': o['fga']}

def real_rows():
    out = {0: [], 1: []}
    for l in open(REAL, encoding='utf-8'):
        s = json.loads(l); t = s['teams']; h = int(s['id']) & 1
        for k in (0, 1):
            o, p = t[k]['opponent'], t[k]['defensivePossessions']
            if p > 0: out[h].append({'o': t[1 - k]['players'], 'd': t[k]['players'], 'poss': p, 'pts': o['points'], **part(o)})
    return out

def sim_rows():
    out = {0: [], 1: []}
    for n, f in enumerate(SIMF):
        for r in json.load(open(f, encoding='utf-8'))['rows']:
            if r['poss'] > 0: out[n & 1].append({'o': r['o'], 'd': r['d'], 'poss': r['poss'], 'pts': r['pts'], **part(r)})
    return out

def fit(rows, lam=3000, lamL=1.0):
    ids = sorted({i for r in rows for i in r['o'] + r['d']}); ix = {v: k for k, v in enumerate(ids)}; n = len(ids); rr, cc, vv = [], [], []
    for k, r in enumerate(rows):
        for i in r['o']: rr.append(k); cc.append(ix[i]); vv.append(1)
        for i in r['d']: rr.append(k); cc.append(n + ix[i]); vv.append(1)
        for j, s in ((0, 'o'), (1, 'd')):
            c = sum(map(isC, r[s])); g = sum(map(isG, r[s]))
            if c: rr.append(k); cc.append(2 * n + j); vv.append(c)
            if g: rr.append(k); cc.append(2 * n + 2 + j); vv.append(g)
    X = sp.csr_matrix((vv, (rr, cc)), shape=(len(rows), 2 * n + 4)); W = np.array([r['poss'] for r in rows], float)
    lu = sl.splu((X.T @ sp.diags(W) @ X + sp.diags(np.r_[np.full(2 * n, lam), [lamL] * 4])).tocsc()); out = {}
    for q in PARTS:
        num = np.array([r[q] for r in rows], float); y = num / W - num.sum() / W.sum(); b = lu.solve(X.T @ (W * y)) * 100
        def val(i, b=b):   # 進攻端產出 − 防守端放掉（含位置欄）
            po = (b[2 * n] if isC(i) else 0) + (b[2 * n + 2] if isG(i) else 0); pd = (b[2 * n + 1] if isC(i) else 0) + (b[2 * n + 3] if isG(i) else 0)
            return {'O': b[ix[i]] + po, 'D': -(b[n + ix[i]] + pd)}   # D：+＝讓對手少
        out[q] = {'_pos': {'Co': b[2 * n], 'Cd': b[2 * n + 1], 'Go': b[2 * n + 2], 'Gd': b[2 * n + 3]}, **{i: val(i) for i in ids}}
        out[q]['_ids'] = set(ids)
    return out

POSS_VAL = 1.05   # 一個回合約值多少分（只用在計數通道換算，報告標明）
def net(F, i):
    v = {q: F[q][i] for q in PARTS}
    r = {'net': v['pts']['O'] + v['pts']['D']}
    for q in ('rim', 'mid', 'three', 'ftm'): r['O_' + q] = v[q]['O']; r['D_' + q] = v[q]['D']
    r['reb'] = POSS_VAL * (v['oreb']['O'] + v['oreb']['D'])     # 自己進攻籃板多＋讓對手進攻籃板少
    r['tov'] = POSS_VAL * (-v['tov']['O'] + v['tov']['D'])      # 自己少失誤＋逼對手失誤
    r['fga_d'] = v['fga']['D']
    return r

src = {'real': real_rows(), 'sim': sim_rows()}
F = {a: {'full': fit(v[0] + v[1]), 0: fit(v[0]), 1: fit(v[1])} for a, v in src.items()}
P = [i for i in INFO if INFO[i]['min'] >= 1000 and all(i in F[a][h]['pts']['_ids'] for a in F for h in ('full', 0, 1))]
V = {a: {h: {i: net(F[a][h], i) for i in P} for h in ('full', 0, 1)} for a in F}
poss = {a: sum(r['poss'] for h in (0, 1) for r in src[a][h]) for a in src}

# 類型（引擎屬性，P 內分位；優先順序互斥）
A = {i: ATT[str(i)] for i in P}
z = lambda k, g: (lambda m, s: {i: (A[i][k] - m) / s for i in g})(np.mean([A[i][k] for i in g]), np.std([A[i][k] for i in g]))
nonC = [i for i in P if POS(i) != 'C']; Cs = [i for i in P if POS(i) == 'C']
zc = {k: z(k, nonC) for k in ('pass', 'drive', 'long', 'onBall', 'help', 'rebound')}
hC = np.median([A[i]['help'] for i in Cs]); rq = np.quantile([A[i]['rebound'] for i in nonC], 0.75)
cre = {i: zc['pass'][i] + zc['drive'][i] for i in nonC}; creq = np.quantile(list(cre.values()), 0.70)
def typ(i):
    if POS(i) == 'C': return '護框中鋒' if A[i]['help'] >= hC else '其他中鋒'
    if POS(i) in ('SF', 'PF') and A[i]['rebound'] >= rq: return '籃板型前鋒'
    if cre[i] >= creq: return '外線持球手'
    if zc['long'][i] + zc['onBall'][i] >= 0 and POS(i) in ('SG', 'SF', 'PF'): return '3D 側翼'
    return '其他'
T = {i: typ(i) for i in P}

def ranks(d):   # 1＝最好
    o = sorted(P, key=lambda i: -d[i]); return {i: k + 1 for k, i in enumerate(o)}
rv = {i: V['real']['full'][i]['net'] for i in P}; sv = {i: V['sim']['full'][i]['net'] for i in P}
Rr, Rs = ranks(rv), ranks(sv)
def half_r(a, k='net'):
    return np.corrcoef([V[a][0][i][k] for i in P], [V[a][1][i][k] for i in P])[0, 1]
def noise_sd(a, k='net'):   # 全樣本估計的雜訊 sd ≈ sd(h0−h1)/2
    return np.std([V[a][0][i][k] - V[a][1][i][k] for i in P]) / 2

L = []; pr = L.append
pr(f'# E-226 診斷輸出  sim 帳本：{"0.1.2 only (4 seeds)" if ONLY012 else "0.1.1×2 + 0.1.2×4"}')
pr(f'inputs sha256: stints {hashlib.sha256(open(REAL, "rb").read()).hexdigest()[:16]} | ' + ' '.join(f.split('/')[-1] + ':' + hashlib.sha256(open(f, 'rb').read()).hexdigest()[:12] for f in SIMF))
pr(f'possessions real {poss["real"]:,} sim {poss["sim"]:,}; players (≥1000 min, 兩邊兩半都有) {len(P)}')
r_full = np.corrcoef(list(rv.values()), [sv[i] for i in rv])[0, 1]; rho = spearmanr([rv[i] for i in P], [sv[i] for i in P])[0]
hr_r, hr_s = half_r('real'), half_r('sim')
rel = lambda r: 2 * r / (1 + r)
pr(f'單人淨值 real sd {np.std(list(rv.values())):.2f} (noise {noise_sd("real"):.2f}, half-r {hr_r:+.2f}) | sim sd {np.std(list(sv.values())):.2f} (noise {noise_sd("sim"):.2f}, half-r {hr_s:+.2f})')
pr(f'corr(real, sim) Pearson {r_full:+.3f} Spearman {rho:+.3f}; 去雜訊上限 sqrt(rel_r·rel_s) {np.sqrt(rel(hr_r) * rel(hr_s)):.3f}; 去雜訊後 r {r_full / np.sqrt(rel(hr_r) * rel(hr_s)):+.3f}')
for a in ('real', 'sim'):
    p = F[a]['full']['pts']['_pos']; pr(f'位置欄（pts，每 100，每多一人）{a}: C 進攻 {p["Co"]:+.2f} C 防守放掉 {p["Cd"]:+.2f} | 後衛 進攻 {p["Go"]:+.2f} 防守放掉 {p["Gd"]:+.2f}')
CH = ('net', 'O_rim', 'O_mid', 'O_three', 'O_ftm', 'D_rim', 'D_mid', 'D_three', 'D_ftm', 'reb', 'tov')
def table(groups, title):
    pr(f'\n## {title}\n名次差＝實測名次−模擬名次（+＝模擬高估幾名）；Δ＝模擬−實測（每 100 回合，+＝模擬給太多）；SE 由兩半雜訊估')
    pr('| 組 | n | 實測淨值 | 模擬淨值 | Δ淨值 (SE) | 名次差 | ' + ' | '.join('Δ' + c for c in CH[1:]) + ' |')
    pr('|' + '---|' * (6 + len(CH) - 1))
    for g, ids in groups:
        if not ids: continue
        d = {c: np.mean([V['sim']['full'][i][c] - V['real']['full'][i][c] for i in ids]) for c in CH}
        se = np.sqrt((noise_sd('real') ** 2 + noise_sd('sim') ** 2) / len(ids))
        pr(f'| {g} | {len(ids)} | {np.mean([rv[i] for i in ids]):+.2f} | {np.mean([sv[i] for i in ids]):+.2f} | {d["net"]:+.2f} ({se:.2f}) | {np.mean([Rr[i] - Rs[i] for i in ids]):+.0f} | ' + ' | '.join(f'{d[c]:+.2f}' for c in CH[1:]) + ' |')
table([(p, [i for i in P if POS(i) == p]) for p in ('PG', 'SG', 'SF', 'PF', 'C')], '按位置')
table([(t, [i for i in P if T[i] == t]) for t in ('外線持球手', '3D 側翼', '籃板型前鋒', '護框中鋒', '其他中鋒', '其他')], '按類型')
pr('\n## 半數一致性：Δ（模擬半 h − 實測半 h），h=0 / h=1')
for g, ids in [(p_, [i for i in P if POS(i) == p_]) for p_ in ('PG', 'SG', 'SF', 'PF', 'C')] + [(t, [i for i in P if T[i] == t]) for t in ('籃板型前鋒', '護框中鋒', '其他中鋒')]:
    pr(f'{g:6s} ' + '  '.join(c + ' ' + '/'.join(f"{np.mean([V['sim'][h][i][c] - V['real'][h][i][c] for i in ids]):+.2f}" for h in (0, 1)) for c in CH))
# 通道的雜訊與相關
pr('\n## 各通道：實測與模擬散布、拆半相關、兩者相關（全部球員）')
for c in CH:
    a_ = [V['real']['full'][i][c] for i in P]; b_ = [V['sim']['full'][i][c] for i in P]
    pr(f'{c:8s} real sd {np.std(a_):.2f} half-r {half_r("real", c):+.2f} | sim sd {np.std(b_):.2f} half-r {half_r("sim", c):+.2f} | corr {np.corrcoef(a_, b_)[0, 1]:+.2f}')
nm = lambda i: INFO[i]['name']
row = lambda i: f'| {nm(i)} | {POS(i)} | {T[i]} | {Rr[i]} | {Rs[i]} | {Rr[i] - Rs[i]:+d} | {rv[i]:+.2f} | {sv[i]:+.2f} | {V["sim"]["full"][i]["reb"] - V["real"]["full"][i]["reb"]:+.2f} | {V["sim"]["full"][i]["D_rim"] - V["real"]["full"][i]["D_rim"]:+.2f} |'
hdr = '| 球員 | 位置 | 類型 | 實測名次 | 模擬名次 | 名次差 | 實測 | 模擬 | Δ籃板 | Δ籃下防守 |\n|---|---|---|---|---|---|---|---|---|---|'
o = sorted(P, key=lambda i: Rs[i] - Rr[i])
pr(f'\n## 模擬高估最多 12 人（名次差 +）\n{hdr}'); [pr(row(i)) for i in o[:12]]
pr(f'\n## 模擬低估最多 12 人\n{hdr}'); [pr(row(i)) for i in o[::-1][:12]]
pr(f'\n## 指定例子\n{hdr}')
for n_ in ('Jayson Tatum', 'Jaylen Brown', 'Paul George', 'Shai Gilgeous-Alexander', 'Nikola Jok', 'Rudy Gobert', 'Draymond Green', 'Herbert Jones', 'Alex Caruso', 'Derrick White', 'Anthony Edwards', 'Steven Adams', 'Domantas Sabonis', 'Stephen Curry'):
    for i in P:
        if nm(i).startswith(n_): pr(row(i))
tag = 'diag-sim012' if ONLY012 else 'diag'
open(OUT + tag + '.txt', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
json.dump({str(i): {'name': nm(i), 'pos': POS(i), 'type': T[i], 'real': V['real']['full'][i], 'sim': V['sim']['full'][i], 'rank_real': Rr[i], 'rank_sim': Rs[i]} for i in P},
          open(OUT + tag + '-players.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('\n'.join(L))
# 雜訊：名次偏差的拆半估計與 Spearman 的球員 bootstrap（給預註冊 MDE）
def grp_rank(h, ids):
    a = ranks({i: V['real'][h][i]['net'] for i in P}); b = ranks({i: V['sim'][h][i]['net'] for i in P}); return np.mean([a[i] - b[i] for i in ids])
M = ['\n## 雜訊（MDE 用）']
for g, ids in [(p_, [i for i in P if POS(i) == p_]) for p_ in ('SF', 'C')] + [(t, [i for i in P if T[i] == t]) for t in ('籃板型前鋒', '護框中鋒', '外線持球手', '3D 側翼')]:
    r0, r1 = grp_rank(0, ids), grp_rank(1, ids); M.append(f'{g} 名次差 半0 {r0:+.1f} 半1 {r1:+.1f}  全樣本 SE≈|差|/2 {abs(r0 - r1) / 2:.1f}')
rng = np.random.default_rng(20261103); a_ = np.array([rv[i] for i in P]); b_ = np.array([sv[i] for i in P]); bs = []
for _ in range(2000):
    k = rng.integers(0, len(P), len(P)); bs.append(spearmanr(a_[k], b_[k])[0])
M.append(f'Spearman {rho:+.3f} 球員 bootstrap 90% [{np.quantile(bs, .05):+.3f}, {np.quantile(bs, .95):+.3f}] sd {np.std(bs):.3f}')
M.append(f'Spearman 半對半：real0~sim0 {spearmanr([V["real"][0][i]["net"] for i in P], [V["sim"][0][i]["net"] for i in P])[0]:+.3f} real1~sim1 {spearmanr([V["real"][1][i]["net"] for i in P], [V["sim"][1][i]["net"] for i in P])[0]:+.3f} real0~real1 {spearmanr([V["real"][0][i]["net"] for i in P], [V["real"][1][i]["net"] for i in P])[0]:+.3f}')
open(OUT + tag + '.txt', 'a', encoding='utf-8').write('\n'.join(M) + '\n'); print('\n'.join(M))
