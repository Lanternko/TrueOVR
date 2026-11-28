"""E-128：唯讀檔 sha256 快照（仿 E-107 readonly_sha.py）。用法：python -I -B readonly_sha.py <輸出 json>
run_c4_live.py 會加 027 分支，單獨列在 'modifiedByE128'（只記錄、不算唯讀）。"""
import glob, hashlib, json, os, sys
OUT = os.path.abspath(sys.argv[1])
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
pats = [
    'src/**/*',
    'reports/card-*/**/*',
    'reports/impact-rapm/**/*',
    'reports/ovr-inseason-2026-27/v4/tools/*.py',
    'reports/ovr-inseason-2026-27/v5/tools/*.py',
    'reports/ovr-inseason-2026-27/tools/*.py',
    'reports/ovr-inseason-2026-27/v5/pathA/backtest-e064/**/*',
    'reports/ovr-inseason-2026-27/e095-card025-minutes/**/*',
    'reports/ovr-inseason-2026-27/e107-card026/**/*',
    'reports/ovr-inseason-2026-27/e128-card027b/preregistration.md',
    'reports/ovr-inseason-2026-27/live/prior-2025-26-card0*.json',
    'reports/ovr-inseason-2026-27/live/usage-2025-26-card02[46].json',
    'reports/ovr-inseason-2026-27/live/pool-026.json',
    'reports/ovr-inseason-2026-27/live/build_*_0[12]?.py',
    'reports/ovr-inseason-2026-27/live/2026-*/**/*',
    'reports/ovr-inseason-2026-27/live/publish_state.json',
    'reports/ovr-inseason-2026-27/out-*/**/*',
    'docs/**/*',
    'data/defense-seventh/2026-27/*.json',
]
d = {}
for p in pats:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f) and '__pycache__' not in f:
            d[f.replace(chr(92), '/')] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
mod = 'reports/ovr-inseason-2026-27/live/run_c4_live.py'
out = {'readonly': d, 'modifiedByE128': {mod: hashlib.sha256(open(mod, 'rb').read()).hexdigest()}}
json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
print(len(d), 'files')
