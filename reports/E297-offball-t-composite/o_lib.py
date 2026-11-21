"""E-297 共用：不改 E-227 凍結檔，加 kind 'ob:<欄+欄>'＝R2-stats 41 欄＋指定無球欄（data/offball-<季>.csv，季內 z，<10 值或常數整欄遮罩）。
臂名：'base'（kind 'stats'）、'+<欄>'、'ALL'、'SEL'（欄由 results/sel.json 讀）。"""
import csv, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.join(os.path.dirname(HERE), 'E227-lineup-transformer-r2'))
sys.path.insert(0, SRC)
import e227_common as C  # noqa: E402
import e227_model as M  # noqa: E402

OB = ['cut36', 'cutPPP', 'offScr36', 'handoff36', 'spotup36', 'roll36', 'putback36', 'trans36', 'distOff36', 'speedOff', 'cs3a36', 'cs3pct']
_bf, _nf = M.base_feats, M.n_feat
_RAW, _XC = {}, {}


def cols_of(kind):
    return kind[3:].split('+') if kind.startswith('ob:') and len(kind) > 3 else []


def arm_cols(arm):
    if arm == 'base':
        return []
    if arm == 'ALL':
        return list(OB)
    if arm == 'SEL':
        return json.load(open(os.path.join(HERE, 'results', 'sel.json'), encoding='utf-8'))['selected']
    if arm.startswith('+'):
        return arm[1:].split('+')
    raise KeyError(arm)


def kind_of(arm):
    c = arm_cols(arm)
    return 'ob:' + '+'.join(c) if c else 'stats'


def raw(season):
    if season not in _RAW:
        d = {}
        with open(os.path.join(HERE, 'data', f'offball-{season}.csv'), encoding='utf-8') as f:
            for r in csv.DictReader(f):
                d[r['pid']] = {c: (float(r[c]) if r[c] != '' else None) for c in OB}
        _RAW[season] = d
    return _RAW[season]


def n_feat(kind):
    return _nf('stats') + len(cols_of(kind)) if kind.startswith('ob:') else _nf(kind)


def base_feats(season, kind):
    if not kind.startswith('ob:'):
        return _bf(season, kind)
    if (season, kind) in _XC:
        return _XC[(season, kind)]
    b = _bf(season, 'stats'); ext = raw(season); cols = cols_of(kind)
    xv = {p: np.zeros(len(cols), np.float32) for p in b}; xm = {p: np.zeros(len(cols), np.float32) for p in b}
    for j, c in enumerate(cols):
        v = [ext[p][c] for p in b if p in ext and ext[p][c] is not None]
        if len(v) < 10 or np.std(v) < 1e-9:
            continue
        mu, sd = float(np.mean(v)), float(np.std(v))
        for p in b:
            x = ext.get(p, {}).get(c)
            if x is not None:
                xv[p][j] = (x - mu) / sd; xm[p][j] = 1.0
    out = {p: (np.concatenate([b[p][0], xv[p]]), np.concatenate([b[p][1], xm[p]])) for p in b}
    _XC[(season, kind)] = out
    return out


M.n_feat, M.base_feats = n_feat, base_feats


def feature_names(kind):
    return C.ATTRS + C.STATS + cols_of(kind)
