"""E-210 合成檢查：「表現完全照預期」的新秀（視窗無資料、MPGhat 維持 mpg0），只讓場次 N 往上走。
B0：usage 層權重 min(N/10,1) → 機械爬升；U1：應該全程不動（= 起點）。用 2026 屆 42 人（live 檔的 B0 起點／U1 起點）。"""
import sys, json, statistics as S
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E210-rookie-usage-start')
sys.stdout.reconfigure(encoding='utf-8')
import u1_lib as U
L, RW = U.L, U.RW
en = L.init()
b0 = json.load(open(RW.ROOKIE_JSON, encoding='utf-8'))['players']
u1 = {p['playerId']: p for p in json.load(open(U.HERE / 'rookie-prior-2026-u1.json', encoding='utf-8'))['players']}
rows = {}
for N in (0, 1, 3, 6, 10, 20):
    d = {'B0': [], 'U1': []}
    for rk in b0:
        for v, r, ch in (('B0', rk, U._CHAIN0), ('U1', u1[rk['playerId']], U.chain_u1)):
            e = RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, r, None, 'e116', en.rel)
            cur = {'pid': r['playerId'], 'pred0': e['pred0'], 'mpgHat': e['mpgHat'], 'mpg0': r['mpg0']}
            d[v].append(ch(en.ns, en.pw, en.anc, en.r_repl, cur, r['pos'], N, {}, en.coef, 0.0)['ovr'])
    rows[N] = {v: S.fmean(x) for v, x in d.items()}
    rows[N]['maxAbsDevFromN0'] = {v: None for v in d}
    rows[N]['_vals'] = d
out = {}
for N in rows:
    out[N] = {v: {'mean': rows[N][v], 'meanDeltaVsN0': S.fmean(a - b for a, b in zip(rows[N]['_vals'][v], rows[0]['_vals'][v])),
                  'maxAbsDeltaVsN0': max(abs(a - b) for a, b in zip(rows[N]['_vals'][v], rows[0]['_vals'][v]))} for v in ('B0', 'U1')}
json.dump(out, open(U.HERE / 'synth-expected.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('| N | B0 平均 Δ | B0 最大 |Δ| | U1 平均 Δ | U1 最大 |Δ| |\n|---|---|---|---|---|')
for N in out:
    print(f"| {N} | {out[N]['B0']['meanDeltaVsN0']:+.2f} | {out[N]['B0']['maxAbsDeltaVsN0']:.2f} | {out[N]['U1']['meanDeltaVsN0']:+.2f} | {out[N]['U1']['maxAbsDeltaVsN0']:.2f} |")
