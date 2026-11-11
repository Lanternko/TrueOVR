"""E-101 results.json：照預註冊 §5 判定（主要變體 e101 對 card 0.2.5）；e101z、e101g、e101w 只報告（§4、L-026）。
由 reports/card-0.2.5+E097-topscale/chain/write_results.py 改寫：加 c-pre、c4（15 項屬性 > 140 的值 ≤ 2 個）；檔案清單換成本實驗。
用法：python -I -B reports/card-0.2.5+E101-crossera/chain/write_results.py
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
E25 = HERE.parent / 'card-0.2.5+E090-onball-tail'
E24 = HERE.parent / 'card-0.2.4+E090-onball-tail'
E96 = HERE.parent / 'card-0.2.5+E096-tail150'
E97 = HERE.parent / 'card-0.2.5+E097-topscale'
V61 = HERE.parent / 'ovr-v61-shrink-history-2025-26'
ROOT = HERE.parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
VARS = ['e101', 'e101z', 'e101g', 'e101w']
ATTRS13 = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']
C4_MAX, C4_CUT = 2, 140.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def j(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


assert sha(HERE / 'preregistration.md') == (HERE / 'preregistration.sha256').read_text(encoding='utf-8').split()[0]
cpre = j(HERE / 'c-pre.json')
c0 = j(E25 / 'c0.json')
c2 = {v: j(HERE / f'c2-{v}.json') for v in VARS}
h1 = j(HERE / 'h1-results.json')
h1v = j(HERE / 'h1v-results.json')
ev = j(HERE / 'evaluation.json')
cand = {c['label']: c for c in ev['candidates']}
ex = (HERE / 'npm-test.exit').read_text(encoding='utf-8').strip()
c1 = ex == '0'
g = lambda k: cand[k]['gates']
LAB = {'e101': 'E101', 'e101z': 'E101z', 'e101g': 'E101g', 'e101w': 'E101w'}


def c4(v):
    hits = []
    for r in csv.DictReader(open(HERE / f'attributes-{v}.csv', encoding='utf-8')):
        hits += [[r['name'], a, float(r[a])] for a in ATTRS13 if float(r[a]) > C4_CUT]
    for r in csv.DictReader(open(HERE / f'value-attrs-{v}.csv', encoding='utf-8')):
        hits += [[r['name'], z + 'Value', float(r[z + 'Attr'])] for z in ('mid', 'short') if float(r[z + 'Attr']) > C4_CUT]
    return {'count>140': len(hits), 'values': hits, 'threshold': f'<= {C4_MAX}', 'pass': len(hits) <= C4_MAX}


def c3(v):
    return bool(g(LAB[v])['pass'] >= g('card-0.2.5')['pass'] and g(LAB[v])['of'] == g('card-0.2.5')['of'])


C4 = {v: c4(v) for v in VARS}
gates = {'c-pre': cpre['pass'], 'c0': c0['pass'], 'c1': c1, 'c2N': c2['e101']['c2N']['pass'], 'c2Q': c2['e101']['c2Q']['pass'],
         'c3': c3('e101'), 'c4': C4['e101']['pass']}
verdict = '通過' if all(gates.values()) else '未過'
CMP = ('card-0.2.5', 'E090', 'E096', 'E096v', 'E097', 'E101', 'E101z', 'E101g', 'E101w')
files = ['zones-check.json', 'c-pre.json', 'a0-e101.json', 'h1-pairs-e101.json', 'h1-results.json', 'h1v-pairs-e101.json', 'h1v-results.json',
         'tail-summary.json', 'pool/manifest.json',
         *[f'history/pbp-zones-{s}.csv.gz' for s in ('2022-23', '2023-24', '2024-25', '2025-26')],
         *[f'pool/raw-{s}.json' for s in ('2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24', '2024-25')],
         *[f'attributes-{v}.csv' for v in VARS], *[f'value-attrs-{v}.csv' for v in VARS],
         'calibrate-wing.py', 'work/extract_pbp_e101.py', 'work/e101_zones.py', 'work/c_pre.py', 'work/a0_e101.py', 'work/h1_e101_data.py',
         'work/h1_e101.py', 'work/h1v_e101.py', 'work/pool_data.py', 'work/build_e101.py',
         'chain/run_cards.py', 'chain/build_card_022.py', 'chain/e084.py', 'chain/evaluate.mjs', 'chain/compare.py', 'chain/run_all.sh',
         'chain/report_data.py', 'chain/copy-log.txt',
         *[f'cards/{v}/ranking022.csv' for v in VARS], *[f'cards/{v}/e084/ranking.csv' for v in VARS],
         'evaluation.json', *[f'c2-{v}.json' for v in VARS], 'report-data.json', 'npm-test.log', 'deviations.json']
ext = {'E090@0.2.4/work/a0-raw.json': E24 / 'work/a0-raw.json', 'E090@0.2.4/work/current-attrs.csv': E24 / 'work/current-attrs.csv',
       'E090@0.2.4/h1-results.json': E24 / 'h1-results.json', 'E090@0.2.4/work/h1-pairs.json': E24 / 'work/h1-pairs.json',
       'E090@0.2.4/work/tmp/e070/vol-fit.json': E24 / 'work/tmp/e070/vol-fit.json',
       'E090@0.2.5/c0.json': E25 / 'c0.json', 'E090@0.2.5/cards/cur/e084/ranking.csv': E25 / 'cards/cur/e084/ranking.csv',
       'E096/attributes-e096.csv': E96 / 'attributes-e096.csv', 'E096/value-attrs.csv': E96 / 'value-attrs.csv', 'E096/h1v-pairs.json': E96 / 'h1v-pairs.json',
       'E097/a0-league.json': E97 / 'a0-league.json', 'E097/diag/area-count.txt': E97 / 'diag/area-count.txt',
       'V61/backtest.json': V61 / 'backtest.json', 'V61/build_attrs.py': V61 / 'build_attrs.py', 'V61/engine.py': V61 / 'engine.py',
       'V61/extract_pbp.py': V61 / 'extract_pbp.py',
       **{f'V61/history/pbp-zones-{s}.csv.gz': V61 / f'history/pbp-zones-{s}.csv.gz' for s in ('2022-23', '2023-24', '2024-25', '2025-26')},
       'data/benchmark-source/shots.json': ROOT / 'data/benchmark-source/shots.json',
       'reports/card-0.2.5/ranking.csv': ROOT / 'reports/card-0.2.5/ranking.csv', 'src/constants.js': ROOT / 'src/constants.js'}
missing = [f for f in files if not (HERE / f).exists()]
out = {
    'experiment': 'E-101', 'baseline': 'card 0.2.5', 'verdict': verdict,
    'verdict_rule': '預註冊 §5：c-pre 過才判定；主要變體 e101 對 cur，(c0)(c1)(c2N)(c2Q)(c3)(c4) 全過=通過（card 0.2.6 候選、取代 E-090 與 E-096，交使用者 G5）',
    'gates': gates,
    'checks': {
        'c-pre': {'diff': cpre['diff'], 'pbpFixed': cpre['pbpFixed']['league'], 'shotsJson': cpre['shotsJson']['league'], 'threshold': '|差| <= 0.010', 'pass': cpre['pass']},
        'c0': c0, 'c1': {'value': f'npm test exit {ex}', 'pass': c1}, 'c2N': c2['e101']['c2N'], 'c2Q': c2['e101']['c2Q'],
        'c3': {'E101': f"{g('E101')['pass']}/{g('E101')['of']}", 'card-0.2.5': f"{g('card-0.2.5')['pass']}/{g('card-0.2.5')['of']}", 'pass': c3('e101')},
        'c4': C4['e101'],
    },
    'h1_e101': {k: {e: v[e]['pass'] for e in ('top', 'bot')} for k, v in h1['h1'].items()},
    'h1v_e101': {k: {e: v[e]['pass'] for e in ('top', 'bot')} for k, v in h1v['h1v'].items()},
    'reportOnly': {
        'rho2k_perGame': {k: cand[k]['rho2k'] for k in CMP if k in cand},
        'rhoRapm_inSample_R007': {k: cand[k]['rhoRapm'] for k in CMP if k in cand},
        'rhoDef': {k: cand[k]['rhoDef'] for k in CMP if k in cand},
        'rho_N': c2['e101']['rho_N'], 'rho_Q': c2['e101']['rho_Q'],
        **{v: {'c2N': c2[v]['c2N'], 'c2Q': c2[v]['c2Q'], 'c3': f"{g(LAB[v])['pass']}/{g(LAB[v])['of']}", 'c4': C4[v],
               'note': '只報告、不判定（§4、L-026）'} for v in VARS[1:]},
    },
    'missingFiles': missing,
    'inputs_sha256': {**{f: sha(HERE / f) for f in files if (HERE / f).exists()}, **{k: sha(p) for k, p in ext.items()}},
    'preregistration_sha256': sha(HERE / 'preregistration.md'),
}
(HERE / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
print(verdict, gates)
print('missing', missing)
print(json.dumps({k: out[k] for k in ('checks', 'h1_e101', 'h1v_e101', 'reportOnly')}, ensure_ascii=False, default=float))
