"""E-208 B（2025-26 屆重播）＋C（2026 屆放進 B 的分布）。輸出 B-players.csv、C-players.csv、BC-meta.json。"""
import sys, json, csv, statistics, time
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L

t0 = time.time()
en = L.init()
L.install_split_creation(en)
NS = (3, 6, 10, 20)
meta = {}

# ---------------- B：2025-26 屆
target = '2025-26'
sd, rowsby, gmax = L.target_data(en, target)
pop = L.read_pop('D3')
rks, filled = [], []
for r in pop:
    rks.append(L.make_rk(en, int(r['playerId']), r['name'], int(r['pick']), r['pos'], r['kind'], 'D3'))
have = {rk['playerId'] for rk in rks}
# 補：E-141 的 bio（data/defense-seventh）沒有的 2025 屆球員 → 讀 data/benchmark-source/bio.json 補（選秀順位、身高）
bs = json.load(open(L.ROOT / 'data/benchmark-source/bio.json', encoding='utf-8'))
rs = bs['resultSets'][0] if 'resultSets' in bs else bs['data']['resultSets'][0]
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
    pos = L.BR.height_pos(float(d['PLAYER_HEIGHT_INCHES']))
    rk = L.make_rk(en, pid, d['PLAYER_NAME'], pick, pos, 'drafted', 'D3')
    rk['supplement'] = True
    rks.append(rk)
    filled.append({'name': d['PLAYER_NAME'], 'pick': pick, 'height': d['PLAYER_HEIGHT_INCHES'], 'minTot': tot, 'games': len(lst)})
meta['B_supplement'] = filled
print('B supplement', filled, flush=True)
ng = {rk['playerId']: len(L.own_list(rowsby, rk['playerId'])) for rk in rks}
wins = {}
for N in NS + ('end',):
    lo_hi = {rk['playerId']: (0, ng[rk['playerId']] if N == 'end' else N) for rk in rks}
    wins[N] = L.window_recs(en, 'D3', rks, lo_hi)
rowsB = []
for rk in rks:
    pid = rk['playerId']
    lst = L.own_list(rowsby, pid)
    r = {'name': rk['name'], 'playerId': pid, 'pick': rk['pick'], 'pos': rk['pos'], 'supplement': int(bool(rk.get('supplement'))),
         'games': ng[pid], 'min6': sum(float(t[1]['MIN']) for t in lst[:6]), 'minTot': sum(float(t[1]['MIN']) for t in lst),
         'start': rk['start'], 'curve': rk['T']}
    for N in NS + ('end',):
        o = L.window_ovr(en, rk, wins[N].get(pid), 'e116')
        r[f'ovr{N}'] = o['ovrC']          # 線上算法（含 usage 層）
        r[f'raw{N}'] = o['ovr']           # 只有資料更新、不含 usage 層
    rowsB.append(r)
with open(L.HERE / 'B-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(rowsB[0])); w.writeheader(); w.writerows(rowsB)
print('B done', len(rowsB), round(time.time() - t0), 's', flush=True)

# ---------------- C：2026 屆
doc = json.load(open(L.RW.ROOKIE_JSON, encoding='utf-8'))
pl = doc['players']
sd26, rowsby26, g26 = L.target_data(en, '2026-27')
det = {int(x['playerId']): x for x in json.load(open(L.ROOT / 'reports/ovr-inseason-2026-27/live/2026-10-31/rookies-detail.json', encoding='utf-8'))}
rk26 = {int(r['playerId']): r for r in csv.DictReader(open(L.ROOT / 'reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv', encoding='utf-8-sig'))}
crks = []
for rk in pl:
    rk = dict(rk)
    pid = rk['playerId']
    if pid not in det:
        continue
    rk['start'] = L.RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, rk, None, 'e116', en.rel)['ovr']
    crks.append(rk)
cn = {rk['playerId']: len(L.own_list(rowsby26, rk['playerId'])) for rk in crks}
cw = {}
for N in (6, 'now'):
    lo_hi = {rk['playerId']: (0, 6 if N == 6 else cn[rk['playerId']]) for rk in crks}
    cw[N] = L.window_recs(en, 'C26', [rk for rk in crks if cn[rk['playerId']] > 0], {k: v for k, v in lo_hi.items() if cn[k] > 0})
rowsC = []
for rk in crks:
    pid = rk['playerId']
    lst = L.own_list(rowsby26, pid)
    d = det[pid]
    r = {'name': rk['name'], 'playerId': pid, 'pick': rk['pick'], 'games': cn[pid], 'N_pub': d['N'], 'MIN26': rk26.get(pid, {}).get('MIN26', ''),
         'min6': sum(float(t[1]['MIN']) for t in lst[:6]), 'minTot': sum(float(t[1]['MIN']) for t in lst),
         'pub_ovr': d['ovr'], 'pub_last': d['lastOVR'], 'start': rk['start']}
    for N in (6, 'now'):
        if pid in cw[N] and (N == 'now' or cn[pid] >= 6):
            o = L.window_ovr(en, rk, cw[N][pid], 'e116')
            r[f'ovr{N}'], r[f'raw{N}'] = o['ovrC'], o['ovr']
        else:
            r[f'ovr{N}'] = r[f'raw{N}'] = ''
    rowsC.append(r)
with open(L.HERE / 'C-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, list(rowsC[0])); w.writeheader(); w.writerows(rowsC)
meta['C'] = {'n': len(rowsC), 'gamesLeague': len(set(r['GAME_ID'] for b in sd26['box'].values() for r in b['rows']))}
json.dump(meta, open(L.HERE / 'BC-meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('C done', len(rowsC), round(time.time() - t0), 's')
