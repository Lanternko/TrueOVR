raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-107 retired guard
"""由 card 0.2.6 的 ranking.csv 產生賽中用的 2025-26 先驗卡（E-107，CARD_MODE=026）。

照 build_prior_022.py：v5 先驗卡 prior-2025-26-v5.json 的 playerId／observed／sample／usg 原樣保留，16 個屬性依姓名
從 reports/card-0.2.6/ranking.csv 覆寫（尾巴值原樣帶入、不夾 99）。presDisplay、foulDisc 只供顯示。
ranking.csv 的 sha256 先對 reports/card-0.2.6/summary.json 的 ranking_csv_sha256。

foulDraw 凍結常數（E-070 合成值的 z 平均／標準差）同 0.2.2 版；重算檢查改對 0.2.6 的量尺：
合成值 → E-101 合併池百分位（卡片端 2025-26 池＋pool/raw-2022-23..2024-25 的 foulDraw，GP>=30 且 MPG>=20）＋尾巴
（top_tail 尺 S、bot_tail 尺 SD_pool；開關照 E-090＋E-101 h1），必須重現 card 0.2.6 的 foulDraw（|差| < 0.06）。
賽中實際用的 foulDraw 映射池是 live/pool-026.json（E-107 預註冊 §2.3），不在這裡。
用法：python -I reports/ovr-inseason-2026-27/live/build_prior_026.py
"""
import bisect
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'reports/ovr-inseason-2026-27/v5/data/prior-2025-26-v5.json'
CARD = ROOT / 'reports/card-0.2.6/ranking.csv'
CARD_SUMMARY = ROOT / 'reports/card-0.2.6/summary.json'
E070 = ROOT / 'reports/card-0.2.0+E070-foul-volume/attributes-w075/attributes-new.csv'
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E101 = ROOT / 'reports/card-0.2.5+E101-crossera'
BENCH = ROOT / 'data/benchmark-source'
OUT = HERE / 'prior-2025-26-card026.json'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall',
         'help', 'stamina', 'heightInches', 'creation', 'pressure']
DISPLAY = ['presDisplay', 'foulDisc']
POOL = (30, 20)                  # build_attrs.POOL：GP>=30 且 MPG>=20
W_VOL, W_RATE = 0.75, 0.25
CEIL, K_SD, Z9990 = 150.0, 1.96, 1.044          # build_e101.py
E101_SEASONS = ['2022-23', '2023-24', '2024-25']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def pct(x, arr):
    return 100 * (sum(v < x for v in arr) + 0.5 * sum(v == x for v in arr)) / len(arr)


def pct_sorted(x, s):
    lo, hi = bisect.bisect_left(s, x), bisect.bisect_right(s, x)
    return 100 * (lo + 0.5 * (hi - lo)) / len(s)


def passed(h, a, end):
    return bool(h.get(a, {}).get(end, {}).get('pass', False))


def top_tail(d, sd):
    return 99 + (CEIL - 99) * (1 - math.exp(-max(0.0, d) / (K_SD * sd)))


def bot_tail(d, sd):
    return 40 - 15 * (1 - math.exp(-max(0.0, d) / sd))


def merged_anchors(vals):
    """同 build_e101.Pool.anchors('max')。"""
    s = sorted(float(v) for v in vals)
    n = len(s)
    r90 = min(v for v in s if pct_sorted(v, s) >= 90)
    r99 = min(v for v in s if pct_sorted(v, s) >= 99)
    r1 = max(v for v in s if pct_sorted(v, s) <= 1)
    m = sum(s) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in s) / n)
    gap = (r99 - r90) / Z9990
    return {'r90': r90, 'r99': r99, 'r1': r1, 'SD_pool': sd, 'gapScale': gap, 'S': max(gap, sd), 'poolN': n}


