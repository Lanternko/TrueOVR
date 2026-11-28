raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-107 retired guard
"""由 card 0.2.2 的 ranking.csv 產生賽中用的 2025-26 先驗卡（inseason 0.2.1，E-074）。

只換屬性欄（x0）：v5 先驗卡 prior-2025-26-v5.json 的 playerId／observed／sample／usg 等原樣保留，
16 個 card 0.2.2 屬性依姓名（兩邊各 582 人、無同名）覆寫；pressure＝card 0.2.2 的逼失誤 force（E-071 P1）。
另帶 presDisplay、foulDisc（只供顯示）。不重擬合、不改任何公式。

foulDraw 賽中更新用的凍結常數（E-070：percentile(0.75·z(FTA/36) + 0.25·z(FTA/FGA))）也寫進 JSON 的 foulDrawFreeze：
母體與門檻＝card 0.2.2 建 foulDraw 時的 2025-26 池（GP>=30 且 MPG>=20，reports/card-0.2.0+E070-foul-volume/e070_vol.py 的 in_pool），
z 的平均／標準差（ddof=0）取自池內的 rate_vol（拉回後 FTA/36）與 rate_foulDraw（拉回後 FTA/FGA），
百分位對照池內合成值 foulDraw_composite。建構時會用這組常數重算 582 人的 foulDraw，必須與 ranking.csv 一致。
用法：python -I reports/ovr-inseason-2026-27/live/build_prior_022.py
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / 'reports/ovr-inseason-2026-27/v5/data/prior-2025-26-v5.json'
CARD = ROOT / 'reports/card-0.2.2/ranking.csv'
CARD_SHA = '2102b2f6463405a3711827372cb0774af0d6b4f769d65d0403b938de1369059e'
E070 = ROOT / 'reports/card-0.2.0+E070-foul-volume/attributes-w075/attributes-new.csv'
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
BENCH = ROOT / 'data/benchmark-source'
OUT = HERE / 'prior-2025-26-card022.json'
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall',
         'help', 'stamina', 'heightInches', 'creation', 'pressure']
DISPLAY = ['presDisplay', 'foulDisc']
POOL = (30, 20)                  # build_attrs.POOL：GP>=30 且 MPG>=20
W_VOL, W_RATE = 0.75, 0.25


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def attr_of(p):
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def pct(x, arr):
    return 100 * (sum(v < x for v in arr) + 0.5 * sum(v == x for v in arr)) / len(arr)


def pool_ids():
    """build_attrs.bench_rows('base') 的池（GP>=30、MIN/GP>=20）；同 e070_vol.py。"""
    doc = json.loads((BENCH / 'base.json').read_text(encoding='utf-8'))
    rs = doc['data']['resultSets']
    rs = rs[0] if isinstance(rs, list) else rs
    rows = [dict(zip(rs['headers'], r)) for r in rs['rowSet']]
    return {str(r['PLAYER_ID']) for r in rows if r['GP'] >= POOL[0] and r['MIN'] / r['GP'] >= POOL[1]}


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
    # 驗證：凍結常數重算 foulDraw，必須等於 E-070 的 new_foulDraw 與 card 0.2.2 ranking.csv
    d_csv = max(abs(attr_of(pct(comp[p], ref)) - float(e[p]['new_foulDraw'])) for p in e)
    d_comp = max(abs(comp[p] - float(e[p]['foulDraw_composite'])) for p in e)
    by_name = {r['name']: float(r['foulDraw']) for r in ranking}
    d_card = max(abs(attr_of(pct(comp[p], ref)) - by_name[e[p]['name']]) for p in e)
    print(f'foulDraw 凍結：池 {len(pool)} 人；vol mean/std {mv:.6f}/{sv:.6f}；rate mean/std {mr:.6f}/{sr:.6f}')
    print(f'  重算 vs E-070 new_foulDraw 最大差 {d_csv:.2e}；合成值 vs csv {d_comp:.2e}；vs card 0.2.2 ranking.csv {d_card:.2e}')
    assert d_csv < 1e-4 and d_comp < 1e-5 and d_card < 0.06, '凍結常數不能重現 card 0.2.2 的 foulDraw'
    return {'formula': 'percentile_pool(0.75*z(FTA/36)+0.25*z(FTA/FGA))；z 的 mean/std（ddof=0）與百分位對照母體＝2025-26 池（GP>=30、MPG>=20），'
                       '取自 card 0.2.2 建 foulDraw 時的拉回後值（E-070 attributes-w075 的 rate_vol、rate_foulDraw、foulDraw_composite）；不用 2026-27 資料重估',
            'wVol': W_VOL, 'wRate': W_RATE, 'pool': POOL, 'poolSize': len(pool),
            'vol': {'mean': mv, 'std': sv}, 'rate': {'mean': mr, 'std': sr}, 'poolComposite': ref,
            'checkMaxAbsDiff': {'vsE070NewFoulDraw': d_csv, 'vsCardRanking': d_card}}


def main():
    if sha(CARD) != CARD_SHA:
        raise SystemExit(f'card 0.2.2 ranking.csv sha256 不符：{sha(CARD)}')
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
    doc['note'] = ('S* 的 x0：2025-26 card 0.2.2 屬性（pressure＝逼失誤 force；foulDraw 以量為主）。attrs 取自 '
                   'reports/card-0.2.2/ranking.csv；其餘欄位沿用 prior-2025-26-v5.json。presDisplay、foulDisc 只供顯示。')
    doc['sources'] = {
        'formalCard': {'file': CARD.relative_to(ROOT).as_posix(), 'sha256': sha(CARD)},
        'baseV5Prior': {'file': OLD.relative_to(ROOT).as_posix(), 'sha256': sha(OLD)},
        'foulDrawPool': {'file': E070.relative_to(ROOT).as_posix(), 'sha256': sha(E070)},
        'poolSource': {'file': (BENCH / 'base.json').relative_to(ROOT).as_posix(), 'sha256': sha(BENCH / 'base.json')},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote', OUT, len(doc['players']), 'sha256', sha(OUT))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
