"""稽核 A3：個人價值的獨立（縮小版）重算與特徵歸因。
 (1) 對報告的 value-raw.json 重算 Spearman／名次（驗證表格算術）。
 (2) 自己重寫價值算法（1000 組抽樣、自己的 RNG），R2-stats 有／無 stamina 兩版，和報告名次比。
 (3) Scottie／Harrison Barnes、Kevin Porter Jr.、Mitchell Robinson 的最極端特徵 z 值，與單欄歸零的敏感度。
python -X utf8 a3_value.py"""
import sys, os, json, csv
import numpy as np, torch
from scipy.stats import spearmanr, rankdata
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE)
sys.path.insert(0, R)
from e227_model import LineupNet
from e227_common import ATTRS, STATS
torch.set_num_threads(6)
raw = json.load(open(os.path.join(R, 'results/value-raw.json'), encoding='utf-8'))
pids, names, modal = raw['pids'], raw['names'], raw['modalPos']; n = len(pids)
V = {m: np.array(raw['new'][m]) for m in raw['new']}
idx = {nm: i for i, nm in enumerate(names)}
FOCUS = ['Scottie Barnes', 'Harrison Barnes', 'Kevin Porter Jr.', 'Mitchell Robinson']

# (1) 報告值 -> 名次（母體＝276 全部；以及有卡 OVR 者見報告）
rk_all = {m: rankdata(-V[m], method='min').astype(int) for m in V}
print('== 報告 value-raw 的 276 人名次（R2-abil / R2-stats / R2-stats-rapm）')
for f in FOCUS:
    i = idx[f]; print(f, {m: int(rk_all[m][i]) for m in ('R2-abil', 'R2-stats', 'R2-stats-rapm')}, 'value', {m: round(float(V[m][i]), 3) for m in ('R2-abil', 'R2-stats')})
card = {}
for r in csv.DictReader(open(os.path.join(os.path.dirname(os.path.dirname(R)), 'reports/card-0.2.12c/ranking.csv'), encoding='utf-8')):
    card[r['name']] = float(r['ovr'])
ok = np.array([nm in card for nm in names]); cv = np.array([card.get(nm, np.nan) for nm in names])
print('with card', ok.sum())
for m in ('R2-abil', 'R2-stats', 'R2-stats-rapm'):
    print('Spearman vs 卡OVR', m, round(float(spearmanr(V[m][ok], cv[ok])[0]), 3))
rc = rankdata(-cv[ok], method='min').astype(int); rr = rankdata(-V['R2-stats'][ok], method='min').astype(int)
nm_ok = [nm for nm in names if nm in card]
for f in FOCUS:
    if f in nm_ok:
        j = nm_ok.index(f); print(f, '卡名次', rc[j], 'R2-stats 名次(有卡母體)', rr[j])

# (2) 特徵與重寫的價值
SEASON = '2025-26'


def rd(p):
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def table():
    t = {}
    for r in rd(os.path.join(R, 'data', f'players-{SEASON}.csv')):
        t.setdefault(r['pid'], {}).update({c: (float(r[c]) if r[c] != '' else np.nan) for c in ATTRS})
    for r in rd(os.path.join(R, 'data', f'stats-{SEASON}.csv')):
        t.setdefault(r['pid'], {}).update({c: (float(r[c]) if r[c] != '' else np.nan) for c in STATS})
    return t


tab = table(); cols = ATTRS + STATS; F = len(cols)
Z = {}
for j, c in enumerate(cols):
    ids = [p for p in tab if not np.isnan(tab[p].get(c, np.nan))]; v = np.array([tab[p][c] for p in ids])
    if len(v) < 10 or v.std() < 1e-9:
        continue
    for p, x in zip(ids, v): Z.setdefault(p, np.full(F, np.nan))[j] = (x - v.mean()) / v.std()
feat = np.zeros((n, 2 * F), np.float32)
for i, p in enumerate(pids):
    z = Z.get(p, np.full(F, np.nan)); feat[i, :F] = np.nan_to_num(z); feat[i, F:] = ~np.isnan(z)
nets = []
for sd in range(5):
    net = LineupNet(F); net.load_state_dict(torch.load(os.path.join(R, f'results/weights/R2-stats-{sd}.pt'), map_location='cpu')); net.eval(); nets.append(net)
POS = torch.tensor(list(range(5)) * 2).unsqueeze(0); SIDE = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
modal = np.array(modal); pool = {p: np.where(modal == p)[0] for p in range(5)}
print('pool sizes', {p: len(v) for p, v in pool.items()})


def netpred(X):
    """X [B,10,2F] -> 平均 5 seed 的 100*(ptsA-ptsB)"""
    out = 0
    with torch.no_grad():
        for net in nets:
            o = net(X, POS.expand(len(X), -1), SIDE.expand(len(X), -1))[..., 0]
            out = out + 100 * (o[:, 0] - o[:, 1])
    return (out / len(nets)).numpy()


