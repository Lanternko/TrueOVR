"""E-161：唯讀檔 sha256 快照（預註冊 §7）。用法：python -I readonly_sha.py <輸出 json>"""
import glob, hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
pats = ['src/**/*', 'reports/card-0.2.9/**/*', 'reports/ovr-inseason-2026-27/v5/tools/*',
        'reports/ovr-inseason-2026-27/v5/pathA/backtest-e064/*', 'reports/ovr-inseason-2026-27/e095-card025-minutes/**/*']
d = {}
for p in pats:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f) and '__pycache__' not in f:
            d[f.replace(chr(92), '/')] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
json.dump(d, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(len(d), 'files')
