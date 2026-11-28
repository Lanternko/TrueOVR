"""card 0.2.11：把 E-123 的逐季 abilityC（難度調整 3P%，t_season 的 acc）存成一個 json，供窗口 threeValue 用（只有 2022-23 起有出手難度資料）。
用法：python -I -X utf8 reports/card-0.2.12/dump_abilityc.py"""
import json, sys, hashlib
from pathlib import Path
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work'))
import e123lib as E
out = {}
for s in E.SEASONS:
    t = E.t_season(s)
    out[s] = {str(p): {'acc': v['acc'], 'N': v['N'], 'mu': v['mu']} for p, v in t.items()}
    print(s, len(t), flush=True)
nl = json.loads((E.V62 / 'new-long.json').read_text(encoding='utf-8'))
d = max(abs(out['2025-26'][k]['acc'] - v['abilityC']) for k, v in nl.items() if k in out['2025-26'] and v['abilityC'] is not None)
print('2025-26 acc vs new-long abilityC max diff', d)
(H / 'abilityC-by-season.json').write_text(json.dumps({'note': 'e123lib.t_season(s)[pid][acc]：acc = mu + (M − E)/(N + 294.667)；N=0 者 acc＝該季聯盟 FG3M/FG3A', 'seasons': out}, ensure_ascii=False), encoding='utf-8')
print(hashlib.sha256((H / 'abilityC-by-season.json').read_bytes()).hexdigest())
