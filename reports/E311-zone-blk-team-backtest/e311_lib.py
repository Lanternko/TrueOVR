"""E-311 共用：四臂的特徵種類，不改任何凍結檔。
  B ＝ stats（E-227 R2-stats 41 欄）
  Z2＝ statsz2（E-309 z_lib：41 欄＋rimDet＋threeDet）
  TG＝ sG（E-307 x_lib：41 欄，blk36 欄換成 AG＝有效蓋帽扣干擾）
  ZG＝ zg（TG 的 41 欄＋rimDet＋threeDet；本實驗新組合）
E-307 的 x_lib 和 E-285 的 x_lib 同名，用 importlib 以 x307 名稱載入。"""
import importlib.util, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REP, 'E309-zone-deterrence'))
import z_lib as Z  # noqa: E402  先 patch e227_model（statsz2）
_sp = importlib.util.spec_from_file_location('x307', os.path.join(REP, 'E307-blk-quality', 'x_lib.py'))
X7 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(X7)   # 再 patch（sG），其他 kind 交回 z_lib
import e227_model as M  # noqa: E402
sys.path.insert(0, os.path.join(REP, 'E228-transformer-team-rating'))
import t_lib as T  # noqa: E402
import torch  # noqa: E402
from e227_model import LineupNet  # noqa: E402

KIND = {'B': 'stats', 'Z2': 'statsz2', 'TG': 'sG', 'ZG': 'zg'}
_bf, _nf = M.base_feats, M.n_feat
_C = {}


def n_feat(kind):
    return _nf('stats') + 2 if kind == 'zg' else _nf(kind)


def base_feats(season, kind):
    if kind != 'zg':
        return _bf(season, kind)
    if season not in _C:
        g, z = _bf(season, 'sG'), _bf(season, 'statsz2'); k = _nf('stats')
        assert set(g) == set(z)
        _C[season] = {p: (np.concatenate([g[p][0], z[p][0][k:]]), np.concatenate([g[p][1], z[p][1][k:]])) for p in g}
    return _C[season]


M.n_feat, M.base_feats = n_feat, base_feats


def use_kind(kind):
    T.KIND = kind; T.F = n_feat(kind)


def ctx(arm, wpat, prior, dev='cpu'):
    """E-286 x286.ctx 同邏輯。"""
    import csv, gzip
    use_kind(KIND[arm])
    C = T.Ctx.__new__(T.Ctx)
    C.dev = dev; C.nets = []
    for sd in range(5):
        n = LineupNet(T.F); n.load_state_dict(torch.load(wpat.format(sd), map_location='cpu')); n.eval(); C.nets.append(n.to(dev))
    C.tab = T.load_player_table(prior); C.B = base_feats(prior, KIND[arm])
    C.med_h = float(np.median([d['heightInches'] for d in C.tab.values() if d.get('heightInches') is not None]))
    poss = 0.0; gids = set()
    with gzip.open(os.path.join(T.E227, 'data', f'stints-train-{prior}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['possa'] != '' and r['possb'] != '':
                poss += float(r['possa']) + float(r['possb']); gids.add(r['gid'])
    C.avg_poss = poss / 2 / len(gids)
    return C
