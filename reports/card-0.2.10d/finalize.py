"""card 0.2.10d（E-185）：把 work/ 的 KAU 重建結果整理成和 card-0.2.10c 同構的目錄，寫 summary.json／results.json（記錄輸入輸出 sha256）。
前提：run_all.py selfcheck、real 已跑；自我檢查（0.2.10a tail-U、不覆寫 MPG）的 ranking.csv 必須與 card-0.2.10c 逐位元相同。
用法（repo root）：python -I -X utf8 reports/card-0.2.10d/finalize.py"""
import csv, hashlib, json, shutil, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C10C = ROOT / 'reports/card-0.2.10c'
C12 = ROOT / 'reports/card-0.2.12'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rd = lambda p: list(csv.DictReader(Path(p).open(encoding='utf-8')))


def rk(rows):
    rr = sorted(((r['name'], float(r['ovr'])) for r in rows if float(r['MIN']) >= 500), key=lambda x: -x[1])
    return {n: i + 1 for i, (n, _) in enumerate(rr)}


def main():
    sc = OUT / 'work-selfcheck/KAU-2025-26/out/ranking.csv'
    assert sha(sc) == sha(C10C / 'ranking.csv'), '自我檢查失敗：關窗口重建與 card 0.2.10c 不同'
    W = OUT / 'work/KAU-2025-26/out'
    assert sha(W / 'ranking.csv') == sha(OUT / 'ranking.csv')
    a, b = rd(C10C / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert len(a) == len(b) == 582
    ra, rb = rk(a), rk(b)
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    m100 = sum(1 for n in ra if ra[n] <= 100 and abs(rb.get(n, 999) - ra[n]) >= 10)
    m300 = sum(1 for n in ra if ra[n] <= 300 and abs(rb.get(n, 999) - ra[n]) >= 10)
    keys = ('Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Stephen Curry', 'Joel Embiid', 'Franz Wagner', 'Alperen Sengun')
    uf = json.loads((OUT / 'usage-features.json').read_text(encoding='utf-8'))
    assert all(p['ok'] for p in uf['players'].values()) and uf['predNewVsPipeline'] < 1e-12
    srcs = [C12 / 'tail-U.csv', C12 / 'mpg-c82.csv', C12 / 'three-value.csv', C12 / 'mpg-L-selection.json', C10C / 'rapm-T6.csv', C10C / 'ranking.csv', ROOT / 'reports/card-0.2.10a/tail-U.csv',
            OUT / 'build.py', OUT / 'e162_build.py', OUT / 'run_all.py', ROOT / 'reports/E142-card-target/phase1-work/cands/T6-2025-26.pkl']
    out = {
        'version': 'card 0.2.10d', 'baseVersion': 'card 0.2.10c', 'players': 582,
        'change': 'E-185：long、creation（進 OVR）、threeValue（3PT 欄，只顯示）、MPG（g 的 MPG_hat）改 E-175 四季滑動窗口；建在官方 card 0.2.10c 上（E-187 KAU：修正後 T6、全部係數在這組新屬性上重擬合、傳球全位置共用斜率）。'
                  'MPG 窗口只換 g 與錨用的預測 MPG（L、設計矩陣不動），窗口長度 L=1 季（card-0.2.12/mpg-L-selection.json）。',
        'version_rule': 'R-109 字母版：前 20 名進出 %d 人、前 100 名移動 ≥10 名 %d 人。' % (len(set(n for n in ra if ra[n] <= 20) - set(n for n in rb if rb[n] <= 20)), m100),
        'moved10_top300': m300, 'moved10_top100': m100,
        'refit': {'wls_card': uf['coef'], 'r_repl': uf['rRepl'], 'anchors': uf['anchors']},
        'self_check': '輸入換回 0.2.10a 的 tail-U.csv、不覆寫 MPG，同一條鏈重建的 ranking.csv ＝ card-0.2.10c/ranking.csv 逐位元相同（work-selfcheck）',
        'key_players_2025_26': {n: {'0.2.10c': [oa[n], ra[n]], '0.2.10d': [ob[n], rb[n]]} for n in keys if n in rb and n in ra},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'part_card_sha256': {p: sha(OUT / 'cards/K6' / p / 'summary.json') for p in ('primary', 'fitA', 'fitB')},
        'part_card_pred_csv_sha256': {p: sha(OUT / 'cards/K6' / p / 'pred.csv') for p in ('primary', 'fitA', 'fitB')},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'build_command': 'python -I -B -X utf8 reports/card-0.2.10d/run_all.py selfcheck; ... run_all.py real; python -I -X utf8 reports/card-0.2.10d/finalize.py',
        'generator': 'reports/card-0.2.10d/finalize.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    res = {'selfcheck_ranking_sha256': sha(sc), 'card_0.2.10c_ranking_sha256': sha(C10C / 'ranking.csv'), 'ranking_sha256': out['ranking_csv_sha256'],
           'three_value_sha256': sha(OUT / 'three-value.csv'), 'rapm_T6_sha256': sha(OUT / 'rapm-T6.csv'), 'usage_features_sha256': sha(OUT / 'usage-features.json'),
           'usage_check': {'players': len(uf['players']), 'mismatch': 0, 'predNewVsPipeline': uf['predNewVsPipeline']}, 'sources_sha256': out['sources_sha256']}
    (OUT / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], m100, m300, out['top20'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
