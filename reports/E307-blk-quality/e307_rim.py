"""E-307 RIM 顯示欄臂（prereg §4.3）：0.7·z(help)＋0.3·z(指標)，指標＝A0（現行 D30）／AE／AG／AV（四季窗口，同 E-305）。
2026-27 賽中頁（最新有 t-swap.json 的 live 日）＋2025-26 卡片頁（card-0.2.15）。只讀，輸出 results/rim.json。
用法（repo root）：python -I -X utf8 reports/E307-blk-quality/e307_rim.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e307_lib as L  # noqa: E402

DR = L.DR
spec = importlib.util.spec_from_file_location('e305', L.ROOT / 'reports/E305-rim-blk/e305_rim_blk.py')
E305 = importlib.util.module_from_spec(spec); spec.loader.exec_module(E305)
LIVE = DR / 'reports/ovr-inseason-2026-27/live'
PAST = ('2022-23', '2023-24', '2024-25', '2025-26')
SLOTS, G_TOTAL = 82, 1230
POOL_MPG = 15.0
METRIC_ARMS = {'D30': 'A0', 'RE': 'AE', 'RG': 'AG', 'RV': 'AV'}
W_HELP, W_M = 0.7, 0.3


def tabs_past():
    out = {}
    for s in PAST:
        out[s] = {p: (m, b36 * m / 36 if b36 is not None else 0.0) for p, (m, b36, _) in L.minutes_blk(s).items() if m > 0}
    return out


def tab_cur(cutoff):
    t = {}
    for r in E305.rs(DR / 'data/defense-seventh/2026-27/player-games.json'):
        if r['GAME_DATE'] > cutoff or not r['MIN']:
            continue
        a = t.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
        a[0] += r['MIN']; a[1] += r['BLK'] or 0
    return {k: tuple(v) for k, v in t.items()}


def evaluate(rows, pool_keys, tabs, ww, pri, targets):
    pool = [r for r in rows if r['pid'] in pool_keys]
    win = L.window_metrics(tabs, ww, [r['_pid'] for r in pool if r['_pid']], pri)
    h = np.array([r['help'] for r in pool]); mu_h, sd_h = h.mean(), h.std()
    zh = lambda r: (r['help'] - mu_h) / sd_h
    disp = {'B0': {id(r): r['help'] for r in rows}}
    for arm, col in METRIC_ARMS.items():
        v = np.array([win[r['_pid']][col] for r in pool if r['_pid'] in win]); m, s = v.mean(), v.std()
        zm = lambda r: (win[r['_pid']][col] - m) / s if r['_pid'] in win else 0.0
        sc = {id(r): W_HELP * zh(r) + W_M * zm(r) for r in rows}
        ps = np.array([sc[id(r)] for r in pool]); pm, pss = ps.mean(), ps.std()
        disp[arm] = {id(r): mu_h + sd_h * (sc[id(r)] - pm) / pss for r in rows}
    res = {'n_pool': len(pool), 'missing_in_pool': sum(1 for r in pool if r['_pid'] not in win), 'arms': {}}
    for arm, d in disp.items():
        ordr = sorted(pool, key=lambda r: -d[id(r)])
        rank = {r['name']: i + 1 for i, r in enumerate(ordr)}
        pfc = [r for r in ordr if r['pos'] in ('PF', 'C')][:10]
        wv = lambda r: win.get(r['_pid'], {})
        a = {'first': ordr[0]['name'], 'gap12': round(d[id(ordr[0])] - d[id(ordr[1])], 2),
             'top10': [(r['name'], r['pos'], round(d[id(r)], 1)) for r in ordr[:10]],
             'pfcTop10': [(r['name'], round(d[id(r)], 1), rank[r['name']], round(wv(r).get('A0', float('nan')), 2), round(wv(r).get('rS', float('nan')), 3),
                           round(wv(r).get('gt36S', float('nan')), 3)) for r in pfc],
             'named': {n: (rank.get(n), round(d[id(next(r for r in pool if r['name'] == n))], 1)) for n in
                       ('Victor Wembanyama', 'Isaiah Stewart', 'Chet Holmgren', 'Evan Mobley', 'Rudy Gobert', 'Walker Kessler', 'Anthony Davis', 'Jaren Jackson Jr.', 'Brook Lopez', 'Myles Turner', 'Alex Sarr', 'Bam Adebayo')
                       if any(r['name'] == n for r in pool)},
             'rho': {}}
        for tn, tv in targets.items():
            for grp, f in (('all', lambda r: True), ('PFC', lambda r: r['pos'] in ('PF', 'C'))):
                sel = [r for r in pool if r['pid'] in tv and f(r)]
                a['rho'][f'{tn}/{grp}'] = (round(E305.spearman([d[id(r)] for r in sel], [tv[r['pid']] for r in sel]), 4), len(sel))
        res['arms'][arm] = a
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pri = json.loads((L.HERE / 'data/priors.json').read_text(encoding='utf-8'))
    out = {}
    day = max(p.parent.name for p in LIVE.glob('2026-*/t-swap.json')); ld = LIVE / day
    meta = json.loads((ld / 'meta.json').read_text(encoding='utf-8'))
    gd = meta['window8']['gamesDone']; c = SLOTS * gd / G_TOTAL; ww = E305.weights(c)
    tabs = tabs_past(); tabs['2026-27'] = tab_cur(meta['dataCutoff'])
    rows = []
    for r in csv.DictReader(open(ld / 'ranking.csv', encoding='utf-8')):
        if r['help'] == '':
            continue
        rows.append({'name': r['name'], 'pos': r['pos'], 'help': float(r['help']), 'pid': r['playerId'], '_pid': int(r['playerId']),
                     'mpg': float(r['MIN26'] or 0) / int(r['N']) if int(r['N']) else 0.0})
    pool = {r['pid'] for r in rows if r['mpg'] >= POOL_MPG}
    epm = {r['playerId']: float(r['D']) for r in csv.DictReader(open(DR / 'reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8'))}
    ts = json.loads((ld / 't-swap.json').read_text(encoding='utf-8'))
    tdef = {k: -v for k, v in ts['oppPts100'].items()}
    out['2026-27'] = evaluate(rows, pool, tabs, ww, pri, {'EPM_D': epm, 'T_DEF': tdef})
    out['2026-27']['meta'] = {'day': day, 'cutoff': meta['dataCutoff'], 'gamesDone': gd, 'weights': ww}
    # 2025-26 卡片頁（c=0）
    _, names = E305.season_tabs()
    rows2 = []
    for r in csv.DictReader(open(L.ROOT / 'reports/card-0.2.15/ranking.csv', encoding='utf-8')):
        if r['help'] == '':
            continue
        rows2.append({'name': r['name'], 'pos': r['pos'], 'help': float(r['help']), 'pid': r['name'], '_pid': names.get(E305.nm(r['name'])), 'mpg': float(r['mpg'] or 0)})
    pool2 = {r['pid'] for r in rows2 if r['mpg'] >= POOL_MPG}
    epm2 = {E305.nm(r['name']): float(r['D']) for r in csv.DictReader(open(DR / 'data/external-impact/epm_self/epm_2025-26.csv', encoding='utf-8'))}
    epm2k = {r['pid']: epm2[E305.nm(r['name'])] for r in rows2 if E305.nm(r['name']) in epm2}
    out['2025-26'] = evaluate(rows2, pool2, tabs_past(), E305.weights(0.0), pri, {'EPM_D': epm2k})
    # 判定（prereg §5.3）
    ver = {}
    for arm in ('RE', 'RG', 'RV'):
        a = out['2026-27']['arms'][arm]
        v = {'c1': bool(a['first'] == 'Victor Wembanyama' and a['gap12'] >= 5), 'delta': {}}
        for s in ('2026-27', '2025-26'):
            for k, (rho, n) in out[s]['arms'][arm]['rho'].items():
                v['delta'][f'{s}:{k}'] = round(rho - out[s]['arms']['D30']['rho'][k][0], 4)
        v['c2'] = bool(all(d >= -0.02 for d in v['delta'].values()))
        v['pass'] = v['c1'] and v['c2']
        ver[arm] = v
    out['verdict'] = ver
    (L.HERE / 'results').mkdir(exist_ok=True)
    (L.HERE / 'results' / 'rim.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(ver, ensure_ascii=False, indent=1))
    for s in ('2026-27', '2025-26'):
        for arm, a in out[s]['arms'].items():
            print(s, arm, a['first'], a['gap12'], a['named'].get('Victor Wembanyama'), a['rho'])


if __name__ == '__main__':
    main()
