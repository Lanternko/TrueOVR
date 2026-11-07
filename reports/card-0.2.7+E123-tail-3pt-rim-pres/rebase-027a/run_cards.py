"""E-123 疊到 card 0.2.7a（rebase-027a）。由 ../run_cards.py（E-123）與 E-125 work/run_cards_p.py 合併；參數、旗標、順序一字不改。
  c0   = card 0.2.7 原樣（tail＝E-101 attributes-e101.csv，def＝E-060 原檔）：只用來建 pools（E-125 的 P0 同此）。
  c0a  = 只放 E-125：tail＝E-101 的 pass 欄換成 E-125 attributes-P50.csv 的 pass；E-123 部分（help／pressure）用現行值。要和 card 0.2.7a 逐位元相同。
  e123a= pass 照 E-125 P50、pressure 照 E-123 work/tail-new.csv、help 照 E-123 work/def-new.csv（presDisplay 之後依名字覆寫）。
tail 檔由 merge() 以欄為單位合併（不重新擬合任何量）；c0a 的 tail 必須和 E-125 attributes-P50.csv 逐位元相同。
用法（repo 根目錄）：python -I -X utf8 reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/run_cards.py merge
                     python -I -X utf8 .../run_cards.py run [<arm>[,<arm>]] [<part>[,<part>]]
子程序一律 CREATE_NO_WINDOW。輸出：<D>/cards/<arm>/<part>/
"""
import csv
import hashlib
import io
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a'
E123 = 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
E125 = 'reports/card-0.2.7+E125-pass-volume'
TAIL_CUR = 'reports/card-0.2.5+E101-crossera/attributes-e101.csv'
TAIL_P50 = E125 + '/attributes-P50.csv'
TAIL_E123 = E123 + '/work/tail-new.csv'
TAIL_C0A = D + '/work/tail-c0a.csv'
TAIL_E123A = D + '/work/tail-e123a.csv'
E104 = 'reports/card-0.2.5+E104-defense-pergame-decay'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
DEF_CUR = E060 + '/defense-attributes-e060.csv'
DEF_NEW = E123 + '/work/def-new.csv'
ARMS = {  # arm -> (tailSource, defSource)
    'c0': (TAIL_CUR, DEF_CUR),
    'c0a': (TAIL_C0A, DEF_CUR),
    'e123a': (TAIL_E123A, DEF_NEW),
}
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv', '--perGame']
P1 = ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv']
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}
FACTOR = '0.5'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def wr(p, rows):
    buf = io.StringIO(newline='')
    csv.writer(buf, lineterminator='\n').writerows(rows)
    Path(p).write_bytes(buf.getvalue().encode('utf-8'))


def replace_col(base, src, col):
    """base 表的 col 欄換成 src 表同一 playerId 的 col 欄值（字串原樣）；其他欄不動。"""
    assert base[0] == src[0] and len(base) == len(src)
    j = base[0].index(col)
    sv = {r[0]: r for r in src[1:]}
    out = [base[0]]
    for r in base[1:]:
        s = sv[r[0]]
        assert s[1] == r[1], ('name mismatch', r[0])
        r2 = list(r)
        r2[j] = s[j]
        out.append(r2)
    return out


def merge():
    root = Path('.')
    cur, p50, e123 = rd(root / TAIL_CUR), rd(root / TAIL_P50), rd(root / TAIL_E123)
    c0a = replace_col(cur, p50, 'pass')            # E-125：只換 pass
    wr(root / TAIL_C0A, c0a)
    e123a = replace_col(c0a, e123, 'pressure')     # 再加 E-123：只換 pressure（help 走 defSource，presDisplay 之後覆寫）
    wr(root / TAIL_E123A, e123a)
    res = {
        'tail_c0a_sha256': sha(root / TAIL_C0A), 'attributes_P50_sha256': sha(root / TAIL_P50),
        'tail_c0a_equals_attributes_P50_bytes': sha(root / TAIL_C0A) == sha(root / TAIL_P50),
        'tail_e123a_sha256': sha(root / TAIL_E123A),
    }
    # e123a 和 c0a 只差 pressure；和 E-123 tail-new 只差 pass
    h = e123a[0]
    def ndiff(x, y):
        return {h[j]: sum(a[j] != b[j] for a, b in zip(x[1:], y[1:])) for j in range(len(h)) if any(a[j] != b[j] for a, b in zip(x[1:], y[1:]))}
    res['e123a_vs_c0a_diffcols'] = ndiff(e123a, c0a)
    res['e123a_vs_E123_tail_new_diffcols'] = ndiff(e123a, e123)
    res['e123a_vs_E125_P50_diffcols'] = ndiff(e123a, p50)
    import json
    (root / D / 'work/merge-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=1))
    assert res['tail_c0a_equals_attributes_P50_bytes'], 'c0a tail 和 E-125 attributes-P50.csv 不逐位元相同'
    assert set(res['e123a_vs_c0a_diffcols']) == {'pressure'}
    assert set(res['e123a_vs_E123_tail_new_diffcols']) == {'pass'}
    return 0


def arm_args(p):   # E-107 UL6 原樣
    return ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', f'{E104}/def-L-{p}.csv', '--defPossFactor', FACTOR]


def run_one(a, p):
    out = f'{D}/cards/{a}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    tail, dsrc = ARMS[a]
    common = COMMON[:6] + ['--defSource', dsrc] + COMMON[6:]
    args = [sys.executable, '-I', E123 + '/calibrate-wing.py'] + common + P1 + ['--tailSource', tail] + PART[p] + arm_args(p) + ['--out', out]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW, timeout=1500)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return a, p, r.returncode, time.time() - t, (r.stdout + r.stderr)[-300:]


def run():
    arms = sys.argv[2].split(',') if len(sys.argv) > 2 else ['c0', 'c0a']
    ps = sys.argv[3].split(',') if len(sys.argv) > 3 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=4) as ex:
        for a, p, rc, dt, tail in ex.map(lambda x: run_one(*x), [(a, p) for a in arms for p in ps]):
            print(a, p, 'rc', rc, f'{dt:.0f}s', tail.strip().splitlines()[-1] if tail.strip() else '', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit({'merge': merge, 'run': run}[sys.argv[1]]())
