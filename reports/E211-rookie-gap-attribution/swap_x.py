"""用法：E211_ROOT=<wt> python -I swap_x.py <x來源 csv(run_h 輸出)> <out.csv>：在此 worktree 的 pw／anchors 下，用另一版的窗口屬性 x 重算 OVR。
輸出 ovr_swapped；比較同一個 x 在不同版 pw 下的 OVR（x 對調 2×2）。"""
import sys, csv
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E211-rookie-gap-attribution')
import h_lib as L
en = L.init()
src = {(r['season'], r['playerId']): r for r in csv.DictReader(open(sys.argv[1], encoding='utf-8'))}
out = []
for s in L.SEASONS:
    for r in L.read_pop():
        if r['season'] != s:
            continue
        pid = int(r['playerId'])
        x = {k[2:]: float(v) for k, v in src[(s, r['playerId'])].items() if k.startswith('x_') and v != ''}
        h = float(en.bio[pid]['PLAYER_HEIGHT_INCHES'])
        mpg = float(src[(s, r['playerId'])]['mpgHat'])
        keep = {a: x[a] for a in x}
        try:
            _, _, ovr = L.RW.ovr_of(en.ns, en.pw, en.anc, en.r_repl, keep, r['pos'], mpg, h)
        except KeyError as e:
            ovr = float('nan')
        out.append({'season': s, 'playerId': pid, 'name': r['name'], 'pick': r['pick'], 'kind': r['kind'], 'ovr_swapped': ovr})
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
print('done', len(out))
