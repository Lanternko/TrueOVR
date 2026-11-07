"""位置標籤反事實診斷（不是採用）：只在校準階段把指定球員改標位置，重跑 card 0.2.2 P1 primary。
模擬目標 y 本身是用原 slot 跑的，這裡不重跑模擬，所以只量到校準端（位置交互項＋RAPM 位置置中）的影響。
  python -I reports/diag-position-labels/run_diag.py
"""
import csv, os, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = Path('reports/diag-position-labels')
SRC = Path('reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv')
VARIANTS = {'v0-orig': {}, 'v1-JWilliams-SF': {'Jalen Williams': 'SF'}, 'v2-JJohnson-SF': {'Jalen Johnson': 'SF'},
            'v3-Banchero-SF': {'Paolo Banchero': 'SF'}}
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', 'reports/card-0.2.0+E070-foul-volume/attributes-w075/attributes-new.csv',
          '--defSource', 'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv', '--perGame',
          '--pressure', 'force', '--pressureSource', 'reports/card-0.2.0+E071-pressure/force-pressure-source.csv']
for v, relabel in VARIANTS.items():
    out = D / v
    out.mkdir(exist_ok=True)
    rows = list(csv.DictReader(SRC.open(encoding='utf-8')))
    for r in rows:
        r['position'] = relabel.get(r['name'], r['position'])
    t = out / 'target.csv'
    with t.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    env = dict(os.environ, DIAG_TARGET=str(t))
    r = subprocess.run([sys.executable, '-I', str(D / 'calibrate-wing-diag.py')] + COMMON + ['--out', str(out)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    (out / 'run.log').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
    print(v, 'rc', r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] )
