"""E-127 phase 0：特徵、隊名、人數。讀 RAPM 只取 poss。-> phase0.json、feats-<季>.json"""
import hashlib, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
import feats as F
HERE, ROOT = F.HERE, F.ROOT
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
res = {'doc': 'E-127 phase 0', 'prereg_sha256': hashlib.sha256((HERE / 'preregistration.md').read_bytes()).hexdigest()}
assert res['prereg_sha256'] == 'dbafa0fe5aa764a7e706b58814630b4f69ab9ad3c71e889a35263203ed75e3e2'
FE, META, POSS = {}, {}, {}
for s in F.SEASONS:
    FE[s], META[s] = F.build(s)
    (HERE / f'feats-{s}.json').write_text(json.dumps({str(k): v for k, v in FE[s].items()}, ensure_ascii=False), encoding='utf-8')
    r = json.loads((E126 / f'rapm-{s}.json').read_text(encoding='utf-8'))['players']
    POSS[s] = {int(k): v['poss'] for k, v in r.items()}      # 只取 poss
    META[s]['rapmFileSha256'] = hashlib.sha256((E126 / f'rapm-{s}.json').read_bytes()).hexdigest()
res['seasons'] = META
# c0f
ref = json.loads((ROOT / 'reports/ovr-inseason-2026-27/live/usage-2025-26-card027.json').read_text(encoding='utf-8'))['players']
fe = FE['2025-26']; mism_y = mism_d = 0; mxL = 0.0; miss = 0; lbad = []
for k, f in ref.items():
    q = int(k)
    if q not in fe:
        miss += 1; continue
    mism_y += fe[q]['y'] != f['y']; mism_d += fe[q]['d'] != f['d']
    dl = abs(fe[q]['L'] - f['L']); mxL = max(mxL, dl)
    if dl >= 0.01: lbad.append((q, f['name'], round(dl, 4)))
res['c0f'] = {'nRef': len(ref), 'missingInMine': miss, 'yMismatch': int(mism_y), 'dMismatch': int(mism_d), 'maxAbsDiffL': mxL,
              'nLdiffGE0.01': len(lbad), 'LdiffList': lbad[:20], 'pass': bool(miss == 0 and mism_y == 0 and mism_d == 0 and mxL < 0.01)}
# c0s
res['c0s'] = {s: {'nTeams': len(META[s]['tankTeams']), 'teams': META[s]['tankTeams']} for s in F.SEASONS}
res['c0s']['pass'] = all(3 <= res['c0s'][s]['nTeams'] <= 8 for s in F.SEASONS[:3])
# c0n
pairs = list(zip(F.SEASONS[:-1], F.SEASONS[1:])); n_pair = {}
for S, S1 in pairs:
    ok = lambda q: FE[S][q]['age'] is not None and POSS[S].get(q, 0) >= 1500
    elig = [q for q in FE[S] if ok(q) and POSS[S1].get(q, 0) >= 1500]
    lost = [q for q in FE[S] if ok(q) and POSS[S1].get(q, 0) < 1500]
    c = lambda y, d: sum(FE[S][q]['y'] == y and FE[S][q]['d'] == d for q in elig)
    n_pair[f'{S}->{S1}'] = {'eligible': len(elig), 'y1d1': c(1, 1), 'y1d0': c(1, 0), 'y0d1': c(0, 1), 'y0d0': c(0, 0), 'lost': len(lost)}
tot = sum(v['y1d1'] for v in n_pair.values())
res['c0n'] = {'perPair': n_pair, 'totalY1D1': tot, 'threshold': 30, 'pass': tot >= 30}
res['allPass'] = bool(res['c0f']['pass'] and res['c0s']['pass'] and res['c0n']['pass'])
(HERE / 'phase0.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: res[k] for k in ('c0f', 'c0s', 'c0n', 'allPass')}, ensure_ascii=False, indent=1))
print({s: (META[s]['nGamesDnp'], META[s]['nPlayers']) for s in F.SEASONS})
