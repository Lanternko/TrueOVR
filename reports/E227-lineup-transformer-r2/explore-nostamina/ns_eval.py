"""探索性（測試集已讀過）：R2-stats-nost 在 E-227 測試集上的淨值 MSE，與 R2-stats、R2-abil、B0 的成對差（用 e227_eval 的 metrics／draws_for／paired，同 seed 20261103、B=2000）。
判定 2 三個守門指標、門檻取 R2-stats 的（mde-noise.json）。不改凍結檔，輸出 results/nost-test-results.json。純 CPU 推論，不起子程序。
  python -I -X utf8 ns_eval.py   （-I 會拿掉腳本目錄，所以這裡用 E227_SRC／sys.path 自行處理）"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import torch
from ns_common import ARM, strip
import e227_eval as ev
from e227_common import ARMS, SEASONS, load_rows
from e227_model import LineupNet, n_feat, season_means, tensors

PARENT = os.path.dirname(HERE)
rows = load_rows(SEASONS); tr = [r for r in rows if r['fold'] != 0]; means = season_means(tr)
test = ev.load_test()
T = {'R2-abil': tensors(test, 'abil', means, 'test'), 'R2-stats': tensors(test, 'stats', means, 'test')}
T[ARM] = strip(T['R2-stats'])
ye = T['R2-stats'][3].reshape(-1, 6).numpy()


def nets_of(arm, F, wdir):
    out = []
    for sd in range(5):
        n = LineupNet(F); n.load_state_dict(torch.load(os.path.join(wdir, f'{arm}-{sd}.pt'), map_location='cpu')); n.eval(); out.append(n)
    return out


NETS = {'R2-abil': nets_of('R2-abil', n_feat('abil'), os.path.join(PARENT, 'results', 'weights')),
        'R2-stats': nets_of('R2-stats', n_feat('stats'), os.path.join(PARENT, 'results', 'weights')),
        ARM: nets_of(ARM, n_feat('stats') - 1, os.path.join(HERE, 'results', 'weights'))}
P = {a: ev.t_raw(NETS[a], T[a]) for a in NETS}
models = {a: ev.ens(P[a]) for a in NETS}
sea2 = np.repeat([r['season'] for r in test], 2)
tv = {s: sum(r['tova'] + r['tovb'] for r in tr if r['season'] == s) / sum(r['possa'] + r['possb'] for r in tr if r['season'] == s) for s in SEASONS}
ob = {s: sum(r['orba'] + r['orbb'] for r in tr if r['season'] == s) / sum(r['rebOppa'] + r['rebOppb'] for r in tr if r['season'] == s) for s in SEASONS}
models['B0'] = (np.zeros(len(sea2)), np.array([tv[s] for s in sea2]), np.array([ob[s] for s in sea2]))
for a in NETS:
    for sd in range(5):
        models[f'{a}#{sd}'] = ev.ens(P[a][sd:sd + 1])
res, gm, act, G, Pw = ev.metrics(test, ye, models); draws = ev.draws_for(G)
main = ['B0', 'R2-abil', 'R2-stats', ARM]
frozen = json.load(open(os.path.join(PARENT, 'results', 'test-results.json'), encoding='utf-8'))
mde = frozen['mde']['R2-stats']; guard = frozen['guardThresholds']['R2-stats']
out = {'note': '探索性，測試集已被 E-227 讀過；不改 E-227 判定', 'games': G, 'stints': len(test),
       'mse': {k: round(ev.val(res, k, 'net'), 2) for k in main},
       'frozenMse': {k: frozen['test']['mse'][k] for k in ('B0', 'R2-abil', 'R2-stats')},
       'seedMSE': {a: [round(ev.val(res, f'{a}#{sd}', 'net'), 2) for sd in range(5)] for a in NETS},
       'side': {k: {m: round(ev.val(res, k, m), 5) for m in ('ptsSide', 'tovLL', 'orbLL')} for k in main}, 'paired': {}}
for a, b in [(ARM, 'R2-abil'), (ARM, 'R2-stats'), ('R2-stats', 'R2-abil'), (ARM, 'B0'), ('R2-abil', 'B0')]:
    p = ev.paired(res, a, b, 'net', draws)
    if (a, b) in ((ARM, 'R2-abil'), (ARM, 'R2-stats'), ('R2-stats', 'R2-abil')):
        p['guard'] = {m: ev.paired(res, a, b, m, draws) for m in ('ptsSide', 'tovLL', 'orbLL')}
    out['paired'][f'{a}−{b}'] = p
p = out['paired'][f'{ARM}−R2-abil']
out['verdictLike'] = {'thresholdsFrom': 'R2-stats（mde-noise.json）', 'judge1': {'point': p['point'], 'ci90': p['ci90'], 'needAtMost': -mde, 'pass': bool(p['point'] <= -mde and p['ci90'][1] < 0)},
                      'judge2': {m: {'point': p['guard'][m]['point'], 'threshold': guard[m], 'ok': bool(p['guard'][m]['point'] <= guard[m])} for m in ('ptsSide', 'tovLL', 'orbLL')}}
out['judge2pass'] = all(v['ok'] for v in out['verdictLike']['judge2'].values())
# 分組置換重要性（nost 臂）：整類一起打亂，看 5 seed 平均 MSE 上升
y = T[ARM][3].numpy(); pts2, poss2 = y[..., 0].reshape(-1), y[..., 1].reshape(-1); possA, possB = poss2[0::2], poss2[1::2]; Pw2 = (possA + possB) / 2
actual = np.where(Pw2 > 0, 100 * (pts2[0::2] - pts2[1::2]) / np.maximum(Pw2, 1e-9), 0); m_ = y[..., 5].reshape(-1)


def mse_of(attr):
    Pp = ev.ens(ev.t_raw(NETS[ARM], [attr, T[ARM][1], T[ARM][2], T[ARM][3]]))[0]
    muA, muB = Pp[0::2] + m_[0::2], Pp[1::2] + m_[1::2]
    pred = 100 * (muA * possA - muB * possB) / np.maximum(Pw2, 1e-9)
    return float((Pw2 * (actual - pred) ** 2).sum() / Pw2.sum())


from e227_common import ATTRS, STATS
names = [a for a in ATTRS if a != 'stamina'] + STATS; F = len(names); base = mse_of(T[ARM][0]); N = T[ARM][0].shape[0]; imp = {}
rng = np.random.default_rng(7)
for label in names:
    i = names.index(label); a2 = T[ARM][0].clone(); flat = a2.reshape(N * 10, -1); perm = torch.from_numpy(rng.permutation(N * 10))
    flat[:, [i, F + i]] = flat[perm][:, [i, F + i]]; imp[label] = round(mse_of(a2) - base, 3)
out['importance'] = {'baseMSE': round(base, 2), 'features': dict(sorted(imp.items(), key=lambda kv: -kv[1]))}
json.dump(out, open(os.path.join(HERE, 'results', 'nost-test-results.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: out[k] for k in ('mse', 'frozenMse', 'seedMSE', 'paired', 'verdictLike', 'judge2pass')}, ensure_ascii=False, indent=1)); print(list(out['importance']['features'].items())[:8])
