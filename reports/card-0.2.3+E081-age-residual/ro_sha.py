"""預註冊 §5 唯讀目錄的 sha256 manifest（每個檔案一筆 + 每個目錄的彙總）。用法：python ro_sha.py out.json"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DIRS = ['reports/impact-rapm', 'reports/ovr-v58-holdout-2025-26', 'reports/card-0.2.2', 'reports/card-0.2.3',
        'reports/card-0.2.2+E073-usage-evidence', 'data']
out = {}
for d in DIRS:
    files = sorted(p for p in (ROOT / d).rglob('*') if p.is_file())
    h = hashlib.sha256()
    per = {}
    for p in files:
        s = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(ROOT).as_posix()
        per[rel] = s
        h.update(rel.encode() + b'\0' + s.encode() + b'\n')
    out[d] = {'n_files': len(files), 'aggregate_sha256': h.hexdigest(), 'files': per}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding='utf-8')
print({d: (v['n_files'], v['aggregate_sha256'][:16]) for d, v in out.items()})
