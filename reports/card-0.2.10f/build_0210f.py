"""card 0.2.10f = card 0.2.10e + E-191b P1m（3PT 欄新對照池，使用者 2026-11-01 核准「疊」）。
ranking.csv、rapm-T6.csv 與 0.2.10e 逐位元組相同（threeValue 只顯示，不進 OVR）；three-value.csv 的 tv_main 換成
reports/E191-threevalue-dispersion/three-value-candidate.csv 的 tv_main（其餘欄不動、列集與順序不變）。
用法：python -I -X utf8 reports/card-0.2.10f/build_0210f.py"""
import csv, hashlib, io, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
E, F = ROOT / 'reports/card-0.2.10e', ROOT / 'reports/card-0.2.10f'
CAND = ROOT / 'reports/E191-threevalue-dispersion/three-value-candidate.csv'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    for n in ('ranking.csv', 'rapm-T6.csv'):
        shutil.copyfile(E / n, F / n)
        assert (F / n).read_bytes() == (E / n).read_bytes()
    summ = json.loads((E / 'summary.json').read_text(encoding='utf-8'))
    assert sha(F / 'ranking.csv') == summ['ranking_csv_sha256']
    old = list(csv.DictReader((E / 'three-value.csv').open(encoding='utf-8', newline='')))
    cand = list(csv.DictReader(CAND.open(encoding='utf-8', newline='')))
    cols = list(old[0])
    assert [r['playerId'] for r in old] == [r['playerId'] for r in cand], '列集或順序與 0.2.10e 不同'
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\r\n')
    w.writeheader()
    changed = {k: 0 for k in cols}
    for a, b in zip(old, cand):
        for k in cols:
            changed[k] += a[k] != b[k]
        w.writerow({k: b[k] for k in cols})
    assert all(v == 0 for k, v in changed.items() if k != 'tv_main'), f'tv_main 以外的欄有變：{changed}'
    (F / 'three-value.csv').write_bytes(buf.getvalue().encode('utf-8'))
    # ranking.csv 無 threeValue 欄；OVR／名次逐列相同由 byte-equal 保證
    out = dict(summ)
    out.update({
        'version': 'card 0.2.10f', 'base': 'reports/card-0.2.10e',
        'change': 'E-191b P1m：3PT 欄（three-value.csv 的 tv_main）改用「近三季同窗口人群＋本季」對照池映射；threeValue 只顯示，ranking.csv／OVR／名次與 0.2.10e 逐位元組相同。',
        'three_value_changed_rows': changed['tv_main'],
        'sources_sha256': {'reports/card-0.2.10e/ranking.csv': summ['ranking_csv_sha256'],
                           'reports/card-0.2.10e/three-value.csv': sha(E / 'three-value.csv'),
                           'reports/E191-threevalue-dispersion/three-value-candidate.csv': sha(CAND)},
        'build_command': 'python -I -X utf8 reports/card-0.2.10f/build_0210f.py',
        'ranking_csv_sha256': sha(F / 'ranking.csv'),
        'three_value_csv_sha256': sha(F / 'three-value.csv'),
    })
    for k in ('anchor_source', 'ovr_map', 'ovr_changed', 'pool_90_99', 'pool_ge99', 'anchors'):
        out[k] = summ[k]
    (F / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'rows': len(old), 'tv_main_changed': changed['tv_main'], 'ranking_sha': out['ranking_csv_sha256'],
                      'three_value_sha': out['three_value_csv_sha256']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
