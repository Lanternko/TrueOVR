"""E-129：唯讀目錄 sha256 快照（預註冊 §3）。用法：python -I -B -X utf8 readonly_sha_e129.py pre|post|check
  pre/post 寫 readonly-sha-<pre|post>.json；check 比較兩者寫 readonly-sha-check.json。
  v5/、e111-card027/、reports/card-0.2.7/ 必須完全不變；live/ 每日抓取會寫，只記錄不算違規。"""
import hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
DIRS = {'v5': REPORT / 'v5', 'e111-card027': REPORT / 'e111-card027', 'live': REPORT / 'live',
        'card-0.2.7': ROOT / 'reports' / 'card-0.2.7'}
STRICT = ['v5', 'e111-card027', 'card-0.2.7']


def snap():
    out = {}
    for k, d in DIRS.items():
        files = {}
        for f in sorted(d.rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:
                files[f.relative_to(d).as_posix()] = hashlib.sha256(f.read_bytes()).hexdigest()
        comb = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        out[k] = {'n': len(files), 'combined': comb, 'files': files}
    return out


mode = sys.argv[1]
if mode in ('pre', 'post'):
    s = snap()
    (HERE / f'readonly-sha-{mode}.json').write_text(json.dumps(s, indent=0, sort_keys=True), encoding='utf-8')
    print(mode, {k: (v['n'], v['combined'][:12]) for k, v in s.items()})
else:
    a = json.loads((HERE / 'readonly-sha-pre.json').read_text(encoding='utf-8'))
    b = json.loads((HERE / 'readonly-sha-post.json').read_text(encoding='utf-8'))
    res = {}
    for k in a:
        fa, fb = a[k]['files'], b[k]['files']
        changed = sorted(f for f in set(fa) | set(fb) if fa.get(f) != fb.get(f))
        res[k] = {'strict': k in STRICT, 'same': a[k]['combined'] == b[k]['combined'], 'nPre': a[k]['n'], 'nPost': b[k]['n'],
                  'changedFiles': changed}
    res['violation'] = any(res[k]['strict'] and not res[k]['same'] for k in a)
    (HERE / 'readonly-sha-check.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps({k: (v if k == 'violation' else (v['same'], len(v['changedFiles']))) for k, v in res.items()}))
