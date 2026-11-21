import csv, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac
t0=time.time()
db = ac.DB(); inp = ac.load_inputs(); print('load', round(time.time()-t0,1))
ch = ac.Chain(db, inp, 'V')
rk = {}
for r in csv.DictReader(open(ac.R/'card-0.2.9a/ranking.csv', encoding='utf-8')): rk.setdefault(r['name'], []).append(r)
full = {int(r['playerId']): r for r in csv.DictReader(open(ac.R/'card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv', encoding='utf-8'))}
idx = {p:i for i,p in enumerate(ch.pids)}
out = {'n_cards': len(ch.pids), 'attrs': {}}
tot = ok = 0
for a in ac.ATTRS8:
    m = ch.mapped[a]
    d1 = [abs(m[idx[p]] - float(rk[nm][0][a])) for p, nm in zip(ch.pids, ch.names) if len(rk.get(nm, [])) == 1]
    d2 = [abs(m[idx[p]] - float(full[p][a])) for p in ch.pids if p in full]
    o = sum(x <= 0.1+1e-9 for x in d1); tot += len(d1); ok += o
    out['attrs'][a] = {'n_ranking': len(d1), 'within0.1': o, 'max_diff_ranking': max(d1), 'n_full': len(d2), 'max_diff_full': max(d2), 'share_full_within_0.1': float(np.mean(np.array(d2) <= 0.1))}
    print(a, len(d1), o, round(max(d1),4), len(d2), round(max(d2),6))
out['pooled_share_ranking'] = ok/tot; out['values'] = tot
print('pooled', ok, tot, ok/tot)
Path(__file__).with_name('audit_repro.json').write_text(json.dumps(out, indent=1, default=float), encoding='utf-8')
