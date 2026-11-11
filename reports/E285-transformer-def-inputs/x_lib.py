"""E-285 共用：在不改 E-227 凍結檔的前提下加一個 kind 'statsx'＝E227 'stats' 的 41 欄＋ extra-<季>.csv 的 4 欄。
E227_SRC（預設 ../E227-lineup-transformer-r2）指向 E-227 程式與 data/。import 本檔後，e227_model.tensors／n_feat／base_feats 都認得 'statsx'。"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(os.path.dirname(HERE), 'E227-lineup-transformer-r2'))
sys.path.insert(0, SRC)
import e227_common as C  # noqa: E402
import e227_model as M  # noqa: E402

XCOLS = ['mtov36', 'fOn36', 'fOff36', 'fGen36']
ARMS = {'R2-stats': 'stats', 'R2-statsX': 'statsx'}
_bf, _nf = M.base_feats, M.n_feat
_XC = {}


def n_feat(kind):
    return _nf('stats') + len(XCOLS) if kind == 'statsx' else _nf(kind)


def base_feats(season, kind):
    if kind != 'statsx':
        return _bf(season, kind)
    if season in _XC:
        return _XC[season]
    b = _bf(season, 'stats')
    ext = {}
    with open(os.path.join(HERE, 'data', f'extra-{season}.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            ext[r['pid']] = {c: (float(r[c]) if r[c] != '' else None) for c in XCOLS}
    xv = {p: np.zeros(len(XCOLS), np.float32) for p in b}; xm = {p: np.zeros(len(XCOLS), np.float32) for p in b}
    for j, c in enumerate(XCOLS):   # 同 base_feats：季內 z 分數；<10 個值或常數 → 整欄遮罩
        v = [ext[p][c] for p in b if p in ext and ext[p][c] is not None]
        if len(v) < 10 or np.std(v) < 1e-9:
            continue
        mu, sd = float(np.mean(v)), float(np.std(v))
        for p in b:
            x = ext.get(p, {}).get(c)
            if x is not None:
                xv[p][j] = (x - mu) / sd; xm[p][j] = 1.0
    out = {p: (np.concatenate([b[p][0], xv[p]]), np.concatenate([b[p][1], xm[p]])) for p in b}
    _XC[season] = out
    return out


M.n_feat, M.base_feats = n_feat, base_feats


def feature_names(kind):
    return C.ATTRS + C.STATS + (XCOLS if kind == 'statsx' else [])
