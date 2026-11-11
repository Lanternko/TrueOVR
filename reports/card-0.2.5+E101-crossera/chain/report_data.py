"""E-101 §6 只報告項：每屬性合併池錨點與保險、2025-26 >99／>120／>140 名單（並列 E-096）、各季 ≥99 人數、
指定球員（中距離、近距離、其他頂端）、中距離剛好 99 人數、與 E-096 名次差異、ρ2K／ρRAPM／ρDef、各變體 c2／c3／c4。
基準 = E-090＠0.2.5 的 cards/cur/e084/ranking.csv（(c0)：等於 card 0.2.5）；對照 = E-096 cards/e096；候選 = cards/e101（e101z、e101g、e101w 只報告）。
由 E-097 chain/report_data.py 改寫。用法：python -I -B reports/card-0.2.5+E101-crossera/chain/report_data.py → report-data.json
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
E25 = HERE.parent / 'card-0.2.5+E090-onball-tail'
E96 = HERE.parent / 'card-0.2.5+E096-tail150'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ATTRS13 = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']
VARS = ['e101', 'e101z', 'e101g', 'e101w']
LAB = {'e101': 'E101', 'e101z': 'E101z', 'e101g': 'E101g', 'e101w': 'E101w'}
MID_WATCH = ['Walker Kessler', 'Daniel Gafford', 'Jakob Poeltl', 'Dereck Lively II', 'Mason Plumlee', 'Andre Drummond', 'Clint Capela',
             'Shai Gilgeous-Alexander', 'Kevin Durant']
SHORT_WATCH = ['Giannis Antetokounmpo', 'Obi Toppin', 'Jalen Duren', 'Jaxson Hayes']
OTHER_TOP = [('Stephen Curry', 'ft'), ('Zach Edey', 'physique'), ('Luke Kennard', 'long'), ('Nikola Jokić', 'pass')]
WATCH = ['Shai Gilgeous-Alexander', 'Nikola Jokić', 'Giannis Antetokounmpo', 'Kevin Durant', 'Chet Holmgren', 'Kawhi Leonard', 'Dyson Daniels',
         'Luguentz Dort', 'Stephen Curry', 'Zach Edey', 'Joel Embiid', 'Jalen Duren', 'Victor Wembanyama', 'Walker Kessler', 'Luke Kennard']


def rd(p):
    return {r['name']: r for r in csv.DictReader(open(p, encoding='utf-8'))}


f = lambda r, k: float(r[k])
old = rd(E25 / 'cards/cur/e084/ranking.csv')
e096 = rd(E96 / 'cards/e096/e084/ranking.csv')
rk = {v: rd(HERE / f'cards/{v}/e084/ranking.csv') for v in VARS}
a096 = rd(E96 / 'attributes-e096.csv')
val096 = rd(E96 / 'value-attrs.csv')
att = {v: rd(HERE / f'attributes-{v}.csv') for v in VARS}
val = {v: rd(HERE / f'value-attrs-{v}.csv') for v in VARS}
tail = json.load(open(HERE / 'tail-summary.json', encoding='utf-8'))
ev = {c['label']: c for c in json.load(open(HERE / 'evaluation.json', encoding='utf-8'))['candidates']}
c2 = {v: json.load(open(HERE / f'c2-{v}.json', encoding='utf-8')) for v in VARS}
assert all(set(old) == set(x) for x in [e096, a096, val096, *rk.values(), *att.values(), *val.values()])


def shift(a, b):
    d = [f(b[k], 'ovr') - f(a[k], 'ovr') for k in a]
    m = [abs(int(b[k]['rank']) - int(a[k]['rank'])) for k in a]
    return {'n': len(d), 'up': sum(x >= 0.05 for x in d), 'down': sum(x <= -0.05 for x in d), 'median': sorted(d)[len(d) // 2],
            'maxUp': max(d), 'maxDown': min(d), 'rankMove>=5': sum(x >= 5 for x in m), 'rankMove>=10': sum(x >= 10 for x in m)}


top10 = lambda r: sorted(r, key=lambda k: int(r[k]['rank']))[:10]
new = rk['e101']
out = {'ovrShift_vs_card025': shift(old, new), 'ovrShift_vs_E096': shift(e096, new),
       **{f'ovrShift_{v}_vs_card025': shift(old, rk[v]) for v in VARS[1:]},
       **{f'ovrShift_{v}_vs_E096': shift(e096, rk[v]) for v in VARS[1:]},
       'top10': {'card025': top10(old), 'E096': top10(e096), **{v: top10(rk[v]) for v in VARS}}}
movers = sorted(e096, key=lambda k: -abs(int(new[k]['rank']) - int(e096[k]['rank'])))[:20]
out['movers20_vs_E096'] = [{'name': k, 'ovr': [f(e096[k], 'ovr'), f(new[k], 'ovr')], 'rank': [int(e096[k]['rank']), int(new[k]['rank'])],
                            'attrsChanged': {a: [round(f(a096[k], a), 1), round(f(att['e101'][k], a), 1)] for a in ATTRS13
                                             if abs(f(a096[k], a) - f(att['e101'][k], a)) > 0.05}} for k in movers]
out['watch'] = [{'name': k, 'card025': [int(old[k]['rank']), f(old[k], 'ovr')], 'E096': [int(e096[k]['rank']), f(e096[k], 'ovr')],
                 **{v: [int(rk[v][k]['rank']), f(rk[v][k], 'ovr')] for v in VARS}} for k in WATCH if k in new]

# §6 每屬性：合併池錨點、比值、保險（每個變體）
KEEP = ('type', 'topTail', 'botTail', 'r90', 'r99', 'r1', 'SD_pool', 'gapScale', 'ratio', 'S', 'insuranceActive', 'poolN', 'a99')
out['anchors'] = {v: {a: {k: i[k] for k in KEEP if k in i} for a, i in tail[v].items() if not a.startswith('_')} for v in VARS}


# §6 2025-26 >99／>120／>140 人數與名單，和 E-096 並列（15 項屬性；short 為卡片值＝折扣後）
def col(v, a):
    if a.endswith('Value'):
        src, k = (val096 if v == 'E096' else val[v]), a[:-5] + 'Attr'
    else:
        src, k = (a096 if v == 'E096' else att[v]), a
    return {n: f(r, k) for n, r in src.items()}


ATTRS15 = ATTRS13 + ['midValue', 'shortValue']
out['top2025'] = {}
for a in ATTRS15:
    o = {}
    for v in ['E096'] + VARS:
        c = col(v, a)
        o[v] = {cut: sorted(([n, round(x, 2)] for n, x in c.items() if x > t), key=lambda z: -z[1])
                for cut, t in (('>99', 99.0), ('>120', 120.0), ('>140', 140.0))}
        o[v]['counts'] = {cut: len(o[v][cut]) for cut in ('>99', '>120', '>140')}
    out['top2025'][a] = o
out['top2025_countTable'] = {a: {v: out['top2025'][a][v]['counts'] for v in ['E096'] + VARS} for a in ATTRS15}
# §6 各季 ≥99 人數（合併錨點）
out['season99'] = {v: tail[v]['_season99'] for v in VARS if '_season99' in tail[v]}
out['season99_rule'] = '命中率型 p >= a99（short 為折扣前）；百分位型 r >= r99；量價型 value >= r99；min500 = 池內（MIN>=500 或 GP/MPG 門檻），all = 該季所有有值球員'


# §6 中距離、近距離、其他頂端
def zone(names, z):
    return [{'name': k, 'A': f(val['e101'][k], z + 'A'), 'M': f(val['e101'][k], z + 'M'),
             'acc_shrunkP': {'E096': round(f(val096[k], z + 'Acc'), 3), **{v: round(f(val[v][k], z + 'Acc'), 3) for v in VARS}},
             'attr': {'E096': round(f(a096[k], z), 2), **{v: round(f(att[v][k], z), 2) for v in VARS}},
             'value': {'E096': round(f(val096[k], z + 'Attr'), 2), **{v: round(f(val[v][k], z + 'Attr'), 2) for v in VARS}}}
            for k in names if k in new]


out['midWatch'] = zone(MID_WATCH, 'mid')
out['shortWatch'] = zone(SHORT_WATCH, 'short')
out['otherTop'] = [{'name': k, 'attr': a, 'E096': round(f(a096[k], a), 2), **{v: round(f(att[v][k], a), 2) for v in VARS}} for k, a in OTHER_TOP]
out['missingWatch'] = [k for k in MID_WATCH + SHORT_WATCH + [x for x, _ in OTHER_TOP] if k not in new]
out['mid==99'] = {'E096': sum(abs(f(a096[k], 'mid') - 99) < 1e-9 for k in a096),
                  **{v: sum(abs(f(att[v][k], 'mid') - 99) < 1e-9 for k in att[v]) for v in VARS}}
out['mid==99_names_e101'] = [[k, f(val['e101'][k], 'midA')] for k in att['e101'] if abs(f(att['e101'][k], 'mid') - 99) < 1e-9]
out['mid>=98.5_e101'] = sorted(([k, round(f(att['e101'][k], 'mid'), 2), f(val['e101'][k], 'midA')] for k in att['e101']
                                if f(att['e101'][k], 'mid') >= 98.5), key=lambda z: -z[1])
# §6 ρ 與各變體 c2／c3／c4
CMP = ('card-0.2.5', 'E090', 'E096', 'E096v', 'E097', 'E101', 'E101z', 'E101g', 'E101w')
out['rho'] = {k: {'rho2k': ev[k]['rho2k'], 'rhoRapm_inSample_R007': ev[k]['rhoRapm'], 'rhoDef': ev[k]['rhoDef'],
                  'gates': f"{ev[k]['gates']['pass']}/{ev[k]['gates']['of']}"} for k in CMP if k in ev}
c4 = {}
for v in VARS:
    hits = [[n, a, round(x, 2)] for a in ATTRS15 for n, x in col(v, a).items() if x > 140]
    c4[v] = {'count>140': len(hits), 'values': hits, 'pass': len(hits) <= 2}
out['variantGates'] = {v: {'c2N': c2[v]['c2N'], 'c2Q': c2[v]['c2Q'], 'c3': f"{ev[LAB[v]]['gates']['pass']}/{ev[LAB[v]]['gates']['of']}",
                           'c3pass': ev[LAB[v]]['gates']['pass'] >= ev['card-0.2.5']['gates']['pass'], 'c4': c4[v]} for v in VARS}
json.dump(out, open(HERE / 'report-data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k in ('ovrShift_vs_card025', 'ovrShift_vs_E096', 'top10', 'mid==99', 'rho', 'top2025_countTable'):
    print(k, json.dumps(out[k], ensure_ascii=False))
for v, g in out['variantGates'].items():
    print(v, json.dumps({k: (x if k != 'c4' else x['count>140']) for k, x in g.items()}, ensure_ascii=False))
for w in out['watch']:
    print(w)
for w in out['midWatch'] + out['shortWatch']:
    print(w['name'], 'attr', w['attr'], 'value', w['value'])
print('otherTop', out['otherTop'], 'missing', out['missingWatch'])
print('movers', [(m['name'], m['rank']) for m in out['movers20_vs_E096']])
print('mid>=98.5', out['mid>=98.5_e101'])