def value(i, ND, rng, fe):
    """球員 i 固定在 modal 位置；隊友、對手同位置真人抽；基準＝把 i 換成隨機同位置真人。"""
    p = modal[i]; ids = np.zeros((ND, 10), int)
    for slot in range(10):
        pl = pool[slot % 5]; ids[:, slot] = rng.choice(pl, ND)
    ids[:, p] = i
    for slot in range(10):               # 隊友與對手不能是他自己
        if slot != p:
            bad = ids[:, slot] == i
            while bad.any():
                ids[bad, slot] = rng.choice(pool[slot % 5], bad.sum()); bad = ids[:, slot] == i
    base = ids.copy(); rep = rng.choice(pool[p], ND); rep = np.where(rep == i, rng.choice(pool[p], ND), rep); base[:, p] = rep
    a = netpred(torch.from_numpy(fe[ids])); b = netpred(torch.from_numpy(fe[base]))
    # 讓他在 B 邊再算一次（對稱）：位置 p+5
    ids2 = ids.copy(); ids2[:, [p, p + 5]] = ids2[:, [p + 5, p]]
    base2 = ids2.copy(); base2[:, p + 5] = rep
    # 交換後他在 B 邊（slot p+5）；他的價值＝基準淨值－含他淨值（B 邊視角）
    c = netpred(torch.from_numpy(fe[ids2])); d = netpred(torch.from_numpy(fe[base2]))
    return float(((a.mean() - b.mean()) + (d.mean() - c.mean())) / 2)


ND = 600
st = cols.index('stamina')
fe_nost = feat.copy(); fe_nost[:, st] = 0; fe_nost[:, F + st] = 0
res = {}
for label, fe in (('stats', feat), ('stats_no_stamina', fe_nost)):
    rng = np.random.default_rng(20261104); v = np.zeros(n)
    for i in range(n):
        v[i] = value(i, ND, rng, fe)
    res[label] = v; print(label, 'done', flush=True)
mine = res['stats']; r_mine = rankdata(-mine, method='min').astype(int); r_ns = rankdata(-res['stats_no_stamina'], method='min').astype(int)
print('Spearman(我的 stats 價值, 報告 stats 價值)', round(float(spearmanr(mine, V['R2-stats'])[0]), 3))
print('Spearman(stats, stats 去 stamina)', round(float(spearmanr(mine, res['stats_no_stamina'])[0]), 3))
tab_rows = {}
for f in FOCUS:
    i = idx[f]
    tab_rows[f] = dict(report_rank=int(rk_all['R2-stats'][i]), my_rank=int(r_mine[i]), my_rank_no_stamina=int(r_ns[i]), my_val=float(mine[i]), my_val_no_stamina=float(res['stats_no_stamina'][i]))
    print(f, tab_rows[f])

# (3) 極端 z 與單欄歸零敏感度
sens = {}
for f in FOCUS:
    i = idx[f]; z = feat[i, :F]; m = feat[i, F:]
    top = sorted([(c, float(z[j])) for j, c in enumerate(cols) if m[j] > 0], key=lambda t: -abs(t[1]))[:8]
    miss = [c for j, c in enumerate(cols) if m[j] == 0]
    # 單欄歸零（z=0、mask=0）的敏感度：他的 slot 在固定的 800 組抽樣
    rng = np.random.default_rng(5); ND2 = 800; p = modal[i]
    ids = np.zeros((ND2, 10), int)
    for slot in range(10): ids[:, slot] = rng.choice(pool[slot % 5], ND2)
    ids[:, p] = i
    for slot in range(10):
        if slot != p:
            bad = ids[:, slot] == i
            while bad.any(): ids[bad, slot] = rng.choice(pool[slot % 5], bad.sum()); bad = ids[:, slot] == i
    base = netpred(torch.from_numpy(feat[ids])).mean()
    ds = {}
    for j, c in enumerate(cols):
        if m[j] == 0: continue
        fe2 = feat.copy(); fe2[i, j] = 0; fe2[i, F + j] = 0
        ds[c] = float(netpred(torch.from_numpy(fe2[ids])).mean() - base)
    allabs = sum(abs(v) for v in ds.values())
    topd = sorted(ds.items(), key=lambda t: -abs(t[1]))[:6]
    # 全部歸零（能力值＋統計全 mask）時的淨值變化，供比例用
    fe3 = feat.copy(); fe3[i] = 0; tot = float(netpred(torch.from_numpy(fe3[ids])).mean() - base)
    sens[f] = dict(extreme_z=top, missing=miss, ablate_single=topd, sum_abs=allabs, ablate_all=tot, stamina_delta=ds.get('stamina'))
    print('\n', f, 'minutes', raw['min'][i], 'pos', modal[i])
    print('  最極端 z：', [(c, round(v, 2)) for c, v in top])
    print('  缺值欄：', miss)
    print('  單欄歸零造成的 100 回合淨值變化（前 6）：', [(c, round(v, 2)) for c, v in topd], '| stamina', round(ds.get('stamina', float('nan')), 2), '| 全歸零', round(tot, 2), '| 絕對值總和', round(allabs, 2))
json.dump(dict(rows=tab_rows, sens=sens, spearman_mine_vs_report=float(spearmanr(mine, V['R2-stats'])[0]), spearman_stats_vs_nostamina=float(spearmanr(mine, res['stats_no_stamina'])[0])),
          open(os.path.join(HERE, 'a3_result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
np.save(os.path.join(HERE, 'a3_value_mine.npy'), np.stack([mine, res['stats_no_stamina']]))
