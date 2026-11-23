"""E-309 共用：照 E-285 x_lib 的做法，不改 E-227 凍結檔，加 kind 'statsz'（41 欄＋rimDet）與 'statsz2'（＋rimDet＋threeDet）。
值來自 data/rimdet-T-<季>.csv（build_rimdet.py；四季窗含當季、排除 E-225 測試場次）；2021-22 沒有分區 stints → 整欄遮罩。
季內 z 分數、缺值遮罩，同 x_lib。"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(os.path.dirname(HERE), 'E227-lineup-transformer-r2'))
sys.path.insert(0, SRC)
import e227_common as C  # noqa: E402
import e227_model as M  # noqa: E402

ZCOLS = {'statsz': ['rimDet'], 'statsz2': ['rimDet', 'threeDet']}
ARMS = {'R2-stats': 'stats', 'R2-statsZ': 'statsz', 'R2-statsZ2': 'statsz2'}
_bf, _nf = M.base_feats, M.n_feat
_XC = {}


def n_feat(kind):
    return _nf('stats') + len(ZCOLS[kind]) if kind in ZCOLS else _nf(kind)


def base_feats(season, kind):
    if kind not in ZCOLS:
        return _bf(season, kind)
    if (season, kind) in _XC:
        return _XC[season, kind]
    cols = ZCOLS[kind]; b = _bf(season, 'stats'); ext = {}
    f = os.path.join(HERE, 'data', f'rimdet-T-{season}.csv')
    if os.path.exists(f):
        with open(f, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                ext[r['pid']] = {c: float(r[c]) for c in cols}
    xv = {p: np.zeros(len(cols), np.float32) for p in b}; xm = {p: np.zeros(len(cols), np.float32) for p in b}
    for j, c in enumerate(cols):
        v = [ext[p][c] for p in b if p in ext]
        if len(v) < 10 or np.std(v) < 1e-9:
            continue
        mu, sd = float(np.mean(v)), float(np.std(v))
        for p in b:
            if p in ext:
                xv[p][j] = (ext[p][c] - mu) / sd; xm[p][j] = 1.0
    out = {p: (np.concatenate([b[p][0], xv[p]]), np.concatenate([b[p][1], xm[p]])) for p in b}
    _XC[season, kind] = out
    return out


M.n_feat, M.base_feats = n_feat, base_feats


def feature_names(kind):
    return C.ATTRS + C.STATS + ZCOLS.get(kind, [])
