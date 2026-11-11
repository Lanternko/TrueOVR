"""card 0.2.14-cand2：0.2.14-cand 的 MIX 加分，500 分鐘以下按比例打折（E-292、R-184）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.14-cand2/build_cand2.py"""
import csv, hashlib, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE = ROOT / 'reports/card-0.2.13a/ranking.csv'; CAND = ROOT / 'reports/card-0.2.14-cand/ranking.csv'
BD = ROOT / 'reports/E292-mix-ramp/bonus_D.npz'; TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
rows = list(csv.DictReader(open(BASE, encoding='utf-8'))); cols = list(rows[0].keys())
z = np.load(BD); names = list(z['names']); bD = z['bD']
assert names == [r['name'] for r in rows]
cand = {r['name']: r for r in csv.DictReader(open(CAND, encoding='utf-8'))}
for r, b in zip(rows, bD):
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['mixBonus'] = round(float(b), 3); r['ovr'] = round(r['ovr0'] + float(b), 1)
    if float(r['MIN']) >= 500:
        assert abs(float(b) - float(cand[r['name']]['mixBonus'])) <= 0.001, r['name']
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
MIN = np.array([float(r['MIN']) for r in rows]); B = np.array([r['mixBonus'] for r in rows])
summ = {'version': 'card 0.2.14-cand2', 'base': 'card 0.2.13a（reports/card-0.2.13a/ranking.csv）', 'players': len(rows),
        'change': 'E-290 MIX 籃板／兩分干擾加分（R-183），500 分鐘以下按比例打折修 L-138 斷崖（E-292，R-184 使用者裁定 T2 以分鐘反事實判過，看過結果後的裁定）；候選卡，未取代正式卡。',
        'formula': 'ovr_new = round(ovr_0213a + mixBonus, 1)；MIN>=500：mixBonus＝card-0.2.14-cand 現值（lambda*sd*P_MIX）；MIN<500：mixBonus＝E-291 臂 C（同尺不收縮全套）× MIN/500；其他欄位同 0.2.13a，rank 依新 ovr 重排、同分依原名次',
        'bonus_population': {'MIN>=500 非零': int(((MIN >= 500) & (B > 0)).sum()), 'MIN<500 非零': int(((MIN < 500) & (B > 0)).sum()), '零（籃板與干擾都不高於平均，或沒資料）': int((B == 0).sum())},
        'bonus_max': float(B.max()), 'n_at_cap': int((B >= B.max() - 0.01).sum()),
        'sources_sha256': {'card_0213a_ranking': sha(BASE), 'card_0214cand_ranking': sha(CAND), 'E292_bonus_D': sha(BD),
                           'E292_preregistration': sha(ROOT / 'reports/E292-mix-ramp/preregistration.md')},
        'ranking_csv_sha256': sha(out), 'build_command': 'python -I -B -X utf8 reports/card-0.2.14-cand2/build_cand2.py'}
(HERE / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding='utf-8')
tw = {}
for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')):
    if r.get('overall2k'): tw[r['name']] = r['overall2k']
big = lambda r: '*' if r['pos'] in ('PF', 'C') else ''
L = ['# card 0.2.14-cand2 G5 清單', '', '- 非盲測：MIX、λ=0.5（R-183）與 T2 判定（R-184）都是看過結果後的使用者裁定（L-026）。',
     '- 與 0.2.14-cand 差別：只有上場 <500 分鐘的人加分改變（原本 0，改按比例打折）；≥500 分鐘完全相同。', '', '## 前十（長人標 *）', '',
     '| 名次 | 球員 | 位置 | OVR | 0.2.13a 名次 | 2K27 |', '|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']}{big(r)} | {r['pos']} | {r['ovr']} | {r['rank0']} | {tw.get(r['name'], '')} |" for r in rows[:10]]
L += ['', '## 上場 <500 分鐘加分最多的人', '', '| 球員 | 位置 | 分鐘 | 加分 | 0.2.13a → cand2 名次 | 2K27 |', '|---|---|---|---|---|---|']
lo = sorted([r for r in rows if float(r['MIN']) < 500], key=lambda r: -r['mixBonus'])[:12]
L += [f"| {r['name']} | {r['pos']} | {int(float(r['MIN']))} | +{r['mixBonus']:.2f} | {r['rank0']} → {r['rank']} | {tw.get(r['name'], '')} |" for r in lo]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print(json.dumps(summ, ensure_ascii=False, indent=1)); print('\n'.join(L))
