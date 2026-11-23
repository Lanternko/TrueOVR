"""E-307 T 臂：在不改 E-227 凍結檔的前提下加 kind。
  stats（T0 基準）＝E-227 R2-stats 41 欄
  sE／sG／sV（TE／TG／TV）＝41 欄，但 blk36 欄的值換成 AE／AG／AV（季內 z 分數；遮罩沿用原 blk36 遮罩）
  sX（TX）＝41 欄 ＋ rS、paS、gsS 3 欄（季內 z；遮罩＝有值）
E227_SRC（預設 ../E227-lineup-transformer-r2）指向 E-227 程式與 data/。"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(os.path.dirname(HERE), 'E227-lineup-transformer-r2'))
sys.path.insert(0, SRC)
import e227_common as C  # noqa: E402
import e227_model as M  # noqa: E402

REPL = {'sE': 'AE', 'sG': 'AG', 'sV': 'AV'}
XCOLS = ['rS', 'paS', 'gsS']
ARMS = {'T0': 'stats', 'TE': 'sE', 'TG': 'sG', 'TV': 'sV', 'TX': 'sX'}
BLK_J = len(C.ATTRS) + C.STATS.index('blk36')
_bf, _nf = M.base_feats, M.n_feat
_XC = {}


def n_feat(kind):
    if kind in REPL:
        return _nf('stats')
    if kind == 'sX':
        return _nf('stats') + len(XCOLS)
    return _nf(kind)


def _feat(season):
    out = {}
    with open(os.path.join(HERE, 'data', f'feat-{season}.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r['pid']] = {k: (float(v) if v != '' else None) for k, v in r.items() if k != 'pid'}
    return out


def _z(b, ext, col, need_mask=None):
    ps = [p for p in b if ext.get(p, {}).get(col) is not None and (need_mask is None or need_mask(p))]
    v = [ext[p][col] for p in ps]
    if len(v) < 10 or np.std(v) < 1e-9:
        return {}
    mu, sd = float(np.mean(v)), float(np.std(v))
    return {p: (ext[p][col] - mu) / sd for p in ps}


def base_feats(season, kind):
    if kind not in REPL and kind != 'sX':
        return _bf(season, kind)
    key = (season, kind)
    if key in _XC:
        return _XC[key]
    b = _bf(season, 'stats'); ext = _feat(season)
    if kind in REPL:
        z = _z(b, ext, REPL[kind], need_mask=lambda p: b[p][1][BLK_J] == 1.0)
        out = {}
        for p, (v, m) in b.items():
            v2, m2 = v.copy(), m.copy()
            if m[BLK_J] == 1.0:
                if p in z:
                    v2[BLK_J] = z[p]
                else:   # 新指標沒有值（不應發生）→ 遮罩
                    v2[BLK_J] = 0.0; m2[BLK_J] = 0.0
            out[p] = (v2, m2)
    else:
        zs = [_z(b, ext, c) for c in XCOLS]
        out = {}
        for p, (v, m) in b.items():
            xv = np.array([z.get(p, 0.0) for z in zs], np.float32); xm = np.array([1.0 if p in z else 0.0 for z in zs], np.float32)
            out[p] = (np.concatenate([v, xv]), np.concatenate([m, xm]))
    _XC[key] = out
    return out


M.n_feat, M.base_feats = n_feat, base_feats


def feature_names(kind):
    return C.ATTRS + C.STATS + (XCOLS if kind == 'sX' else [])
