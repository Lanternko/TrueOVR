"""E-334 線上滾動多任務球員 OVR 融合模組（13 季 L=40 豐富序列 + 多季衰減 EPM 先驗，15 模型集成）。
在 run_c4_live_rookie.py 合併老將與新秀、套完 mixBonus 與 formBonus 後呼叫：
  - 嚴格因果：只讀 GAME_DATE <= cutoff 的 2026-27 player-games / team-games
  - 讀 reports/E334-player-super-ens/e334_live_cache.npz + weights_prod/*.pt（CPU < 2 秒）
  - 計算 E-334 滾動分數（0.30*z(gmsc) + 0.70*z(epm)），對齊現役名單 OVR 均值與標準差後，
    依本季上場分鐘數平滑融合 w = 0.45 * min(1, (MIN26 + 150) / 450)（N=0 不動）。
  - 回退開關：E334_OVR=0 完全停用，還原舊 OVR。"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
E334_DIR = ROOT / 'reports/E334-player-super-ens'
CACHE_NPZ = E334_DIR / 'e334_live_cache.npz'
FAM_STATS_JSON = E334_DIR / 'e334_fam_stats.json'
WEIGHTS_DIR = E334_DIR / 'weights_prod'
DOB_JSON = ROOT / 'data/defense-seventh/2026-27/birthdates.json'

ROOK_PRIOR = np.array([9.5, 13.0, 3.0, 1.3, 4.2, 1.0, 0.6, 2.0, 3.0, 1.2, 3.5, -1.5, -1.0, 0.54], dtype=np.float32)

_MEMO = {}


def _load_resources():
    if 'ready' in _MEMO:
        return _MEMO
    if str(E334_DIR) not in sys.path:
        sys.path.insert(0, str(E334_DIR))
    import train_e334_prod as E334

    c = np.load(CACHE_NPZ)
    pids = c['pids']
    pid_to_i = {int(p): i for i, p in enumerate(pids)}
    fam_stats = json.loads(FAM_STATS_JSON.read_text(encoding='utf-8'))

    dob = {}
    if DOB_JSON.exists():
        bd = json.loads(DOB_JSON.read_text(encoding='utf-8'))
        for pid, s in (bd.get('birthdates', bd) if isinstance(bd, dict) else {}).items():
            if isinstance(s, str) and len(s) >= 4:
                try:
                    dob[int(pid)] = int(s[:4])
                except ValueError:
                    pass

    fams = ['DecayResNet', 'DecaySwiGLU', 'DecayTCNMix']
    models = {}
    for fam in fams:
        ms = []
        for s in range(5):
            m = E334.make_model(fam, 18, 47, 40)
            m.load_state_dict(torch.load(WEIGHTS_DIR / f'{fam}_s{s}.pt', map_location='cpu'))
            m.eval()
            ms.append(m)
        models[fam] = ms

    _MEMO.update(
        ready=True,
        mu=c['mu'].astype(np.float32),
        sd=c['sd'].astype(np.float32),
        pid_to_i=pid_to_i,
        prior_vec=c['prior_vec'],
        prior_meta=c['prior_meta'],
        epm_pf=c['epm_pf'],
        seq_vals=c['seq_vals'],
        seq_ords=c['seq_ords'],
        seq_len=c['seq_len'],
        fam_stats=fam_stats,
        models=models,
        dob=dob,
    )
    return _MEMO


def _load_rs(path: Path):
    d = json.loads(path.read_text(encoding='utf-8'))
    d = d.get('data', d)
    rs = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return [dict(zip(rs['headers'], r)) for r in rs['rowSet']]


def _parse_min(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if ':' in v:
        a, b = v.split(':')
        return int(a) + int(b) / 60.0
    return float(v)


def _gmsc(r):
    pts = float(r.get('PTS') or 0); fgm = float(r.get('FGM') or 0); fga = float(r.get('FGA') or 0)
    ftm = float(r.get('FTM') or 0); fta = float(r.get('FTA') or 0)
    orb = float(r.get('OREB') or 0); drb = float(r.get('DREB') or 0)
    stl = float(r.get('STL') or 0); ast = float(r.get('AST') or 0)
    blk = float(r.get('BLK') or 0); pf = float(r.get('PF') or 0); tov = float(r.get('TOV') or 0)
    return pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm) + 0.7 * orb + 0.3 * drb + stl + 0.7 * ast + 0.7 * blk - 0.4 * pf - tov


def apply(merged: list[dict], r1, data26_dir: Path, cutoff: str | None = None) -> dict | None:
    """原地更新 merged 中每位 N>0 球員的 _ovr / ovr / dOVR / e334Bonus。回傳明細 dict 供記錄。"""
    if os.environ.get('E334_OVR', '1') == '0':
        return None
    if not (CACHE_NPZ.exists() and FAM_STATS_JSON.exists() and WEIGHTS_DIR.is_dir()):
        return None

    res = _load_resources()
    torch.set_num_threads(min(4, os.cpu_count() or 2))

    # 讀本季 2026-27 比賽（嚴格 <= cutoff）
    trows = _load_rs(data26_dir / 'team-games.json')
    prows = _load_rs(data26_dir / 'player-games.json')

    t_parsed, g_teams, g_margin = [], defaultdict(list), {}
    max_d_ord = 0
    for r in trows:
        dstr = str(r['GAME_DATE'])[:10]
        if cutoff and dstr > cutoff:
            continue
        try:
            d_ord = dt.date.fromisoformat(dstr).toordinal()
        except ValueError:
            continue
        if d_ord > max_d_ord:
            max_d_ord = d_ord
        gid = str(r['GAME_ID']); tid = int(r['TEAM_ID']); tm = float(r.get('PLUS_MINUS') or 0)
        g_margin[(gid, tid)] = tm
        g_teams[gid].append(tid)
        t_parsed.append((d_ord, gid, tid, tm))

    t_parsed.sort(key=lambda x: (x[0], x[1]))
    t_sum, t_cnt, pre_net = defaultdict(float), defaultdict(int), {}
    by_day = defaultdict(list)
    for x in t_parsed:
        by_day[x[0]].append(x)
    for day in sorted(by_day):
        for d_ord, gid, tid, tm in by_day[day]:
            pre_net[(gid, tid)] = t_sum[tid] / (t_cnt[tid] + 8.0)
        for d_ord, gid, tid, tm in by_day[day]:
            t_sum[tid] += tm; t_cnt[tid] += 1
    opp_of = {}
    for gid, tids in g_teams.items():
        if len(tids) == 2:
            opp_of[(gid, tids[0])] = tids[1]; opp_of[(gid, tids[1])] = tids[0]

    by_pid = defaultdict(list)
    for r in prows:
        dstr = str(r['GAME_DATE'])[:10]
        if cutoff and dstr > cutoff:
            continue
        mn = _parse_min(r.get('MIN'))
        if mn <= 0:
            continue
        try:
            d_ord = dt.date.fromisoformat(dstr).toordinal()
        except ValueError:
            continue
        pid = int(r['PLAYER_ID']); gid = str(r['GAME_ID']); tid = int(r['TEAM_ID'])
        gs = _gmsc(r)
        pts = float(r.get('PTS') or 0); ast = float(r.get('AST') or 0)
        orb = float(r.get('OREB') or 0); drb = float(r.get('DREB') or 0)
        stl = float(r.get('STL') or 0); blk = float(r.get('BLK') or 0)
        tov = float(r.get('TOV') or 0); pf_ = float(r.get('PF') or 0)
        fga = float(r.get('FGA') or 0); fta = float(r.get('FTA') or 0)
        fg3m = float(r.get('FG3M') or 0); fg3a = float(r.get('FG3A') or 0)
        pm = float(r.get('PLUS_MINUS') or 0)
        tm = g_margin.get((gid, tid), 0.0)
        on_off = pm - tm * (mn / 48.0)
        opp_tid = opp_of.get((gid, tid))
        opp_net = pre_net.get((gid, opp_tid), 0.0) if opp_tid is not None else 0.0
        by_pid[pid].append((d_ord, gid, mn, gs, pts, ast, orb, drb, stl, blk, tov, pf_, fga, fta, fg3m, fg3a, pm, on_off, opp_net))

    ref_ord = (dt.date.fromisoformat(cutoff).toordinal() + 1) if cutoff else (max_d_ord + 1)

    active_rows = [r for r in merged if int(r.get('N') or 0) > 0]
    if not active_rows:
        return None

    pid_to_i = res['pid_to_i']
    dob = res['dob']
    N_act = len(active_rows)
    stat_mat = np.zeros((N_act, 47), dtype=np.float32)
    seq_mat = np.zeros((N_act, 40, 18), dtype=np.float32)

    for idx_r, r in enumerate(active_rows):
        pid = int(r['playerId'])
        ci = pid_to_i.get(pid)
        if ci is not None:
            prior_vec = res['prior_vec'][ci]
            prior_mpg, has_p, pw = res['prior_meta'][ci]
            epm_pf = res['epm_pf'][ci]
            h_len = int(res['seq_len'][ci])
            cseq = [(int(res['seq_ords'][ci, k]), res['seq_vals'][ci, k]) for k in range(h_len)]
        else:
            prior_vec = ROOK_PRIOR
            prior_mpg, has_p, pw = 18.0, 0.0, 0.0
            epm_pf = np.zeros(10, dtype=np.float32)
            cseq = []

        pseq = sorted(by_pid.get(pid, []), key=lambda x: (x[0], x[1]))
        c_min = 0.0; c_acc = np.zeros(15, np.float64)
        for row in pseq:
            (d_ord, gid, mn, gs, pts, ast, orb, drb, stl, blk, tov, pf_, fga, fta, fg3m, fg3a, pm, on_off, opp_net) = row
            c_min += mn
            c_acc += np.array([gs, pts, ast, orb, drb, stl, blk, tov, pf_, fg3m, fg3a, pm, on_off, fga, fta], np.float64)
            dts_g = 2.0 * (fga + 0.44 * fta)
            ts_g = (pts / dts_g) if dts_g > 0 else 0.55
            gv = np.array([
                mn / 36.0, gs / 15.0, pts / 20.0, ast / 6.0, orb / 3.0, drb / 7.0,
                stl / 2.0, blk / 2.0, tov / 3.0, pf_ / 4.0, fg3m / 3.0, fg3a / 7.0,
                ts_g - 0.55, pm / 15.0, on_off / 12.0, opp_net / 10.0,
            ], dtype=np.float32)
            cseq.append((d_ord, gv))

        if c_min > 0:
            f36 = 36.0 / c_min
            c_dts = 2.0 * (c_acc[13] + 0.44 * c_acc[14])
            c_ts = (c_acc[1] / c_dts) if c_dts > 0 else 0.55
            cur_v = np.concatenate([c_acc[:13] * f36, [c_ts]]).astype(np.float32)
            cur_mpg = c_min / max(1, len(pseq))
        else:
            cur_v = prior_vec.copy(); cur_mpg = prior_mpg

        age = float(2026 - dob[pid]) if pid in dob else 25.0
        a_std = (age - 25.5) / 4.0
        stat_37 = np.concatenate([
            prior_vec, cur_v,
            [prior_mpg / 36.0, cur_mpg / 36.0, has_p, pw / 10.0,
             math.log1p(c_min) / 8.0, float(len(pseq)) / 82.0,
             a_std, a_std * a_std, 0.0],
        ]).astype(np.float32)
        stat_mat[idx_r, :37] = stat_37
        stat_mat[idx_r, 37:] = epm_pf

        recent = cseq[-40:]
        off = 40 - len(recent)
        for k, (pd_ord, gv) in enumerate(recent):
            dt_days = min(180.0, max(1.0, float(ref_ord - pd_ord)))
            seq_mat[idx_r, off + k, :16] = gv
            seq_mat[idx_r, off + k, 16] = math.log1p(dt_days) / 5.0
            seq_mat[idx_r, off + k, 17] = 1.0

    stat_n = np.clip((stat_mat - res['mu'][None, :]) / res['sd'][None, :], -6.0, 6.0)
    sq_t = torch.from_numpy(seq_mat)
    st_t = torch.from_numpy(stat_n)

    fam_g, fam_e = [], []
    with torch.no_grad():
        for fam, ms in res['models'].items():
            outs = np.mean([m(sq_t, st_t).numpy() for m in ms], axis=0)
            fs = res['fam_stats'][fam]
            fam_g.append((outs[:, 0] - fs['g_mu']) / fs['g_sd'])
            fam_e.append((outs[:, 1] - fs['e_mu']) / fs['e_sd'])

    z_g = np.mean(fam_g, axis=0)
    z_e = np.mean(fam_e, axis=0)
    # E-332/E-334 verified wE70 balanced impact + performance score
    z_e334 = 0.30 * z_g + 0.70 * z_e

    # Scale-match z_e334 to current active pool OVR distribution so 0-99 scale & top stars stay natural
    cur_ovrs = np.array([float(r['_ovr']) for r in active_rows], dtype=np.float64)
    ovr_mu = float(cur_ovrs.mean())
    ovr_sd = float(cur_ovrs.std() + 1e-6)
    e_mu = float(z_e334.mean())
    e_sd = float(z_e334.std() + 1e-6)
    e334_ovr = ovr_mu + (z_e334 - e_mu) / e_sd * ovr_sd

    w_max = float(os.environ.get('E334_W', '0.45'))
    details = {}
    for idx_r, r in enumerate(active_rows):
        old_o = float(r['_ovr'])
        mn26 = float(r.get('MIN26') or 0.0)
        w = w_max * min(1.0, (mn26 + 150.0) / 450.0)
        new_o = max(40.0, (1.0 - w) * old_o + w * float(e334_ovr[idx_r]))
        r['_ovr'] = new_o
        r['ovr'] = r1(new_o)
        if r.get('lastOVR') not in (None, ''):
            r['dOVR'] = round(new_o - float(r['lastOVR']), 2)
        bonus = round(new_o - old_o, 2)
        r['e334Bonus'] = bonus
        details[str(r['playerId'])] = {'old': round(old_o, 2), 'e334': round(float(e334_ovr[idx_r]), 2), 'w': round(w, 3), 'bonus': bonus}

    for r in merged:
        if 'e334Bonus' not in r:
            r['e334Bonus'] = 0.0
    return details
