"""card 0.2.14b 正式卡：E-295 臂 W1（使用者裁定採用、字母版 0.2.14b；role-audit 4/5 reports/audit-0.2.14b/）。
MIX 加分取自凍結檔 live/mix-pool-card0214b.json 的 cardBonus（mix_live.py freeze_w1：照 E-295 W1 重算，
BBRef 對名另加手動別名 bbref-alias.csv＝Ronald Holland II↔Ron Holland、Trevon Scott↔Tre Scott、Adama Bal↔Adama-Alpha Bal）。
ranking.csv＝card 0.2.13a＋mixBonus（ovr＝round(ovr_0213a＋未四捨五入加分, 1)，同分依原名次），欄同 card-0.2.14b-cand（mixBonus、cShare）；
其他附檔（three-value、gravity、pnr、def-L、rapm-T6）與 0.2.13a／0.2.14a 相同，複製過來讓本卡自足。summary.json 格式照 card-0.2.14a。
核對：別名 3 人以外，加分與 card-0.2.14b-cand 差 ≤0.02（freeze_w1 已 assert，這裡再查一次）。
用法（repo root）：python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_w1 → python -I -B -X utf8 reports/card-0.2.14b/build_card_0214b.py"""
import csv, hashlib, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE, C14A, CAND = ROOT / 'reports/card-0.2.13a', ROOT / 'reports/card-0.2.14a', ROOT / 'reports/card-0.2.14b-cand'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214b.json'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
fz = json.loads(FROZEN.read_text(encoding='utf-8'))
assert fz['version'] == 'card／inseason 0.2.14b'
assert fz['base_sha256']['mix-pool-card0214a.json'] == sha(ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214a.json')
by_name = {v['name']: v for v in fz['players'].values()}
rows = list(csv.DictReader(open(BASE / 'ranking.csv', encoding='utf-8'))); cols = list(rows[0].keys())
ca = {r['name']: r for r in csv.DictReader(open(C14A / 'ranking.csv', encoding='utf-8'))}
cc = {r['name']: r for r in csv.DictReader(open(CAND / 'ranking.csv', encoding='utf-8'))}
alias = {r['card_name'] for r in csv.DictReader(open(HERE / 'bbref-alias.csv', encoding='utf-8'))}
POSW = fz['config']['w1']['posWeight']
for r in rows:
    q = by_name[r['name']]; b = q['cardBonus']
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['rankA'] = int(ca[r['name']]['rank']); r['bonusA'] = float(ca[r['name']]['mixBonus'])
    r['rankC'] = int(cc[r['name']]['rank']); r['bonusC'] = float(cc[r['name']]['mixBonus'])
    r['mixBonus'] = round(b, 3); r['ovr'] = round(r['ovr0'] + b, 1)
    r['cShare'] = round(sum(p * w for p, w in zip(q['pi'], POSW)), 3)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
worst = max((abs(r['mixBonus'] - r['bonusC']), r['name']) for r in rows if r['name'] not in alias)
assert worst[0] <= 0.02 + 1e-9, worst
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus', 'cShare'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
for f in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'pnr-attr.csv', 'rapm-T6.csv', 'three-value.csv'):
    assert sha(BASE / f) == sha(C14A / f), f
    shutil.copyfile(BASE / f, HERE / f)
