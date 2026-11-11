"""card 0.2.14c 正式卡：E-300 臂 M（使用者 2026-11-10「採用 M 上線」）。
＝card 0.2.14b，但 MIX 加分再乘 min(1, W(mpg))，W(m)＝(1−e^(−m/15))/(1−e^(−36/15))＝OVR 主體同一條分鐘曲線（R-025／R-047），
mpg＝card 0.2.13a 的 mpg 欄。加分底＝凍結檔 live/mix-pool-card0214b.json 的 cardBonus（同 0.2.14b，不另凍結）。
ovr＝round(ovr_0213a＋cardBonus×min(1,W(mpg)), 1)，同分依原名次；欄同 card-0.2.14b（mixBonus、cShare）＋wMin。
其他附檔與 card-0.2.14b 相同，複製過來讓本卡自足。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.14c/build_card_0214c.py"""
import csv, hashlib, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE, C14B = ROOT / 'reports/card-0.2.13a', ROOT / 'reports/card-0.2.14b'
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214b.json'
fz = json.loads(FROZEN.read_text(encoding='utf-8'))
assert fz['version'] == 'card／inseason 0.2.14b'
by_name = {v['name']: v for v in fz['players'].values()}
W = lambda m: min(1.0, (1 - math.exp(-max(m, 0.0) / 15)) / (1 - math.exp(-36 / 15)))
rows = list(csv.DictReader(open(BASE / 'ranking.csv', encoding='utf-8'))); cols = list(rows[0].keys())
cb = {r['name']: r for r in csv.DictReader(open(C14B / 'ranking.csv', encoding='utf-8'))}
POSW = fz['config']['w1']['posWeight']
for r in rows:
    q = by_name[r['name']]; wm = W(float(r['mpg']))
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['rankB'] = int(cb[r['name']]['rank']); r['bonusB'] = float(cb[r['name']]['mixBonus'])
    assert abs(r['bonusB'] - round(q['cardBonus'], 3)) < 1e-9, r['name']
    b = q['cardBonus'] * wm
    r['wMin'] = round(wm, 4); r['mixBonus'] = round(b, 3); r['ovr'] = round(r['ovr0'] + b, 1)
    r['cShare'] = round(sum(p * w for p, w in zip(q['pi'], POSW)), 3)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
out = HERE / 'ranking.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols + ['mixBonus', 'cShare', 'wMin'], extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
for f in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'pnr-attr.csv', 'rapm-T6.csv', 'three-value.csv', 'bbref-alias.csv'):
    shutil.copyfile(C14B / f, HERE / f)
s = json.loads((C14B / 'summary.json').read_text(encoding='utf-8'))
Bn = {r['name']: r['mixBonus'] for r in rows}
s.update({
    'version': 'card 0.2.14c',
    'base': 'card 0.2.14b（reports/card-0.2.14b/）；加分底同 0.2.14b 凍結檔 cardBonus',
    'change': 'E-300 臂 M（使用者 2026-11-10「採用 M 上線」）：MIX 加分再乘 min(1, W(mpg))，W＝OVR 主體分鐘曲線 (1−e^(−m/15))/(1−e^(−36/15))；mpg＝card 0.2.13a mpg 欄。其餘同 0.2.14b。',
    'ovr_changed': 'ovr = round(ovr_0213a + cardBonus×min(1,W(mpg)), 1)；rank 依新 ovr 重排、同分依原名次；新欄 wMin',
    'report': 'reports/E300-mix-minutes-opp/report.md',
    'card_0214b_ranking_csv_sha256': sha(C14B / 'ranking.csv'),
    'ranking_csv_sha256': sha(out),
    'build_command': 'python -I -B -X utf8 reports/card-0.2.14c/build_card_0214c.py',
})
s['mix']['bonus_max'] = max(Bn.values())
(HERE / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
L = ['# card 0.2.14c G5 清單（E-300 M：加分×min(1,W(mpg))）', '', '## 前二十', '',
     '| 名次 | 球員 | MPG | W | OVR | 加分 | 0.2.14b 名次（加分） |', '|---|---|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']} | {float(r['mpg']):.1f} | {r['wMin']:.2f} | {r['ovr']} | +{r['mixBonus']:.2f} | {r['rankB']}（+{r['bonusB']:.2f}） |" for r in rows[:20]]
L += ['', '## 名次變動最大的 15 人（對 0.2.14b）', '', '| 球員 | MPG | 0.2.14b 加分 | 新加分 | 名次 |', '|---|---|---|---|---|']
L += [f"| {r['name']} | {float(r['mpg']):.1f} | +{r['bonusB']:.2f} | +{r['mixBonus']:.2f} | {r['rankB']} → {r['rank']} |"
      for r in sorted(rows, key=lambda r: -abs(r['rank'] - r['rankB']))[:15]]
L += ['', '## POR 三人', '']
L += [f"- {r['name']}：{r['rankB']} → {r['rank']}（加分 +{r['bonusB']:.2f} → +{r['mixBonus']:.2f}）" for r in rows if r['name'] in ('Deni Avdija', 'Donovan Clingan', 'Robert Williams III')]
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k: s[k] for k in ('version', 'ranking_csv_sha256')}, ensure_ascii=False))
print('\n'.join(L))
