"""Inventory a compact GitHub snapshot without deleting local research data.
Run from the repository root. Staging remains an explicit separate git operation.
"""
from pathlib import Path
import csv
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CODE = {'.js', '.mjs', '.cjs', '.py', '.ts', '.tsx', '.css', '.html', '.md', '.sha256'}
MEDIA = {'.png', '.jpg', '.jpeg', '.svg', '.pdf', '.webp'}
# 2026-10-30 起只把「證據」類 JSON 放進 GitHub（預註冊、協定、manifest、ranking、驗證、決策、設定、fit）；
# 模擬結果（league、cards、card-values、coefficients、audit、provenance…）超過 128KB 就留在本機，用旁邊的 .sha256／.md 核對。
SUMMARY = re.compile(r'(protocol|prereg|manifest|ranking|verif|decision|config|^fit$|sha256)', re.I)
RAW_DIRS = {'runs', 'pbp', 'playbyplay', 'play-by-play', 'replays', '__pycache__'}

def select(path):
    rel = path.relative_to(ROOT)
    parts = rel.parts
    size = path.stat().st_size
    if any(x in {'.git', 'node_modules', '__pycache__'} for x in parts) or path.suffix in {'.pyc', '.log'}:
        return False, 'local cache or log'
    if rel.as_posix() == 'test/.defense_eighth_b_serialized.js':
        return False, 'generated serialization test'
    if parts[0] not in {'reports', 'data'}:
        return True, 'source, documentation, assets or tests'
    if path.suffix in CODE:
        return True, 'research source or documentation'
    if path.suffix in MEDIA and size <= 2 * 1024**2:
        return True, 'compact visual artifact'
    if parts[0] == 'data':
        if len(parts) == 2 or (path.suffix == '.json' and path.name in {'manifest.json', 'league.json', 'bio.json'} and size <= 2 * 1024**2):
            return True, 'curated application data or source metadata'
        return False, 'external source data retained locally'
    if any(x in RAW_DIRS for x in parts) or re.search(r'(checkpoint|raw|replay)', path.name, re.I):
        return False, 'raw simulation output retained locally'
    if re.fullmatch(r'\d{8,}.*\.json', path.name):
        return False, 'per-game or team source dump retained locally'
    if path.suffix == '.json' and (size <= 128 * 1024 or (SUMMARY.search(path.stem) and size <= 2 * 1024**2)):
        return True, 'compact result or model configuration'
    if path.suffix == '.csv' and size <= 2 * 1024**2:
        return True, 'compact result table'
    return False, 'bulk research artifact retained locally'

if __name__ == '__main__':
    included, excluded = [], []
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0'))
    candidates = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    # Include ignored research paths in inventory so omissions remain visible.
    paths = {ROOT / p for p in candidates if p}
    for folder in ('reports', 'data'):
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file())
    for path in sorted(paths):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith('reports/github-snapshot/'):
            continue
        keep, reason = select(path)
        if rel in tracked:
            keep, reason = True, 'previously tracked file'
        row = {'path': rel, 'bytes': path.stat().st_size, 'reason': reason}
        (included if keep else excluded).append(row)
    out = ROOT / 'reports/github-snapshot'
    out.mkdir(exist_ok=True)
    for name, rows in [('included', included), ('excluded', excluded)]:
        with (out / (name + '.csv')).open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['path', 'bytes', 'reason'])
            writer.writeheader()
            writer.writerows(rows)
    summary = {name: {'files': len(rows), 'bytes': sum(r['bytes'] for r in rows)} for name, rows in [('included', included), ('excluded', excluded)]}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    stage = Path(tempfile.gettempdir()) / 'basketball-github-paths.txt'
    stage.write_bytes(b'\0'.join(r['path'].encode('utf-8') for r in included) + b'\0' + b'\0'.join(p.relative_to(ROOT).as_posix().encode('utf-8') for p in out.iterdir() if p.is_file()) + b'\0')
    print(json.dumps({'summary': summary, 'staging_pathspec': str(stage)}))
