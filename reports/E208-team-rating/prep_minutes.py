# E-208 追加：上場分鐘 (c) 最近實際分鐘、(d) 照能力值排。規則寫死於預註冊。
# python -I -X utf8 reports/E208-team-rating/prep_minutes.py 2526|2425  -> minutes-<s>.json  (per game i: hrC, arC, hrD, arD)
import json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
s = sys.argv[1]
inp = json.load(open(f'{HERE}/' + ('inputs.json' if s == '2526' else 'inputs-2425.json'), encoding='utf-8'))
pp = json.load(open(f'{HERE}/' + ('pprime-day0.json' if s == '2526' else 'pprime-day0-2425.json'), encoding='utf-8'))
pa = json.load(open(f'{HERE}/players-attrs.json', encoding='utf-8')); A = pa['attrs']
P7 = ['drive', 'ft', 'mid', 'pass', 'rebound', 'short', 'tovSkill']
delta = {}
for i, pid in enumerate(pp['pids']):
    d = {}
    for a in P7:
        v0, v1 = pp['day0'][a][i], pp['end'][a][i]
        if v0 is not None and v1 is not None and v0 == v0 and v1 == v1: d[a] = v0 - v1
    delta[str(pid)] = d
def prof(pid):
    b = pa['players'].get(str(pid), pa['avg']); p = dict(b)
    for a, dv in delta.get(str(pid), {}).items(): p[a] = max(0, min(120, p[a] + dv))
    return p
def ovr(pid): p = prof(pid); return sum(p[a] for a in A) / len(A)   # OVR 代理：10 項引擎能力值平均
def pos(pid): return prof(pid)['pos']
from minutes_rules import norm, rule_c, rule_d
hist = collections.defaultdict(list); out = {}
for g in inp['games']:
    hp, ap = str(g['home']), str(g['away'])
    o = {}
    for tag, t, key in (('h', hp, 'hr'), ('a', ap, 'ar')):
        prior = hist[t][-10:]
        o[tag + 'rC'] = rule_c(prior, inp['pre'][t]); o[tag + 'rD'] = rule_d(prior, inp['pre'][t], ovr, pos)
    out[g['i']] = o
    hist[hp].append(g['hr']); hist[ap].append(g['ar'])
json.dump(out, open(f'{HERE}/minutes-{s}.json', 'w', encoding='utf-8'))
k = 200; g = inp['games'][k]
print(s, len(out), 'example game', k, g['home'])
for lab in ('hrC', 'hrD'): print(lab, [(p, round(m, 1), pos(p), round(ovr(p), 1)) for p, m in out[k]['h' + lab[1:]] ] if False else [(p, round(m, 1), pos(p), round(ovr(p), 1)) for p, m in out[k][lab]])
miss = sum(str(p) not in pa['players'] for o in out.values() for p, _ in o['hrD'] + o['arD']); print('D slots w/o profile (avg used):', miss, 'of', 20 * len(out))
