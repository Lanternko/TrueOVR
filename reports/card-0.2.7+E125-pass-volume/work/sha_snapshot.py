"""預註冊 §4 唯讀核對：對列出目錄的每個檔算 sha256，存 json。用法：python -I sha_snapshot.py <out.json>"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DIRS = ['reports/card-0.2.7', 'reports/card-0.2.6+E107-defense-UL', 'reports/card-0.2.5+E094-defense-ceiling', 'reports/card-0.2.5+E101-crossera',
        'reports/card-0.2.0+E070-foul-volume', 'reports/ovr-v61-shrink-history-2025-26', 'reports/impact-rapm', 'data']
out = {}
for d in DIRS:
    for p in sorted((ROOT / d).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            out[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
agg = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
Path(sys.argv[1]).write_text(json.dumps({'aggregate': agg, 'n': len(out), 'files': out}, indent=0), encoding='utf-8')
print(len(out), agg)