def pool_ids():
    """build_attrs.bench_rows('base') 的池（GP>=30、MIN/GP>=20）；同 e070_vol.py。"""
    doc = json.loads((BENCH / 'base.json').read_text(encoding='utf-8'))
    rs = doc['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    rows = [dict(zip(rs['headers'], r)) for r in rs['rowSet']]
    return {str(r['PLAYER_ID']) for r in rows if r['GP'] >= POOL[0] and r['MIN'] / r['GP'] >= POOL[1]}


def card_side_foul_pool(cur):
    """E-101 卡片端 foulDraw 合併池：2025-26 池＋pool/raw-<季>.json（in_pool：GP>=30 且 MIN/GP>=20）。
    2025-26 那段用凍結常數重算的合成值 cur（E-101 用 a0-raw 的值，兩者差 < 2e-7；用 cur 才和被映射的值同一套數字，
    否則池內球員和自己的「相等」會因 1e-7 的差變成小於／大於，百分位差 0.5/961，見 E-107 deviations）。"""
    vals = list(cur)
    per = {'2025-26': len(vals)}
    for s in E101_SEASONS:
        d = json.loads((E101 / 'pool' / f'raw-{s}.json').read_text(encoding='utf-8'))
        info = d['poolInfo']
        v = [x for k, x in d['attrs']['foulDraw'].items()
             if k in info and info[k]['GP'] > 0 and info[k]['GP'] >= POOL[0] and info[k]['MIN'] / info[k]['GP'] >= POOL[1]]
        vals += v
        per[s] = len(v)
    return vals, per


def freeze_foul_draw(ranking):
    e = {r['playerId']: r for r in csv.DictReader(E070.open(encoding='utf-8'))}
    pool = [p for p in pool_ids() if p in e]
    vol = [float(e[p]['rate_vol']) for p in pool]
    rate = [float(e[p]['rate_foulDraw']) for p in pool]

    def ms(x):
        m = sum(x) / len(x)
        return m, math.sqrt(sum((v - m) ** 2 for v in x) / len(x))     # ddof=0（同 e070_vol.zs）

    (mv, sv), (mr, sr) = ms(vol), ms(rate)
    comp = {p: W_VOL * (float(e[p]['rate_vol']) - mv) / sv + W_RATE * (float(e[p]['rate_foulDraw']) - mr) / sr for p in e}
    ref = sorted(comp[p] for p in pool)
    d_comp = max(abs(comp[p] - float(e[p]['foulDraw_composite'])) for p in e)
    # 0.2.6 量尺：合成值 → E-101 合併池（卡片端）＋尾巴，必須重現 card 0.2.6 ranking.csv 的 foulDraw
    h1 = {**json.loads((E090 / 'h1-results.json').read_text(encoding='utf-8'))['h1'],
          **json.loads((E101 / 'h1-results.json').read_text(encoding='utf-8'))['h1']}
    top, bot = passed(h1, 'foulDraw', 'top'), passed(h1, 'foulDraw', 'bot')
    mvals, per = card_side_foul_pool([comp[p] for p in pool])
    an = merged_anchors(mvals)
    msorted = sorted(float(v) for v in mvals)
    ts = json.loads((E101 / 'tail-summary.json').read_text(encoding='utf-8'))['e101']['foulDraw']
    d_anchor = max(abs(an[k] - ts[k]) for k in ('r90', 'r99', 'r1', 'SD_pool', 'S'))
    assert an['poolN'] == ts['poolN'] and d_anchor < 1e-6, ('E-101 foulDraw 合併池錨點不符', an, d_anchor)

    def map026(x):
        p = pct_sorted(x, msorted)
        if p >= 99 and top:
            return top_tail(x - an['r99'], an['S'])
        if p <= 1 and bot:
            return bot_tail(an['r1'] - x, an['SD_pool'])
        return attr_of(p)

    by_name = {r['name']: float(r['foulDraw']) for r in ranking}
    d_card = max(abs(map026(comp[p]) - by_name[e[p]['name']]) for p in e)
    print(f'foulDraw 凍結：池 {len(pool)} 人；vol mean/std {mv:.6f}/{sv:.6f}；rate mean/std {mr:.6f}/{sr:.6f}')
    print(f'  合成值 vs csv {d_comp:.2e}；E-101 合併池 n={an["poolN"]} 錨點 vs tail-summary {d_anchor:.2e}；'
          f'0.2.6 量尺重算 vs card 0.2.6 ranking.csv 最大差 {d_card:.4f}（top={top}, bot={bot}）')
    assert d_comp < 1e-5 and d_card < 0.06, '凍結常數＋E-101 合併映射不能重現 card 0.2.6 的 foulDraw'
    return {'formula': 'percentile_pool(0.75*z(FTA/36)+0.25*z(FTA/FGA))；z 的 mean/std（ddof=0）＝2025-26 池（GP>=30、MPG>=20），'
                       '同 card 0.2.2／0.2.6 建 foulDraw 時的拉回後值（E-070 attributes-w075）；不用 2026-27 資料重估。'
                       'poolComposite 是 2025-26 單季池（025 模式用）；026 模式的百分位與尾巴改用 live/pool-026.json 的 foulDraw 合併池。',
            'wVol': W_VOL, 'wRate': W_RATE, 'pool': POOL, 'poolSize': len(pool),
            'vol': {'mean': mv, 'std': sv}, 'rate': {'mean': mr, 'std': sr}, 'poolComposite': ref,
            'scale026Check': {'mapping': 'E-101 percentile_attr_merged（卡片端合併池，mode max）', 'top': top, 'bot': bot,
                              'anchors': an, 'poolPerSeason': per, 'anchorsVsTailSummaryMaxAbs': d_anchor},
            'checkMaxAbsDiff': {'compositeVsE070Csv': d_comp, 'vsCard026Ranking': d_card}}


def main():
    want = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))['ranking_csv_sha256']
    if sha(CARD) != want:
        raise SystemExit(f'card 0.2.6 ranking.csv sha256 不符：{sha(CARD)} vs summary {want}')
    doc = json.loads(OLD.read_text(encoding='utf-8'))
    ranking = list(csv.DictReader(CARD.open(encoding='utf-8')))
    rows = {r['name']: r for r in ranking}
    assert len(rows) == 582 == len(doc['players']), (len(rows), len(doc['players']))
    for p in doc['players']:
        r = rows[p['name']]
        assert r['pos'] == p['pos'], p['name']
        for a in ATTRS:
            p[a] = float(r[a])
        for a in DISPLAY:
            p[a] = float(r[a]) if r[a] != '' else None
    doc['foulDrawFreeze'] = freeze_foul_draw(ranking)
    doc['note'] = ('E-107 CARD_MODE=026 的 x0：2025-26 card 0.2.6 屬性（尾巴值原樣、不夾 99）。attrs 取自 '
                   'reports/card-0.2.6/ranking.csv；其餘欄位沿用 prior-2025-26-v5.json。presDisplay、foulDisc 只供顯示。')
    doc['sources'] = {
        'formalCard': {'file': CARD.relative_to(ROOT).as_posix(), 'sha256': sha(CARD)},
        'formalCardSummary': {'file': CARD_SUMMARY.relative_to(ROOT).as_posix(), 'sha256': sha(CARD_SUMMARY)},
        'baseV5Prior': {'file': OLD.relative_to(ROOT).as_posix(), 'sha256': sha(OLD)},
        'foulDrawPool': {'file': E070.relative_to(ROOT).as_posix(), 'sha256': sha(E070)},
        'e101TailSummary': {'file': (E101 / 'tail-summary.json').relative_to(ROOT).as_posix(), 'sha256': sha(E101 / 'tail-summary.json')},
        'poolSource': {'file': (BENCH / 'base.json').relative_to(ROOT).as_posix(), 'sha256': sha(BENCH / 'base.json')},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    n99 = {a: sum(1 for p in doc['players'] if p[a] > 99) for a in ATTRS}
    print('x0 > 99 人數：', {a: n for a, n in n99.items() if n})
    print('wrote', OUT, len(doc['players']), 'sha256', sha(OUT))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
