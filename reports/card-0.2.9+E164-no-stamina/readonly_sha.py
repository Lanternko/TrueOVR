"""E-164：唯讀檔 sha256 快照（預註冊 §6）。用法：python -I readonly_sha.py <輸出 json>"""
import glob, hashlib, json, os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
pats = ['src/**/*', 'reports/card-0.2.9/**/*', 'reports/E142-card-target/**/*', 'reports/card-0.2.7d+E153-t6-target/**/*',
        'reports/card-0.2.8+E158-young-under-T6/**/*', 'reports/card-0.2.9+E162-per-volume/**/*',
        'reports/card-0.2.7c+E134-rolling-prior/stage1/*.py', 'reports/card-0.2.8+E157-next-epm-metric/*.py']
d = {}
for p in pats:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f) and '__pycache__' not in f:
            d[f.replace(chr(92), '/')] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
json.dump(d, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(len(d), 'files')
