"""card 0.2.9 = card 0.2.8 的用人層拿掉年輕×爛隊×時間（y·d·L）折扣（E-158 Y0 2025-26；使用者 2026-11-01 裁定，R-104）。
ranking.csv 來自 E-158 ranking-Y0-2025-26.csv（sha 對 results.json）；校準的三張部件卡和 0.2.8 相同（E-158 只動用人層），cards/、rapm-T6.csv、three-value.csv 沿用 0.2.8。
能力值欄與 0.2.8 逐位元相同，只動 OVR 相關欄。
用法：python -I -X utf8 reports/card-0.2.9/build_card_029.py
"""
import csv, hashlib, json, shutil
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E158 = ROOT / 'reports/card-0.2.8+E158-young-under-T6'
C028 = ROOT / 'reports/card-0.2.8'
ATTR_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
             'heightInches', 'creation', 'pressure', 'foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    res = json.loads((E158 / 'results.json').read_text(encoding='utf-8'))
    assert res['c0_pass'] and res['verdict'] == 'Y0'
    assert sha(C028 / 'ranking.csv') == res['sha256']['K-2025-26'], '0.2.8 ranking 與 E-158 c0 記錄不同'
    src = E158 / 'ranking-Y0-2025-26.csv'
    assert sha(src) == res['sha256']['Y0-2025-26'] == '032889088a08064bf045d479f8bad442d9f288f690bc7f851f6651f66c334eae'
    shutil.copyfile(src, OUT / 'ranking.csv')
    for f in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(C028 / f, OUT / f)
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(C028 / 'cards/K6' / part / f, d / f)
    a, b = rd(C028 / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert list(a[0].keys()) == list(b[0].keys()) and len(a) == len(b) == 582
    ka = {r['name']: r for r in a}
    assert all(ka[r['name']][c] == r[c] for r in b for c in ATTR_COLS), '能力值欄與 0.2.8 不同'
    ra = {r['name']: int(r['rank']) for r in a}; rb = {r['name']: int(r['rank']) for r in b}
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    keys = ('Cooper Flagg', 'Kon Knueppel', 'Paolo Banchero', 'Stephon Castle', 'Dylan Harper', 'Brandin Podziemski', 'Kyshawn George',
            'Keyonte George', 'Shai Gilgeous-Alexander', 'Nikola Jokić')
    out = {
        'version': 'card 0.2.9', 'baseVersion': 'card 0.2.8', 'players': 582,
        'change': 'E-158 Y0：用人層設計矩陣拿掉 y·d·L（≤23 歲×E-147 連續爛隊度×時間）一欄後重擬合；rapm1 不換、校準部件卡同 0.2.8。',
        'prereg_verdict': 'E-158 預註冊 Y1、Y0 都過，依規則取 Y0（年輕 C 差 +0.106、下界 +0.035；全體 +0.001）；使用者 2026-11-01 裁定採用（R-104）。',
        'version_rule': 'PATCH：前 20 名換 1 人，但前 300 名移動 ≥10 名 160 人（> 30），不符字母版；全體 C 沒有變準，不升 MINOR。',
        'key_players_2025_26': {n: {'0.2.8': [oa[n], ra[n]], '0.2.9': [ob[n], rb[n]]} for n in keys if n in ob},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (C028 / 'ranking.csv', src, E158 / 'results.json', E158 / 'preregistration.md')},
        'generator': 'reports/card-0.2.9/build_card_029.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], out['top20'], json.dumps(out['key_players_2025_26'], ensure_ascii=False))


if __name__ == '__main__':
    main()
