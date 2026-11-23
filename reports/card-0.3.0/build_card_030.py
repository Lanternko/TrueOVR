"""card 0.3.0 正式卡：E-310（使用者 2026-11-23「採用並上線」；樣本外變準＝升 MINOR）。
底卡 card-0.2.15-base 的每 36 預測（predictedPer36，封頂後）再往凍結四季 RAPM 拉 30%：
  Δ ＝ 0.3·P/(P+30000)·(r − pred)（live/e310_live.py，凍結 live/e310-r4-card030.json）；回合 <1000 的人 Δ＝0。
  用人層 predNew 對 p 的斜率 b1（usage-2025-26-card0215.json）→ gRepl' ＝ gRepl ＋ b1·Δ·W(mpg)（W＝card 0.2.5 分鐘權重，同 run_c4_live.sat_w；
  卡片路線 NEG_MIN=0，D<0 也是 D·W(m)）；ovr_base' ＝ ovr_base ＋ ovr_map(gRepl') − ovr_map(gRepl)（錨點＝底卡 summary，不重取）。
  用增量而不是整條重算，底卡既有的四捨五入誤差（≤0.05）不會被放大；ovr36 欄未重算（頁面不用）。
→ reports/card-0.3.0-base/（無 MIX 加分，賽中管線 _OV 的對照卡）；
→ reports/card-0.3.0/（＋MIX 加分，疊法同 card 0.2.15；MIX 只看 mpg 所以不變，ovr＝round(ovr_0215＋同一增量, 1)）。
同分依底卡名次。新欄 rapmBlend（Δ）。回滾：卡片頁改讀 card-0.2.15。
用法（repo root）：python -I -B -X utf8 reports/card-0.3.0/build_card_030.py"""
import csv, hashlib, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE)); sys.path.insert(0, str(ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale'))
import e310_live as E3  # noqa: E402
from ovr_map import ovr_map  # noqa: E402

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
OLD_B, OLD_C, NEW_B = ROOT / 'reports/card-0.2.15-base', ROOT / 'reports/card-0.2.15', ROOT / 'reports/card-0.3.0-base'
NEW_B.mkdir(exist_ok=True)
U = json.loads((LIVE / 'usage-2025-26-card0215.json').read_text(encoding='utf-8'))
B1 = U['coef']['b1_p']
pid_of = {v['name']: int(k) for k, v in U['players'].items()}
assert all(v['has'] for v in U['players'].values())
W = lambda m: (1 - math.exp(-m / 15)) / (1 - math.exp(-36 / 15))
bs = json.loads((OLD_B / 'summary.json').read_text(encoding='utf-8')); AN = bs['anchors']
f = lambda g: float(ovr_map(g, AN))


def write(path, rows, cols):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)


# ---- 底卡
rows = list(csv.DictReader(open(OLD_B / 'ranking.csv', encoding='utf-8'))); cols = list(rows[0].keys()) + ['rapmBlend']
for r in rows:
    p, g = float(r['predictedPer36']), float(r['gRepl'])
    d = E3.delta(pid_of[r['name']], p)
    g2 = g + B1 * d * W(float(r['mpg']))
    r['rank0'] = int(r['rank']); r['ovr0'] = float(r['ovr'])
    r['rapmBlend'] = round(d, 4)
    r['predictedPer36'] = round(p + d, 3)
    r['gRepl'] = round(g2, 3)
    r['dOvr'] = f(g2) - f(g)
    r['ovr'] = round(r['ovr0'] + r['dOvr'], 1)
rows.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(rows): r['rank'] = i + 1
write(NEW_B / 'ranking.csv', rows, cols)
for fn in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'crt-attr.csv', 'rapm-T6.csv', 'three-value.csv'):
    shutil.copyfile(OLD_B / fn, NEW_B / fn)
CHANGE = ('E-310（使用者 2026-11-23「採用並上線」）：每 36 預測（封頂後）再往凍結四季 RAPM 拉 30%，'
          'Δ＝0.3·P/(P+30000)·(r−pred)，r＝0.75×無先驗四季 RAPM（2022-23～2025-26）−同位置平均；封頂不管這一項；回合<1000 不動。')
