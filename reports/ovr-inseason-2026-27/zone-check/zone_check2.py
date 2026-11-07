"""第二輪核對：window8._zone（加佔位球規則）的推導區域 vs 官方 area。
用法：python -I -X utf8 zone_check2.py <pbp 資料夾> <tag>   → 寫 zone-check-<tag>.json
門檻（看結果前由使用者定）：只對 2024-25 判定——官方 mid／short 的「推導可判斷」一致率各 ≥95%，且無法判斷比例各 ≤10%。
2025-26 只報告不判定。"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window8 as W  # noqa: E402
W.DERIVE_ZONES = True

src, tag = Path(sys.argv[1]).resolve(), sys.argv[2]
NAME = {0: 'mid', 1: 'short', None: 'other'}
conf = Counter()
und = Counter()                                   # 官方類別 -> 推導無法判斷筆數
off_r = defaultdict(lambda: [0, 0, 0, 0])
der_r = defaultdict(lambda: [0, 0, 0, 0])
files = sorted(src.glob('*.json'))
noarea = 0
for f in files:
    for a in json.loads(f.read_text(encoding='utf-8'))['data']['game']['actions']:
        if a['actionType'] != '2pt' or a.get('isFieldGoal') != 1:
            continue
        if not a.get('area'):
            noarea += 1
            continue
        o = W._zone(a)
        b = dict(a)
        b.pop('area', None)
        d = W._zone(b)
        if d is None:
            und[NAME[o]] += 1
        else:
            conf[(NAME[o], NAME[d])] += 1
        made = a.get('shotResult') == 'Made'
        for tab, k in ((off_r, o), (der_r, d)):
            if k is not None:
                v = tab[a['personId']]
                v[2 * k] += 1
                v[2 * k + 1] += made
res = {'source': str(src.relative_to(ROOT)), 'games': len(files), 'no_area_shots_skipped': noarea,
       'confusion_judged': {f'{o}->{d}': n for (o, d), n in sorted(conf.items())}, 'undetermined_by_official': dict(und)}
cats = ['mid', 'short', 'other']
print('官方\推導', *cats, '無法判斷', '一致率(可判斷)', '無法判斷比例', sep='\t')
for o in cats:
    row = [conf[(o, d)] for d in cats]
    tot = sum(row)
    allo = tot + und[o]
    res[f'agree_{o}'] = conf[(o, o)] / tot if tot else None
    res[f'undet_{o}'] = und[o] / allo if allo else None
    print(o, *row, und[o], f"{res[f'agree_{o}']:.4f}" if tot else '-', f"{res[f'undet_{o}']:.4f}" if allo else '-', sep='\t')
res['pass'] = all(res[f'agree_{c}'] >= .95 and res[f'undet_{c}'] <= .10 for c in ('mid', 'short'))
print('no_area skipped', noarea, 'games', len(files))
print('PASS' if res['pass'] else 'FAIL')
rows = []
for p in set(off_r) | set(der_r):
    o, d = off_r[p], der_r[p]
    for name, i in (('mid', 0), ('short', 2)):
        ro = o[i + 1] / o[i] if o[i] else None
        rd = d[i + 1] / d[i] if d[i] else None
        rows.append((name, p, o[i], d[i], ro, rd))
for name in ('mid', 'short'):
    rr = [r for r in rows if r[0] == name and r[4] is not None and r[5] is not None and r[2] >= 100]
    big = sorted(rr, key=lambda r: -abs(r[4] - r[5]))[:10]
    res[f'{name}_ratio_maxabsdiff_A>=100'] = abs(big[0][4] - big[0][5])
    res[f'{name}_top10_by_absdiff_A>=100'] = [{'pid': r[1], 'offA': r[2], 'derA': r[3], 'off': round(r[4], 4), 'der': round(r[5], 4)} for r in big]
    print(name, 'n', len(rr), 'max|diff|', round(res[f'{name}_ratio_maxabsdiff_A>=100'], 4))
(HERE / f'zone-check-{tag}.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
