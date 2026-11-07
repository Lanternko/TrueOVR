"""card 0.2.8 = card 0.2.7d 的 OVR 迴歸目標整個換成 T6（E-153 K6 2025-26；使用者 2026-11-01 裁定，R-102）。
ranking.csv 來自 E-153 work/K6-2025-26/c0/ranking.csv（gitignore 的 work 目錄，sha 對 results.json）；能力值欄與 0.2.7d 逐位元相同，只動 OVR 相關欄。
three-value.csv 沿用 0.2.7d。cards/K6/{primary,fitA,fitB} 是 E-153 K6 的三張部件卡（賽中用人層要讀 pred.csv／pergame-summary.json／summary.json）。
用法：python -I -X utf8 reports/card-0.2.8/build_card_028.py
"""
import csv, hashlib, json, shutil
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
C027D = ROOT / 'reports/card-0.2.7d'
C027D_SHA = None   # 由 E-153 results.json checks.rank_sha256['K0-2025-26'] 核對（c0：K0 ranking 與 0.2.7d 逐位元相同）
ATTR_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
             'heightInches', 'creation', 'pressure', 'foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    res = json.loads((E153 / 'results.json').read_text(encoding='utf-8'))
    shas = res['checks']['rank_sha256']
    assert sha(C027D / 'ranking.csv') == shas['K0-2025-26'], '0.2.7d ranking 與 E-153 c0 記錄不同'
    assert res['judgement']['verdict'] == 'adopt_candidate'
    wk = E153 / 'work/K6-2025-26/c0'
    src = wk / 'ranking.csv'
    assert sha(src) == shas['K6-2025-26'] == 'e920a840e55d7d32cb378100b2ea47b8d87a1d27587d934ea1cc8b8ec981278e'
    shutil.copyfile(src, OUT / 'ranking.csv')
    shutil.copyfile(C027D / 'three-value.csv', OUT / 'three-value.csv')
    shutil.copyfile(wk / 'rapm-R.csv', OUT / 'rapm-T6.csv')   # 賽中 align／封頂用：primary 的 T6 換進去 RAPM（504 人）
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(wk / 'cards/K0' / part / f, d / f)
    a, b = rd(C027D / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert list(a[0].keys()) == list(b[0].keys()) and len(a) == len(b) == 582
    ka = {r['name']: r for r in a}
    assert all(ka[r['name']][c] == r[c] for r in b for c in ATTR_COLS), '能力值欄與 0.2.7d 不同'
    ra = {r['name']: int(r['rank']) for r in a}; rb = {r['name']: int(r['rank']) for r in b}
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    out = {
        'version': 'card 0.2.8', 'baseVersion': 'card 0.2.7d', 'players': 582,
        'change': 'E-153 K6：OVR 迴歸目標整個換成 T6（DARKO＋BPM 季內 z 平均）；2025-26 原點 alpha=1、B12 目標表不用，primary／fitA／fitB 的 --rapm 全換 T6，usage 層 rapm1 不換（errata-1）。',
        'prereg_verdict': '4/4 全過（E-153 預註冊 §4），採用候選；使用者 2026-11-01 裁定採用（R-102）。bootstrap 90% 下界 +0.0033，邊際小。',
        'judgement': res['judgement'], 'bootstrap': res['bootstrap'],
        'key_players_2025_26': {n: {'0.2.7d': [oa[n], ra[n]], '0.2.8': [ob[n], rb[n]]} for n in
                                ('Cooper Flagg', 'Paolo Banchero', 'Anthony Edwards', 'Shai Gilgeous-Alexander', 'Herbert Jones') if n in ob},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (C027D / 'ranking.csv', src, E153 / 'results.json', E153 / 'preregistration.md', E153 / 'errata-1.md')},
        'generator': 'reports/card-0.2.8/build_card_028.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], out['top20'], out['key_players_2025_26'])


if __name__ == '__main__':
    main()
