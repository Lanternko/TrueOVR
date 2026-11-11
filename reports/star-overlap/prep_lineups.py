# star-overlap 預處理（跑模擬前執行，只用輸入，不看任何模擬結果）。
# python -I -X utf8 reports/star-overlap/prep_lineups.py  ->  lineups.json
# 代表輪替＝球隊整季各場 (c) 分鐘（minutes-<s>.json 的 hrC／arC）逐人平均（缺席場記 0）、前 10 人、norm 到 240（cap 48，同 E-208 minutes_rules.norm）。
# 球星＝代表輪替中 >=20 分鐘者依 OVR 代理（10 項引擎能力值平均，同 E-208 (d)；P′/P″ 差值已套用）前 4 名，同分以 pid 小者先。
import json, sys, os, collections, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); E = os.path.join(HERE, '..', 'E208-team-rating'); sys.path.insert(0, E)
from minutes_rules import norm
pa = json.load(open(f'{E}/players-attrs.json', encoding='utf-8')); A = pa['attrs']
P7 = ['drive', 'ft', 'mid', 'pass', 'rebound', 'short', 'tovSkill']
def build(s):
    inp = json.load(open(f'{E}/' + ('inputs.json' if s == '2526' else 'inputs-2425.json'), encoding='utf-8'))
    pp = json.load(open(f'{E}/' + ('pprime-day0.json' if s == '2526' else 'pprime-day0-2425.json'), encoding='utf-8'))
    mins = json.load(open(f'{E}/minutes-{s}.json', encoding='utf-8'))
    delta = {}
    for i, pid in enumerate(pp['pids']):
        d = {}
        for a in P7:
            v0, v1 = pp['day0'][a][i], pp['end'][a][i]
            if v0 is not None and v1 is not None and v0 == v0 and v1 == v1: d[a] = v0 - v1
        delta[str(pid)] = d
    def prof(pid):
        p = dict(pa['players'].get(str(pid), pa['avg']))
        for a, dv in delta.get(str(pid), {}).items(): p[a] = max(0, min(120, p[a] + dv))
        return p
    ovr = lambda pid: sum(prof(pid)[a] for a in A) / len(A)
    tot = collections.defaultdict(collections.Counter); ng = collections.Counter()
    for g in inp['games']:
        o = mins[str(g['i'])]
        for t, key in ((str(g['home']), 'hrC'), (str(g['away']), 'arC')):
            ng[t] += 1
            for p, m in o[key]: tot[t][p] += m
    out = {}
    for t in sorted(inp['teams']):
        rot = norm([[p, v / ng[t]] for p, v in tot[t].items()])
        elig = sorted([p for p, m in rot if m >= 20], key=lambda p: (-ovr(p), p))
        out[t] = {'abbr': inp['teams'][t]['abbr'], 'games': ng[t], 'rotation': rot, 'stars': elig[:4], 'nEligible': len(elig),
                  'ovrProxy': {str(p): round(ovr(p), 3) for p, _ in rot}, 'inProfile': {str(p): str(p) in pa['players'] for p, _ in rot}}
    return out
res = {'2025-26': build('2526'), '2024-25': build('2425')}
json.dump(res, open(f'{HERE}/lineups.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for s, d in res.items():
    print(s, 'teams', len(d), 'nEligible dist', dict(collections.Counter(v['nEligible'] for v in d.values())), 'teams<4:', [v['abbr'] for v in d.values() if v['nEligible'] < 4])
print(hashlib.sha256(open(f'{HERE}/lineups.json', 'rb').read()).hexdigest())