s = json.loads((BASE / 'summary.json').read_text(encoding='utf-8'))
sa = json.loads((C14A / 'summary.json').read_text(encoding='utf-8'))
scand = json.loads((CAND / 'summary.json').read_text(encoding='utf-8'))
MIN = {r['name']: float(r['MIN']) for r in rows}
Bn = {r['name']: r['mixBonus'] for r in rows}
s.update({
    'version': 'card 0.2.14b',
    'base': 'card 0.2.13a（reports/card-0.2.13a/）＋MIX 加分 E-295 W1（候選 reports/card-0.2.14b-cand/＋BBRef 手動別名 3 人）；取代 card 0.2.14a',
    'change': 'E-295 臂 W1（使用者裁定採用，字母版 0.2.14b＝修 0.2.14a 的 PF／C 標籤斷崖；role-audit 4/5 reports/audit-0.2.14b/）：MIX 加分的位置權重 w 與位置平均 m 都改 BBRef 2025-26 上場位置比例 π 加權'
              '（w＝c＝π_C＋0.243·π_PF；m_i＝Σ_p π_ip·m_p，m_p＝算尺人群以 π 加權的 z_L 平均），取代硬標籤；MP<200 往身高帶 π̂ 收縮、沒有 BBRef 用身高帶。'
              'z_H＝z_L−0.5·m_i、1.5·tanh、λ＝0.5、sd＝13.41、500 分鐘打折同 0.2.14a；三個均方根縮放在 W1 下重算（s_reb 1.05193、s_con 1.03870、s_mix 1.12362）。'
              'BBRef 對名補手動別名（Ronald Holland II、Trevon Scott、Adama Bal；audit 必修 1）。能力值、係數、錨點與 0.2.13a 相同。',
    'ovr_changed': 'ovr = round(ovr_0213a + mixBonus, 1)；rank 依新 ovr 重排、同分依原名次；欄 mixBonus、cShare（＝w）',
    'mix': {'config': {k: v for k, v in fz['config'].items() if k != 'w1'},
            'w1': {k: v for k, v in fz['config']['w1'].items() if k != 'heightPrior'},
            'frozen': 'reports/ovr-inseason-2026-27/live/mix-pool-card0214b.json', 'frozen_sha256': sha(FROZEN),
            'base_frozen_sha256': fz['base_sha256'],
            'bonus_population': {'MIN>=500 非零': sum(1 for n in Bn if MIN[n] >= 500 and Bn[n] > 0), 'MIN<500 非零': sum(1 for n in Bn if MIN[n] < 500 and Bn[n] > 0),
                                 '零': sum(1 for n in Bn if Bn[n] == 0)},
            'bonus_max': max(Bn.values()), 'share_source_counts': fz['shareSourceCounts'],
            'aliases': fz['aliases'], 'aliasBonusChange': fz['aliasBonusChange'],
            'cand_max_abs_except_alias': worst[0], 'cand_worst_except_alias': worst[1]},
    'source_cand': {'summary': 'reports/card-0.2.14b-cand/summary.json', 'ranking_csv_sha256': scand['ranking_csv_sha256'], 'sources_sha256': scand['sources_sha256']},
    'audit': 'reports/audit-0.2.14b/report.md（4/5 建議採用）',
    'card_0213a_ranking_csv_sha256': s['ranking_csv_sha256'],
    'card_0214a_ranking_csv_sha256': sa['ranking_csv_sha256'],
    'ranking_csv_sha256': sha(out),
    'build_command': 'python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_w1 → python -I -B -X utf8 reports/card-0.2.14b/build_card_0214b.py',
})
for k in ('source_cand2',):
    s.pop(k, None)
(HERE / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
tw = {}
for r in csv.DictReader(open(TWOK, encoding='utf-8-sig')):
    if r.get('overall2k'): tw[r['name']] = r['overall2k']
big = lambda r: '*' if r['cShare'] >= 0.5 else ''
L = ['# card 0.2.14b G5 清單（E-295 W1＋BBRef 別名）', '', '## 前二十（c≥0.5 標 *）', '',
     '| 名次 | 球員 | 標籤 | c | OVR | 加分 | 0.2.14a 名次（加分） | 2K27 |', '|---|---|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']}{big(r)} | {r['pos']} | {r['cShare']:.2f} | {r['ovr']} | +{r['mixBonus']:.2f} | {r['rankA']}（+{r['bonusA']:.2f}） | {tw.get(r['name'], '')} |" for r in rows[:20]]
L += ['', '## 加分變動最大的 15 人（對 0.2.14a）', '', '| 球員 | 標籤 | c | 分鐘 | 0.2.14a 加分 | 新加分 | 名次 | 2K27 |', '|---|---|---|---|---|---|---|---|']
L += [f"| {r['name']} | {r['pos']} | {r['cShare']:.2f} | {int(float(r['MIN']))} | +{r['bonusA']:.2f} | +{r['mixBonus']:.2f} | {r['rankA']} → {r['rank']} | {tw.get(r['name'], '')} |"
      for r in sorted(rows, key=lambda r: -abs(r['mixBonus'] - r['bonusA']))[:15]]
L += ['', '## 別名 3 人（對候選卡）', '', '| 球員 | c | 候選加分 | 新加分 | 候選名次 → 名次 |', '|---|---|---|---|---|']
L += [f"| {r['name']} | {r['cShare']:.2f} | +{r['bonusC']:.2f} | +{r['mixBonus']:.2f} | {r['rankC']} → {r['rank']} |" for r in rows if r['name'] in alias]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k: s[k] for k in ('version', 'ranking_csv_sha256')}, ensure_ascii=False), 'cand worst', worst)
print('\n'.join(L))
