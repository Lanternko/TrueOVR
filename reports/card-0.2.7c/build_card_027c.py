"""card 0.2.7c = card 0.2.7b + E-131（卡片 OVR 迴歸拿掉 physique，heightInches 保留；使用者 2026-10-30「採用並重分組」）。
ranking.csv 來自 reports/card-0.2.7b+E131-no-physique/K1/ranking.csv；能力值欄（含 physique，顯示用已拿掉）與 0.2.7b 逐位元相同。
c0：同一程式不帶 --dropAttr 重建的 K0 與 card 0.2.7b 逐位元相同（work/c0-result.json）。
R-064（對 card 0.2.7b）：前 20 換 1 人、evaluate 18/19 不減，前 300 名移動 ≥ 10 名 36 人（> 30）；使用者 2026-10-30 裁定仍用字母小版本 0.2.7c（R-084）。
three-value.csv 沿用 card 0.2.7b（threeValue 沒動）。
用法：python -I -X utf8 reports/card-0.2.7c/build_card_027c.py
"""
import csv, hashlib, json, shutil, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E131 = ROOT / 'reports/card-0.2.7b+E131-no-physique'
C027B = ROOT / 'reports/card-0.2.7b'
C027B_SHA = '361bcac61075dec1150c3b89b406ecd62dcaf4fdb5d738ccff68a0634de81105'
K1_SHA = '99466f369d53316a260f2b6d91ee056e2da8048e65d8283a68cec1322fef1655'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C027B / 'ranking.csv') == C027B_SHA
    res = json.loads((E131 / 'results.json').read_text(encoding='utf-8'))
    assert res['c0']['pass'] and res['c0']['sha256'] == C027B_SHA and res['u1']['pass']
    cards = json.loads((E131 / 'work/cards-result.json').read_text(encoding='utf-8'))
    src = E131 / 'K1/ranking.csv'
    assert sha(src) == cards['final_ranking_sha256'] == K1_SHA
    shutil.copyfile(src, OUT / 'ranking.csv')
    a, b = rd(C027B / 'ranking.csv'), rd(OUT / 'ranking.csv')
    cols = list(a[0].keys())
    assert list(b[0].keys()) == cols and len(a) == len(b) == 582 and [int(r['rank']) for r in b] == list(range(1, 583))
    shutil.copyfile(C027B / 'three-value.csv', OUT / 'three-value.csv')
    assert {r['name'] for r in b} <= {r['name'] for r in rd(OUT / 'three-value.csv')}
    shutil.copyfile(E131 / 'npm-test.log', OUT / 'npm-test.log')
    ra = {r['name']: int(r['rank']) for r in a}; rb = {r['name']: int(r['rank']) for r in b}
    movers = sorted(([n, ra[n], rb[n]] for n in ra if ra[n] <= 300 and abs(ra[n] - rb[n]) >= 10), key=lambda x: x[1])
    t20a = {n for n in ra if ra[n] <= 20}; t20b = {n for n in rb if rb[n] <= 20}
    ev = res['evaluate']
    srcs = [C027B / 'ranking.csv', C027B / 'three-value.csv', src, E131 / 'preregistration.md', E131 / 'results.json',
            E131 / 'work/c0-result.json', E131 / 'work/cards-result.json', E131 / 'evaluation.json', E131 / 'calibrate-wing.py']
    out = {
        'version': 'card 0.2.7c', 'baseVersion': 'card 0.2.7b',
        'change': 'E-131（使用者 2026-10-30 採用）：卡片 OVR 迴歸的 ATTRS 拿掉 physique（身高＋體重百分位），heightInches 保留；form／ridge 照原 CV 選法（仍 position-interactions、1.0）。能力值欄不動；physique 仍在 ranking.csv（模擬端 physEdge、reboundContest 另案）。',
        'players': 582, 'columns': cols,
        'anchors': cards['anchors']['pipeline_K1'] if 'pipeline_K1' in cards.get('anchors', {}) else res['anchors']['pipeline_K1'],
        'top20Changes': {'out': sorted(t20a - t20b), 'in': sorted(t20b - t20a)},
        'gates': {'c0': 'pass（K0 與 card 0.2.7b 逐位元相同）', 'c1': res['c1'], 'u1': 'pass（能力值欄逐位元相同）', 'm1_m2_m3': res['m'],
                  'evaluate': {k: ev[k] for k in ev if k != 'baselines'} if isinstance(ev, dict) else ev},
        'R064': {'top20_swaps': len(t20a - t20b), 'top300_movers_ge10': len(movers), 'movers_list': movers,
                 'evaluate_drop': False, 'small': False, 'versionByUser': 'card 0.2.7c（R-084：使用者裁定字母小版本）'},
        'audit': 'lead 從 results.json 重算關鍵數字（L-065）；未做 role-audit',
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'generator': 'reports/card-0.2.7c/build_card_027c.py',
        'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], out['anchors'], out['top20Changes'], 'movers', len(movers))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
