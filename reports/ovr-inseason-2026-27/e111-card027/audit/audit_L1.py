"""E-111 稽核 (L1)：重跑 CARD_MODE=027（輸出到 audit/out-027-audit），攔截 N=0 ref 的 e064_convert 輸入輸出，
用自己的 W(m)、兩段映射重算 ref OVR，再用自己的比對碼對 card 0.2.7 ranking.csv 的 ovr。"""
import csv
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
os.environ['CARD_MODE'] = '027'
sys.path.insert(0, str(LIVE))
os.chdir(LIVE)
sys.argv = ['run_c4_live.py', '../e111-card027/audit/out-027-audit']
spec = importlib.util.spec_from_file_location('rcl', LIVE / 'run_c4_live.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CAP = []
orig = m.e064_convert


def hook(entries, mpg_by_pid, anc, r_repl=0.0, sat=False):
    out = orig(entries, mpg_by_pid, anc, r_repl, sat)
    CAP.append({'in': {p: dict(v) for p, v in entries.items() if isinstance(v, dict)}, 'mpg': dict(mpg_by_pid), 'anc': list(anc), 'r_repl': r_repl,
                'sat': sat, 'out': {p: dict(v) for p, v in out.items() if isinstance(v, dict)}})
    return out


m.e064_convert = hook
m.main()


def W(x):  # R-047 scale 15：W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))
    return (1 - math.exp(-x / 15)) / (1 - math.exp(-36 / 15))


def mapg(g, a):
    p1, p50, p99 = a
    return 40 + 30 * (g - p1) / (p50 - p1) if g <= p50 else 70 + 29 * (g - p50) / (p99 - p50)


card = list(csv.DictReader(open(ROOT / 'reports/card-0.2.7/ranking.csv', encoding='utf-8')))
cov = {r['name']: float(r['ovr']) for r in card}
prior = json.loads((LIVE / 'prior-2025-26-card027.json').read_text(encoding='utf-8'))
pl = prior['players'] if isinstance(prior, dict) and 'players' in prior else prior
name = {int(p['playerId']): p['name'] for p in pl}
res = {'captures': len(CAP)}
# ref 是第一個呼叫（line 904，ref＝x0 only）；live 的是之後的呼叫
for i, c in enumerate(CAP):
    mine = {p: mapg((e['pred'] - c['r_repl']) * W(c['mpg'].get(p, 0.0)), c['anc']) for p, e in c['in'].items()}
    selfdiff = max(abs(mine[p] - c['out'][p]['ovr']) for p in mine)
    d = {name.get(int(p), str(p)): mine[p] - cov[name[int(p)]] for p in mine if int(p) in name and name[int(p)] in cov}
    worst = sorted(d.items(), key=lambda kv: -abs(kv[1]))[:8]
    res[f'call{i}'] = {'n': len(mine), 'anchors': c['anc'], 'rRepl': c['r_repl'], 'sat': c['sat'],
                       'myConvert_vs_pipeline_maxAbs': selfdiff, 'nMatchedCard': len(d),
                       'maxAbsVsCard027': max(abs(v) for v in d.values()) if d else None,
                       'nGt0.1': sum(abs(v) > 0.1 for v in d.values()), 'worst': worst,
                       'Camara': (d.get('Toumani Camara'), cov.get('Toumani Camara')),
                       'Hauser': (d.get('Sam Hauser'), cov.get('Sam Hauser'))}
(HERE / 'audit_L1.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
print(json.dumps(res, ensure_ascii=False, default=float)[:3000])
