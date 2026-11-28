"""E-095：唯讀檔 sha256 快照。用法：python -I readonly_sha.py <輸出 json>"""
import glob, hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
pats = ['src/**/*', 'reports/card-0.2.4/**/*', 'reports/card-0.2.5/**/*', 'reports/card-0.2.4+E089-minutes-saturation/**/*',
        'reports/ovr-inseason-2026-27/v5/tools/*', 'reports/ovr-inseason-2026-27/v5/pathA/backtest-e064/*',
        'reports/card-0.2.3+E084-current-target/results.json', 'reports/ovr-inseason-2026-27/live/usage-2025-26-card024.json']
d = {}
for p in pats:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f) and '__pycache__' not in f:
            d[f.replace(chr(92), '/')] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
json.dump(d, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(len(d), 'files')
