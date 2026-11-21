"""唯讀目錄 sha256 清單（L-037）。用法：python -I hash_ro.py <out.json>。E-081 目錄由另一 session 寫入，單獨標記。"""
import hashlib, json, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DIRS = ['reports/impact-rapm', 'reports/ovr-v58-holdout-2025-26', 'reports/card-0.2.2', 'reports/card-0.2.3',
        'reports/card-0.2.2+E073-usage-evidence', 'reports/card-0.2.3+E081-age-residual', 'reports/defense-tenth', 'data']
out = {}
for d in DIRS:
    h = hashlib.sha256(); n = 0
    for p in sorted((ROOT / d).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            h.update(p.relative_to(ROOT).as_posix().encode()); h.update(hashlib.sha256(p.read_bytes()).digest()); n += 1
    out[d] = {'files': n, 'sha256': h.hexdigest()}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
