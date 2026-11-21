"""E-211 步驟 1：在重建的 E-141 環境（worktree 9a1cf39＋E141 資料夾）重算 ans0，逐人比對 rookie-players.csv。
用法：python -I repro_e141.py <worktree-root> <out.csv>。本檔只在 worktree 裡讀寫（輸出檔寫到指定路徑）。"""
import sys, csv, json, time
wt = sys.argv[1]; out = sys.argv[2]
sys.path.insert(0, 'D:/Projects/CODING/_wt'); import fallback  # noqa: E402,F401
sys.path.insert(0, wt + '/reports/E141-rookie-start-shift')
sys.stdout.reconfigure(encoding='utf-8')
import e141_lib as L  # noqa: E402
t0 = time.time()
ctx = L.init()
rows = []
for s in L.SEASONS:
    qual, rook, others, info = L.build_rookies(ctx, s)
    ans = L.answers(ctx, s, qual)
    for rk in qual:
        pid = rk['playerId']
        if not all(N in ans[pid] for N in L.NCHK):
            continue
        rows.append({'season': s, 'playerId': pid, 'name': rk['name'], 'pick': rk['pick'], 'ans0': ans[pid][0][0],
                     'ans5': ans[pid][5][0], 'ans10': ans[pid][10][0]})
    print(s, len(qual), round(time.time() - t0), 's', flush=True)
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
