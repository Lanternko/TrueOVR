"""E-305：RIM（護框）欄加蓋帽。預註冊見 prereg.md。只讀不寫線上檔；輸出 results.json、tables.md。
用法（repo root）：python -I -X utf8 reports/E305-rim-blk/e305_rim_blk.py"""
import csv, json, sys, unicodedata
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
STATS = ROOT / 'reports/E227-lineup-transformer-r2/data'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')
SLOTS, WIN, G_TOTAL = 82, 4 * 82, 1230
K_MIN = 200.0
POOL_MPG = 15.0
ARMS = {'B0': (1, 0, 0), 'D30': (.7, .3, 0), 'D50': (.5, .5, 0), 'D70': (.3, .7, 0), 'DV': (1 / 3, 1 / 3, 1 / 3)}


def nm(x):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', x) if not unicodedata.combining(ch)).lower().replace('.', '').replace(' jr', '').replace(' iii', '').replace(' ii', '').strip()


def weights(c):
    """同 rookie_defense.window_weights（E-104 窗口搬到季總計）。"""
    w = {}
    if c > 0:
        w['2026-27'] = (WIN - c / 2) / WIN
    for k, s in enumerate(reversed(PAST), 1):
        b = WIN - c - SLOTS * (k - 1)
        a = b - SLOTS
        w[s] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * WIN * SLOTS)
    return {s: v / 2.0 for s, v in w.items()}


