"""E-141 階段 0 + 逐人逐檢查點誤差。輸出 phase0.json、rookie-players.csv。階段 0 不含任何 J／S／T。"""
import sys
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E141-rookie-start-shift')
import csv, json, copy, time
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
import e141_lib as L

HERE = L.HERE
t0 = time.time()
ctx = L.init()
c0k_old = json.load(open(HERE / 'c0k.json', encoding='utf-8'))
c0k2 = json.load(open(HERE / 'c0k2.json', encoding='utf-8'))

rows = []
c0n, c0s, c0a, c0d_s = {}, {}, {}, {}
brackets = {}
all_seasons = sorted(p.parent.name for p in (L.ROOT / 'data/defense-seventh').glob('*/bio.json'))
older_cache = {}


def has_games_in(season, pid):
    if season not in older_cache:
        try:
            sdo = L.C.load_target_season(season)
            older_cache[season] = {p for p, b in sdo['box'].items() if any(r['MIN'] > 0 for r in b['rows'])}
        except Exception as e:  # 該季沒有 box 資料
            older_cache[season] = None
    return None if older_cache[season] is None else pid in older_cache[season]


for s in L.SEASONS:
    qual, rook, others, info = L.build_rookies(ctx, s)
    kinds = Counter(r['kind'] for r in rook)
    qk = Counter(rk['meta']['kind'] for rk in qual)
    c0n[s] = {'prior': L.C.CHAIN[s]['prior'], 'target': L.C.CHAIN[s]['target'], 'drafted': kinds['drafted'], 'undrafted': kinds['undrafted'],
              'qualified': len(qual), 'qualifiedDrafted': qk['drafted'], 'qualifiedUndrafted': qk['undrafted'],
              'othersNoPriorCard': dict(Counter(o['why'] for o in others)),
              'othersQualifiedByMinutes': sum(1 for o in others if o['minTot'] >= L.MIN_TOT and o['ownGames'] >= L.MIN_GAMES),
              'undefinedAttrs': ctx.en.fit[s]['undefined'], 'pressureOpen': ctx.en.fit[s]['pressureOpen']}
    # c0d：邊界個案
    bio_older = [x for x in all_seasons if x < L.C.CHAIN[s]['prior']]
    und_q = [rk for rk in qual if rk['meta']['kind'] == 'undrafted']
    und_old = 0
    und_old_known = 0
    for rk in und_q:
        hits = [has_games_in(x, rk['playerId']) for x in bio_older]
        if any(h is not None for h in hits):
            und_old_known += 1
        if any(h for h in hits):
            und_old += 1
    c0d_s[s] = {'qualifiedTraded(多隊)': sum(1 for rk in qual if rk['meta']['nTeams'] > 1),
                'qualifiedMidSeasonStart(首場在球隊第21場後)': sum(1 for rk in qual if rk['meta']['firstTeamGame'] > 20),
                'qualifiedUndrafted': len(und_q), 'qualifiedUndraftedWithOlderSeasonGames(早於上季)': und_old,
                'olderSeasonsCheckable': len(bio_older),
                'othersNoBio': sum(1 for o in others if o['why'] == 'noBio'),
                'othersDraftedEarlier(上季無卡)': sum(1 for o in others if o['why'] == 'draftedEarlier'),
                'othersUndraftedWithPriorGames': sum(1 for o in others if o['why'] == 'undraftedWithPriorGames')}
    # c0s：開季 OVR 差
    pr = L.predictions(ctx, s, qual)
    mxs, mxo = 0.0, 0.0
    for rk in qual:
        pid = rk['playerId']
        for c, sh in L.CANDS.items():
            mxs = max(mxs, abs((pr[c][pid][0] - pr[L.BASE][pid][0]) - (sh - L.CANDS[L.BASE])))
            mxo = max(mxo, abs(pr[c][pid][0] - rk['cand'][c]['T']))
    c0s[s] = {'n': len(qual), 'maxAbsDiffVsShift': mxs, 'maxAbsOpenMinusT': mxo, 'pass': mxs < 1e-6}
    # 答案與 c0a：四個候選各算一次（非 B0r 的 x0 換成亂值，確認答案不依賴候選）
    ans = L.answers(ctx, s, qual)
    ident = True
    for c in L.CANDS:
        qc = copy.deepcopy(qual)
        for rk in qc:
            for c2 in L.CANDS:
                if c2 != L.BASE:
                    rk['cand'][c2]['x0'] = {a: 7.0 for a in rk['x0']}
        a2 = L.answers(ctx, s, qc, cand=c)
        for pid in ans:
            for N in L.NCHK:
                if N in ans[pid]:
                    ident &= (ans[pid][N][0] == a2[pid][N][0]) and (ans[pid][N][1] == a2[pid][N][1])
                else:
                    ident &= (N not in a2[pid])
    c0a[s] = {'n': len(qual), 'bitIdenticalAcrossCandidates': bool(ident)}
    for rk in qual:
        pid = rk['playerId']
        if not all(N in ans[pid] for N in L.NCHK):
            continue
        row = {'season': s, 'playerId': pid, 'name': rk['name'], 'pick': rk['pick'], 'kind': rk['meta']['kind'],
               'pos': rk['pos'], 'ownGames': rk['meta']['ownGames'], 'minTot': round(rk['meta']['minTot'], 1)}
        for N in L.NCHK:
            row[f'ans{N}'] = ans[pid][N][0]
        row['card'] = sum(ans[pid][N][0] for N in L.NCHK) / len(L.NCHK)
        for c in L.CANDS:
            row[f'delta_{c}'] = rk['cand'][c]['delta']
            for N in L.NCHK:
                row[f'pred{N}_{c}'] = pr[c][pid][N]
                row[f'err{N}_{c}'] = pr[c][pid][N] - ans[pid][N][0]
        rows.append(row)
    print(s, 'done', len(qual), round(time.time() - t0), 's', flush=True)

