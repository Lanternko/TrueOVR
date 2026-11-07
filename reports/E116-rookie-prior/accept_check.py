"""E-116 驗收三項：老將列逐字相同（除 rank）、相對順序不變、新秀都有 OVR、no-prior 只剩非新秀。"""
import csv
import json
import sys
from pathlib import Path

L = Path(__file__).resolve().parents[1] / 'ovr-inseason-2026-27' / 'live'
rk = json.load(open(L / 'rookie-prior-2026.json', encoding='utf-8'))['players']
rk_ids = {str(r['playerId']) for r in rk}


def rd(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig', newline='')))


o, n = rd(L / 'e116-check-orig/ranking.csv'), rd(L / 'e116-check-rookie/ranking.csv')
strip = lambda r: {k: v for k, v in r.items() if k != 'rank'}
n_vet = [r for r in n if r['playerId'] not in rk_ids]
n_rk = [r for r in n if r['playerId'] in rk_ids]
c1_same = len(o) == len(n_vet) and all(strip(a) == strip(b) for a, b in zip(o, n_vet))
c1_cnt = (len(o), len(n_vet))
order_o = [r['playerId'] for r in o]
order_n = [r['playerId'] for r in n_vet]
c1_order = order_o == order_n
c2 = {'rookiesInPrior': len(rk), 'rookiesInRanking': len(n_rk),
      'withOvr': sum(1 for r in n_rk if r['ovr'] not in ('', None))}
det = json.load(open(L / 'e116-check-rookie/rookies-detail.json', encoding='utf-8'))
c2['playedN>0'] = sum(1 for d in det if d['N'] > 0)
c2['allPlayedHaveOvr'] = all(d['ovr'] is not None for d in det if d['N'] > 0)
npo, npn = rd(L / 'e116-check-orig/no-prior.csv'), rd(L / 'e116-check-rookie/no-prior.csv')
c3 = {'origNoPrior': len(npo), 'rookieNoPrior': len(npn),
      'rookiesLeftInNoPrior': sum(1 for r in npn if r['playerId'] in rk_ids),
      'removed': len(npo) - len(npn),
      'restIdentical': [strip(r) for r in npo if r['playerId'] not in rk_ids] == [strip(r) for r in npn]}
res = {'c1_veteran_rows_identical_ex_rank': c1_same, 'c1_counts_orig_vs_rookieVets': c1_cnt,
       'c1_relative_order_same': c1_order, 'c2_rookies': c2, 'c3_no_prior': c3}
print(json.dumps(res, ensure_ascii=False, indent=1))
json.dump(res, open(Path(__file__).resolve().parent / 'accept.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
