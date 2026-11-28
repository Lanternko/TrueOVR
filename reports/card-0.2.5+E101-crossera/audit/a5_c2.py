"""稽核 5：c2N、c2Q 自己重算。
資料組裝（半季卡片 g、答案）借 chain/e084.py 的 load_data/build_pools/pipeline（chain 與 E-097/E-096 鏈只差路徑與變體名，已 diff），
Spearman、兩方向平均、bootstrap 與 CI 自己寫。另用 seed 7、5000 次重抽檢查 CI 穩定。只寫 audit/。"""
import importlib.util, json, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(__file__).resolve().parents[1]

def load(var):
    os.environ['E090_VARIANT'] = var
    spec = importlib.util.spec_from_file_location('e084_' + var, OUT/'chain/e084.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.load_data(); pools = m.build_pools()
    return pools, m.pipeline(m.BASE_OPTS, pools, 'season')['_aux']['dirs']

pc, dc = load('cur')
pe, de = load('e101')
assert pc == pe
def sp(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])
X = {}
for dn in ('AB', 'BA'):
    c, b = de[dn], dc[dn]
    assert c['names'] == b['names']
    assert np.allclose(c['ans'], b['ans']) and np.allclose(np.nan_to_num(c['netN'], nan=9e9), np.nan_to_num(b['netN'], nan=9e9))
    X[dn] = dict(names=c['names'], gc=np.asarray(c['cand']), gb=np.asarray(b['cand']), ansQ=np.asarray(c['ans']),
                 ansN=np.asarray(c['netN'])*np.asarray(c['mpg_ev']), hasN=~np.isnan(np.asarray(c['netN'])))

def deltas(sel):
    dN, dQ = [], []
    for dn in ('AB', 'BA'):
        x, s = X[dn], sel[dn]
        sn = s[x['hasN'][s]]
        dN.append(sp(x['gc'][sn], x['ansN'][sn]) - sp(x['gb'][sn], x['ansN'][sn]))
        dQ.append(sp(x['gc'][s], x['ansQ'][s]) - sp(x['gb'][s], x['ansQ'][s]))
    return np.mean(dN), np.mean(dQ)

full = {dn: np.arange(len(X[dn]['names'])) for dn in X}
pN, pQ = deltas(full)
master = sorted(set(X['AB']['names']) | set(X['BA']['names']))
mp = {dn: np.array([{n: i for i, n in enumerate(X[dn]['names'])}.get(n, -1) for n in master]) for dn in X}
def boot(seed, nb):
    rng = np.random.default_rng(seed); bN, bQ = [], []
    for _ in range(nb):
        ix = rng.integers(0, len(master), len(master))
        sel = {dn: mp[dn][ix][mp[dn][ix] >= 0] for dn in X}
        a, b = deltas(sel); bN.append(a); bQ.append(b)
    return [float(np.percentile(bN, 5)), float(np.percentile(bN, 95))], [float(np.percentile(bQ, 5)), float(np.percentile(bQ, 95))]
ciN, ciQ = boot(1, 2000)
ciN7, ciQ7 = boot(7, 5000)
res = {'n': {dn: len(X[dn]['names']) for dn in X}, 'nHasN': {dn: int(X[dn]['hasN'].sum()) for dn in X}, 'master': len(master),
       'c2N': {'point': float(pN), 'ci90_seed1_2000': ciN, 'ci90_seed7_5000': ciN7},
       'c2Q': {'point': float(pQ), 'ci90_seed1_2000': ciQ, 'ci90_seed7_5000': ciQ7}}
prod = json.load(open(OUT/'c2-e101.json', encoding='utf-8'))
res['producer'] = {'c2N': prod['c2N'], 'c2Q': prod['c2Q']}
(Path(__file__).parent/'a5_c2.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, indent=1))
