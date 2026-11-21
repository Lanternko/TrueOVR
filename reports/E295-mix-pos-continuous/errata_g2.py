"""E-295 errata-1：G2「距上限 0.2 內」在連續權重下退化（見 errata-1.md）。不改凍結檔；匯入 e295_eval 的同一份加分重算。
用法（repo root）：python -I -B -X utf8 reports/E295-mix-pos-continuous/errata_g2.py"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location('e295', HERE / 'e295_eval.py'); E = importlib.util.module_from_spec(s); sys.modules['e295'] = E; s.loader.exec_module(E)
res = json.load(open(HERE / 'results.json', encoding='utf-8'))
out = {}
for a in E.ARMS:
    b, cap = E.BON[a], E.CAPB[a]
    m_lit = E.EP & (cap > 0)
    lit = m_lit & (b >= cap - 0.2)
    m1 = E.EP & (cap >= 1.0)                      # errata：上限至少 1 分的人才有「碰頂」可言
    e1 = m1 & (b >= cap - 0.2)
    rel = m1 & (b >= 0.95 * cap)                  # 只報告：相對 95%
    zero_lit = int((lit & (b <= 0.05)).sum())
    out[a] = {'literal_near_cap': int(lit.sum()), 'literal_near_cap_with_zero_bonus': zero_lit,
              'literal_max_cap_among_hits': float(cap[lit].max()) if lit.any() else 0.0,
              'errata_near_cap_cap_ge_1': int(e1.sum()), 'errata_names': [E.names[i] for i in np.where(e1)[0]],
              'rel95_cap_ge_1': int(rel.sum()), 'n_cap_ge_1': int(m1.sum()),
              'max_same_bonus_group': res['card'][a]['disc']['max_same_bonus_group']}
    c = res['card'][a]['checks']
    g2e = out[a]['errata_near_cap_cap_ge_1'] == 0 and out[a]['max_same_bonus_group'] <= res['card']['A']['disc']['max_same_bonus_group'] + 2
    out[a]['G2_errata'] = g2e
    out[a]['verdict_errata'] = 'baseline' if a == 'A' else ('adopt_candidate' if all([c['G1'], g2e, c['G3'], c['G4'], c['G5']]) else 'reject')
    print(a, out[a])
pick = next((a for a in E.CAND if out[a]['verdict_errata'] == 'adopt_candidate'), None)
out['pick_errata'] = pick; print('pick_errata', pick)
(HERE / 'errata-1-results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
if pick:
    np.savez(HERE / 'bonus_pick.npz', names=np.array(E.names), bonus=E.BON[pick], pick=np.array(pick + '-errata1'),
             pi=E.SPEC[pick][0], w=E.SPEC[pick][1], src=np.array(E.SRC))
