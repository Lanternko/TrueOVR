"""E-292：MIX 加分 500 分鐘以下按比例打折。用法（repo root）：python -I -B -X utf8 reports/E292-mix-ramp/e292_eval.py"""
import csv, hashlib, json, re, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), 'prereg sha'
CARD = ROOT / 'reports/card-0.2.13a/ranking.csv'; ARMS = ROOT / 'reports/E291-mix-shrink/arms.npz'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'; EPM = ROOT / 'reports/impact-epm-2026-27/epm-live.csv'


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s); s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


card = list(csv.DictReader(open(CARD, encoding='utf-8'))); N = len(card)
names = [r['name'] for r in card]; pos = np.array([r['pos'] for r in card])
MIN = np.array([float(r['MIN']) for r in card]); ovr0 = np.array([float(r['ovr']) for r in card]); rank0 = np.array([int(r['rank']) for r in card])
z = np.load(ARMS, allow_pickle=False); assert list(z['names']) == names
bA, bC = z['bA'], z['bC']
bD = np.where(MIN >= 500, bA, bC * np.minimum(1.0, MIN / 500.0))


def ranks(o):
    idx = sorted(range(N), key=lambda i: (-o[i], rank0[i])); r = np.empty(N, int); r[idx] = np.arange(1, N + 1); return r


tw = {norm(r['name']): float(r['overall2k']) for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')) if r['overall2k']}
ep = {norm(r['name']): (float(r['net']), float(r['poss2627'])) for r in csv.DictReader(open(EPM, encoding='utf-8'))}


def corr(o, mask, src):
    if src == '2k':
        idx = [i for i in range(N) if mask[i] and norm(names[i]) in tw]; y = [tw[norm(names[i])] for i in idx]
    else:
        idx = [i for i in range(N) if mask[i] and norm(names[i]) in ep and ep[norm(names[i])][1] >= 200]; y = [ep[norm(names[i])][0] for i in idx]
    return round(float(spearmanr([o[i] for i in idx], y)[0]), 4), len(idx)


NEW = {'A': np.round(ovr0 + bA, 1), 'D': np.round(ovr0 + bD, 1)}; R = {k: ranks(v) for k, v in NEW.items()}
res = {'prereg_sha256': sha(HERE / 'preregistration.md'), 'sources_sha256': {'card_0213a': sha(CARD), 'e291_arms': sha(ARMS)}, 'arms': {}}
for k, b in (('A', bA), ('D', bD)):
    r = R[k]; o = NEW[k]
    res['arms'][k] = {'top10': [names[i] for i in np.argsort(r)[:10]],
                      'top30_drops': [(names[i], int(rank0[i]), int(r[i])) for i in range(N) if rank0[i] <= 30 and r[i] - rank0[i] > 10],
                      'n_bonus_pos': int((b > 0).sum()),
                      'rho_2k_all': corr(o, np.ones(N, bool), '2k'), 'rho_epm_all': corr(o, np.ones(N, bool), 'epm'),
                      'rho_2k_min500': corr(o, MIN >= 500, '2k'), 'rho_epm_min500': corr(o, MIN >= 500, 'epm'),
                      'C_lt200_mean': float(b[(pos == 'C') & (MIN < 200)].mean()), 'C_ge500_mean': float(b[(pos == 'C') & (MIN >= 500)].mean())}
res['rho_0213a'] = {'2k_all': corr(ovr0, np.ones(N, bool), '2k'), 'epm_all': corr(ovr0, np.ones(N, bool), 'epm')}
# T2
jump = float(np.max(np.abs(bC * np.minimum(1, 501 / 500) - bC * 499 / 500)))
band = np.where((MIN >= 400) & (MIN <= 600) & np.isin(pos, ['PF', 'C']))[0]; band = band[np.argsort(MIN[band])]
bad = [(names[a], MIN[a], round(float(bD[a]), 2), names[b], MIN[b], round(float(bD[b]), 2)) for a, b in zip(band[:-1], band[1:])
       if abs(bD[b] - bD[a]) >= 3 and MIN[b] - MIN[a] < 10]
A, D = res['arms']['A'], res['arms']['D']
T1 = float(np.abs(bD - bA)[MIN >= 500].max()) <= 0.001
T2 = jump <= 0.10 and not bad
T3 = D['top10'] == A['top10'] and len(D['top30_drops']) <= 2
T4 = D['C_lt200_mean'] < 0.4 * D['C_ge500_mean']
T5 = D['rho_2k_all'][0] >= A['rho_2k_all'][0] - .005 and D['rho_epm_all'][0] >= A['rho_epm_all'][0] - .005
res.update({'jump_499_501': jump, 'band_jumps': bad, 'checks': {'T1': T1, 'T2': T2, 'T3': T3, 'T4': T4, 'T5': T5}, 'pass': bool(T1 and T2 and T3 and T4 and T5)})
SHOW = ['Ariel Hukporti', 'Trayce Jackson-Davis', 'Zach Edey', 'Khaman Maluach', 'Paul Reed', 'Goga Bitadze', 'Victor Wembanyama',
        'Anthony Davis', 'Rudy Gobert', 'Devin Booker', 'Kevin Durant']
res['show'] = {n: {'pos': pos[i], 'MIN': MIN[i], 'rank0': int(rank0[i]), 'bonus_A': round(float(bA[i]), 2), 'rank_A': int(R['A'][i]),
                   'bonus_D': round(float(bD[i]), 2), 'rank_D': int(R['D'][i])} for n in SHOW if n in names for i in [names.index(n)]}
res['top_lt500'] = [(names[i], pos[i], MIN[i], round(float(bD[i]), 2), int(rank0[i]), int(R['D'][i])) for i in np.argsort(-bD) if MIN[i] < 500][:12]
(HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')
np.savez(HERE / 'bonus_D.npz', names=np.array(names), bD=bD)
print(json.dumps({k: res[k] for k in ('checks', 'pass', 'jump_499_501', 'band_jumps', 'rho_0213a')}, ensure_ascii=False, default=str))
for k in ('A', 'D'): print(k, json.dumps(res['arms'][k], ensure_ascii=False, default=str))
for n, v in res['show'].items(): print(n, v)
print('top <500', res['top_lt500'])
