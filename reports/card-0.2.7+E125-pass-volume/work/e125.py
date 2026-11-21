"""E-125：由 E-107 e107.py 複製（預註冊 §2.1、§3）。基準 B6 換成 P0、候選 UL6 換成 P50，選項（M.BASE_OPTS、'season'）原樣；候選和基準共用同一組抽樣（M.e089_eval）。
c0 = P0 名次對 card 0.2.7 ranking.csv 逐位元相同（sha256 aebcadf1…c6b6）。E-107 的 c0a/b/c、f2、u1（bonus）不在本預註冊，已移除；本預註冊的 c0a、u1 是 attributes 檢查，由 work/check_attrs.py 做。
用法（repo 根目錄）：python -I -B reports/card-0.2.7+E125-pass-volume/work/e125.py p0     只跑 P0 並驗 c0（P50 不碰）
                     python -I -B reports/card-0.2.7+E125-pass-volume/work/e125.py full   P0＋P50 全跑
以下為 E-107 原說明已省略。"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent.parent   # work/ 的上一層＝本實驗目錄
ROOT = HERE.parents[1]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay'
E106 = ROOT / 'reports/card-0.2.5+E106-defense-bonus-monotone'
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'
C027_SHA = 'aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6'
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


def main(mode='full'):
    arms = ('P50',) if mode == 'full' else ()
    assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text().split()[0], '預註冊 sha256 與凍結值不同'
    M.load_data()
    M.set_card_dir(HERE / 'cards/P0')
    pools = M.build_pools()
    base = M.pipeline(M.BASE_OPTS, pools, 'season')
    (M.W / 'P0').mkdir(parents=True, exist_ok=True)
    M.write_rank(M.W / 'P0/ranking.csv', base['_aux']['cols23'], base['_aux']['rows23'])
    c0 = {'sha256': sha(M.W / 'P0/ranking.csv'), 'want': C027_SHA, 'card027_sha256_now': sha(C027)}
    c0['pass'] = bool(c0['sha256'] == C027_SHA == c0['card027_sha256_now'])
    print('(c0)', c0['pass'], c0['sha256'], flush=True)
    if not c0['pass'] or mode == 'p0':
        (HERE / ('phase1.json' if c0['pass'] else 'errata-c0.json')).write_text(json.dumps({'c0': c0}, ensure_ascii=False, indent=1), encoding='utf-8')
        return 0 if c0['pass'] else 1
    c1 = M.read_c1()
    rows = {'P0': base['_aux']['rows23']}
    anchors = {'P0': base['card']['anchors']}
    res = {'experiment': 'E-125', 'baseline': 'P0 = card 0.2.7（work/P0/ranking.csv，c0 對 reports/card-0.2.7/ranking.csv 逐位元相同）',
           'c0': c0, 'arms': {}, 'r1p_P0': r1p_check(rows['P0'])}
    for a in arms:
        M.set_card_dir(HERE / 'cards' / a)
        r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
        M.write_rank(M.W / a / 'ranking.csv', r_['_aux']['cols23'], r_['_aux']['rows23'])
        rows[a] = r_['_aux']['rows23']
        anchors[a] = r_['card']['anchors']
        ev = M.e089_eval(r_['_aux']['dirs'], base['_aux']['dirs'])
        checks = {'c0': {'pass': c0['pass']}, 'c1': {'value': c1, 'pass': c1}}
        checks.update(ev['checks'])
        checks['r1p'] = r1p_check(rows[a])
        fails = [k for k, v in checks.items() if v['pass'] is False]
        hard = [k for k in fails if k in ('c0', 'c1')]
        verdict = ('停下修程式（' + '、'.join(hard) + '）' if hard else
                   ('照 R-042 權衡，交使用者（' + '、'.join(fails) + ' 沒過）') if fails else '全過，交使用者 G5')
        res['arms'][a] = {'verdict': verdict, 'failed': fails, 'checks': checks, 'eval': ev, 'ranking_sha256': sha(M.W / a / 'ranking.csv')}
        print(a, verdict, {k: round(ev[k]['point'], 4) for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')}, checks['r1p'], flush=True)
    # 只報告
    by = {a: {r['name']: r for r in rs} for a, rs in rows.items()}
    k2, net, dd = ext_ranks()
    missing = [n for n in NAMED if n not in by['P0']]
    assert not missing, missing
    rep = {'named': {n: {'rank2k': k2.get(n), 'rapmNetRank': net.get(n), 'rapmDRank': dd.get(n),
                         **{a: {'rank': int(by[a][n]['rank']), 'ovr': float(by[a][n]['ovr']), 'bonus': float(by[a][n]['defenseBonus'])}
                            for a in rows}} for n in NAMED},
           'anchors': anchors}
    for a in arms:
        top = {t: [r['name'] for r in sorted(rows[t], key=lambda r: int(r['rank']))[:20]] for t in ('P0', a)}
        mv = [{'name': n, 'rank_P0': int(by['P0'][n]['rank']), 'rank_new': int(by[a][n]['rank']), 'ovr_P0': float(by['P0'][n]['ovr']),
               'ovr_new': float(by[a][n]['ovr']), 'bonus_P0': float(by['P0'][n]['defenseBonus']), 'bonus_new': float(by[a][n]['defenseBonus'])}
              for n in by[a] if abs(int(by[a][n]['rank']) - int(by['P0'][n]['rank'])) >= 10]
        mv.sort(key=lambda x: x['rank_new'] - x['rank_P0'])
        top300 = [x for x in mv if min(x['rank_P0'], x['rank_new']) <= 300]
        gap = {}
        for tag in ('P0', a):
            rs = [r for r in rows[tag] if r['name'] in k2]
            order = sorted(rs, key=lambda r: int(r['rank']))
            rel = {r['name']: i + 1 for i, r in enumerate(order)}
            k2rel = {n: i + 1 for i, n in enumerate(sorted(rel, key=lambda n: k2[n]))}
            gap[tag] = {n: rel[n] - k2rel[n] for n in rel}
        worst = sorted(gap[a], key=lambda n: -abs(gap[a][n]))[:10]
        rep[a] = {'top20_in': [n for n in top[a] if n not in top['P0']], 'top20_out': [n for n in top['P0'] if n not in top[a]],
                  'top20': top,
                  'movers_ge10': len(mv), 'movers_ge10_top300': len(top300), 'movers_top300_list': top300,
                  'changed_ovr': sum(1 for n in by[a] if float(by[a][n]['ovr']) != float(by['P0'][n]['ovr'])),
                  'bonus_positive': {t: int(sum(float(r['defenseBonus']) > 0 for r in rows[t])) for t in ('P0', a)},
                  'gap2k_worst10': [{'name': n, 'gap_new': gap[a][n], 'gap_P0': gap['P0'][n]} for n in worst],
                  'gap2k_meanAbs': {t: float(np.mean([abs(v) for v in gap[t].values()])) for t in ('P0', a)},
                  'pr96_bonus_primary': [{**x, 'rank_P0': int(by['P0'][x['name']]['rank']), 'rank_new': int(by[a][x['name']]['rank'])}
                                         for x in M.jload(HERE / 'cards' / a / 'primary/summary.json')['e094']['pr96_bonus']],
                  'rapmCap_primary': {t: {k_: v_ for k_, v_ in M.jload(HERE / 'cards' / t / 'primary/summary.json')['cap'].items()}
                                      for t in ('P0', a)}}
    res['reportOnly'] = rep
    res['evaluate_gates'] = M.read_gates_e094()
    with (HERE / 'ranking.csv').open('w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['name', 'pos', 'rank2k', 'rapmNetRank', 'rapmDRank'] + [f'{c}_{a}' for a in rows for c in ('rank', 'ovr', 'defenseBonus')])
        for r in sorted(rows['P0'], key=lambda r: int(r['rank'])):
            n = r['name']
            wr.writerow([n, r['pos'], k2.get(n, ''), net.get(n, ''), dd.get(n, '')]
                        + [x for a in rows for x in (by[a][n]['rank'], by[a][n]['ovr'], by[a][n]['defenseBonus'])])
    res['preregistration_sha256'] = sha(HERE / 'preregistration.md')
    res['inputs_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in
                            [E94 / 'e094.py', ROOT / 'reports/card-0.2.6+E107-defense-UL/calibrate-wing.py', HERE / 'work/run_cards_p.py', E101 / 'attributes-e101.csv', HERE / 'attributes-P0.csv', HERE / 'attributes-P50.csv']
                            + sorted(E104.glob('def-L-*.csv'))}
    (HERE / 'results-e125.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'full'))
