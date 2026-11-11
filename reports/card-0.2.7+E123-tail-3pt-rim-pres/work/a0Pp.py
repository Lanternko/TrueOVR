import json, sys, hashlib
sys.path.insert(0, 'work')
import e123lib as L
R = L.ROOT / 'reports'
def tab(p):
    d = json.load(open(p, encoding='utf-8'))['data']['resultSets']; d = d[0] if isinstance(d, list) else d
    return d['headers'], [dict(zip(d['headers'], r)) for r in d['rowSet']]
out = {}
# 1) 欄位名一致
hs, hr = {}, {}
for s in L.SEASONS:
    hs[s], hr[s] = tab(R / f'defense-tenth/step4-t2/raw/{s}/0-hustle.json')
ref_h, _ = tab(R / 'card-0.2.0+E071-pressure/data/2024-25-hustle.json')
ref_m, _ = tab(R / 'card-0.2.0+E071-pressure/data/2024-25-matchups.json')
out['hustle_headers_equal_E071'] = {s: hs[s] == ref_h for s in L.SEASONS}
mh = {}
for s in L.SEASONS:
    mh[s], mr = tab(R / f'defense-tenth/step4-t2/raw/{s}/0-matchups.json')
out['matchups_headers_equal_E071'] = {s: mh[s] == ref_m for s in L.SEASONS}
# 2) 2024-25 逐列 DEFLECTIONS / CHARGES_DRAWN 相同（及全欄位）
_, ref_rows = tab(R / 'card-0.2.0+E071-pressure/data/2024-25-hustle.json')
a = {r['PLAYER_ID']: r for r in hr['2024-25']}; b = {r['PLAYER_ID']: r for r in ref_rows}
out['2024-25_rows'] = [len(hr['2024-25']), len(ref_rows)]
out['2024-25_idsets_equal'] = set(a) == set(b)
dif = [pid for pid in a if pid in b and (a[pid]['DEFLECTIONS'] != b[pid]['DEFLECTIONS'] or a[pid]['CHARGES_DRAWN'] != b[pid]['CHARGES_DRAWN'])]
out['2024-25_defl_chg_rowdiffs'] = len(dif)
out['2024-25_fullrow_rowdiffs'] = sum(1 for pid in a if pid in b and a[pid] != b[pid])
# matchups 2024-25 完全相同?
_, ma = tab(R / 'defense-tenth/step4-t2/raw/2024-25/0-matchups.json'); _, mb = tab(R / 'card-0.2.0+E071-pressure/data/2024-25-matchups.json')
out['2024-25_matchups_identical'] = ma == mb
# 3) 單位：hustle MIN vs base MIN（總分鐘）；每季 PLAYER_ID 唯一
import collections
for s in L.SEASONS:
    ids = [r['PLAYER_ID'] for r in hr[s]]
    base = {r['PLAYER_ID']: r for r in L.base_rows(s)}
    ratio = sorted(r['MIN'] / base[r['PLAYER_ID']]['MIN'] for r in hr[s] if r['PLAYER_ID'] in base and base[r['PLAYER_ID']]['MIN'] >= 500)
    out[f'{s}_hustle'] = dict(rows=len(ids), uniqueIds=len(set(ids)) == len(ids), medianHustleMIN_over_baseMIN=round(ratio[len(ratio)//2], 4), minRatio=round(ratio[0], 3), maxRatio=round(ratio[-1], 3),
                              deflPer36Median=round(sorted(r['DEFLECTIONS'] / r['MIN'] * 36 for r in hr[s] if r['MIN'] >= 500)[len([1 for r in hr[s] if r['MIN'] >= 500]) // 2], 3))
    mm = tab(R / f'defense-tenth/step4-t2/raw/{s}/0-matchups.json')[1]
    out[f'{s}_matchups'] = dict(rows=len(mm), medianPossPerRow=sorted(r['PARTIAL_POSS'] for r in mm)[len(mm)//2], tovSum=round(sum(r['MATCHUP_TOV'] or 0 for r in mm), 1), possSum=round(sum(r['PARTIAL_POSS'] or 0 for r in mm), 1))
# 2025-26: defense-tenth vs E-071
_, h25 = tab(R / 'defense-tenth/step4-t2/raw/2025-26/0-hustle.json'); _, h25e = tab(R / 'card-0.2.0+E071-pressure/data/2025-26-hustle.json')
out['2025-26_hustle_equal_E071'] = h25 == h25e
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open('work/a0Pp-result.json', 'w'), indent=1)
