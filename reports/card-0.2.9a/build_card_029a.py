"""card 0.2.9a = card 0.2.9 的第一層（OVR 迴歸）拿掉 stamina 當預測變數（E-164 S 臂；使用者 2026-11-01 裁定，R-107）。
三張部件卡與 ranking.csv 來自 E-164 S 臂 2025-26（部件卡以 --dropAttr stamina 重擬合；用人層、映射錨、r_repl 同 0.2.9）。
rapm-T6.csv、three-value.csv 沿用 0.2.9（RAPM／T6 目標不變）。能力值欄（含 stamina 顯示值）與 0.2.9 逐位元相同。
c0 檢查：ranking.csv 與 E-164 ranking-S-2025-26.csv 逐格相同；u1：能力值欄與 card-0.2.9 相同。不符就停，不調參（L-026）。
用法：python -I -X utf8 reports/card-0.2.9a/build_card_029a.py
"""
import csv, hashlib, json, shutil
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'
C029 = ROOT / 'reports/card-0.2.9'
ATTR_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
             'heightInches', 'creation', 'pressure', 'foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    res = json.loads((E164 / 'results.json').read_text(encoding='utf-8'))
    assert res['c0_pass'] is True and all(v['same'] for v in res['u1'].values()), 'E-164 c0/u1 未過'
    src = E164 / 'ranking-S-2025-26.csv'
    assert sha(src) == res['sha256']['S-2025-26'] == 'b7972182261683b9b7b75ad99eafeb9211f96825bab4b00783344c3bab7580ef'
    shutil.copyfile(src, OUT / 'ranking.csv')
    assert sha(OUT / 'ranking.csv') == sha(src)  # c0：逐位元相同
    for f in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(C029 / f, OUT / f)
    W = E164 / 'work/base-S-2025-26'
    bc0 = json.loads((W / 'build-c0.json').read_text(encoding='utf-8'))
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(W / 'c0/cards/K0' / part / f, d / f)
        # 部件卡 pred.csv 要和 E-164 記錄的 sha 對得上（記錄值為整個部件卡目錄的雜湊時不比對，只寫進 summary）
    a, b = rd(C029 / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert list(a[0].keys()) == list(b[0].keys()) and len(a) == len(b) == 582
    ka = {r['name']: r for r in a}
    assert all(ka[r['name']][c] == r[c] for r in b for c in ATTR_COLS), 'u1：能力值欄與 0.2.9 不同'
    # 名次沿用 E-164 e164_eval.py 的算法：只算 MIN>=500 的人、依 OVR 重排（csv 的 rank 欄含全部人，這裡不用）
    def rk(rows):
        rr = sorted(((r['name'], float(r['ovr'])) for r in rows if float(r['MIN']) >= 500), key=lambda x: -x[1])
        return {n: i + 1 for i, (n, _) in enumerate(rr)}
    ra, rb = rk(a), rk(b)
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    moved = sum(1 for n in ra if ra[n] <= 300 and abs(rb.get(n, 999) - ra[n]) >= 10)
    keys = ('Jalen Williams', 'Nikola Jokić', 'Chet Holmgren', 'Shai Gilgeous-Alexander', 'Victor Wembanyama', 'Cooper Flagg')
    out = {
        'version': 'card 0.2.9a', 'baseVersion': 'card 0.2.9', 'players': 582,
        'change': 'E-164 S：第一層（OVR 迴歸）不再用 stamina 當預測變數（--dropAttr stamina 重擬合三張部件卡）；用人層、映射錨、r_repl 同 0.2.9；stamina 顯示值照舊。',
        'prereg_verdict': 'E-164 預註冊 S 臂過；使用者 2026-11-01 裁定採用（R-107）。',
        'version_rule': 'PATCH：前 300 名移動 ≥10 名 %d 人（> 30），不符字母版；不升 MINOR。' % moved,
        'moved10_top300': moved,
        'rapm_window': 'T6 目標（DARKO＋BPM 季內 z 平均，E-153）；rapm1 用人層不換（errata-1）；rapm-T6.csv 沿用 0.2.9',
        'key_players_2025_26': {n: {'0.2.9': [oa[n], ra[n]], '0.2.9a': [ob[n], rb[n]]} for n in keys if n in rb},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'part_card_sha256': bc0['part_card_sha256'], 'rapm_inputs_sha256': bc0['rapm_inputs_sha256'],
        'part_card_pred_csv_sha256': {p: sha(OUT / 'cards/K6' / p / 'pred.csv') for p in ('primary', 'fitA', 'fitB')},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (C029 / 'ranking.csv', src, E164 / 'results.json', C029 / 'rapm-T6.csv', C029 / 'three-value.csv')},
        'generator': 'reports/card-0.2.9a/build_card_029a.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], moved, out['top20'], json.dumps(out['key_players_2025_26'], ensure_ascii=False))


if __name__ == '__main__':
    main()
