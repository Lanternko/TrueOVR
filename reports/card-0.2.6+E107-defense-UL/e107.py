"""E-107：由 reports/card-0.2.5+E106-defense-bonus-monotone/e106.py 複製（預註冊 §2、§3；凍結 sha256 見 preregistration.sha256）。
基準換成 B6（card 0.2.6 原樣）；c0 拆成 c0a（B6 卡對 E-101 P1 卡）、c0b（B6 名次對 card 0.2.6）、c0c（不帶 --tailSource 對 E-106 UL）；
r1 換成 r1'（R-061：Wagner 名次低於 Wembanyama；Cade、Tatum 只報告）；只報告的具名名單加 2K27、四季 RAPM 淨值、防守名次。
用法（repo 根目錄，先跑 run_cards.py、run_gates.py）：PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 python -I reports/card-0.2.6+E107-defense-UL/e107.py
以下為 E-106 原說明：
E-106：由 reports/card-0.2.5+E104-defense-pergame-decay/e104.py 複製（預註冊 §2、§3；凍結 sha256 見 preregistration.sha256）。
組別 T、U、UL；f1（ceiling 專用）換成 u1（不打折的 bonus = 門檻內 max(0, centeredD)）；f2 只檢 UL，讀 E-104 的 def-L csv。
以下為 E-104 原說明：
唯讀匯入 reports/card-0.2.5+E094-defense-ceiling/e094.py（組卡 pipeline、e089_eval 的 m1–m3 都不改），
只把它的 CARDS／W／HERE 指到本目錄。寫 work/<組>/ranking.csv、ranking.csv（B6、UL6 並列）、phase2.json。"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay'
E106 = ROOT / 'reports/card-0.2.5+E106-defense-bonus-monotone'
C026 = ROOT / 'reports/card-0.2.6/ranking.csv'
C026_SHA = 'a0a81ecb2d591497bc1d6680573e6fbf71a11124c4d33ba60df3e4d412f16c91'
_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(M)
M.HERE, M.W, M.CARDS = HERE, HERE / 'work', HERE / 'cards'

PARTS = ('primary', 'fitA', 'fitB')
FACTOR_L = 0.5
RAPM_THR = 5000   # H1 名次封頂的池（pooledPoss ≥ 5000）
NAMED = ['Victor Wembanyama', 'Shai Gilgeous-Alexander', 'Nikola Jokić', 'Luka Dončić', 'Giannis Antetokounmpo', 'Kawhi Leonard',
         'Chet Holmgren', 'Franz Wagner', 'Cade Cunningham', 'Derrick White', 'Stephen Curry', 'Kevin Durant', 'Joel Embiid',
         'Alex Caruso', 'Jimmy Butler III', 'Herbert Jones', 'Jayson Tatum', 'LeBron James', 'Rudy Gobert', 'Anthony Davis',
         'Jalen Brunson', 'Anthony Edwards', 'Evan Mobley']
CARD_FILES = ('pred.csv', 'ranking.csv', 'pergame-main.csv', 'pergame-repl.csv', 'pergame-summary.json')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same_cards(a, b):
    """上列檔逐位元相同；summary.json 另比 JSON 內容（職位 dict 的 key 順序依 set 迭代，不比位元）。"""
    files = {f: sha(a / f) == sha(b / f) for f in CARD_FILES}
    files['summary.json(內容)'] = M.jload(a / 'summary.json') == M.jload(b / 'summary.json')
    return files


def c0a_check():
    out = {p: same_cards(E101 / 'cards/e101/P1' / p, HERE / 'cards/B6' / p) for p in PARTS}
    return {'pass': bool(all(all(v.values()) for v in out.values())), 'cards': out}


def c0c_check():
    out = {'primary': same_cards(E106 / 'cards/UL/primary', HERE / 'cards/c0c/primary')}
    return {'pass': bool(all(out['primary'].values())), 'cards': out}


def f2_check(arm):
    """§3 (f2)：summary 抽的 10 人，centeredD 對 0.75 × D_csv − posMeanD（差 < 1e-9）；posMeanD 另由 pred.csv＋csv 獨立重算，只報告差值。"""
    out = {}
    for part in PARTS:
        d = HERE / 'cards' / arm / part
        sm = M.jload(d / 'summary.json')['e094']
        src_p = E104 / f'def-L-{part}.csv'
        src = {int(x['playerId']): x for x in M.read(src_p)}
        pr_ = M.read(d / 'pred.csv')
        n2p = {r['name']: int(r['playerId']) for r in pr_}
        thr = 1000 * (1.0 if part == 'primary' else 0.5) * FACTOR_L
        pm = {}
        for pos in {r['pos'] for r in pr_}:
            pool = [r for r in pr_ if r['pos'] == pos and int(r['playerId']) in src and float(src[int(r['playerId'])]['poss']) >= thr]
            pm[pos] = sum(float(r['MIN']) * 0.75 * float(src[int(r['playerId'])]['D']) for r in pool) / sum(float(r['MIN']) for r in pool)
        samp = []
        for x in sm['f2_sample']:
            ds = float(src[n2p[x['name']]]['D'])
            rec = 0.75 * ds - x['posMeanD']
            samp.append({'name': x['name'], 'pos': x['pos'], 'D_csv': ds, 'centeredD': x['centeredD'], 'diff': abs(x['centeredD'] - rec),
                         'posMeanD_indep_diff': abs(pm[x['pos']] - x['posMeanD'])})
        out[part] = {'source': src_p.relative_to(ROOT).as_posix() + f'（池門檻 {thr:g}）', 'sample': samp,
                     'pass': bool(len(samp) == 10 and all(s_['diff'] < 1e-9 for s_ in samp))}
    return {'pass': bool(all(v['pass'] for v in out.values())), 'cards': out}


def u1_check(arm):
    """§3 (u1)：summary 抽 10 人，RAPM 封頂前 bonus = 門檻內 max(0, centeredD)、門檻外或無 centeredD 為 0（差 < 1e-9）。"""
    out = {}
    for part in PARTS:
        sm = M.jload(HERE / 'cards' / arm / part / 'summary.json')['e094']
        assert sm['bonusShape'] == 'none'
        samp = []
        for x in sm['u1_sample']:
            want = max(0.0, x['centeredD']) if (x['eligible'] and x['centeredD'] is not None) else 0.0
            samp.append({**x, 'want': want, 'diff': abs(x['bonusPreCap'] - want)})
        out[part] = {'sample': samp, 'pass': bool(len(samp) == 10 and all(s_['diff'] < 1e-9 for s_ in samp)),
                     'pr96_bonus': sm['pr96_bonus']}
    return {'pass': bool(all(v['pass'] for v in out.values())), 'cards': out}


def r1p_check(rows):
    """r1'（R-061）：Wagner 名次數字 > Wembanyama；Cade、Tatum 只報告。"""
    rk = {r['name']: int(r['rank']) for r in rows}
    w, v = rk['Franz Wagner'], rk['Victor Wembanyama']
    return {'Wagner': w, 'Wembanyama': v, 'Cade_reportOnly': rk['Cade Cunningham'], 'Tatum_reportOnly': rk.get('Jayson Tatum'),
            'gap': w - v, 'pass': bool(w > v)}


