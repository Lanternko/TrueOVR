"""card／inseason 0.2.10i（R-130／R-132）：切入（drive_D）與自主創造（creationJ）拆開。開關 SPLIT_DC（預設 1；0＝完全走 0.2.10g／0.2.10h 舊路徑）。

drive → drive_D：候選出手改 E-190 errata-1 的 D 類（2pt、descriptor 含 driving、無 2ndchance／fastbreak；tip／putback／alley-oop／cutting 不算），
  其餘管線不變（量 0.5＋效率 0.5、收縮、z、合併池、尾巴）。歷史季讀 card-0.2.10c+E190-creation-jumper/work/history/pbp-drive-D-<季>.csv.gz
  （欄位與 V61 history/pbp-drive 相同），本季用 extract_classes.parse_game 的 D 列；過去季池值（E-101 合併池）換成
  card-0.2.10i/work/pool-drive-D.json（drive_pool_D.py 照 pool_data.py 重算；OLD 重現原池值 max|差| 0）。
creation → creationJ：分子＝J 類（三分、>10 呎兩分、低位／後仰／pullup…；不含 D、R 類）沒被助攻的進球＋失手×pu[cls]
  （pu＝該季 J 類同 cls 進球中沒被助攻的比例；build_drive.py 的加權），分母＝分鐘，r＝分子／分鐘×36（不再乘 1−creationDependence）。
  歷史逐場計數 card-0.2.10i/work/history/crJ-<季>.csv.gz（extract_j.py）；本季從 pbp 現算，失手權重沿用上一季（2025-26）的 pu（同 window8 drive 的慣例）。
  過去季池值＝各季單季 creationJ r（池規則同 creation：GP≥30 且 MPG≥20，poolInfo 判定）。
"""
import csv
import gzip
import importlib.util
import io
import json
import os
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ON = os.environ.get('SPLIT_DC', '1') != '0'
I10 = ROOT / 'reports/card-0.2.10i'
E190 = ROOT / 'reports/card-0.2.10c+E190-creation-jumper'
E190H = E190 / 'work/history'
CRJ_SEASONS = ('2022-23', '2023-24', '2024-25', '2025-26')
POOL_D = I10 / 'work/pool-drive-D.json'


@lru_cache(None)
def XC():
    """E-190 extract_classes（classify、parse_game）。"""
    import sys
    v61 = str(ROOT / 'reports/ovr-v61-shrink-history-2025-26')
    added = v61 not in sys.path
    if added:
        sys.path.insert(0, v61)
    try:
        s = importlib.util.spec_from_file_location('e190_extract_classes', E190 / 'extract_classes.py')
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
    finally:
        if added:
            sys.path.remove(v61)
    return m


def drive_path(path):
    """pbp-drive-<季>.csv.gz → E-190 的 D 類檔（只在 ON 時）。"""
    p = Path(path)
    if ON and p.name.startswith('pbp-drive-') and not p.name.startswith(('pbp-drive-D-', 'pbp-drive-OLD-')):
        return E190H / p.name.replace('pbp-drive-', 'pbp-drive-D-')
    return p


@lru_cache(None)
def _parsed(gid, path):
    return XC().parse_game((gid, path))


def parse_drive(args):
    """同 v61 extract_pbp.parse_game 的回傳形狀 (gid, None, drive 列)；drive 列＝D 類。"""
    gid, _, dd, _ = _parsed(str(args[0]), str(args[1]))
    return gid, None, dd


# ------------------------------------------------------------------ creationJ
def _gz(path):
    with gzip.open(path, 'rb') as fh:
        return list(csv.DictReader(io.TextIOWrapper(fh, encoding='utf-8')))


@lru_cache(None)
def crj_hist(season):
    """({(gameId, pid): [madeUn, madeAst, miss] by cls 已加權後的分子}, pu)。"""
    rows = _gz(I10 / 'work/history' / f'crJ-{season}.csv.gz')
    made, un = defaultdict(int), defaultdict(int)
    for r in rows:
        made[r['cls']] += int(r['madeUn']) + int(r['madeAst'])
        un[r['cls']] += int(r['madeUn'])
    pu = {k: un[k] / made[k] for k in made if made[k] > 0}
    n = defaultdict(float)
    for r in rows:
        n[(r['gameId'], int(r['playerId']))] += int(r['madeUn']) + int(r['miss']) * pu.get(r['cls'], 1.0)
    return dict(n), pu


def crj_game(path, pu):
    """一場 pbp → {pid: creationJ 分子}（失手權重 pu）。"""
    gid, _, _, al = _parsed(Path(path).stem, str(path))
    out = defaultdict(float)
    for pid, made, ast, typ, k, cls in al:
        if k != 'J':
            continue
        if made:
            out[pid] += 0.0 if ast else 1.0
        else:
            out[pid] += pu.get(cls, 1.0)
    return dict(out)


def crj_season_r(season, season_path):
    """單季 creationJ r：{str(pid): 分子／MIN×36}（MIN＝該季 player-games 全部列；MIN>0 者）。"""
    n, _ = crj_hist(season)
    rs = json.loads(Path(season_path).read_text(encoding='utf-8'))
    rs = rs['data']['resultSets'] if 'data' in rs else rs['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    H = rs['headers']
    iG, iP, iM = H.index('GAME_ID'), H.index('PLAYER_ID'), H.index('MIN')
    num, mins = defaultdict(float), defaultdict(float)
    for r in rs['rowSet']:
        if not r[iM]:
            continue
        p = int(r[iP])
        mins[p] += float(r[iM])
        num[p] += n.get((r[iG], p), 0.0)
    return {str(p): num[p] / mins[p] * 36 for p in mins if mins[p] > 0}


# ------------------------------------------------------------------ e175 鏈的補丁（window8 匯入時套用）
def pool_drive_D():
    return json.loads(POOL_D.read_text(encoding='utf-8'))


def season_path(s):
    return ROOT / 'data/season-source/player-games.json' if s == '2025-26' else ROOT / 'data/defense-seventh' / s / 'player-games.json'


def patch_e175(L, C):
    """L.read_gz 的 pbp-drive 換 D 類；C.load_inputs 的過去季池值：drive 換 D、加 creationJ。冪等。"""
    if not ON or getattr(L, '_split_dc', False):
        return
    orig_read, orig_load = L.read_gz, C.load_inputs

    def read_gz(path):
        return orig_read(drive_path(path))

    def load_inputs():
        inp = orig_load()
        pdD = pool_drive_D()['D']
        seas = {}
        for s, d in inp['seas'].items():
            attrs = dict(d['attrs'])
            attrs['drive'] = dict(pdD[s])
            attrs['creationJ'] = crj_season_r(s, season_path(s))
            seas[s] = {**d, 'attrs': attrs}
        inp['seas'] = seas
        return inp
    L.read_gz, C.load_inputs = read_gz, load_inputs
    L._split_dc = True