def rs(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


def season_tabs():
    """{季: {pid(int): (minutes, blk_total, cont2_total)}, name→pid}"""
    tabs, names = {}, {}
    for s in PAST:
        t = {}
        for r in csv.DictReader(open(STATS / f'stats-{s}.csv', encoding='utf-8')):
            m = float(r['minutes'] or 0)
            if m <= 0:
                continue
            blk = float(r['blk36']) * m / 36 if r['blk36'] != '' else None
            c2 = float(r['cont2pt36']) * m / 36 if r['cont2pt36'] != '' else None
            t[int(r['pid'])] = (m, blk, c2)
            names.setdefault(nm(r['name']), int(r['pid']))
        tabs[s] = t
    return tabs, names


def cur_tab(cutoff):
    t = {}
    for r in rs(ROOT / 'data/defense-seventh/2026-27/player-games.json'):
        if r['GAME_DATE'] > cutoff or not r['MIN']:
            continue
        a = t.setdefault(int(r['PLAYER_ID']), [0.0, 0.0, 0.0])
        a[0] += r['MIN']; a[1] += r['BLK'] or 0
    for r in rs(ROOT / 'data/defense-seventh/2026-27/tracking/hustle.json'):
        t.setdefault(int(r['PLAYER_ID']), [0.0, 0.0, 0.0])[2] = r['CONTESTED_SHOTS_2PT'] or 0
    return {k: tuple(v) for k, v in t.items()}


def window_rates(pids, tabs, ww):
    """{pid: (min_eff, blk_total_w, c2_total_w)}（權重 ww[季]，每人除以自己有資料那幾季的最大權重）。"""
    out = {}
    for p in pids:
        mm = bb = cc = 0.0; mx = 0.0; has_c = False
        for s, t in tabs.items():
            if p in t and ww.get(s, 0) > 0:
                m, b, c2 = t[p]
                w = ww[s]
                mm += w * m; mx = max(mx, w)
                bb += w * (b or 0); cc += w * (c2 or 0)
        if mx > 0:
            out[p] = (mm / mx, bb / mx, cc / mx)
    return out


def shrunk36(win, idx, pool):
    mu = sum(win[p][idx] for p in pool if p in win) / sum(win[p][0] for p in pool if p in win)
    return {p: (v[idx] + K_MIN * mu) / (v[0] + K_MIN) * 36 for p, v in win.items()}


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    # 平均名次處理並列
    def avg(x):
        o = np.argsort(x, kind='stable'); r = np.empty(len(x)); i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[o[j + 1]] == x[o[i]]:
                j += 1
            r[o[i:j + 1]] = (i + j) / 2; i = j + 1
        return r
    return float(np.corrcoef(avg(np.asarray(a)), avg(np.asarray(b)))[0, 1])


def run(label, rows, key, pool_keys, win_key, tabs_all, ww, targets):
    """rows＝[{key,name,pos,help}]；key＝用來對 EPM／T 的 id；win_key(row)→窗口用的 pid 或 None。"""
    pids = {r['_pid'] for r in rows if r['_pid']}
    win = window_rates(pids, tabs_all, ww)
    pool = [r for r in rows if r[key] in pool_keys]
    pool_pids = [r['_pid'] for r in pool if r['_pid']]
    blk = shrunk36(win, 1, pool_pids)
    con = shrunk36(win, 2, pool_pids)
    h = np.array([r['help'] for r in pool])
    mu_h, sd_h = h.mean(), h.std()
    def z(vals, default=None):
        v = np.array([vals[r['_pid']] for r in pool if r['_pid'] in vals])
        m, s = v.mean(), v.std()
        return lambda r: ((vals[r['_pid']] - m) / s) if r['_pid'] in vals else 0.0
    zh = lambda r: (r['help'] - mu_h) / sd_h
    zb, zc = z(blk), z(con)
    miss_blk = sum(1 for r in pool if r['_pid'] not in blk)
    disp = {}
    for arm, (wh, wb, wc) in ARMS.items():
        sc = {id(r): wh * zh(r) + wb * zb(r) + wc * zc(r) for r in rows}
        if arm == 'B0':
            disp[arm] = {id(r): r['help'] for r in rows}
            continue
        ps = np.array([sc[id(r)] for r in pool]); m, s = ps.mean(), ps.std()
        disp[arm] = {id(r): mu_h + sd_h * (sc[id(r)] - m) / s for r in rows}
    res = {'n_pool': len(pool), 'missing_blk_in_pool': miss_blk, 'arms': {}}
    for arm in ARMS:
        d = disp[arm]
        ordr = sorted(pool, key=lambda r: -d[id(r)])
        top = [(r['name'], r['pos'], round(d[id(r)], 1), round(r['help'], 1), round(blk.get(r['_pid'], float('nan')), 2)) for r in ordr[:20]]
        rank = {r['name']: i + 1 for i, r in enumerate(ordr)}
        a = {'top20': top, 'gap12': round(d[id(ordr[0])] - d[id(ordr[1])], 2), 'first': ordr[0]['name'],
             'wemby': (rank.get('Victor Wembanyama'), round(d[id(next(r for r in pool if r['name'] == 'Victor Wembanyama'))], 1)) if any(r['name'] == 'Victor Wembanyama' for r in pool) else None,
             'stewart': (rank.get('Isaiah Stewart'), round(d[id(next(r for r in pool if r['name'] == 'Isaiah Stewart'))], 1)) if any(r['name'] == 'Isaiah Stewart' for r in pool) else None, 'rho': {}}
        for tname, tv in targets.items():
            for grp, f in (('all', lambda r: True), ('PFC', lambda r: r['pos'] in ('PF', 'C'))):
                sel = [r for r in pool if r[key] in tv and f(r)]
                a['rho'][f'{tname}/{grp}'] = (round(spearman([d[id(r)] for r in sel], [tv[r[key]] for r in sel]), 4), len(sel))
        res['arms'][arm] = a
    # 全體顯示值（含人群外），給卡片／線上用
    res['_disp'] = {arm: {r['name']: d[id(r)] for r in rows} for arm, d in disp.items()}
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tabs, names = season_tabs()
    out = {}
    # ---- 2026-27 ----
    day = max(p.parent.name for p in LIVE.glob('2026-*/t-swap.json'))
    ld = LIVE / day
    meta = json.loads((ld / 'meta.json').read_text(encoding='utf-8'))
    gd = meta['window8']['gamesDone']
    c = SLOTS * gd / G_TOTAL
    ww = weights(c)
    tabs26 = dict(tabs); tabs26['2026-27'] = cur_tab(meta['dataCutoff'])
    rows = []
    for r in csv.DictReader(open(ld / 'ranking.csv', encoding='utf-8')):
        if r['help'] == '':
            continue
        rows.append({'name': r['name'], 'pos': r['pos'], 'help': float(r['help']), 'pid': r['playerId'], '_pid': int(r['playerId']),
                     'mpg': float(r['MIN26'] or 0) / int(r['N']) if int(r['N']) else 0.0})
    pool = {r['pid'] for r in rows if r['mpg'] >= POOL_MPG}
    epm = {r['playerId']: float(r['D']) for r in csv.DictReader(open(ROOT / 'reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8'))}
    ts = json.loads((ld / 't-swap.json').read_text(encoding='utf-8'))
    tdef = {k: -v for k, v in ts['oppPts100'].items()}
    out['2026-27'] = run('2026-27', rows, 'pid', pool, None, tabs26, ww, {'EPM_D': epm, 'T_DEF': tdef})
    out['2026-27']['meta'] = {'day': day, 'gamesDone': gd, 'c': round(c, 3), 'weights': {k: round(v, 4) for k, v in ww.items()}}
    # ---- 2025-26 卡片頁 ----
    rows2 = []
    for r in csv.DictReader(open(ROOT / 'reports/card-0.2.15/ranking.csv', encoding='utf-8')):
        if r['help'] == '':
            continue
        rows2.append({'name': r['name'], 'pos': r['pos'], 'help': float(r['help']), 'pid': r['name'], '_pid': names.get(nm(r['name'])), 'mpg': float(r['mpg'] or 0)})
    pool2 = {r['pid'] for r in rows2 if r['mpg'] >= POOL_MPG}
    # EPM 2025-26 以名字對
    epm2 = {}
    nm_of = {}
    for r in csv.DictReader(open(ROOT / 'data/external-impact/epm_self/epm_2025-26.csv', encoding='utf-8')):
        epm2[nm(r['name'])] = float(r['D'])
    for r in rows2:
        nm_of[r['pid']] = nm(r['name'])
    epm2k = {r['pid']: epm2[nm_of[r['pid']]] for r in rows2 if nm_of[r['pid']] in epm2}
    out['2025-26'] = run('2025-26', rows2, 'pid', pool2, None, dict(tabs), weights(0.0), {'EPM_D': epm2k})
    out['2025-26']['meta'] = {'weights': {k: round(v, 4) for k, v in weights(0.0).items()}}
    # ---- 判定 ----
    verdict = {}
    for arm in ARMS:
        if arm == 'B0':
            continue
        v = {}
        a = out['2026-27']['arms'][arm]
        v['c1_wemby_first_gap5'] = bool(a['first'] == 'Victor Wembanyama' and a['gap12'] >= 5)
        deltas = {}
        for s in ('2026-27', '2025-26'):
            b0 = out[s]['arms']['B0']['rho']
            for k, (rho, n) in out[s]['arms'][arm]['rho'].items():
                deltas[f'{s}:{k}'] = round(rho - b0[k][0], 4)
        v['rho_delta'] = deltas
        v['c2_no_worse'] = bool(all(d >= -0.02 for d in deltas.values()))
        v['c2_fail_items'] = [k for k, d in deltas.items() if d < -0.02]
        v['pfc_epm_2627'] = out['2026-27']['arms'][arm]['rho']['EPM_D/PFC'][0]
        v['pass'] = v['c1_wemby_first_gap5'] and v['c2_no_worse']
        verdict[arm] = v
    ok = {k: v for k, v in verdict.items() if v['pass']}
    chosen = None
    if ok:
        best = max(v['pfc_epm_2627'] for v in ok.values())
        tied = [k for k, v in ok.items() if best - v['pfc_epm_2627'] <= 0.003]
        chosen = 'D50' if 'D50' in tied else sorted(tied)[0]
    verdict['_chosen'] = chosen
    out['verdict'] = verdict
    # 顯示值（供未來旗標使用）只留 2026-27 選中臂
    disp = out['2026-27'].pop('_disp'); out['2025-26'].pop('_disp')
    (HERE / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    if chosen:
        (HERE / f'rim-display-2026-27-{chosen}.json').write_text(json.dumps({k: round(v, 2) for k, v in disp[chosen].items()}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'rho_delta'} for k, v in verdict.items() if k != '_chosen'}, ensure_ascii=False, indent=1))
    print('chosen', chosen)
    for s in ('2026-27', '2025-26'):
        print(s, 'pool', out[s]['n_pool'], 'missing blk', out[s]['missing_blk_in_pool'])
        for arm, a in out[s]['arms'].items():
            print(' ', arm, 'first', a['first'], 'gap', a['gap12'], 'wemby', a['wemby'], 'stewart', a['stewart'], a['rho'])


if __name__ == '__main__':
    main()
