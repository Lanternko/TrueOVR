"""card 0.2.14b-cand：E-295 臂 W1（MIX 加分的位置平均 m 與位置權重 w 都改 BBRef 上場位置比例 π 加權，c＝π_C＋0.243·π_PF），
其餘（z_H＝z_L−0.5·m、1.5·tanh、λ=0.5、sd、500 分鐘打折）同 card 0.2.14a。只產候選、不動線上。
判定依 errata-1（G2「距上限 0.2 內」只算上限 ≥1 分的人；字面版被權重 <0.02 的後衛以 0 加分觸發），見 reports/E295-mix-pos-continuous/errata-1.md。
也輸出 mix-pool-cand.json（每人 π、m_p、縮放），供之後賽中版接線用（新秀等缺 BBRef 的人用身高帶 π̂，表一併凍結）。
用法（repo root）：python -I -B -X utf8 reports/E295-mix-pos-continuous/errata_g2.py → python -I -B -X utf8 reports/card-0.2.14b-cand/build_cand.py"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE = ROOT / 'reports/card-0.2.13a/ranking.csv'; C14A = ROOT / 'reports/card-0.2.14a/ranking.csv'
X = ROOT / 'reports/E295-mix-pos-continuous'; BP = X / 'bonus_pick.npz'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
s = importlib.util.spec_from_file_location('e295', X / 'e295_eval.py'); E = importlib.util.module_from_spec(s); sys.modules['e295'] = E; s.loader.exec_module(E)
z = np.load(BP); assert str(z['pick']) == 'W1-errata1'
assert np.array_equal(z['bonus'], E.BON['W1'])
rows = list(csv.DictReader(open(BASE, encoding='utf-8'))); cols = list(rows[0].keys())
assert [r['name'] for r in rows] == list(z['names'])
ca = {r['name']: r for r in csv.DictReader(open(C14A, encoding='utf-8'))}
for i, (r, b) in enumerate(zip(rows, z['bonus'])):
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['rankA'] = int(ca[r['name']]['rank']); r['bonusA'] = float(ca[r['name']]['mixBonus'])
    r['mixBonus'] = round(float(b), 3); r['ovr'] = round(r['ovr0'] + float(b), 1)
    r['cShare'] = round(float(z['w'][i]), 3)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus', 'cShare'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
# 凍結檔（賽中接線用）
inf = E.INFO['W1']
hb = sorted(set(range(70, 92)))
pool = {'version': 'card／inseason 0.2.14b-cand（E-295 W1）', 'base_frozen': 'reports/ovr-inseason-2026-27/live/mix-pool-card0214a.json',
        'formula': 'w_i＝c_i＝π_C＋0.243·π_PF；m_i,k＝Σ_p π_ip·m_p,k；z_H＝z_L−0.5·m_i（缺值 0.5·m_i）；P＝(0.5·f(zR)·s_reb＋0.5·f(zC)·s_con)·s_mix·w_i；f＝1.5·tanh(z⁺/1.5)',
        'posOrder': list(E.POSL), 'mpos': {k: [float(x) for x in v] for k, v in inf['mpos'].items()},
        'scales': {'reb': inf['scales'][0], 'con': inf['scales'][1], 'mix': inf['scales'][2]},
        'heightPrior': {str(h): [round(float(x), 6) for x in E.PRIOR(h)] for h in hb},
        'heightPriorRule': '卡片 2025-26 BBRef MP≥200 的 463 人，|身高−h|≤1 吋 π 平均（不足 15 人放寬）；賽中新秀／缺 BBRef 用此表',
        'players': {E.pids[i]: {'name': E.names[i], 'pi': [round(float(x), 6) for x in E.PI_B[i]], 'src': E.SRC[i]} for i in range(E.N)}}
(HERE / 'mix-pool-cand.json').write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding='utf-8')
MIN = np.array([float(r['MIN']) for r in rows]); Bn = np.array([r['mixBonus'] for r in rows])
er = json.load(open(X / 'errata-1-results.json', encoding='utf-8'))
summ = {'version': 'card 0.2.14b-cand', 'base': 'card 0.2.13a＋MIX 加分 E-295 W1；取代對象 card 0.2.14a', 'players': len(rows),
        'change': 'E-295 臂 W1：MIX 加分的位置權重 w 與位置平均 m 都改 BBRef 2025-26 上場位置比例加權（c＝π_C＋0.243·π_PF），取代硬標籤；MP<200 往身高帶收縮、'
                  '沒有 BBRef 用身高帶。其餘同 0.2.14a。候選卡，未取代正式卡；判定依 errata-1（G2 度量修正）。',
        'bonus_population': {'MIN>=500 非零': int(((MIN >= 500) & (Bn > 0)).sum()), 'MIN<500 非零': int(((MIN < 500) & (Bn > 0)).sum()), '零': int((Bn == 0).sum())},
        'bonus_max': float(Bn.max()), 'share_source_counts': {k: E.SRC.count(k) for k in sorted(set(E.SRC))},
        'errata_near_cap_cap_ge_1': er['W1']['errata_near_cap_cap_ge_1'],
        'sources_sha256': {'card_0213a_ranking': sha(BASE), 'card_0214a_ranking': sha(C14A), 'E295_bonus_pick': sha(BP),
                           'E295_preregistration': sha(X / 'preregistration.md'), 'E295_results': sha(X / 'results.json'),
                           'E295_errata1': sha(X / 'errata-1.md'), 'mix_pool_cand': sha(HERE / 'mix-pool-cand.json')},
        'ranking_csv_sha256': sha(out),
        'build_command': 'python -I -B -X utf8 reports/E295-mix-pos-continuous/e295_eval.py → errata_g2.py → reports/card-0.2.14b-cand/build_cand.py'}
(HERE / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding='utf-8')
tw = {}
for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')):
    if r.get('overall2k'): tw[r['name']] = r['overall2k']
big = lambda r: '*' if r['cShare'] >= 0.5 else ''
L = ['# card 0.2.14b-cand G5 清單（E-295 W1）', '', '## 前二十（c≥0.5 標 *）', '',
     '| 名次 | 球員 | 標籤 | c | OVR | 加分 | 0.2.14a 名次（加分） | 2K27 |', '|---|---|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']}{big(r)} | {r['pos']} | {r['cShare']:.2f} | {r['ovr']} | +{r['mixBonus']:.2f} | {r['rankA']}（+{r['bonusA']:.2f}） | {tw.get(r['name'], '')} |" for r in rows[:20]]
L += ['', '## 加分變動最大的 15 人（對 0.2.14a）', '', '| 球員 | 標籤 | c | 分鐘 | 0.2.14a 加分 | 新加分 | 名次 | 2K27 |', '|---|---|---|---|---|---|---|---|']
L += [f"| {r['name']} | {r['pos']} | {r['cShare']:.2f} | {int(float(r['MIN']))} | +{r['bonusA']:.2f} | +{r['mixBonus']:.2f} | {r['rankA']} → {r['rank']} | {tw.get(r['name'], '')} |"
      for r in sorted(rows, key=lambda r: -abs(r['mixBonus'] - r['bonusA']))[:15]]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print(json.dumps({k: summ[k] for k in ('version', 'bonus_population', 'bonus_max', 'ranking_csv_sha256')}, ensure_ascii=False)); print('\n'.join(L))