def ext_ranks():
    """2K27 名次（merged.csv rank2k）；四季 RAPM 淨值、防守名次（impact-rapm/rapm.csv，pooledPoss ≥ 5000 的池）。"""
    k2 = {r['name']: float(r['rank2k']) for r in M.read(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv') if r['rank2k']}
    rp = [r for r in M.read(ROOT / 'reports/impact-rapm/rapm.csv') if float(r['pooledPoss']) >= RAPM_THR]
    net = {r['name']: i + 1 for i, r in enumerate(sorted(rp, key=lambda r: -float(r['pooledNet'])))}
    dd = {r['name']: i + 1 for i, r in enumerate(sorted(rp, key=lambda r: -float(r['pooledD'])))}
    return k2, net, dd


def main(arms=('UL6',)):
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().strip(), '預註冊 sha256 與凍結值不同'
    M.load_data()
    M.set_card_dir(HERE / 'cards/B6')
    pools = M.build_pools()
    c0 = {'c0a': c0a_check(), 'c0c': c0c_check()}
    base = M.pipeline(M.BASE_OPTS, pools, 'season')
    M.write_rank(M.W / 'B6/ranking.csv', base['_aux']['cols23'], base['_aux']['rows23'])
    c0['c0b'] = {'sha256': sha(M.W / 'B6/ranking.csv'), 'want': C026_SHA, 'card026_sha256_now': sha(C026)}
    c0['c0b']['pass'] = bool(c0['c0b']['sha256'] == C026_SHA == c0['c0b']['card026_sha256_now'])
    c0['pass'] = bool(all(c0[k]['pass'] for k in ('c0a', 'c0b', 'c0c')))
    print('(c0a)', c0['c0a']['pass'], '(c0b)', c0['c0b']['pass'], '(c0c)', c0['c0c']['pass'], flush=True)
    if not c0['pass']:
        (HERE / 'phase2.json').write_text(json.dumps({'c0': c0}, ensure_ascii=False, indent=1), encoding='utf-8')
        return 1
    c1 = M.read_c1()
    rows = {'B6': base['_aux']['rows23']}
    anchors = {'B6': base['card']['anchors']}
    res = {'experiment': 'E-107', 'baseline': 'B6 = card 0.2.6（work/B6/ranking.csv，c0b 對 reports/card-0.2.6/ranking.csv 逐位元相同）',
           'c0': c0, 'arms': {}, 'r1p_B6': r1p_check(rows['B6'])}
    for a in arms:
        M.set_card_dir(HERE / 'cards' / a)
        r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
        M.write_rank(M.W / a / 'ranking.csv', r_['_aux']['cols23'], r_['_aux']['rows23'])
        rows[a] = r_['_aux']['rows23']
        anchors[a] = r_['card']['anchors']
        ev = M.e089_eval(r_['_aux']['dirs'], base['_aux']['dirs'])
        checks = {'c0': {'pass': c0['pass']}, 'c1': {'value': c1, 'pass': c1}, 'u1': u1_check(a), 'f2': f2_check(a)}
        checks.update(ev['checks'])
        checks['r1p'] = r1p_check(rows[a])
        fails = [k for k, v in checks.items() if v['pass'] is False]
        hard = [k for k in fails if k in ('c0', 'c1', 'u1', 'f2')]
        verdict = ('停下修程式（' + '、'.join(hard) + '）' if hard else
                   ('照 R-042 權衡，交使用者（' + '、'.join(fails) + ' 沒過）') if fails else '全過，交使用者 G5')
        res['arms'][a] = {'verdict': verdict, 'failed': fails, 'checks': checks, 'eval': ev, 'ranking_sha256': sha(M.W / a / 'ranking.csv')}
        print(a, verdict, {k: round(ev[k]['point'], 4) for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')}, checks['r1p'], flush=True)
    # 只報告
    by = {a: {r['name']: r for r in rs} for a, rs in rows.items()}
    k2, net, dd = ext_ranks()
    missing = [n for n in NAMED if n not in by['B6']]
    assert not missing, missing
    rep = {'named': {n: {'rank2k': k2.get(n), 'rapmNetRank': net.get(n), 'rapmDRank': dd.get(n),
                         **{a: {'rank': int(by[a][n]['rank']), 'ovr': float(by[a][n]['ovr']), 'bonus': float(by[a][n]['defenseBonus'])}
                            for a in rows}} for n in NAMED},
           'anchors': anchors}
    for a in arms:
        top = {t: [r['name'] for r in sorted(rows[t], key=lambda r: int(r['rank']))[:20]] for t in ('B6', a)}
        mv = [{'name': n, 'rank_B6': int(by['B6'][n]['rank']), 'rank_new': int(by[a][n]['rank']), 'ovr_B6': float(by['B6'][n]['ovr']),
               'ovr_new': float(by[a][n]['ovr']), 'bonus_B6': float(by['B6'][n]['defenseBonus']), 'bonus_new': float(by[a][n]['defenseBonus'])}
              for n in by[a] if abs(int(by[a][n]['rank']) - int(by['B6'][n]['rank'])) >= 10]
        mv.sort(key=lambda x: x['rank_new'] - x['rank_B6'])
        top300 = [x for x in mv if min(x['rank_B6'], x['rank_new']) <= 300]
        gap = {}
        for tag in ('B6', a):
            rs = [r for r in rows[tag] if r['name'] in k2]
            order = sorted(rs, key=lambda r: int(r['rank']))
            rel = {r['name']: i + 1 for i, r in enumerate(order)}
            k2rel = {n: i + 1 for i, n in enumerate(sorted(rel, key=lambda n: k2[n]))}
            gap[tag] = {n: rel[n] - k2rel[n] for n in rel}
        worst = sorted(gap[a], key=lambda n: -abs(gap[a][n]))[:10]
        rep[a] = {'top20_in': [n for n in top[a] if n not in top['B6']], 'top20_out': [n for n in top['B6'] if n not in top[a]],
                  'top20': top,
                  'movers_ge10': len(mv), 'movers_ge10_top300': len(top300), 'movers_top300_list': top300,
                  'changed_ovr': sum(1 for n in by[a] if float(by[a][n]['ovr']) != float(by['B6'][n]['ovr'])),
                  'bonus_positive': {t: int(sum(float(r['defenseBonus']) > 0 for r in rows[t])) for t in ('B6', a)},
                  'gap2k_worst10': [{'name': n, 'gap_new': gap[a][n], 'gap_B6': gap['B6'][n]} for n in worst],
                  'gap2k_meanAbs': {t: float(np.mean([abs(v) for v in gap[t].values()])) for t in ('B6', a)},
                  'pr96_bonus_primary': [{**x, 'rank_B6': int(by['B6'][x['name']]['rank']), 'rank_new': int(by[a][x['name']]['rank'])}
                                         for x in M.jload(HERE / 'cards' / a / 'primary/summary.json')['e094']['pr96_bonus']],
                  'rapmCap_primary': {t: {k_: v_ for k_, v_ in M.jload(HERE / 'cards' / t / 'primary/summary.json')['cap'].items()}
                                      for t in ('B6', a)}}
    res['reportOnly'] = rep
    res['evaluate_gates'] = M.read_gates_e094()
    with (HERE / 'ranking.csv').open('w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['name', 'pos', 'rank2k', 'rapmNetRank', 'rapmDRank'] + [f'{c}_{a}' for a in rows for c in ('rank', 'ovr', 'defenseBonus')])
        for r in sorted(rows['UL6' if 'UL6' in rows else 'B6'], key=lambda r: int(r['rank'])):
            n = r['name']
            wr.writerow([n, r['pos'], k2.get(n, ''), net.get(n, ''), dd.get(n, '')]
                        + [x for a in rows for x in (by[a][n]['rank'], by[a][n]['ovr'], by[a][n]['defenseBonus'])])
    res['preregistration_sha256'] = sha(HERE / 'preregistration.md')
    res['inputs_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in
                            [E94 / 'e094.py', HERE / 'calibrate-wing.py', HERE / 'run_cards.py', E101 / 'attributes-e101.csv']
                            + sorted(E104.glob('def-L-*.csv'))}
    (HERE / 'phase2.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
