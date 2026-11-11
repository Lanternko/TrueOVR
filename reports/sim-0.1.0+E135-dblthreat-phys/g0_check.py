# E-135 g0: flag-off runner (i=0..15, 10 smallest ids) must be bit-identical to E-102 merged-legacy for the same (opp,i) cells.
# Report-only extra: ch1 runner vs the same cells (how many draws differ).
import json, sys
E102 = '../sim-0.1.0+E102-winimp-240/merged-legacy.jsonl'
def load(p, ids=None):
    out = {}
    for l in open(p, encoding='utf8'):
        if l.strip():
            r = json.loads(l)
            if ids is None or r['id'] in ids: out[r['id']] = r
    return out
def cells(r): return {(d[0], d[1]): d for d in r['avg']['draws']}
new = {m: load(f'g0-{m}.jsonl') for m in ('legacy', 'ch1')}
old = load(E102, set(new['legacy']))
res = {'reference': E102, 'cells': '30 opponents x i=0..15, avg', 'legacy': {}, 'ch1_reportOnly': {}}
ok = len(new['legacy']) == 10
for pid in sorted(new['legacy']):
    o = cells(old[pid]); n = cells(new['legacy'][pid]); c = cells(new['ch1'][pid]) if pid in new['ch1'] else {}
    keys = sorted(n)
    same = len(keys) == 480 and all(n[k] == o[k] for k in keys)
    ok &= same
    res['legacy'][pid] = {'name': new['legacy'][pid]['avg']['name'], 'n': len(keys), 'identical': same}
    res['ch1_reportOnly'][pid] = {'n': len(c), 'cellsDifferentFromLegacy': sum(c[k] != n[k] for k in keys if k in c)}
res['pass'] = bool(ok)
json.dump(res, open('g0-check.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('g0', 'PASS' if ok else 'FAIL', 'ch1 differing cells:', sum(v['cellsDifferentFromLegacy'] for v in res['ch1_reportOnly'].values()), 'of', sum(v['n'] for v in res['ch1_reportOnly'].values()))
sys.exit(0 if ok else 1)
