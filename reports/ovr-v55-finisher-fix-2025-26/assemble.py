"""python reports/ovr-v55-finisher-fix-2025-26/assemble.py -> report.md

把 report-head.md（§0~§2）、report-body.md（§3~§5）、report-attribution.md（§6 歸因）、
report-verdict.md（§7 判定）、report-risks.md（§8 風險）按順序接成 report.md。
分檔是因為 §3~§5 要等遠端板跑完才寫得出來，而 §0~§2 在跑之前就定稿了。
"""
import sys
from pathlib import Path
OUT = Path(__file__).parent
ORDER = ['report-head.md', 'report-body.md', 'report-attribution.md', 'report-verdict.md', 'report-risks.md']
parts = []
for f in ORDER:
    p = OUT / f
    if not p.exists():
        print(f'missing {f}', file=sys.stderr); sys.exit(1)
    parts.append(p.read_text(encoding='utf-8').rstrip() + '\n')
(OUT / 'report.md').write_text('\n'.join(parts), encoding='utf-8')
print('report.md', len((OUT / 'report.md').read_text(encoding='utf-8').splitlines()), 'lines from', len(parts), 'parts')
