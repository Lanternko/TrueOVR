"""E-183：AST/PASSES_MADE（conv）二項式經驗貝氏收縮。預註冊 §1。寫法同 scripts/build_season_league.js 的 fitShootingEB：
  qualified＝PASSES_MADE>=200；pbar＝qualified 的 AST 總和/PASSES_MADE 總和；varRate＝qualified 各人 conv 的母體變異（ddof=0）；
  meanInvN＝qualified 的 1/n 平均；tau2＝varRate−pbar(1−pbar)·meanInvN；k＝tau2>0 ? clip(pbar(1−pbar)/tau2−1, 50, 2000) : 500。
  mu_pos＝該季同位置（呼叫端給的 pos）以 PASSES_MADE 加權的 conv（只含有追蹤資料且有 pos 的人）。
  conv_s＝(AST + k·mu_pos)/(PASSES_MADE + k)；對不到追蹤資料者 conv_s＝mu_pos。
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'package.json').exists())
RAW = ROOT / 'reports/handle-E069/raw'


def tracking(season):
    d = json.load(open(RAW / season / 'Passing-FULL.json', encoding='utf-8'))
    rs = d['data']['resultSets'][0]
    h = rs['headers']
    ip, ia, ipm = h.index('PLAYER_ID'), h.index('AST'), h.index('PASSES_MADE')
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in rs['rowSet']:
        acc[int(r[ip])][0] += float(r[ia] or 0)
        acc[int(r[ip])][1] += float(r[ipm] or 0)
    return {p: (a, n) for p, (a, n) in acc.items()}


def fit_k(trk):
    q = [(a, n) for a, n in trk.values() if n >= 200]
    pbar = sum(a for a, n in q) / sum(n for a, n in q)
    rates = np.array([a / n for a, n in q])
    var = float(np.mean((rates - rates.mean()) ** 2))
    inv = float(np.mean([1 / n for a, n in q]))
    tau2 = var - pbar * (1 - pbar) * inv
    k = float(max(50, min(2000, pbar * (1 - pbar) / tau2 - 1))) if tau2 > 0 else 500.0
    return {'k': k, 'tau2': float(tau2), 'pbar': float(pbar), 'varRate': var, 'meanInvN': inv, 'qualifiedPlayers': len(q), 'totalPlayers': len(trk)}


def conv_shrunk(season, pids, pos):
    """pids：list；pos：{pid:位置}。回傳 (conv_s ndarray, conv_raw ndarray(NaN=對不到), info)。"""
    trk = tracking(season)
    fit = fit_k(trk)
    num, den = defaultdict(float), defaultdict(float)
    for p in pids:
        if p in trk:
            num[pos[p]] += trk[p][0]; den[pos[p]] += trk[p][1]
    mu = {g: num[g] / den[g] for g in den if den[g] > 0}
    out = np.empty(len(pids)); raw = np.full(len(pids), np.nan)
    for i, p in enumerate(pids):
        m = mu.get(pos[p], fit['pbar'])
        if p in trk:
            a, n = trk[p]
            out[i] = (a + fit['k'] * m) / (n + fit['k'])
            raw[i] = a / n if n > 0 else np.nan
        else:
            out[i] = m
    info = {**fit, 'muPos': mu, 'nPids': len(pids), 'matched': sum(p in trk for p in pids), 'unmatched': sum(p not in trk for p in pids), 'season': season}
    return out, raw, info
