"""建置 E-334 線上每日推論快取（e334_live_cache.npz）：
預先封裝 2014-15～2025-26 歷史底盤、多季衰減 EPM 先驗、過去 ≤40 場生涯序列與訓練集標準化常數 (mu, sd) 及驗證集輸出縮放常數，
讓每日 live 推論只需讀 2026-27 本季 gamelog，CPU < 2 秒完成全聯盟 15 模型推論。"""
import csv, datetime as dt, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'reports/E334-player-super-ens'))
sys.path.insert(0, str(ROOT / 'reports/E324-player-seq40-rich'))
import train_e334_prod as E334
import build_e324_seq40 as B324


def main():
    out_dir = ROOT / 'reports/E334-player-super-ens'
    e335_wdir = ROOT / 'reports/E335-player-structural-fix/weights_prod'
    wdir = e335_wdir if e335_wdir.is_dir() else (out_dir / 'weights_prod')
    epm_dir = ROOT / 'data/external-impact/epm_self'

    # 1. Exact train mu/sd from p1_seq40_rich.npz (s_idx 1..10, matching E-335 softened age + decay=0.35, k=1000!)
    d = np.load(ROOT / 'reports/E324-player-seq40-rich/data/p1_seq40_rich.npz')
    stat_raw = d['stat'].astype(np.float32); seq = d['seq'].astype(np.float32); meta = d['meta']
    a_std = stat_raw[:, -3]
    a_soft = np.minimum(a_std, 2.125) + 0.35 * np.maximum(0.0, a_std - 2.125)
    stat_raw[:, -3] = a_soft
    stat_raw[:, -2] = np.minimum(a_soft * a_soft, 4.5)
    by_s = E334.load_epm_all(str(epm_dir))
    sys.path.insert(0, str(ROOT / 'reports/E335-player-structural-fix'))
    import e335_train as E335
    _, _, _, _, _, _, pf = E335.build_multiepm_features(by_s, meta, stat_raw, decay=0.35)
    stat_full = np.concatenate([stat_raw, pf], axis=1)  # 47 dims
    tr_mask = (meta[:, 0] >= 1) & (meta[:, 0] <= 10)
    va_mask = (meta[:, 0] == 11)
    mu = stat_full[tr_mask].mean(axis=0).astype(np.float32)
    sd = (stat_full[tr_mask].std(axis=0) + 1e-6).astype(np.float32)
    stat_va_n = np.clip((stat_full[va_mask] - mu[None, :]) / sd[None, :], -6.0, 6.0)
    seq_va = seq[va_mask]

    # Compute exact validation output mean/std per family for z-score ensembling
    fams = ['DecayResNet', 'DecaySwiGLU', 'DecayTCNMix']
    fam_stats = {}
    for fam in fams:
        preds = []
        for s in range(5):
            m = E334.make_model(fam, seq_va.shape[-1], stat_va_n.shape[-1], seq_va.shape[1])
            m.load_state_dict(torch.load(wdir / f'{fam}_s{s}.pt', map_location='cpu'))
            m.eval()
            preds.append(E334.predict_arr(m, seq_va, stat_va_n, 'cpu'))
        p_fam = np.mean(preds, axis=0)
        fam_stats[fam] = {
            'g_mu': float(p_fam[:, 0].mean()), 'g_sd': float(p_fam[:, 0].std() + 1e-8),
            'e_mu': float(p_fam[:, 1].mean()), 'e_sd': float(p_fam[:, 1].std() + 1e-8),
        }
    print('Computed fam_stats:', fam_stats)

    # 2. Build end-of-2025-26 historical career state for every NBA player (s_idx 0..11, strictly BEFORE 2026-27!)
    dob = {}
    bd_path = ROOT / 'data/defense-seventh/2026-27/birthdates.json'
    if bd_path.exists():
        bd = json.load(open(bd_path, encoding='utf-8'))
        for pid, s in (bd.get('birthdates', bd) if isinstance(bd, dict) else {}).items():
            if isinstance(s, str) and len(s) >= 4:
                try: dob[int(pid)] = int(s[:4])
                except ValueError: pass

    hist_seasons = defaultdict(list)
    career_seq = defaultdict(list)
    # Process seasons 0..11 (2014-15 ~ 2025-26)
    for s_idx, (sname, sdir) in enumerate(B324.SEASONS[:12]):
        prows = B324.load_rs(sdir / 'player-games.json')
        trows = B324.load_rs(sdir / 'team-games.json')
        t_parsed, g_teams, g_info = [], defaultdict(list), {}
        for r in trows:
            gid = str(r['GAME_ID']); tid = int(r['TEAM_ID']); m = str(r.get('MATCHUP') or '')
            try: d_ord = dt.date.fromisoformat(str(r['GAME_DATE'])[:10]).toordinal()
            except ValueError: continue
            tm = float(r.get('PLUS_MINUS') or 0)
            g_info[(gid, tid)] = (1 if r.get('WL') == 'W' else 0, 1 if ' vs. ' in m else 0, tm)
            g_teams[gid].append(tid); t_parsed.append((d_ord, gid, tid, tm))
        t_parsed.sort(key=lambda x: (x[0], x[1]))
        t_sum, t_cnt, pre_net = defaultdict(float), defaultdict(int), {}
        by_day = defaultdict(list)
        for x in t_parsed: by_day[x[0]].append(x)
        for day in sorted(by_day):
            for d_ord, gid, tid, tm in by_day[day]: pre_net[(gid, tid)] = t_sum[tid] / (t_cnt[tid] + 8.0)
            for d_ord, gid, tid, tm in by_day[day]: t_sum[tid] += tm; t_cnt[tid] += 1
        opp_of = {}
        for gid, tids in g_teams.items():
            if len(tids) == 2: opp_of[(gid, tids[0])] = tids[1]; opp_of[(gid, tids[1])] = tids[0]

        by_pid = defaultdict(list)
        for r in prows:
            mn = B324.parse_min(r.get('MIN'))
            if mn <= 0: continue
            pid = int(r['PLAYER_ID']); gid = str(r['GAME_ID']); tid = int(r['TEAM_ID'])
            try: d_ord = dt.date.fromisoformat(str(r['GAME_DATE'])[:10]).toordinal()
            except ValueError: continue
            gs = B324.gmsc_of(r)
            pts = float(r.get('PTS') or 0); ast = float(r.get('AST') or 0)
            orb = float(r.get('OREB') or 0); drb = float(r.get('DREB') or 0)
            stl = float(r.get('STL') or 0); blk = float(r.get('BLK') or 0)
            tov = float(r.get('TOV') or 0); pf_ = float(r.get('PF') or 0)
            fga = float(r.get('FGA') or 0); fta = float(r.get('FTA') or 0)
            fg3m = float(r.get('FG3M') or 0); fg3a = float(r.get('FG3A') or 0)
            pm = float(r.get('PLUS_MINUS') or 0)
            tm = g_info.get((gid, tid), (0, 0, 0.0))[2]
            on_off = pm - tm * (mn / 48.0)
            opp_tid = opp_of.get((gid, tid))
            opp_net = pre_net.get((gid, opp_tid), 0.0) if opp_tid is not None else 0.0
            by_pid[pid].append((d_ord, gid, tid, mn, gs, pts, ast, orb, drb, stl, blk, tov, pf_, fga, fta, fg3m, fg3a, pm, on_off, opp_net))

        for pid, pseq in by_pid.items():
            pseq.sort(key=lambda x: (x[0], x[1]))
            for row in pseq:
                (d_ord, gid, tid, mn, gs, pts, ast, orb, drb, stl, blk, tov, pf_, fga, fta, fg3m, fg3a, pm, on_off, opp_net) = row
                dts_g = 2.0 * (fga + 0.44 * fta)
                ts_g = (pts / dts_g) if dts_g > 0 else 0.55
                gv = np.array([
                    mn / 36.0, gs / 15.0, pts / 20.0, ast / 6.0, orb / 3.0, drb / 7.0,
                    stl / 2.0, blk / 2.0, tov / 3.0, pf_ / 4.0, fg3m / 3.0, fg3a / 7.0,
                    ts_g - 0.55, pm / 15.0, on_off / 12.0, opp_net / 10.0,
                ], dtype=np.float32)
                career_seq[pid].append((d_ord, gv))
            career_seq[pid] = career_seq[pid][-40:]
            m_t = sum(x[3] for x in pseq)
            if m_t <= 0: continue
            gp_t = len(pseq); f36 = 36.0 / m_t
            fga_t = sum(x[13] for x in pseq); fta_t = sum(x[14] for x in pseq); pts_t = sum(x[5] for x in pseq)
            ts_t = pts_t / (2.0 * (fga_t + 0.44 * fta_t)) if (fga_t + 0.44 * fta_t) > 0 else 0.55
            vec14 = np.array([
                sum(x[4] for x in pseq)*f36, pts_t*f36, sum(x[6] for x in pseq)*f36,
                sum(x[7] for x in pseq)*f36, sum(x[8] for x in pseq)*f36, sum(x[9] for x in pseq)*f36,
                sum(x[10] for x in pseq)*f36, sum(x[11] for x in pseq)*f36, sum(x[12] for x in pseq)*f36,
                sum(x[15] for x in pseq)*f36, sum(x[16] for x in pseq)*f36, sum(x[17] for x in pseq)*f36,
                sum(x[18] for x in pseq)*f36, ts_t,
            ], dtype=np.float64)
            hist_seasons[pid].append((s_idx, m_t, gp_t, vec14))

    # Precompute 2026-27 (s_idx=12) prior_vec, prior_mpg, has_p, pw, epm_pf[10], and last-40 career_seq for all players!
    DEF_PRIOR = np.array([10.5, 14.0, 3.5, 1.4, 4.6, 1.0, 0.7, 2.0, 2.8, 1.4, 3.9, 0.0, 0.0, 0.56])
    s_idx_26 = 12
    all_pids = sorted(set(hist_seasons) | set(career_seq))
    p_prior_vec = np.zeros((len(all_pids), 14), np.float32)
    p_prior_meta = np.zeros((len(all_pids), 3), np.float32)  # prior_mpg, has_p, pw
    p_epm_pf = np.zeros((len(all_pids), 10), np.float32)
    p_seq_vals = np.zeros((len(all_pids), 40, 16), np.float32)
    p_seq_ords = np.zeros((len(all_pids), 40), np.int32)
    p_seq_len = np.zeros(len(all_pids), np.int32)

    for idx_p, pid in enumerate(all_pids):
        hs = hist_seasons.get(pid, [])
        if hs:
            w_tot = 0.0; acc = np.zeros(14, np.float64); mn_n = 0.0; mn_d = 0.0
            for (si, m_t, gp_t, vec14) in hs:
                w = m_t * (0.55 ** (s_idx_26 - 1 - si))
                acc += w * vec14; w_tot += w
                wg = gp_t * (0.55 ** (s_idx_26 - 1 - si)); mn_n += wg * (m_t / max(1, gp_t)); mn_d += wg
            p_prior_vec[idx_p] = (acc + 300.0 * DEF_PRIOR) / (w_tot + 300.0)
            p_prior_meta[idx_p] = [mn_n / max(1e-6, mn_d), 1.0, math.log1p(w_tot)]
        # Multi-season decayed EPM prior for s_idx=12 (E-335: decay=0.35, k=1000, softened age!)
        a_raw = (float(2026 - dob[pid]) - 25.5) / 4.0 if pid in dob else -0.125
        age_z = min(a_raw, 2.125) + 0.35 * max(0.0, a_raw - 2.125)
        w_sum = 0.0; ao = 0.0; ad = 0.0; an = 0.0; mx_n = -10.0; prev_vals = []
        for dt_ in range(1, 5):
            rec = by_s.get(s_idx_26 - dt_, {}).get(pid)
            if rec is not None:
                w = rec[3] * (0.35 ** (dt_ - 1))
                ao += w * rec[0]; ad += w * rec[1]; an += w * rec[2]; w_sum += w
                if rec[2] > mx_n: mx_n = rec[2]
                prev_vals.append((dt_, rec[2]))
        if w_sum > 0:
            mo = (ao - 0.5 * 1000.0) / (w_sum + 1000.0); md = (ad - 0.5 * 1000.0) / (w_sum + 1000.0)
            mn_ = (an - 1.0 * 1000.0) / (w_sum + 1000.0)
            last1 = prev_vals[0][1] if prev_vals[0][0] == 1 else mn_
            has_l1 = 1.0 if prev_vals[0][0] == 1 else 0.0
            trend = (prev_vals[0][1] - prev_vals[1][1]) if len(prev_vals) >= 2 else 0.0
            p_epm_pf[idx_p] = [mo / 5.0, md / 5.0, mn_ / 5.0, math.log1p(w_sum) / 10.0,
                               last1 / 5.0, has_l1, trend / 5.0, mx_n / 5.0, (age_z * mn_) / 5.0, 1.0]
        cseq = career_seq.get(pid, [])[-40:]
        p_seq_len[idx_p] = len(cseq)
        for k, (d_ord, gv) in enumerate(cseq):
            p_seq_ords[idx_p, k] = d_ord; p_seq_vals[idx_p, k] = gv

    np.savez_compressed(
        out_dir / 'e334_live_cache.npz',
        mu=mu, sd=sd,
        pids=np.array(all_pids, np.int64),
        prior_vec=p_prior_vec, prior_meta=p_prior_meta, epm_pf=p_epm_pf,
        seq_vals=p_seq_vals, seq_ords=p_seq_ords, seq_len=p_seq_len,
    )
    json.dump(fam_stats, open(out_dir / 'e334_fam_stats.json', 'w'), indent=2)
    print(f'Saved e334_live_cache.npz for {len(all_pids)} historical players!')


if __name__ == '__main__':
    main()
