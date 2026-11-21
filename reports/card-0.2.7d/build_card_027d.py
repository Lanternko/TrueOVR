"""card 0.2.7d = card 0.2.7c + E-147（usage 層的爛隊程度 d 從「主隊全季勝率 < 0.35」改成連續：+/- 為主混勝負，和賽中同公式；係數照常重擬合）。
使用者 2026-10-31「AB先上線」：E-147 照預註冊判 2/5（≤23 歲對 2K 降 0.0106，超過門檻 0.01），使用者看過結果後裁定採用（R-098）。
ranking.csv 來自 reports/card-0.2.7c+E147-continuous-d/D1/ranking.csv；能力值欄與 0.2.7c 相同，只動 OVR 相關欄。three-value.csv 沿用 0.2.7c。
用法：python -I -X utf8 reports/card-0.2.7d/build_card_027d.py
"""
import csv, hashlib, json, shutil
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
E147 = ROOT / 'reports/card-0.2.7c+E147-continuous-d'
C027C = ROOT / 'reports/card-0.2.7c'
C027C_SHA = '99466f369d53316a260f2b6d91ee056e2da8048e65d8283a68cec1322fef1655'
ATTR_COLS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina',
             'heightInches', 'creation', 'pressure', 'foulDisc', 'presDisplay']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def main():
    assert sha(C027C / 'ranking.csv') == C027C_SHA
    res = json.loads((E147 / 'results.json').read_text(encoding='utf-8'))
    assert res['c0']['pass'] and res['c0']['sha256'] == C027C_SHA
    src = E147 / 'D1/ranking.csv'
    assert sha(src) == res['sha']['D1']
    shutil.copyfile(src, OUT / 'ranking.csv')
    shutil.copyfile(C027C / 'three-value.csv', OUT / 'three-value.csv')
    a, b = rd(C027C / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert list(a[0].keys()) == list(b[0].keys()) and len(a) == len(b) == 582
    ka = {r['name']: r for r in a}
    assert all(ka[r['name']][c] == r[c] for r in b for c in ATTR_COLS), '能力值欄與 0.2.7c 不同'
    ra = {r['name']: int(r['rank']) for r in a}; rb = {r['name']: int(r['rank']) for r in b}
    out = {
        'version': 'card 0.2.7d', 'baseVersion': 'card 0.2.7c', 'players': 582,
        'change': 'E-147：usage 層 y·d·L 的 d 改連續 d＝clip((0.40−s)/0.10,0,1)，s＝0.7·(0.5+0.033·得失分差/(GP+10))+0.3·(W+5)/(GP+10)，主隊全季；係數重擬合。',
        'coef': res['coef'], 'metrics': res['metrics'], 'm1_m3': res['eval_D1_vs_K0']['checks'], 'R064': res['R064'],
        'prereg_verdict': '2/5：(b) 沒過（M2K ≤23 −0.0106 > 0.01）；使用者 2026-10-31 看過結果裁定採用（R-098）',
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (C027C / 'ranking.csv', src, E147 / 'results.json', E147 / 'preregistration.md')},
        'generator': 'reports/card-0.2.7d/build_card_027d.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], out['top20'])


if __name__ == '__main__':
    main()
