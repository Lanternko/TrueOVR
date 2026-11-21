"""card 0.2.15-cand：E-294 臂 H-same（MIX 加分：全聯盟尺但位置平均只留一半＋軟上限 1.5·tanh(z⁺/1.5)＋位置權重 C=1／PF=0.243／其他 0），
500 分鐘以下 × MIN/500（R-184）。只產候選、不動線上。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.15-cand/build_cand.py"""
import csv, hashlib, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE = ROOT / 'reports/card-0.2.13a/ranking.csv'; C14 = ROOT / 'reports/card-0.2.14/ranking.csv'
E294 = ROOT / 'reports/E294-mix-pos-z-soft'; BP = E294 / 'bonus_pick.npz'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
rows = list(csv.DictReader(open(BASE, encoding='utf-8'))); cols = list(rows[0].keys())
z = np.load(BP); names = list(z['names']); bon = z['bonus']; assert str(z['pick']) == 'H-same'
assert names == [r['name'] for r in rows]
c14 = {r['name']: r for r in csv.DictReader(open(C14, encoding='utf-8'))}
for r, b in zip(rows, bon):
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['rank14'] = int(c14[r['name']]['rank']); r['bonus14'] = float(c14[r['name']]['mixBonus'])
    r['mixBonus'] = round(float(b), 3); r['ovr'] = round(r['ovr0'] + float(b), 1)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
MIN = np.array([float(r['MIN']) for r in rows]); B = np.array([r['mixBonus'] for r in rows])
res = json.load(open(E294 / 'results.json', encoding='utf-8'))['card']['H-same']
summ = {'version': 'card 0.2.15-cand', 'base': 'card 0.2.13a（reports/card-0.2.13a/ranking.csv）；取代對象 card 0.2.14', 'players': len(rows),
        'change': 'E-294 臂 H-same：MIX 加分的 z 改「全聯盟尺、位置平均只留一半」（中鋒身分分減半、群內差距照全聯盟尺），飽和改 1.5·tanh(z⁺/1.5)（無平台），'
                  '再乘位置權重 C=1、PF=0.243、其他 0（E-289 M1）；λ=0.5、sd、三個均方根縮放照 0.2.14 規則重算；500 分鐘以下 × MIN/500。候選卡，未取代正式卡；臂 H 是看過探索後加入（非盲測，L-026）。',
        'formula': 'ovr_new = round(ovr_0213a + mixBonus, 1)；mixBonus = 0.5*sd*w(pos)*(0.5*f(zR)*s_reb + 0.5*f(zC)*s_con)*s_mix*min(1,MIN/500)；'
                   'z = 0.5*m_pos + (z_L - m_pos)，f(x)=1.5*tanh(max(x,0)/1.5)；算尺人群同 mix-pool-card0214.json（379 人）',
        'bonus_population': {'MIN>=500 非零': int(((MIN >= 500) & (B > 0)).sum()), 'MIN<500 非零': int(((MIN < 500) & (B > 0)).sum()), '零': int((B == 0).sum())},
        'bonus_max': float(B.max()), 'n_near_cap_0.2': res['disc']['n_near_cap'], 'theoretical_cap_C': res['disc']['cap_C'],
        'sources_sha256': {'card_0213a_ranking': sha(BASE), 'card_0214_ranking': sha(C14), 'E294_bonus_pick': sha(BP),
                           'E294_preregistration': sha(E294 / 'preregistration.md'), 'E294_results': sha(E294 / 'results.json')},
        'ranking_csv_sha256': sha(out), 'build_command': 'python -I -B -X utf8 reports/card-0.2.15-cand/build_cand.py'}
(HERE / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding='utf-8')
tw = {}
for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')):
    if r.get('overall2k'): tw[r['name']] = r['overall2k']
big = lambda r: '*' if r['pos'] in ('PF', 'C') else ''
L = ['# card 0.2.15-cand G5 清單', '', '- 非盲測：臂 H 是看過 E-294 探索後加入；門檻也在探索後寫（L-026）。', '', '## 前二十（長人標 *）', '',
     '| 名次 | 球員 | 位置 | OVR | 加分 | 0.2.14 名次（加分） | 0.2.13a 名次 | 2K27 |', '|---|---|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']}{big(r)} | {r['pos']} | {r['ovr']} | +{r['mixBonus']:.2f} | {r['rank14']}（+{r['bonus14']:.2f}） | {r['rank0']} | {tw.get(r['name'], '')} |" for r in rows[:20]]
L += ['', '## 加分最多的 15 人', '', '| 球員 | 位置 | 分鐘 | 加分 | 0.2.14 加分 | 0.2.14 → cand 名次 | 2K27 |', '|---|---|---|---|---|---|---|']
L += [f"| {r['name']} | {r['pos']} | {int(float(r['MIN']))} | +{r['mixBonus']:.2f} | +{r['bonus14']:.2f} | {r['rank14']} → {r['rank']} | {tw.get(r['name'], '')} |"
      for r in sorted(rows, key=lambda r: -r['mixBonus'])[:15]]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print(json.dumps(summ, ensure_ascii=False, indent=1)); print('\n'.join(L))
