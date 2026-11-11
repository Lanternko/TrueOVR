"""E-210：U1 下 2026 屆新秀剩下的 Δ，有多少來自「實際上場分鐘高過先驗 mpg0」。
用 live-U1/ranking.csv 的 predictedPer36（=p，含防守加成）、MPGhat、N、MPG0 重算 U1 的 OVR（對照檔內 ovr，驗證），
再把 MPGhat 換成 MPG0（分鐘維持先驗；usage 層與 sat_w 都用先驗分鐘）得到「分鐘不動」的 OVR。差 = 分鐘效果。
注意 predictedPer36 在 U1 檔裡是 p（chain 的 pred，不是 predNew）。"""
import sys, csv, json, math, statistics as S
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E210-rookie-usage-start')
sys.stdout.reconfigure(encoding='utf-8')
import u1_lib as U
L, RW = U.L, U.RW
en = L.init()
ns, coef = en.ns, en.coef
rk = {int(r['playerId']): r for r in csv.DictReader(open(U.HERE / 'live-U1/ranking.csv', encoding='utf-8-sig'))}
tab = {r['name']: r for r in csv.DictReader(open(U.HERE / 'start-u1.csv', encoding='utf-8'))}
det = {int(x['playerId']): x for x in json.load(open(U.HERE / 'live-U1/rookies-detail.json', encoding='utf-8'))}


def full(p, mh):
    Lg = math.log1p(mh)
    return coef['b0'] + coef['b1_p'] * p + coef['b2_L'] * Lg + coef['b3_a'] + coef['b4_y'] + coef['b6_yL'] * Lg   # d=0（b8_ydL=0）


def ovr(p, mh, m0, n):
    w = min(n / RW.USAGE_N, 1.0)
    pn = p + (1 - w) * (full(p, m0) - p) + w * (full(p, mh) - p)
    return ns['e064_map']((pn - en.r_repl) * ns['sat_w'](mh), en.anc)


rows, err = [], []
for pid, d in det.items():
    r = rk.get(pid)
    if r is None:
        continue
    p, mh, m0, n = float(r['predictedPer36']), float(r['MPGhat']), float(r['MPG0']), int(r['N'])
    o = ovr(p, mh, m0, n)
    err.append(abs(o - float(r['ovr'])))
    T = float(tab[d['name']]['target'])
    o0 = ovr(p, m0, m0, n)           # 分鐘維持先驗
    rows.append({'name': d['name'], 'N': n, 'MIN26': float(r['MIN26']), 'MPGhat': mh, 'MPG0': m0, 'T': T, 'ovrU1': float(r['ovr']), 'dU1': float(r['ovr']) - T,
                 'dU1_minutesAtPrior': o0 - T, 'minutesEffect': o - o0})
print('verify |recomputed − file ovr| max', max(err), 'mean', S.fmean(err))
g90 = [r for r in rows if r['MIN26'] >= 90]
print('| 球員 | 場數 | 每場分鐘(MPGhat) | U1 Δ | 其中：分鐘高過先驗的部分 | 其餘（資料／防守等） |\n|---|---|---|---|---|---|')
for r in sorted(g90, key=lambda r: -r['dU1']):
    print(f"| {r['name']} | {r['N']} | {r['MPGhat']:.1f}（先驗 {r['MPG0']:.1f}） | {r['dU1']:+.1f} | {r['minutesEffect']:+.1f} | {r['dU1_minutesAtPrior']:+.1f} |")
print(f"\n≥90 分鐘 {len(g90)} 人平均：U1 Δ {S.fmean(r['dU1'] for r in g90):+.1f} = 分鐘部分 {S.fmean(r['minutesEffect'] for r in g90):+.1f} + 其餘 {S.fmean(r['dU1_minutesAtPrior'] for r in g90):+.1f}")
print(f"全部 {len(rows)} 人平均：U1 Δ {S.fmean(r['dU1'] for r in rows):+.1f} = 分鐘部分 {S.fmean(r['minutesEffect'] for r in rows):+.1f} + 其餘 {S.fmean(r['dU1_minutesAtPrior'] for r in rows):+.1f}")
json.dump(rows, open(U.HERE / 'decomp-minutes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