s = dict(bs)
s.update({'version': 'card 0.3.0-base', 'base': 'card-0.2.15-base＋E-310 RAPM 混合（reports/card-0.3.0/build_card_030.py）',
          'change': CHANGE, 'e310': {'w': E3.W, 'k': E3.K, 'b1_p': B1, 'frozen': 'reports/ovr-inseason-2026-27/live/e310-r4-card030.json',
                                     'frozen_sha256': sha(E3.FROZEN), 'n_blended': sum(1 for r in rows if r['rapmBlend'] != 0),
                                     'max_abs_dOvr': round(max(abs(r['ovr'] - r['ovr0']) for r in rows), 2)},
          'ovr_changed': "ovr＝ovr_0215base＋ovr_map(gRepl')−ovr_map(gRepl)，gRepl'＝gRepl＋b1·Δ·W(mpg)；ovr36 未重算",
          'prev_ranking_csv_sha256': bs['ranking_csv_sha256'], 'ranking_csv_sha256': sha(NEW_B / 'ranking.csv'),
          'build_command': 'python -I -B -X utf8 reports/card-0.3.0/build_card_030.py'})
(NEW_B / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
base_ovr = {r['name']: r for r in rows}

# ---- 正式卡（＋MIX）
old = list(csv.DictReader(open(OLD_C / 'ranking.csv', encoding='utf-8'))); ccols = list(old[0].keys()) + ['rapmBlend']
for r in old:
    b = base_ovr[r['name']]
    assert abs(float(r['ovr']) - (b['ovr0'] + float(r['mixBonus']))) <= 0.051, r['name']   # mixBonus 欄已先四捨五入到 3 位
    r['rank0'] = int(r['rank']); r['ovr_old'] = float(r['ovr'])
    r['predictedPer36'], r['gRepl'], r['rapmBlend'] = b['predictedPer36'], b['gRepl'], b['rapmBlend']
    r['ovr'] = round(r['ovr_old'] + b['dOvr'], 1)   # 直接加增量（避開 mixBonus 欄的二次四捨五入）
old.sort(key=lambda r: (-r['ovr'], r['rank0']))
for i, r in enumerate(old): r['rank'] = i + 1
write(HERE / 'ranking.csv', old, ccols)
for fn in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'crt-attr.csv', 'rapm-T6.csv', 'three-value.csv', 'bbref-alias.csv'):
    shutil.copyfile(OLD_C / fn, HERE / fn)
cs = json.loads((OLD_C / 'summary.json').read_text(encoding='utf-8'))
cs.update({'version': 'card 0.3.0', 'base': 'card 0.3.0-base（reports/card-0.3.0-base/）＋MIX 加分同 card 0.2.15',
           'change': CHANGE, 'e310': s['e310'], 'ovr_changed': "ovr＝round(ovr_0215＋ovr_map(gRepl')−ovr_map(gRepl), 1)（＝底卡 0.3.0 同一增量＋MIX 加分）；rank 依新 ovr 重排、同分依 card 0.2.15 名次",
           'base_ranking_csv_sha256': s['ranking_csv_sha256'], 'card_0215_ranking_csv_sha256': sha(OLD_C / 'ranking.csv'),
           'ranking_csv_sha256': sha(HERE / 'ranking.csv'), 'build_command': 'python -I -B -X utf8 reports/card-0.3.0/build_card_030.py'})
(HERE / 'summary.json').write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding='utf-8')

# ---- G5 清單（對 card 0.2.15）
L = ['# card 0.3.0 G5 清單（E-310 RAPM 混合，對 card 0.2.15）', '', '## 前二十', '',
     '| 名次 | 球員 | OVR | 0.2.15 名次（OVR） | 混合量 |', '|---|---|---|---|---|']
L += [f"| {r['rank']} | {r['name']} | {r['ovr']} | {r['rank0']}（{r['ovr_old']}） | {r['rapmBlend']:+.3f} |" for r in old[:20]]
mv = [r for r in old if (r['rank'] <= 100 or r['rank0'] <= 100) and abs(r['rank'] - r['rank0']) >= 10]
L += ['', f'## 前 100 名次變動 ≥10（{len(mv)} 人）', '', '| 球員 | 0.2.15 | 0.3.0 | OVR 變化 |', '|---|---|---|---|']
L += [f"| {r['name']} | {r['rank0']} | {r['rank']} | {r['ovr'] - r['ovr_old']:+.1f} |" for r in sorted(mv, key=lambda r: r['rank'] - r['rank0'])]
t20o = {r['name'] for r in old if r['rank0'] <= 20}; t20n = {r['name'] for r in old if r['rank'] <= 20}
L += ['', f'前 20 名進出：進 {sorted(t20n - t20o)}、出 {sorted(t20o - t20n)}；最大 |ΔOVR| {max(abs(r["ovr"] - r["ovr_old"]) for r in old):.1f}']
(HERE / 'g5.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print('\n'.join(L[-1:]), f'；前 100 名移動 ≥10：{len(mv)} 人；混合 {s["e310"]["n_blended"]} 人')
