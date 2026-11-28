"""用法：E211_ROOT=<worktree> E211_START=R096|R073 python -I run_h.py <out.csv>
輸出：每人 win20（只資料，eval_rookie arm=own）。母體＝E-141 rookie-players.csv 的 246 人。"""
import sys, csv, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E211-rookie-gap-attribution')
import h_lib as L

t0 = time.time()
en = L.init()
has_cr = L.install_split_creation(en)
out = []
for s in L.SEASONS:
    pop = [r for r in L.read_pop() if r['season'] == s]
    rks = []
    for r in pop:
        rk = L.make_rk(en, int(r['playerId']), r['name'], int(r['pick']), r['pos'], s)
        rk['old'] = r
        rks.append(rk)
    with L.mask_creation(en, s, has_cr):
        rec20 = L.window_recs(en, s, rks, {rk['playerId']: (0, 20) for rk in rks})
        for rk in rks:
            pid = rk['playerId']
            e = L.RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, rk, rec20.get(pid), 'own', en.rel)
            r = rk['old']
            out.append({'season': s, 'playerId': pid, 'name': rk['name'], 'pick': rk['pick'], 'kind': r['kind'], 'start': rk['start'],
                        'win20': e['ovr'], 'old_ans0': float(r['ans0']), 'pred0': e['pred0'], 'mpgHat': e['mpgHat'],
                        **{'x_' + a: e['x'][a] for a in sorted(e['x'])}, **{'x0_' + a: rk['x0'].get(a, '') for a in sorted(e['x'])}})
    print(s, len(rks), round(time.time() - t0), 's', flush=True)
with open(sys.argv[1], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
print('has_creation_override', has_cr, 'done', round(time.time() - t0))
