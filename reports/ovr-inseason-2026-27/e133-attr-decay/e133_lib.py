"""E-133 共用函式庫（預註冊 preregistration.md；sha256 見 preregistration.sha256）。
骨架抄 e129-tl-season-step/backtest_e129.py；本檔只新增檔案，不改任何唯讀目錄。
所有子程序（本程式沒有）若有則帶 CREATE_NO_WINDOW。
"""
import csv
import hashlib
import json
import math
import pickle
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'e111-card027'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np  # noqa: E402
import backtest_e111 as E  # noqa: E402
B, BP, PA, C, SA, F, IC, V2, PW, E95 = E.B, E.BP, E.PA, E.C, E.SA, E.F, E.IC, E.V2, E.PW, E.E95
OVRPipeline, ATTRS, m = E.OVRPipeline, E.ATTRS, E.m
Kmod = B.K

E.CARDS = HERE / 'cards'
E111_DEFL = REPORT / 'e111-card027' / 'defL'
E129_DEFL = REPORT / 'e129-tl-season-step' / 'defL'
E133_DEFL = HERE / 'defL'
FORMAL_H1 = ROOT / 'reports' / 'card-0.2.5+E104-defense-pergame-decay' / 'def-L-primary.csv'
BIO_DIR = ROOT / 'data' / 'defense-seventh'

TRAIN = ['Y2', 'Y3', 'Y5', 'Y6']
TEST = ['D1', 'D2', 'D3']
ALL_RUN = TRAIN + TEST
HIST_ALL = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'D1', 'D2', 'D3']
NS = [3, 5, 10, 20]
NS82 = [3, 5, 10, 20, 82]
YOUNG_MAX = 23
S0 = {'M2-a': 0.0025, 'M2-b': 0.005, 'M2-c': 0.01}
CANDS = ['B0', 'M1', 'M2-a', 'M2-b', 'M2-c']
TIE = 0.005
PRE_SHA = None


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def wjson(path, obj):
    Path(path).write_text(json.dumps(E95.tojson(obj), ensure_ascii=False, indent=1), encoding='utf-8')


_AGE = {}


def ages_of(season):
    if season in _AGE:
        return _AGE[season]
    p = BIO_DIR / season / 'bio.json'
    out = {}
    if p.exists():
        rs = json.loads(p.read_text(encoding='utf-8'))['data']['resultSets'][0]
        h = rs['headers']
        ip, ia = h.index('PLAYER_ID'), h.index('AGE')
        for row in rs['rowSet']:
            if row[ia] is not None:
                out[int(row[ip])] = float(row[ia])
    _AGE[season] = out
    return out


# ------------------------------------------------------------------ setup
_ORIG_PRIOR = {}


def build_card027_g(season, fz_w):
    """E.build_card027 的同一配方；舊卡底改讀 PA.install() 後的 C.PRIOR_PATH（Y 季＝pathA 舊卡，直接呼叫 E-111 原函式；
    D 季＝v5 priors，E-111 的 PA_DATA 沒有這些檔）。"""
    old_path = _ORIG_PRIOR.setdefault(season, Path(C.PRIOR_PATH[season]))
    if old_path.parent == PA.PA_DATA:
        return E.build_card027(season, fz_w)
    doc = json.loads(old_path.read_text(encoding='utf-8'))
    old = {int(c['playerId']): c for c in doc['players']}
    sd = C.load_target_season(season)
    mapping = C.mapping_for(season)
    fz = E.season_fz(sd, fz_w['wVol'], fz_w['wRate'])
    saved = m.M26['foulDrawConstants']
    m.M26['foulDrawConstants'] = {k: fz[k] for k in ('vol', 'rate', 'wVol', 'wRate')}
    try:
        w = m.m26_window_cards(sd, 10 ** 4, mapping, old, {'__default__': 0.5})
    finally:
        m.M26['foulDrawConstants'] = saved
    chk = {'players': len(old), 'inWindow': 0, 'notInWindow': [], 'foulDrawFallback': [], 'sampleMismatch': 0,
           'staminaMaxAbsDiff': 0.0, 'driveMaxAbsDiff': 0.0, 'shortBaseMaxAbsDiff': 0.0}
    players = []
    for pid in sorted(old):
        c = dict(old[pid])
        rec = w.get(pid)
        if rec is None:
            chk['notInWindow'].append(pid)
            c['foulDraw'] = 40.0
            players.append(c)
            continue
        chk['inWindow'] += 1
        smp, so = rec['sample'], c['sample']
        if any(abs(float(smp[k]) - float(so[k])) > 1e-9 for k in ('fg3a', 'midA', 'shortA', 'fta', 'fga', 'min', 'gp')):
            chk['sampleMismatch'] += 1
        chk['staminaMaxAbsDiff'] = max(chk['staminaMaxAbsDiff'], abs(rec['stamina'] - float(c['stamina'])))
        chk['driveMaxAbsDiff'] = max(chk['driveMaxAbsDiff'], abs(rec['drive'] - float(c['drive'])))
        for a in E.POOLED:
            v = rec[a]
            if a == 'foulDraw' and v is None:
                v = 40.0
                chk['foulDrawFallback'].append(pid)
            c[a] = float(v)
        c['shortBase'] = float(rec['shortBase'])
        players.append(c)
    out = {'schemaVersion': 1, 'season': season, 'experiment': 'E-133',
           'note': 'E-111 同配方；D 季舊卡底＝v5 priors（C.PRIOR_PATH）', 'base': {'file': rel(old_path), 'sha256': sha(old_path)},
           'pool027PayloadSha256': m.M26['payloadSha256'], 'foulDrawSeasonZ': fz, 'pooledAttrs': E.POOLED, 'check': chk, 'players': players}
    E.CARDS.mkdir(exist_ok=True)
    path = E.CARDS / f'prior-{season}-027.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    chk['n_foulDrawFallback'] = len(chk['foulDrawFallback'])
    return path, chk, fz

