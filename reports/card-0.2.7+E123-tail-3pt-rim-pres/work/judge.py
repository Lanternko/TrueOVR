"""E-123 判定（預註冊 §5.2、§5.3）。從本資料夾根目錄跑：python -I -X utf8 work/judge.py
讀 work/cards-result.json（m1–m3）、npm-test.exit（c1）、evaluation.json（c3）、各組 ranking.csv（c4、R-061、前 20 名）。
寫 gates.json（c1、m1–m3、c3、c4、T）、judge.json（只報告項）。不改任何參數。"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E123 = HERE.parent
ROOT = E123.parents[1]
sys.path.insert(0, str(HERE))
import gate   # noqa: E402
import os
os.chdir(E123)   # gate.add 用相對的 gates.json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'
ARMS = ('e123', 'e123h', 'e123p')
ATTR_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'foulDisc', 'presDisplay']
cards = json.loads((HERE / 'cards-result.json').read_text(encoding='utf-8'))
ev = json.loads((E123 / 'evaluation.json').read_text(encoding='utf-8'))
summ = json.loads((E123 / 'tail-summary.json').read_text(encoding='utf-8'))
c1 = (E123 / 'npm-test.exit').read_text().strip() == '0'
npm_tail = [l for l in (E123 / 'npm-test.log').read_text(encoding='utf-8', errors='replace').splitlines() if 'passed' in l and 'failed' in l][-1:]
tv = {r['name']: r for r in rd(E123 / 'three-value-e123.csv')}
base = rd(C027)
base_by = {r['name']: r for r in base}

cand = {c['label']: c for c in ev['candidates']}
LAB = {'e123': 'E123-e123', 'e123h': 'E123-e123h', 'e123p': 'E123-e123p'}
base_pass = cand['card-0.2.7']['gates']['pass']


def over140(rows, use_new_tv):
    vals = []
    for r in rows:
        for c in ATTR_COLS:
            v = float(r[c])
            if v > 140:
                vals.append((r['name'], c, v))
        t = float(tv[r['name']]['tv_main_new' if use_new_tv else 'tv_main_cur']) if r['name'] in tv else None
        if t is not None and t > 140:
            vals.append((r['name'], 'threeValue', t))
    return vals


out = {'npm_test_tail': npm_tail, 'base_gates_pass': base_pass, 'arms': {}}
rowsby = {}
for a in ARMS:
    rows = rd(E123 / a / 'ranking.csv')
    rowsby[a] = rows
    by = {r['name']: r for r in rows}
    chk = cards['arms'][a]['eval']['checks']
    g = cand[LAB[a]]['gates']
    o140 = over140(rows, a == 'e123')
    # R-061
    rk = {r['name']: int(r['rank']) for r in rows}
    r61 = {'Wagner': rk['Franz Wagner'], 'Wembanyama': rk['Victor Wembanyama'], 'pass': rk['Franz Wagner'] > rk['Victor Wembanyama'],
           'Cade': rk['Cade Cunningham'], 'Tatum': rk.get('Jayson Tatum')}
    top = [r['name'] for r in sorted(rows, key=lambda r: int(r['rank']))[:20]]
    top0 = [r['name'] for r in sorted(base, key=lambda r: int(r['rank']))[:20]]
    chg = [n for n in by if by[n]['ovr'] != base_by[n]['ovr']]
    mv = [(n, int(base_by[n]['rank']), int(by[n]['rank'])) for n in by if abs(int(by[n]['rank']) - int(base_by[n]['rank'])) >= 10]
    out['arms'][a] = {
        'm': {k: {'point': chk[k]['value']['point'], 'ci90': chk[k]['value']['ci90'], 'pass': chk[k]['pass']} for k in ('m1', 'm2', 'm3')},
        'c3': {'pass': g['pass'], 'of': g['of'], 'failed': [k for k in g['hardKeys'] if g[k] is False] if 'hardKeys' in g else None},
        'c4': {'over140': o140, 'n': len(o140), 'pass': len(o140) <= 2},
        'rho2k': cand[LAB[a]]['rho2k'], 'rhoRapm': cand[LAB[a]]['rhoRapm'], 'rhoDef': cand[LAB[a]]['rhoDef'],
        'R061': r61, 'top20': top, 'top20_in': [n for n in top if n not in top0], 'top20_out': [n for n in top0 if n not in top],
        'top20_rank_moves': [(n, int(base_by[n]['rank']), int(by[n]['rank'])) for n in top if int(base_by[n]['rank']) != int(by[n]['rank'])],
        'changed_ovr': len(chg), 'maxabs_dovr': max(abs(float(by[n]['ovr']) - float(base_by[n]['ovr'])) for n in by),
        'movers_ge10': len(mv), 'movers_list': sorted(mv, key=lambda x: x[2] - x[1])[:12] + sorted(mv, key=lambda x: x[2] - x[1])[-12:] if mv else [],
        'help_counts': {'>99': sum(float(r['help']) > 99 for r in rows), '==99': sum(abs(float(r['help']) - 99) < 1e-9 for r in rows), '>120': sum(float(r['help']) > 120 for r in rows)},
        'pressure_counts': {'>99': sum(float(r['pressure']) > 99 for r in rows), '==99': sum(abs(float(r['pressure']) - 99) < 1e-9 for r in rows), '>120': sum(float(r['pressure']) > 120 for r in rows)},
        'presDisplay_counts': {'>99': sum(float(r['presDisplay']) > 99 for r in rows), '==99': sum(abs(float(r['presDisplay']) - 99) < 1e-9 for r in rows), '>120': sum(float(r['presDisplay']) > 120 for r in rows)},
    }
base140 = over140(base, False)
out['card027_c4'] = {'n': len(base140), 'over140': base140}
out['card027'] = {'rho2k': cand['card-0.2.7']['rho2k'], 'rhoRapm': cand['card-0.2.7']['rhoRapm'], 'rhoDef': cand['card-0.2.7']['rhoDef'], 'gates': base_pass,
                  'R061': {'Wagner': int(base_by['Franz Wagner']['rank']), 'Wembanyama': int(base_by['Victor Wembanyama']['rank'])}}

# 指定球員 OVR／名次（e123 對 card 0.2.7）
NAMES = ['Victor Wembanyama', 'Franz Wagner', 'Chet Holmgren', 'Matisse Thybulle', 'Alex Caruso', 'Dru Smith', 'Cason Wallace', 'Ausar Thompson',
         'Rudy Gobert', 'Evan Mobley', 'Isaiah Stewart', 'Ryan Kalkbrenner', 'Stephen Curry', 'Jamal Murray', 'Kon Knueppel']
by1 = {r['name']: r for r in rowsby['e123']}
out['named_e123'] = {n: {'rank_0.2.7': int(base_by[n]['rank']), 'rank_e123': int(by1[n]['rank']), 'ovr_0.2.7': float(base_by[n]['ovr']), 'ovr_e123': float(by1[n]['ovr']),
                         'help_0.2.7': float(base_by[n]['help']), 'help_e123': float(by1[n]['help']), 'pressure_0.2.7': float(base_by[n]['pressure']),
                         'pressure_e123': float(by1[n]['pressure']), 'presDisplay_0.2.7': float(base_by[n]['presDisplay']), 'presDisplay_e123': float(by1[n]['presDisplay'])}
                     for n in NAMES if n in by1}
# 檢查：卡片 ranking 裡 help／pressure／presDisplay 的 >99 名單，對 tail-summary 的對得上
sm = summ['e123']
out['crosscheck'] = {
    'help_gt99_card_vs_summary': [sorted(n for n, _ in sm['help']['above99']), sorted(r['name'] for r in rowsby['e123'] if float(r['help']) > 99)],
    'pressure_gt99_card_vs_summary': [sorted(n for n, _ in sm['pressure']['above99']), sorted(r['name'] for r in rowsby['e123'] if float(r['pressure']) > 99)],
    'presDisplay_gt99_card_vs_summary': [sorted(n for n, _ in sm['presDisplay']['above99']), sorted(r['name'] for r in rowsby['e123'] if float(r['presDisplay']) > 99)]}
out['crosscheck']['all_equal'] = all(v[0] == v[1] for v in out['crosscheck'].values())
(E123 / 'judge.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')

# ---- gates.json（主組 e123；e123h／e123p 只報告） ----
e = out['arms']['e123']
gate.add('c1', '`npm test` 全過', {'exit': 0 if c1 else 1, 'tail': npm_tail}, c1)
for k, lab in (('m1', 'Δρ_{N_W} 90% 下界 > −0.02'), ('m2', 'Δρ_{Q_W} 90% 下界 > −0.05'), ('m3', 'Δρ_{N_lin} 90% 下界 > −0.05')):
    gate.add(k, lab, {'point': e['m'][k]['point'], 'ci90': e['m'][k]['ci90']}, e['m'][k]['pass'])
gate.add('c3', 'evaluate.mjs 通過數 ≥ card 0.2.7 的 18/19', {'e123': f"{e['c3']['pass']}/{e['c3']['of']}", 'card0.2.7': f"{base_pass}/19"}, e['c3']['pass'] >= 18)
gate.add('c4', '卡片所有球員全部屬性（含 threeValue、presDisplay）> 140 的值 ≤ 2 個', {'n_over140': e['c4']['n'], 'list': e['c4']['over140'], 'card0.2.7': out['card027_c4']['n']}, e['c4']['pass'])
t_over = [x for x in e['c4']['over140'] if x[1] == 'threeValue']
gate.add('T-c4', 'T（threeValue）只看 a0T、h1v、c4：threeValue 新值 > 140 的人數（併入 c4 總數）', {'threeValue_over140': t_over, 'max_new_tv': max(float(r['tv_main_new']) for r in tv.values())}, len(t_over) <= 2)
for a in ('e123h', 'e123p'):
    o = out['arms'][a]
    for k in ('m1', 'm2', 'm3'):
        gate.add(f'{k}[{a}]', f'只報告：{k}', {'point': o['m'][k]['point'], 'ci90': o['m'][k]['ci90']}, o['m'][k]['pass'])
    gate.add(f'c3[{a}]', '只報告：c3', f"{o['c3']['pass']}/{o['c3']['of']}", o['c3']['pass'] >= 18)
    gate.add(f'c4[{a}]', '只報告：c4', {'n_over140': o['c4']['n']}, o['c4']['pass'])
gate.add('r1p', '只報告：R-061 Wagner 名次數字 > Wembanyama', e['R061'], e['R061']['pass'])

print(json.dumps({'c1': c1, 'm': {k: (round(v['point'], 4), [round(x, 4) for x in v['ci90']], v['pass']) for k, v in e['m'].items()},
                  'c3': e['c3'], 'c4': e['c4'], 'R061': e['R061'], 'rho': [e['rho2k'], e['rhoRapm']], 'crosscheck': out['crosscheck']['all_equal'],
                  'top20_in': e['top20_in'], 'top20_out': e['top20_out'], 'changed_ovr': e['changed_ovr'], 'maxabs': e['maxabs_dovr'], 'movers': e['movers_ge10'],
                  'e123h': {k: (o if k != 'top20' else 0) for k, o in {'c3': out['arms']['e123h']['c3'], 'c4n': out['arms']['e123h']['c4']['n'], 'r61': out['arms']['e123h']['R061']['pass']}.items()},
                  'e123p': {'c3': out['arms']['e123p']['c3'], 'c4n': out['arms']['e123p']['c4']['n'], 'r61': out['arms']['e123p']['R061']['pass']}},
                 ensure_ascii=False, default=float)[:3500])