with open(HERE / 'rookie-players.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

train_tot = sum(c0n[s]['qualified'] for s in L.TRAIN)
test_tot = sum(c0n[s]['qualified'] for s in L.TEST)
rows_tot = Counter(r['season'] for r in rows)
phase0 = {
    'c0k_old': c0k_old,
    'c0k2': c0k2,
    'c0a': {'perSeason': c0a, 'pass': all(v['bitIdenticalAcrossCandidates'] for v in c0a.values())},
    'c0s': {'perSeason': c0s, 'pass': all(v['pass'] for v in c0s.values())},
    'c0n': {'perSeason': c0n, 'trainTotal': train_tot, 'testTotal': test_tot,
            'rowsWithAllThreeCheckpointsPerSeason': dict(rows_tot),
            'mode': '只報告' if (train_tot < 60 or test_tot < 40) else '照預註冊判定'},
    'c0d': {'perSeason': c0d_s,
            'definition': '真新秀＝DRAFT_YEAR 等於目標季起年且無上季卡列；未選秀＝bio 無選秀年且上季完全沒出賽（MIN>0 列）；其餘沒有上季卡的人列為 others 只計數。'
                          '母體門檻 季總 MIN>=500 且自己出賽>=30 場。未選秀者早於上季有出賽紀錄者因上季沒出賽而照字面納入，數量見 qualifiedUndraftedWithOlderSeasonGames。',
            'versusE139': 'E-139 §0.5 與 c0b 的文字做法：自己實作，未 import e139-prior-weight；E-139 無新秀輸出，差異只能以文字比對。'},
    'c0r': '無法比對（E-139 沒有新秀輸出；errata-1）',
    'interpretations': [
        'N=0 的預測即開季 OVR（無資料）；N=5／10 的預測用自己前 N 場視窗經 RW.eval_rookie（e116 臂）。',
        'fit[s]["undefined"] 內的屬性（歷史季沒有該資料）在預測與答案兩側都不更新，維持 x0。',
        '答案＝自己第 N+1..N+20 場視窗卡覆蓋 B0r x0 的可觀測屬性，再經 RW.ovr_of（mpg＝視窗平均分鐘）；card 欄＝三個檢查點答案平均（僅供顯示）。',
        '歷史季無防守資料，onBall／help 維持 x0（RW.eval_rookie dfn=None）。',
        'E-116 x0 擬合用 2017-2021 新秀，訓練季（Y2、Y3、Y5、Y6）形狀部分為樣本內；凍結如此，報告註明。',
        '各季 δ 在該季自己的 pw／anchor／r_repl 上對 B0r 以外的候選各自求解，求解括號 [-80,80] 失敗即中止。',
    ],
    'elapsedSec': round(time.time() - t0),
}
json.dump(phase0, open(HERE / 'phase0.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('phase0 mode', phase0['c0n']['mode'], 'train', train_tot, 'test', test_tot, 'a', phase0['c0a']['pass'], 's', phase0['c0s']['pass'])