def defl_src(win):
    if win == 'formal-card-H1-m0':
        return FORMAL_H1
    for d in (E133_DEFL, E129_DEFL, E111_DEFL):
        src = d / f'def-L-{win}.csv'
        if src.exists():
            return src
    raise FileNotFoundError(win)


def setup(t0, run_starts, hist_starts):
    PA.install()
    E.m.m26_load_pool(E.POOL027)
    SA.zone_of = m.m26_zone_of
    m.m27_install_zone_filter()
    IC.window_cards = m.m26_window_cards
    C.clip = m.m26_clip
    V2.FROZEN_SUMMARY = E.CARD_SUMMARY
    fz_w = json.loads(E.PRIOR027.read_text(encoding='utf-8'))['foulDrawFreeze']
    defl = {}
    for s in run_starts:
        for k in ('pred', 'ans'):
            win = C.CHAIN[s][k]
            defl[str(PA.rapm_path(win).resolve())] = str(defl_src(win))
    m.m27_install_ul(defl)
    seasons = sorted({C.CHAIN[s]['prior'] for s in hist_starts} | {C.CHAIN[s]['target'] for s in hist_starts})
    cards_info = {}
    for S in seasons:
        if S == '2025-26':      # season-cards-2022-25.json 沒有 2025-26 → 直接用 live 正式 027 卡（D3 的目標季卡）
            path = E.PRIOR027
            cards_info[S] = {'file': rel(path), 'sha256': sha(path), 'note': 'live 正式 card027 先驗卡，非 build_card027 重建'}
            C.PRIOR_PATH[S] = path
            print('card', S, 'live card027', flush=True)
            continue
        path, chk, fz = build_card027_g(S, fz_w)
        C.PRIOR_PATH[S] = path
        cards_info[S] = {'file': rel(path), 'sha256': sha(path), 'inWindow': chk['inWindow'], 'sampleMismatch': chk['sampleMismatch']}
        print('card', S, chk['inWindow'], chk['sampleMismatch'], f'{time.time() - t0:.0f}s', flush=True)
    F.CACHE.clear()
    C._PIPE_CACHE.clear()
    PW._CACHE.clear()
    for k in [k for k in C._CACHE if k[0] == 'win']:
        del C._CACHE[k]
    return defl, cards_info


# ------------------------------------------------------------------ 分年齡 δ²
def delta2_pairs(s, age_filter=None):
    """照 F.delta2_from_pairs；age_filter(pid, target_season)->bool 只限制配對的年齡組。回傳 {a: {m,V,meanS2,delta2,defined}}。"""
    rel_ = V2.load_reliability()
    out = {}
    for a in C.UPD:
        d, s2 = [], []
        for h in C.history_for_attr(s, a):
            prior = C.CHAIN[h]['prior']
            target = C.CHAIN[h]['target']
            cards, _ = F.load_prior(prior)
            tgt_cards, _ = F.load_prior(target)
            for pid, card in cards.items():
                tc = tgt_cards.get(pid)
                if tc is None:
                    continue
                if age_filter is not None and not age_filter(pid, target):
                    continue
                npv, ntv = V2.sample_n(card, a), V2.sample_n(tc, a)
                if npv < SA.PRIOR_MIN_SAMPLE[a] or ntv < SA.PRIOR_MIN_SAMPLE[a]:
                    continue
                d.append(float(tc[a]) - C.clip(float(card[a])))
                s2.append(rel_[a]['sigma2'] * (1.0 / ntv + 1.0 / npv))
        mm = len(d)
        var = float(np.var(d, ddof=1)) if mm > 1 else 0.0
        mean_s2 = float(np.mean(s2)) if mm else 0.0
        out[a] = {'m': mm, 'V': round(var, 6), 'meanS2': round(mean_s2, 6),
                  'delta2': round(max(0.0, var - mean_s2), 6), 'defined': mm > 1}
    return out


def is_young(pid, target):
    ag = ages_of(target)
    return pid in ag and ag[pid] <= YOUNG_MAX


def is_vet(pid, target):
    ag = ages_of(target)
    return pid in ag and ag[pid] >= YOUNG_MAX + 1
