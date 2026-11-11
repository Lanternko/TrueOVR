"""E-202 KT：新 tovSkill（預註冊 §1）。寫 tov-raw.csv 與 tail-KT.csv。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j+E202-to-possession/tov_raw.py"""
import csv, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
import e175_lib as L, e175_card as C

SEASONS_TRK = ['2022-23', '2023-24', '2024-25', '2025-26']
RAW = ROOT / 'reports/handle-E069/raw'
K, KH, LAM = 64, 256, 0.2          # E-069 方法 c，rsec 擬合
TAIL = ROOT / 'reports/card-0.2.10i/tail-U.csv'


def trk_top(season, D):
    d = json.loads((RAW / season / 'Possessions-FULL.json').read_text(encoding='utf-8'))['data']['resultSets']
    rs = d[0] if isinstance(d, list) else d
    h = rs['headers']; ip, it = h.index('PLAYER_ID'), h.index('TIME_OF_POSS')
    top = np.zeros(D.NP); has = np.zeros(D.NP, bool); lost = 0
    for r in rs['rowSet']:
        i = D.pidx.get(r[ip])
        if i is None:
            lost += 1; continue
        top[i] += r[it]; has[i] = True
    return top, has, lost


def main():
    D = L.Data(); inp = C.load_inputs()
    out = C.card_chain(D, inp, 'U')
    pids = inp['pids']; ix = np.array([D.pidx[p] for p in pids]); pos_card = [inp['cards'][p]['pos'] for p in pids]
    cur = L.TEST; G = D.G[cur]
    # 窗口權重（c＝82，季末）
    w = L.window_w(L.SLOTS * G / G)
    seas = [cur] + [L.SEASONS[L.SEASONS.index(cur) - k] for k in (1, 2, 3)]
    wk = {cur: None, **{L.SEASONS[L.SEASONS.index(cur) - k]: w[k] for k in (1, 2, 3)}}
    NP = D.NP
    num_w, tm_w, pm_w = np.zeros(NP), np.zeros(NP), np.zeros(NP)
    cov = {}
    tab_u = None
    for s in seas:
        top, has, lost = trk_top(s, D)
        tov_s, _ = D.tab[s]['tovSkill'].agg()
        min_s = D.tab[s]['vol'].agg()[1] * 36
        if s == cur:
            c = L.SLOTS
            tab = D.tab[s]['tovSkill']; tv = D.tab[s]['vol']
            u = (L.WIN - c + L.SLOTS * (tab.gi + 0.5) / G) / L.WIN
            nw = tab.agg(0, G, w=u)[0]
            mw = tv.agg(0, G, w=u)[1] * 36
        else:
            nw, mw = wk[s] * tov_s, wk[s] * min_s
        frac = np.divide(mw, min_s, out=np.zeros(NP), where=min_s > 0)
        num_w += nw; tm_w += mw; pm_w += top * frac
        cov[s] = {'tracking_rows_unmatched': lost, 'card_players_with_TOV_but_no_tracking': int(((tov_s[ix] > 0) & ~has[ix]).sum()),
                  'card_players_with_tracking': int(has[ix].sum())}
    # 先驗與歷史目標
    top_cur, _, _ = trk_top(cur, D)
    tov_cur = D.tab[cur]['tovSkill'].agg()[0]
    m = L.prior_vec(tov_cur[ix], top_cur[ix], 'position', pos_card)     # 同位置：卡片名單 2025-26 全季 TOV／TOP分鐘
    hn, hd = np.zeros((3, NP)), np.zeros((3, NP))
    for j in range(3):
        hs = L.SEASONS[L.SEASONS.index(cur) - 1 - j]
        hn[j] = D.tab[hs]['tovSkill'].agg()[0]; hd[j] = trk_top(hs, D)[0]
    t = L.hist_target(hn[:, ix], hd[:, ix], m, LAM, KH)
    n, d = num_w[ix], pm_w[ix]
    r = L.shrink_to(n, d, t, K)                   # 每持球分鐘的失誤數（E-069 r_sec 同單位）
    Tm = tm_w[ix]
    v = np.divide(d, Tm, out=np.zeros(len(ix)), where=Tm > 0) * 36
    idx = {p: i for i, p in enumerate(pids)}
    pool = [idx[p] for p in out['poolPids']]
    topMissing = d <= 0
    v_p10 = float(np.percentile(v[pool], 10))
    v = np.where(topMissing, v_p10, v)
    z = lambda x: (x - x[pool].mean()) / x[pool].std()
    raw = 0.5 * z(-r) + 0.5 * z(v)
    h1 = inp['h1']
    mp = L.PctMapper(list(raw[pool]), C.passed(h1, 'tovSkill', 'top'), C.passed(h1, 'tovSkill', 'bot'))
    tov_new = mp(raw)
    # 對照：K0 的 tail-U 值
    tail = list(csv.DictReader(open(TAIL, encoding='utf-8')))
    k0 = {int(x['playerId']): float(x['tovSkill']) for x in tail}
    chain_k0 = {p: float(out['mapped']['tovSkill'][i]) for i, p in enumerate(pids)}
    diff = max(abs(chain_k0[p] - k0[p]) for p in pids if p in k0)
    with open(HERE / 'tov-raw.csv', 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f); wr.writerow(['playerId', 'name', 'pos', 'n_w', 'possMin_w', 'min_w', 'r', 'v', 'raw', 'tovSkill', 'tovSkill_K0', 'topMissing', 'inPool'])
        for i, p in enumerate(pids):
            wr.writerow([p, inp['cards'][p]['name'], pos_card[i], repr(float(n[i])), repr(float(d[i])), repr(float(Tm[i])), repr(float(r[i])), repr(float(v[i])),
                         repr(float(raw[i])), repr(float(tov_new[i])), k0.get(p, ''), int(topMissing[i]), int(i in set(pool))])
    new = {p: float(tov_new[i]) for i, p in enumerate(pids)}
    cols = list(tail[0].keys())
    with open(HERE / 'tail-KT.csv', 'w', encoding='utf-8', newline='') as f:
        wr = csv.writer(f, lineterminator='\n'); wr.writerow(cols)
        for x in tail:
            row = [x[c] for c in cols]
            row[cols.index('tovSkill')] = repr(new[int(x['playerId'])])
            wr.writerow(row)
    info = {'coverage': cov, 'poolN': len(pool), 'topMissingN': int(topMissing.sum()), 'v_p10': v_p10, 'max_abs_diff_chain_vs_tailU_K0': diff,
            'h1_tov': {'top': C.passed(h1, 'tovSkill', 'top'), 'bot': C.passed(h1, 'tovSkill', 'bot')},
            'corr_r_v_pool': float(np.corrcoef(r[pool], v[pool])[0, 1]), 'n_players': len(pids)}
    (HERE / 'tov-raw-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
