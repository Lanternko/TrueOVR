"""把 E-188 OVR 映射（S3）套到任一張重擬合卡：<base> 只換 OVR 映射（E-188，S3：PR90→88、PR95→92；F-131）。
錨取 base 自己這一輪的池：PR1／PR50／PR90／PR95／PR99 全部取 base ranking.csv 的 gRepl（MIN ≥ 500）、e094_t 的 qf（最近名次）；
先核對舊兩段式用這組 PR1／PR50／PR99 能重現 base 的 ovr（凍結錨的卡如 0.2.10a 會被擋下，改用 card-0.2.10b 的做法）。g ≤ PR50 或 ≥ PR99 的 ovr 字串原樣保留，其餘以 ovr_map 重算；名次與其他欄不動。
用法：python -I -X utf8 reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py <base_card_dir> <out_dir> <version>"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
import numpy as np
E188 = Path(__file__).resolve().parent
ROOT = E188.parents[1]
s = importlib.util.spec_from_file_location('ovr_map', E188 / 'ovr_map.py')
OM = importlib.util.module_from_spec(s); s.loader.exec_module(OM)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(base, out, version):
    BASE, OUT = ROOT / base, ROOT / out
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'ranking.csv').exists(), f'{OUT} 已有 ranking.csv，不覆寫'
    rows = list(csv.DictReader((BASE / 'ranking.csv').open(encoding='utf-8')))
    cols = list(rows[0].keys())
    g = np.array([float(r['gRepl']) for r in rows]); pool = np.array([float(r['MIN']) >= 500 for r in rows])
    an = {f'PR{p}': OM.qf(g, pool, p) for p in (1, 50, 90, 95, 99)}
    old = OM.two_segment(g, an['PR1'], an['PR50'], an['PR99'])
    off = [r['name'] for r, v in zip(rows, old) if abs(v - float(r['ovr'])) > 0.06]
    assert not off, f'base 的 ovr 用本池錨重現不了：{off[:5]}'
    new = OM.ovr_map(g, an)
    keep = (g <= an['PR50']) | (g >= an['PR99'])
    for r, v, kp in zip(rows, new, keep):
        if not kp:
            r['ovr'] = f"{v:.1f}"
    with (OUT / 'ranking.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)
    for f in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(BASE / f, OUT / f)
    o = np.array([float(r['ovr']) for r in rows])
    out = {'version': version, 'base': base, 'players': len(rows),
           'change': 'E-188／F-131：OVR 映射 PR50 以上加 PR90→88、PR95→92 兩錨（S3），≥PR99 與 ≤PR50 不變；名次不變。',
           'anchors': an, 'anchor_source': f'{base}/ranking.csv gRepl, MIN>=500, qf（gRepl 4 位小數）',
           'ovr_map': {'function': 'reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py:ovr_map', 'A_PR90': OM.S3['A'], 'B_PR95': OM.S3['B']},
           'ovr_changed': int((~keep).sum()), 'pool_90_99': int(((o >= 90) & (o < 99) & pool).sum()), 'pool_ge99': int(((o >= 99) & pool).sum()),
           'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (BASE / 'ranking.csv', E188 / 'ovr_map.py', E188 / 'preregistration.md')},
           'build_command': f'python -I -X utf8 {E188.relative_to(ROOT).as_posix()}/apply_to_card.py {base} {out} "{version}"', 'ranking_csv_sha256': sha(OUT / 'ranking.csv')}
    out['sources_sha256'][f'{base}/ranking.csv'] = sha(BASE / 'ranking.csv')
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('anchors', 'ovr_changed', 'pool_90_99', 'pool_ge99', 'ranking_csv_sha256')}, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(*sys.argv[1:4])
