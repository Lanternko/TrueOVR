"""每季每部分的原始量表 -> work/season-values.json；sources.json（檔案、sha256、人數）。不算任何斜率。"""
import sys, json
sys.path.insert(0, 'work')
import e123lib as L

vals = {'T': {}, 'H': {}, 'P': {}}
minb = {}
src = {'T': {}, 'H': {}, 'P': {}}
for s in L.SEASONS:
    base = {int(r['PLAYER_ID']): r for r in L.base_rows(s)}
    minb[s] = {pid: float(r['MIN']) for pid, r in base.items()}
    # T
    t = L.t_season(s)
    vals['T'][s] = {pid: dict(name=v['name'], value=v['value'], N=v['N'], MIN=minb[s].get(pid)) for pid, v in t.items()}
    # H
    h = L.h_season(s)
    vals['H'][s] = {pid: dict(name=v['name'], x=v['x'], help=v['help'], n=v['n'], MIN=minb[s].get(pid)) for pid, v in h.items()}
    # P
    p = L.p_season(s, use_card_pool=(s == '2025-26'))
    vals['P'][s] = {pid: dict(name=v['name'], force=v['force'], disp=v['disp'], pressure=v['pressure'], presDisplay=v['presDisplay'], inPool=v['inPool'], GP=v['GP'], MIN=minb[s].get(pid, v['MIN'])) for pid, v in p.items()}
json.dump({'minBase': {s: {str(k): v for k, v in d.items()} for s, d in minb.items()}, 'vals': {k: {s: {str(i): x for i, x in d.items()} for s, d in v.items()} for k, v in vals.items()}},
          open('work/season-values.json', 'w', encoding='utf-8'), ensure_ascii=False)

def pool_T(s): return [pid for pid, v in vals['T'][s].items() if (v['MIN'] or 0) >= 500]
def pool_H(s): return [pid for pid, v in vals['H'][s].items() if (v['MIN'] or 0) >= 500 and v['n'] > 0]
def pool_P(s): return [pid for pid, v in vals['P'][s].items() if v['inPool']]
def elig(part, s1, s2):
    a, b = vals[part][s1], vals[part][s2]
    return [pid for pid in a if pid in b and (a[pid]['MIN'] or 0) >= 500 and (b[pid]['MIN'] or 0) >= 500]

R = L.ROOT
files = {
 'T': {s: [L.raw_dir(s).relative_to(R).as_posix() + f'/{s}-full-*.json'] + [L.base_path(s).relative_to(R).as_posix()] for s in L.SEASONS},
 'H': {s: [L.rim_path(s).relative_to(R).as_posix()] for s in L.SEASONS},
 'P': {s: [L.base_path(s).relative_to(R).as_posix(),
           (f'reports/defense-tenth/step4-t2/raw/{s}/0-hustle.json' if s in ('2022-23', '2023-24') else f'reports/card-0.2.0+E071-pressure/data/{s}-hustle.json'),
           (f'reports/defense-tenth/step4-t2/raw/{s}/0-matchups.json' if s in ('2022-23', '2023-24') else f'reports/card-0.2.0+E071-pressure/data/{s}-matchups.json')] for s in L.SEASONS},
}
import glob, hashlib
def sh(rel):
    if '*' in rel:
        fs = sorted(glob.glob(str(R / rel)))
        return {Path(f).name: L.sha(f) for f in fs}
    return L.sha(R / rel)
from pathlib import Path
out = {'note': '凍結預註冊 §2 的資料來源、人數、sha256；先於任何斜率計算寫出。池與偏離見 deviations.json（D1–D8）。',
       'preregistrationSha256': L.sha(L.E123 / 'preregistration.md'),
       'parts': {}}
for part, pool in (('T', pool_T), ('H', pool_H), ('P', pool_P)):
    pp = {'poolRule': {'T': 'MIN>=500（Base Totals 全季 MIN），且在該季 full 資料索引內；N=0 者 acc 用該季聯盟 FG3M/FG3A（D8）',
                       'H': 'MIN>=500（Base Totals）且 FGA_LT_06 合計 n>0（D1、D4）；n=0 者卡片給 70',
                       'P': '該季 GP>=30 且 MPG>=20（D3）；2025-26 用卡片池（252 人）'}[part],
          'perSeason': {}}
    for s in L.SEASONS:
        pp['perSeason'][s] = {'files': {f: sh(f) for f in files[part][s]}, 'rowsWithValue': len(vals[part][s]), 'poolN': len(pool(s))}
    pp['pairs'] = {f'{a}->{b}': len(elig(part, a, b)) for a, b in zip(L.SEASONS, L.SEASONS[1:])}
    out['parts'][part] = pp
json.dump(out, open('sources.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({p: {'pool': {s: v['poolN'] for s, v in d['perSeason'].items()}, 'pairs': d['pairs']} for p, d in out['parts'].items()}, indent=1))
