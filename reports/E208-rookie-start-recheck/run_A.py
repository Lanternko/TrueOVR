"""E-208 A：歷屆真新秀（E-141 母體）在現行 0.2.12b 管線下的前 20 場視窗 OVR 與季末卡。輸出 A-players.csv、A-meta.json。"""
import sys, json, time, csv, statistics
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L

t0 = time.time()
en = L.init()
L.install_split_creation(en)
out, meta = [], {}
for s in L.SEASONS:
    pop = L.read_pop(s)
    target = en.C.CHAIN[s]['target']
    sd, rowsby, gmax = L.target_data(en, target)
    rks = []
    for r in pop:
        pid = int(r['playerId'])
        rk = L.make_rk(en, pid, r['name'], int(r['pick']), r['pos'], r['kind'], s)
        rk['old'] = r
        rks.append(rk)
    ng = {rk['playerId']: len(L.own_list(rowsby, rk['playerId'])) for rk in rks}
    with L.mask_creation(en, s):
        rec20 = L.window_recs(en, s, rks, {rk['playerId']: (0, 20) for rk in rks})
        recE = L.window_recs(en, s, rks, {rk['playerId']: (0, ng[rk['playerId']]) for rk in rks})
        for rk in rks:
            pid = rk['playerId']
            o20 = L.window_ovr(en, rk, rec20.get(pid))
            oE = L.window_ovr(en, rk, recE.get(pid))
            r = rk['old']
            out.append({'season': s, 'playerId': pid, 'name': rk['name'], 'pick': rk['pick'], 'kind': rk['kind'], 'pos': rk['pos'],
                        'ownGames': ng[pid], 'minTot': r['minTot'], 'curve': rk['T'], 'delta': rk['delta'], 'start': rk['start'],
                        'win20': o20['ovr'], 'seasonEnd': oE['ovr'], 'win20C': o20['ovrC'], 'seasonEndC': oE['ovrC'], 'old_ans0': float(r['ans0']), 'old_ans5': float(r['ans5']),
                        'old_ans10': float(r['ans10']),
                        'mpg20': (rec20[pid]['MIN'] / rec20[pid]['GP']) if pid in rec20 else '', 'n20': rec20[pid]['GP'] if pid in rec20 else 0,
                        'wcreation': o20['w'].get('creation', ''), 'wmid': o20['w'].get('mid', ''), 'wshort': o20['w'].get('short', '')})
    sm = {a: statistics.fmean(rec20[rk['playerId']]['sample'].get(k, 0) for rk in rks if rk['playerId'] in rec20)
          for a, k in (('mid', 'midA'), ('short', 'shortA'), ('long', 'fg3a'), ('ft', 'fta'))}
    meta[s] = {'target': target, 'n': len(rks), 'creationJ': target in L.CRJ_SEASONS, 'meanSample20': sm}
    print(s, len(rks), round(time.time() - t0), 's', meta[s], flush=True)
with open(L.HERE / 'A-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(out[0]))
    w.writeheader()
    w.writerows(out)
json.dump(meta, open(L.HERE / 'A-meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done', round(time.time() - t0))
