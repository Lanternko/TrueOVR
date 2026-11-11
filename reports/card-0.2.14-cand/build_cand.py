"""card 0.2.14-cand：E-290 MIX（REBc 與 CON 各半，λ=0.5，R-183）疊在 card 0.2.13a 上。不改正式卡。
P 的 z 平均／標準差／縮放參考都取評估母體（MIN>=500 且名字唯一對應者，E-290 定義），再套到卡上全部 582 人；對不到 ID 或缺資料的分量記 0。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.14-cand/build_cand.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAM = 0.5


def mod(name, path):
    s = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(s); sys.modules[name] = m; s.loader.exec_module(m); return m


EV = mod('e290', 'reports/E290-reb-bonus-0213a/e290_eval.py')
E, Q = EV.E, EV.Q
sha = EV.sha
card_path = ROOT / 'reports/card-0.2.13a/ranking.csv'
rows = list(csv.DictReader(open(card_path, encoding='utf-8')))
hdr = list(rows[0].keys())

d = E.build('2025-26')
EV.add_arms('2025-26', d)
ref, sd = d['P_ref'], d['sd']
pop_ids = list(d['ids'])

# 母體統計
card_by = {r['name']: r for r in rows}
reb_pop = np.array([float(card_by[n]['rebound']) for n in d['names']])
tab = EV.stats_tab('2025-26')
ob_pop = np.array([(tab.get(str(p)) or {}).get('orebPct') if (tab.get(str(p)) or {}).get('orebPct') is not None else np.nan for p in pop_ids])
db_pop = np.array([(tab.get(str(p)) or {}).get('drebPct') if (tab.get(str(p)) or {}).get('drebPct') is not None else np.nan for p in pop_ids])
st = {}
for k, v in (('reb', reb_pop), ('ob', ob_pop), ('db', db_pop)):
    ok = np.isfinite(v); st[k] = (v[ok].mean(), v[ok].std())
rebc_pop = np.clip((EV.zcol(reb_pop) + EV.zcol(ob_pop) + EV.zcol(db_pop)) / 3, 0, 1.5)
s_reb = ref / np.sqrt((rebc_pop ** 2).mean())
P_reb_pop = rebc_pop * s_reb
con_pop = d['P']['CON']
mix_pop = .5 * P_reb_pop + .5 * con_pop
s_mix = ref / np.sqrt((mix_pop ** 2).mean())
assert np.allclose(mix_pop * s_mix, d['P']['MIX'])

# CON：母體內 con2_36（hustle，MIN>=200）z 與縮放
js = json.loads(E.hustle_path('2025-26').read_text(encoding='utf-8'))
H = {}
for r in js['rowSet']:
    r = dict(zip(js['headers'], r)); a = H.setdefault(int(r['PLAYER_ID']), [0, 0])
    a[0] += r['MIN'] or 0; a[1] += r['CONTESTED_SHOTS_2PT'] or 0


def con36(p):
    h = H.get(int(p))
    return h[1] / h[0] * 36 if h and h[0] >= 200 else None


cp = [con36(p) for p in pop_ids]
cv = np.array([x for x in cp if x is not None]); c_mu, c_sd = cv.mean(), cv.std()
raw_con_pop = np.array([max(0.0, min(1.5, (x - c_mu) / c_sd)) if x is not None else 0.0 for x in cp])
s_con = ref / np.sqrt((raw_con_pop ** 2).mean())
assert np.allclose(raw_con_pop * s_con, con_pop)

# 全卡人群
pop = Q.P.pop_of('2025-26')[0]
n2 = {}
for p, i in pop.items():
    n2.setdefault(Q.P.norm(i['name']), []).append(p)


def P_of(name):
    ids = n2.get(Q.P.norm(name)) or []
    if len(ids) != 1:
        return 0.0, 0.0, 0.0, False
    p = ids[0]
    t = tab.get(str(p)) or {}
    zs = []
    zs.append((float(card_by[name]['rebound']) - st['reb'][0]) / st['reb'][1])
    for k, key in (('ob', 'orebPct'), ('db', 'drebPct')):
        x = t.get(key)
        zs.append(0.0 if x is None else (x - st[k][0]) / st[k][1])
    rebc = min(max(sum(zs) / 3, 0), 1.5)
    c = con36(p)
    conr = 0.0 if c is None else min(max((c - c_mu) / c_sd, 0), 1.5)
    pr, pc = rebc * s_reb, conr * s_con
    return (.5 * pr + .5 * pc) * s_mix, rebc, conr, True


out = []
n_unmapped = 0
for r in rows:
    pm, _, _, ok = P_of(r['name'])
    n_unmapped += (not ok)
    o = float(r['ovr']); b = LAM * sd * pm
    out.append((dict(r), o, round(b, 3), round(o + b, 1)))
out.sort(key=lambda x: (-x[3], int(x[0]['rank'])))
hdr2 = hdr + ['mixBonus']
with open(HERE / 'ranking.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(hdr2)
    for i, (r, o, b, n) in enumerate(out, 1):
        r['rank'] = i; r['ovr'] = f'{n:.1f}'; r['mixBonus'] = b
        w.writerow([r[c] for c in hdr2])

summary = {
    'version': 'card 0.2.14-cand', 'base': 'card 0.2.13a（reports/card-0.2.13a/ranking.csv）', 'players': len(rows),
    'change': 'E-290 MIX（REBc 與 CON 各半）籃板／兩分干擾加分，R-183 使用者裁定採用（第 4 條掉名上限由 1 放寬到 2，看過結果後的裁定，非盲測 L-026）；候選卡，未取代正式卡。',
    'formula': 'ovr_new = round(ovr_0213a + lambda * sd * P_MIX, 1)；欄 mixBonus＝lambda*sd*P_MIX；其他欄位同 0.2.13a（rank 依新 ovr 重排，同分依原名次）',
    'lambda': LAM, 'sd_ovr_eval_pop': sd, 'eval_pop_n': len(pop_ids), 'P_ref_rms_CPOS': ref,
    'P_definition': {
        'REBc': 'clip(mean(z(rebound), z(orebPct), z(drebPct)), 0, 1.5)；rebound＝0.2.13a 卡欄位；orebPct／drebPct＝stats-2025-26.csv；缺值該分量 0；z 的平均／標準差取評估母體',
        'CON': 'clip(z(con2_36), 0, 1.5)；con2_36＝hustle CONTESTED_SHOTS_2PT／MIN×36（MIN>=200，否則 0）',
        'MIX': '0.5*REBc_scaled + 0.5*CON_scaled，再縮放到與 CPOS 同均方根（L-062）；REBc、CON 各自先縮放到同一參考',
        'scales': {'REBc': float(s_reb), 'CON': float(s_con), 'MIX': float(s_mix)},
        'eval_population': 'MIN>=500 且名字唯一對應者（E-290／E-288 X.load），其統計套到卡上全部 582 人；對不到唯一 ID 者 P=0（共 %d 人）' % n_unmapped},
    'sources_sha256': {
        'card_0213a_ranking': sha(card_path),
        'stats-2025-26.csv': sha(EV.DATA / 'stats-2025-26.csv'),
        'hustle-2025-26.json': sha(E.hustle_path('2025-26')),
        'E290_preregistration': sha(ROOT / 'reports/E290-reb-bonus-0213a/preregistration.md')},
    'ranking_csv_sha256': sha(HERE / 'ranking.csv'),
    'build_command': 'python -I -B -X utf8 reports/card-0.2.14-cand/build_cand.py',
}
(HERE / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')

# G5
new = list(csv.DictReader(open(HERE / 'ranking.csv', encoding='utf-8')))
old_rank = {r['name']: int(r['rank']) for r in rows}
new_rank = {r['name']: int(r['rank']) for r in new}
posd = {r['name']: r['pos'] for r in new}
BIG = ('PF', 'C')
L = ['# card 0.2.14-cand G5 清單', '', '- 非盲測：MIX 與 λ=0.5 在 E-290 看過結果後，第 4 條上限由使用者 R-183 從 1 放寬到 2（L-026）。', '']
L.append('## 新前十（長人標 *）\n\n| 名次 | 球員 | 位置 | OVR | 0.2.13a 名次 |\n|---|---|---|---|---|')
for r in new[:10]:
    L.append(f"| {r['rank']} | {r['name']}{'*' if r['pos'] in BIG else ''} | {r['pos']} | {r['ovr']} | {old_rank[r['name']]} |")
t10_old = [r['name'] for r in sorted(rows, key=lambda r: int(r['rank']))[:10]]
L.append('\n前十長人：' + '、'.join(f"{r['name']}({r['pos']})" for r in new[:10] if r['pos'] in BIG) +
         '；舊前十長人：' + '、'.join(f"{n}({posd[n]})" for n in t10_old if posd[n] in BIG))
L.append('新進前十：' + '、'.join(n for n in [r['name'] for r in new[:10]] if n not in t10_old) + '；掉出：' + '、'.join(n for n in t10_old if n not in [r['name'] for r in new[:10]]))
tw = {}
try:
    for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8-sig')):
        tw[r['name']] = r['overall2k']
except Exception:
    pass
L.append('\n## 代表中鋒\n\n| 球員 | 位置 | 0.2.13a | cand | OVR 前→後 | 2K27 |\n|---|---|---|---|---|---|')
ovr0 = {r['name']: r['ovr'] for r in rows}; ovr1 = {r['name']: r['ovr'] for r in new}
for n in ['Rudy Gobert', 'Jarrett Allen', 'Isaiah Hartenstein', 'Ivica Zubac', 'Jakob Poeltl', 'Myles Turner', 'Mitchell Robinson',
          'Bam Adebayo', 'Domantas Sabonis', 'Alperen Sengun', 'Evan Mobley']:
    if n in old_rank:
        L.append(f"| {n} | {posd[n]} | {old_rank[n]} | {new_rank[n]} | {ovr0[n]}→{ovr1[n]} | {tw.get(n, '—')} |")
drops = [(n, old_rank[n], new_rank[n]) for n in old_rank if old_rank[n] <= 30 and new_rank[n] - old_rank[n] > 10]
L.append('\n## 前 30 名掉 >10 名（上限 2）\n')
L.append('、'.join(f'{n} {a}→{b}' for n, a, b in drops) if drops else '無')
L.append(f'（共 {len(drops)} 人）')
L.append('\n## 前 30 名後衛／側翼名次變化\n\n| 球員 | 位置 | 前 | 後 |\n|---|---|---|---|')
for n in sorted([n for n in old_rank if (old_rank[n] <= 30 or new_rank[n] <= 30) and posd[n] not in BIG], key=lambda n: old_rank[n]):
    L.append(f'| {n} | {posd[n]} | {old_rank[n]} | {new_rank[n]} |')
L.append('\n## 每位置平均 OVR 變化（全 582 人／MIN>=500）\n\n| 位置 | 人數 | 全員前→後 | MIN>=500 前→後 |\n|---|---|---|---|')
for pv in ('PG', 'SG', 'SF', 'PF', 'C'):
    a = [n for n in ovr0 if posd[n] == pv]
    q = [n for n in a if float(card_by[n]['MIN']) >= 500]
    f = lambda xs: f"{np.mean([float(ovr0[n]) for n in xs]):.2f}→{np.mean([float(ovr1[n]) for n in xs]):.2f}" if xs else '—'
    L.append(f'| {pv} | {len(a)} | {f(a)} | {f(q)} |')
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print('\n'.join(L))
