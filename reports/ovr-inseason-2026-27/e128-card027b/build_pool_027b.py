"""E-128 §1.2/§1.5 + errata-1/2：凍結合併池 live/pool-027b.json。
由 pool-027.json 出發：8 個非 pass 欄原樣保留；pass 欄換成 E-125 合併池（2025-26 卡片池 252 ＋ 2022-23～2024-25 的 v61 pass，
pool-P50/raw-<s>.json 的 attrs.pass，poolInfo GP>=30 且 MIN/GP>=20）；新增 threeValue 欄（E-123 T 四季合併池，MIN>=500，頂端尾巴、底端 40）；
passFreeze 另存（errata-1）。用法：python -I -B -X utf8 <本檔>"""
import hashlib, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
LIVE = REPORT / 'live'
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'v5' / 'tools')); sys.path.insert(0, str(REPORT / 'v4' / 'tools')); sys.path.insert(0, str(REPORT / 'tools'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import season_attrs_v4 as SA  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402

src = (LIVE / 'run_c4_live.py').read_text(encoding='utf-8')
BLOCK = src[src.index('# ==== E-107 026 BEGIN ===='):src.index('# ==== E-111 027 END ====')]
NS = {'SA': SA, 'IC': IC, 'math': math, 'json': json}
exec(compile(BLOCK, 'run_c4_live.py#E107+E111', 'exec'), NS)
m = type('M', (), NS)

E125 = ROOT / 'reports/card-0.2.7+E125-pass-volume'
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
OUT = LIVE / 'pool-027b.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    doc = json.loads((LIVE / 'pool-027.json').read_text(encoding='utf-8'))
    a0 = json.loads((E125 / 'a0-pass-P50.json').read_text(encoding='utf-8'))
    vals = [float(x) for x in a0['pool']]
    per = {'2025-26': len(vals)}
    for s in SEASONS[:3]:
        r = json.loads((E125 / f'pool-P50/raw-{s}.json').read_text(encoding='utf-8'))
        info = r['poolInfo']
        v = [float(x) for k, x in r['attrs']['pass'].items()
             if k in info and info[k]['GP'] > 0 and info[k]['GP'] >= 30 and info[k]['MIN'] / info[k]['GP'] >= 20]
        vals += v
        per[s] = len(v)
    old = doc['attrs']['pass']
    an = m.m26_anchors(vals)
    doc['attrs']['pass'] = {'type': 'percentile', 'top': old['top'], 'bot': old['bot'], 'anchors': an,
                            'poolPerSeason': per, 'sorted': sorted(vals)}
    print('pass', an['poolN'], per, {k: an[k] for k in ('r90', 'r99', 'r1', 'SD_pool', 'S')})
    sv = json.loads((E123 / 'work/season-values.json').read_text(encoding='utf-8'))['vals']['T']
    tv, tper = [], {}
    for s in SEASONS:
        v = [float(x['value']) for x in sv[s].values() if x['MIN'] >= 500]
        tv += v
        tper[s] = len(v)
    an3 = m.m26_anchors(tv)
    froz = {'r90': 0.3706654405623313, 'r99': 0.6134056300826886, 'S': 0.23250976007697055,
            'r1': -0.043617396216529526, 'SD_pool': 0.14366051729541052, 'poolN': 1480}
    for k, x in froz.items():
        assert abs(an3[k] - x) < 1e-12, (k, an3[k], x)
    doc['attrs']['threeValue'] = {'type': 'percentile', 'top': True, 'bot': False, 'anchors': an3,
                                  'poolPerSeason': tper, 'sorted': sorted(tv),
                                  'source': 'E-123 work/season-values.json vals.T（MIN>=500，四季合併）；errata-2'}
    print('threeValue', an3['poolN'], tper)
    doc['passFreeze'] = json.loads((HERE / 'passfreeze.json').read_text(encoding='utf-8'))
    doc['doc'] = ('E-128 凍結合併池（CARD_MODE=027b 的賽中映射）。8 欄同 pool-027；pass 換 E-125 合併池；新增 threeValue。'
                  '由 e128-card027b/build_pool_027b.py 產出；m26_load_pool() 核對 payloadSha256。')
    doc['pass027bSource'] = {'a0': {'path': (E125 / 'a0-pass-P50.json').relative_to(ROOT).as_posix(), 'sha256': sha(E125 / 'a0-pass-P50.json')},
                             **{s: {'path': f'reports/card-0.2.7+E125-pass-volume/pool-P50/raw-{s}.json',
                                    'sha256': sha(E125 / f'pool-P50/raw-{s}.json')} for s in SEASONS[:3]}}
    doc['threeValueSource'] = {'path': 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work/season-values.json',
                               'sha256': sha(E123 / 'work/season-values.json')}
    doc.pop('payloadSha256', None)
    doc['payloadSha256'] = m.m26_payload_sha(doc)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print('payloadSha256', doc['payloadSha256']); print('file sha256', sha(OUT))


main()
