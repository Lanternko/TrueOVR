"""E-127 section 3 read-only check: per-file sha256 -> tree hash. usage: python -I -B -X utf8 ro_sha.py before|after"""
import hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DIRS = ['reports/card-0.2.7', 'reports/card-0.2.7+E126-tank-next-season', 'reports/impact-rapm', 'reports/card-0.2.5+E094-defense-ceiling',
        'reports/ovr-inseason-2026-27/live/usage-2025-26-card027.json', 'data/defense-seventh/2022-23', 'data/defense-seventh/2023-24',
        'data/defense-seventh/2024-25', 'data/season-source']
def tree(d):
    h = hashlib.sha256(); files = {}
    base = ROOT / d
    ps = [base] if base.is_file() else sorted(x for x in base.rglob('*') if x.is_file())
    for p in ps:
        rel = p.relative_to(ROOT).as_posix(); fh = hashlib.sha256(p.read_bytes()).hexdigest()
        files[rel] = fh; h.update(f'{rel}\0{fh}\n'.encode())
    return h.hexdigest(), files
tag = sys.argv[1]; out = {'tag': tag, 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'dirs': {}}
for d in DIRS:
    t, f = tree(d); out['dirs'][d] = {'treeSha256': t, 'nFiles': len(f), 'files': f}
(Path(__file__).parent / f'ro-{tag}.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
print({d: (v['treeSha256'][:12], v['nFiles']) for d, v in out['dirs'].items()})
