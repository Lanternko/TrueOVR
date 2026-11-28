"""E-210 A（歷屆真新秀，E-141 母體）＋B（2025-26 屆逐場重播）：B0（現行）對 U1。輸出 A-players.csv、B-players.csv、AB-meta.json。
A：前 20 場與季末視窗，arm=own（同 E-209 線上算法欄）與 e116（線上的收縮臂）各算一次。
B：N=0..20、30、季末；arm=e116（同 E-209 B）。同一份窗口卡的算法：B0／U1 各用自己的 x0 重算視窗（fake_cards 帶 x0 的 creation）。"""
import sys, json, csv, time
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E210-rookie-usage-start')
sys.stdout.reconfigure(encoding='utf-8')
import u1_lib as U
L, RW = U.L, U.RW

t0 = time.time()
en = L.init()
L.install_split_creation(en)
CH = {'B0': U._CHAIN0, 'U1': U.chain_u1}
MK = {'B0': L.make_rk, 'U1': U.make_rk_u1}
meta = {'head': L.HEAD_SHA}

# ---------------- A
outA = []
for s in L.SEASONS:
    pop = L.read_pop(s)
    target = en.C.CHAIN[s]['target']
    sd, rowsby, gmax = L.target_data(en, target)
    per = {}
    for v in CH:
        rks = [MK[v](en, int(r['playerId']), r['name'], int(r['pick']), r['pos'], r['kind'], s) for r in pop]
        ng = {rk['playerId']: len(L.own_list(rowsby, rk['playerId'])) for rk in rks}
        with L.mask_creation(en, s):
            rec20 = L.window_recs(en, s, rks, {rk['playerId']: (0, 20) for rk in rks})
            recE = L.window_recs(en, s, rks, {rk['playerId']: (0, ng[rk['playerId']]) for rk in rks})
        per[v] = (rks, rec20, recE, ng)
    for i, r in enumerate(pop):
        pid = int(r['playerId'])
        row = {'season': s, 'playerId': pid, 'name': r['name'], 'pick': int(r['pick']), 'kind': r['kind'], 'pos': r['pos'],
               'ownGames': per['B0'][3][pid], 'minTot': r['minTot'], 'curve': per['B0'][0][i]['T']}
        for v in CH:
            rks, rec20, recE, ng = per[v]
            rk = rks[i]
            row[f'delta_{v}'] = rk['delta']
            for arm in ('own', 'e116'):
                for tag, rec in (('w20', rec20), ('end', recE)):
                    o = U.window_ovr2(en, rk, rec.get(pid), arm, CH[v])
                    row[f'{v}_{arm}_{tag}'] = o['ovr']
                    row[f'{v}_{arm}_{tag}_raw'] = o['raw']
        outA.append(row)
    print('A', s, len(pop), round(time.time() - t0), 's', flush=True)
with open(U.HERE / 'A-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(outA[0])); w.writeheader(); w.writerows(outA)

# ---------------- B：2025-26 屆（人群與補人同 E-209 run_BC）
target = '2025-26'
sd, rowsby, gmax = L.target_data(en, target)
pop = L.read_pop('D3')
people = [(int(r['playerId']), r['name'], int(r['pick']), r['pos'], r['kind'], False) for r in pop]
have = {p[0] for p in people}
bs = json.load(open(L.ROOT / 'data/benchmark-source/bio.json', encoding='utf-8'))
rs = bs['resultSets'][0] if 'resultSets' in bs else bs['data']['resultSets'][0]
filled = []
for row in rs['rowSet']:
    d = dict(zip(rs['headers'], row))
    pid = int(d['PLAYER_ID'])
    if str(d['DRAFT_YEAR']) != '2025' or pid in have or pid not in sd['box']:
        continue
    lst = L.own_list(rowsby, pid)
    tot = sum(float(t[1]['MIN']) for t in lst)
    if tot < 500 or len(lst) < 30:
        continue
    try:
        pick = int(d['DRAFT_NUMBER'])
    except (TypeError, ValueError):
        continue
    en.bio[pid] = {'PLAYER_HEIGHT_INCHES': d['PLAYER_HEIGHT_INCHES'], 'PLAYER_NAME': d['PLAYER_NAME']}
    people.append((pid, d['PLAYER_NAME'], pick, L.BR.height_pos(float(d['PLAYER_HEIGHT_INCHES'])), 'drafted', True))
    filled.append(d['PLAYER_NAME'])
meta['B_supplement'] = filled
NB = list(range(0, 21)) + [30, 'end']
rowsB = {}
for v in CH:
    rks = [MK[v](en, p[0], p[1], p[2], p[3], p[4], 'D3') for p in people]
    ng = {rk['playerId']: len(L.own_list(rowsby, rk['playerId'])) for rk in rks}
    wins = {}
    for N in NB:
        if N == 0:
            continue
        wins[N] = L.window_recs(en, 'D3', rks, {rk['playerId']: (0, ng[rk['playerId']] if N == 'end' else N) for rk in rks})
    for rk, p in zip(rks, people):
        pid = rk['playerId']
        r = rowsB.setdefault(pid, {'name': rk['name'], 'playerId': pid, 'pick': rk['pick'], 'pos': rk['pos'], 'supplement': int(p[5]), 'games': ng[pid],
                                   'min6': sum(float(t[1]['MIN']) for t in L.own_list(rowsby, pid)[:6]),
                                   'minTot': sum(float(t[1]['MIN']) for t in L.own_list(rowsby, pid)), 'curve': rk['T']})
        r[f'delta_{v}'] = rk['delta']
        for N in NB:
            rec = None if N == 0 else wins[N].get(pid)
            o = U.window_ovr2(en, rk, rec, 'e116', CH[v])
            r[f'{v}_{N}'] = o['ovr']
            r[f'{v}_raw{N}'] = o['raw']
    print('B', v, len(rks), round(time.time() - t0), 's', flush=True)
rows = list(rowsB.values())
with open(U.HERE / 'B-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(meta, open(U.HERE / 'AB-meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done', round(time.time() - t0))
