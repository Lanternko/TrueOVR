"""E-210：2026 屆新秀在 U1 下重解 δ（build_2k_start 同法，只是 N=0 目標含 full_prior）。
輸入：live/rookie-prior-2026-e116.json（未平移的 E-116 起點）。輸出：本資料夾 rookie-prior-2026-u1.json、start-u1.csv。不寫 live/。"""
import sys, json, csv, copy
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E210-rookie-usage-start')
sys.stdout.reconfigure(encoding='utf-8')
import u1_lib as U
L, RW, B2 = U.L, U.RW, U.B2
en = L.init()
base = json.load(open(U.RW.ROOKIE_JSON.parent / 'rookie-prior-2026-e116.json', encoding='utf-8'))
cur = json.load(open(U.RW.ROOKIE_JSON, encoding='utf-8'))
cur_by = {p['playerId']: p for p in cur['players']}
doc = copy.deepcopy(cur)
rows = []
for rk in base['players']:
    T = L.curve(rk['pick'])
    d0, o0 = B2.solve(en.ns, en.pw, en.anc, en.r_repl, en.rel, rk, T)           # B0：應重現 live 檔的 delta
    d1, o1 = U.solve_u1(en, rk, T)
    c = cur_by[rk['playerId']]
    x1 = B2.shifted(rk['x0'], d1)
    nb = next(p for p in doc['players'] if p['playerId'] == rk['playerId'])
    nb['x0'] = x1
    nb['e121'] = dict(nb.get('e121', {}), e210Delta=round(d1, 3), e210Target=round(T, 2))
    rows.append({'name': rk['name'], 'pick': rk['pick'], 'pos': rk['pos'], 'target': round(T, 2), 'delta_B0_live': c['e121']['delta'], 'delta_B0_resolved': round(d0, 3),
                 'delta_U1': round(d1, 3), 'startB0': round(o0, 2), 'startU1': round(o1, 2),
                 'U1chain_at_B0x0': round(U.n0_ovr(en, dict(rk, x0=B2.shifted(rk['x0'], d0)), U.chain_u1), 2), 'mpg0': rk['mpg0']})
doc['note'] = doc.get('note', '') + '；E-210 U1：x0 平移 δ 改在含 full_prior 的 N=0 OVR 上重解（僅供實驗，未上線）'
json.dump(doc, open(U.HERE / 'rookie-prior-2026-u1.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(U.HERE / 'start-u1.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
print('max |delta_B0_live - resolved|', max(abs(r['delta_B0_live'] - r['delta_B0_resolved']) for r in rows))
print('max |startU1-target|', max(abs(r['startU1'] - r['target']) for r in rows))
for r in rows[:6]: print(r)
