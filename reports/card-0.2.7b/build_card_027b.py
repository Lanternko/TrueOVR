"""card 0.2.7b = card 0.2.7a + E-123（threeValue／help／pressure／presDisplay 開尾，R-078）。
ranking.csv 來自 rebase-027a/e123a/ranking.csv（pass 欄＝E-125 P50，help／pressure／presDisplay＝E-123 e123；其餘 card 0.2.7a 流程重跑）。
c0：同一合併程式只放 E-125，重建的 ranking.csv 與 card 0.2.7a 逐位元相同（rebase-027a/work/c0-result.json）。
R-064（對 card 0.2.7a）：前 20 換 1 人、前 300 名移動 ≥ 10 名 2 人、evaluate 18/19 不減 → 字母小版本。
用法：python -I -X utf8 reports/card-0.2.7b/build_card_027b.py
"""
import csv, hashlib, json, shutil, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
RB = E123 / 'rebase-027a'
C027A = ROOT / 'reports/card-0.2.7a/ranking.csv'
C027A_SHA = '04a9c266440511ccca0c96b8851c964577f2687d99f84c4f9f3f2d51394f165f'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C027A) == C027A_SHA
    c0 = json.loads((RB / 'work/c0-result.json').read_text(encoding='utf-8'))
    assert c0['pass'] and c0['c0a_card027a']['sha256'] == C027A_SHA
    cards = json.loads((RB / 'work/cards-result.json').read_text(encoding='utf-8'))
    j = json.loads((RB / 'work/judge.json').read_text(encoding='utf-8'))
    src = RB / 'e123a/ranking.csv'
    assert sha(src) == cards['final_ranking_sha256']
    shutil.copyfile(src, OUT / 'ranking.csv')
    a, b = rd(C027A), rd(OUT / 'ranking.csv')
    cols = list(a[0].keys())
    assert list(b[0].keys()) == cols and len(a) == len(b) == 582 and [int(r['rank']) for r in b] == list(range(1, 583))
    A = {r['name']: r for r in a}
    names = {r['name'] for r in b}
    # three-value.csv：build_card_viewer.py 只讀 name、tv_main；tv_main＝E-123 tv_main_new
    tv = rd(E123 / 'three-value-e123.csv')
    with open(OUT / 'three-value.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['playerId', 'name', 'team', 'MIN', 'long', 'vol', 'acc', 'value_main', 'tv_main'])
        for r in tv:
            w.writerow([r['playerId'], r['name'], r['team'], r['MIN'], r['long'], r['vol'], r['acc'], r['value_main'], r['tv_main_new']])
    assert names <= {r['name'] for r in tv}
    shutil.copyfile(RB / 'npm-test.log', OUT / 'npm-test.log')
    srcs = [C027A, src, E123 / 'three-value-e123.csv', E123 / 'work/def-new.csv', E123 / 'work/tail-new.csv', E123 / 'work/presDisplay-new.csv',
            RB / 'work/tail-c0a.csv', RB / 'work/tail-e123a.csv', RB / 'work/c0-result.json', RB / 'work/cards-result.json', RB / 'work/judge.json', RB / 'evaluation.json']
    t20a = {r['name'] for r in a if int(r['rank']) <= 20}; t20b = {r['name'] for r in b if int(r['rank']) <= 20}
    out = {
        'version': 'card 0.2.7b', 'baseVersion': 'card 0.2.7a',
        'change': 'E-123（R-078）疊到 card 0.2.7a：threeValue 顯示值、help、pressure／presDisplay 開尾；pass 沿用 E-125 各半。不改參數、不改 seed、不重擬尾端與錨點。',
        'players': 582, 'columns': cols,
        'columnsDifferentFromCard027a': j['cols_diff_vs_027a'],
        'anchors': cards['anchors'],
        'top20Changes': {'out': sorted(t20a - t20b), 'in': sorted(t20b - t20a)},
        'gates': {'c0': 'pass（ranking.csv 與 card 0.2.7a 逐位元相同）', 'c1': j['c1'], 'm1_m2_m3': j['m'], 'c3': j['c3'], 'c4': {'n_over140': j['c4']['n'], 'pass': j['c4']['pass']},
                  'help_pressure_presDisplay_equal_E123_e123': {k: v['n_diff'] for k, v in j['vs_e123'].items()}, 'R061': j['R061']},
        'R064': {k: j['R064'][k] for k in ('top20_swaps', 'top300_movers_ge10', 'movers_list', 'evaluate_drop', 'small')},
        'audit': '未做 role-audit 重算',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.7b/build_card_027b.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], out['anchors'], out['top20Changes'])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
