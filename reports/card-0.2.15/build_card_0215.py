"""card 0.2.15 正式卡：E-303 MRG5（使用者 2026-11-10「合併做進卡片」）。
底卡＝reports/card-0.2.15-base/（creation 欄＝持球進攻＝CRT＋PNR 合成，pnr 不再是獨立特徵，全部係數 W246 重擬合）；
MIX 加分照 0.2.14→14a→14b→14c 疊法：ovr＝round(ovr_base＋cardBonus×min(1,W(mpg)), 1)，cardBonus＝凍結 live/mix-pool-card0214b.json（同 card 0.2.14c），
mpg＝底卡 mpg 欄；同分依底卡名次。欄同 card-0.2.14c（mixBonus、cShare、wMin）。附檔：crt-attr.csv（持球進攻兩個成分）取代 pnr-attr.csv。
回滾：底卡換 card-0.2.13a＝build_card_0214c.py＝card 0.2.14c。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.15/build_card_0215.py"""
import csv, hashlib, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE, C14C, C14B = ROOT / 'reports/card-0.2.15-base', ROOT / 'reports/card-0.2.14c', ROOT / 'reports/card-0.2.14b'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214b.json'
fz = json.loads(FROZEN.read_text(encoding='utf-8'))
assert fz['version'] == 'card／inseason 0.2.14b'
by_name = {v['name']: v for v in fz['players'].values()}
W = lambda m: min(1.0, (1 - math.exp(-max(m, 0.0) / 15)) / (1 - math.exp(-36 / 15)))
rows = list(csv.DictReader(open(BASE / 'ranking.csv', encoding='utf-8'))); cols = list(rows[0].keys())
old = {r['name']: r for r in csv.DictReader(open(C14C / 'ranking.csv', encoding='utf-8'))}
POSW = fz['config']['w1']['posWeight']
for r in rows:
    q = by_name[r['name']]; wm = W(float(r['mpg']))
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    b = q['cardBonus'] * wm
    r['wMin'] = round(wm, 4); r['mixBonus'] = round(b, 3); r['ovr'] = round(r['ovr0'] + b, 1)
    r['cShare'] = round(sum(p * w for p, w in zip(q['pi'], POSW)), 3)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus', 'cShare', 'wMin'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
for f in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'crt-attr.csv', 'rapm-T6.csv', 'three-value.csv'):
    shutil.copyfile(BASE / f, HERE / f)
shutil.copyfile(C14C / 'bbref-alias.csv', HERE / 'bbref-alias.csv')
s = json.loads((C14C / 'summary.json').read_text(encoding='utf-8'))
for k in ('pnr', 'pnr_attr_csv_sha256', 'change_0213a', 'card_0214b_ranking_csv_sha256', 'report'):
    s.pop(k, None)
bs = json.loads((BASE / 'summary.json').read_text(encoding='utf-8'))
for k in ('anchors', 'anchor_source', 'ovr_map', 'pool_90_99', 'pool_ge99', 'crtpnr', 'three_value_csv_sha256', 'crt_attr_csv_sha256'):
    if k in bs:
        s[k] = bs[k]
s.update({
    'version': 'card 0.2.15',
    'base': 'card 0.2.15-base（reports/card-0.2.15-base/，係數 card-0.2.15-w246）；MIX 加分底同 card 0.2.14c（mix-pool-card0214b.json cardBonus×min(1,W(mpg))）',
    'change': 'E-303 MRG5（使用者 2026-11-10「合併做進卡片」）：CRT＋PNR 合成一個能力值「持球進攻」（creation 欄，顯示縮寫 CRT）；pnr 不再是獨立特徵；全部係數 W246 重擬合；MIX 加分疊法同 0.2.14c。',
    'ovr_changed': 'ovr = round(ovr_base0215 + cardBonus×min(1,W(mpg)), 1)；rank 依新 ovr 重排、同分依底卡名次',
    'base_ranking_csv_sha256': bs['ranking_csv_sha256'], 'card_0214c_ranking_csv_sha256': sha(C14C / 'ranking.csv'),
    'ranking_csv_sha256': sha(out),
    'build_command': 'python -I -B -X utf8 reports/card-0.2.15/build_card_0215.py',
})
s['mix']['bonus_max'] = max(r['mixBonus'] for r in rows)
(HERE / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
oldc = {r['name']: r for r in csv.DictReader(open(C14C / 'ranking.csv', encoding='utf-8'))}
opnr = {r['name']: float(r['pnr']) for r in csv.DictReader(open(C14C / 'pnr-attr.csv', encoding='utf-8'))}
L = ['# card 0.2.15 G5 清單（持球進攻＝CRT＋PNR 合成，對 card 0.2.14c）', '', '## 前二十', '',
     '| 名次 | 球員 | OVR | 0.2.14c 名次（OVR） | 舊 CRT | 舊 PNR | 持球進攻 |', '|---|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']} | {r['ovr']} | {oldc[r['name']]['rank']}（{oldc[r['name']]['ovr']}） | {oldc[r['name']]['creation']} | {opnr.get(r['name'], float('nan')):.1f} | {r['creation']} |" for r in rows[:20]]
L += ['', '## 前 100 名次變動 ≥10', '', '| 球員 | 0.2.14c | 0.2.15 | 舊 CRT | 舊 PNR | 持球進攻 |', '|---|---|---|---|---|---|']
mv = [r for r in rows if (r['rank'] <= 100 or int(oldc[r['name']]['rank']) <= 100) and abs(r['rank'] - int(oldc[r['name']]['rank'])) >= 10]
L += [f"| {r['name']} | {oldc[r['name']]['rank']} | {r['rank']} | {oldc[r['name']]['creation']} | {opnr.get(r['name'], float('nan')):.1f} | {r['creation']} |" for r in sorted(mv, key=lambda r: r['rank'] - int(oldc[r['name']]['rank']))]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k: s[k] for k in ('version', 'ranking_csv_sha256')}, ensure_ascii=False))
