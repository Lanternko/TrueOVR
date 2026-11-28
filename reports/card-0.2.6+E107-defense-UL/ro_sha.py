"""E-107 §4（由 E-106 複製；唯讀目錄加 reports/card-0.2.6，排除的改成本目錄 E107）。以下為 E-106 原說明：E-106 §4（由 E-104 複製；E-104 目錄改列入唯讀，因為 UL 讀它的 def-L csv）。原說明：E-104 §4：唯讀目錄逐檔 sha256（照 E-100 ro_sha.py，目錄＝impact-rapm、E079、card-0.2.5*（本目錄除外））。用法：python -I ro_sha.py <out.json>（repo 根目錄）。"""
import hashlib, json, sys
from pathlib import Path
RO = ['reports/impact-rapm', 'reports/card-0.2.3+E079-recency-rapm', 'reports/card-0.2.6'] + sorted(
    p.as_posix() for p in Path('reports').glob('card-0.2.5*') if p.is_dir() and 'E107' not in p.name)
out = {}
for d in RO:
    for p in sorted(Path(d).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            out[p.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
Path(sys.argv[1]).write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding='utf-8')
print(len(out), 'files')
