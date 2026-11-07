"""核對 window8._zone 的推導區域 vs 2025-26 官方 area（data/defense-a-source/pbp，1227 場）。
門檻（看結果前定）：官方 mid 的推導一致率 ≥ 95%、官方 short 的推導一致率 ≥ 95%。
用法：python -I -X utf8 zone_check.py   → 寫 zone-check.json"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window8 as W  # noqa: E402
W.DERIVE_ZONES = True

NAME = {0: 'mid', 1: 'short', None: 'other'}
conf = Counter()
off_r = defaultdict(lambda: [0, 0, 0, 0])
der_r = defaultdict(lambda: [0, 0, 0, 0])
files = sorted((ROOT / 'data/defense-a-source/pbp').glob('*.json'))
for f in files:
    for a in json.loads(f.read_text(encoding='utf-8'))['data']['game']['actions']:
        if a['actionType'] != '2pt' or a.get('isFieldGoal') != 1:
            continue
        o = W._zone(a)                                   # 有 area → 官方
        b = dict(a)
        b.pop('area', None)
        d = W._zone(b)                                   # 無 area → 推導
        conf[(NAME[o], NAME[d])] += 1
        made = a.get('shotResult') == 'Made'
        for tab, k in ((off_r, o), (der_r, d)):
            if k is not None:
                v = tab[a['personId']]
                v[2 * k] += 1
                v[2 * k + 1] += made
res = {'games': len(files), 'confusion': {f'{o}->{d}': n for (o, d), n in sorted(conf.items())}}
cats = ['mid', 'short', 'other']
print('官方\推導', *cats, '一致率', sep='\t')
for o in cats:
    row = [conf[(o, d)] for d in cats]
    tot = sum(row)
    rate = conf[(o, o)] / tot if tot else float('nan')
    res[f'agree_{o}'] = rate
    print(o, *row, f'{rate:.4f}', sep='\t')
tot = sum(conf.values())
res['agree_all'] = sum(conf[(c, c)] for c in cats) / tot
print('total', tot, 'agree_all', round(res['agree_all'], 4))
res['pass'] = res['agree_mid'] >= .95 and res['agree_short'] >= .95
print('PASS' if res['pass'] else 'FAIL')
# 球員季末原始比率
rows = []
for p in set(off_r) | set(der_r):
    o, d = off_r[p], der_r[p]
    for name, i in (('mid', 0), ('short', 2)):
        ro = o[i + 1] / o[i] if o[i] else None
        rd = d[i + 1] / d[i] if d[i] else None
        rows.append((name, p, o[i], d[i], ro, rd))
for name in ('mid', 'short'):
    rr = [r for r in rows if r[0] == name and r[4] is not None and r[5] is not None]
    for lo in (0, 100):
        s = [r for r in rr if r[2] >= lo]
        mx = max(s, key=lambda r: abs(r[4] - r[5]))
        res[f'{name}_ratio_maxdiff_attempts>={lo}'] = {'pid': mx[1], 'offA': mx[2], 'derA': mx[3], 'off': mx[4], 'der': mx[5], 'absdiff': abs(mx[4] - mx[5])}
        print(name, f'attempts>={lo}', 'n', len(s), 'max|diff|', round(abs(mx[4] - mx[5]), 4), 'pid', mx[1], mx[2], mx[3])
    top = sorted((r for r in rr if r[2] >= 100), key=lambda r: -r[2])[:10]
    res[f'{name}_top10_by_attempts'] = [{'pid': r[1], 'offA': r[2], 'derA': r[3], 'off': round(r[4], 4), 'der': round(r[5], 4)} for r in top]
    print(name, 'top10 attempts:', [(r[1], r[2], r[3], round(r[4], 3), round(r[5], 3)) for r in top])
    big = sorted((r for r in rr if r[2] >= 100), key=lambda r: -abs(r[4] - r[5]))[:10]
    res[f'{name}_top10_by_absdiff_attempts>=100'] = [{'pid': r[1], 'offA': r[2], 'derA': r[3], 'off': round(r[4], 4), 'der': round(r[5], 4)} for r in big]
    print(name, 'top10 |diff| (>=100A):', [(r[1], r[2], r[3], round(r[4], 3), round(r[5], 3)) for r in big])
(HERE / 'zone-check.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
