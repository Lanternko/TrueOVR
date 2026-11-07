"""E-101 複本（自 reports/card-0.2.5+E097-topscale/chain/run_cards.py，只改目錄與變體）。E-097 原說明：E-097 複本（自 reports/card-0.2.5+E096-tail150/chain/run_cards.py，只改目錄與變體）。E-096 原說明：E-096 複本（自 reports/card-0.2.4+E090-onball-tail/chain/run_cards.py，只改目錄與變體）。原說明：E-090 複本（自 reports/card-0.2.2/run_cards.py）：只跑 P1，calibrate-wing 換成本目錄複本並加 --tailSource；參數不變（L-026）。從 repo 根目錄執行。子程序一律 CREATE_NO_WINDOW。
  python -I -B reports/card-0.2.4+E090-onball-tail/chain/run_cards.py [<variant>[,<variant>]] [<part>[,<part>]]
variant：cur（--tailSource work/current-attrs.csv，現行值；(c0) 用）、e090（--tailSource attributes-e090.csv，候選）。part：primary、fitA、fitB。
輸出：reports/card-0.2.4+E090-onball-tail/cards/<variant>/P1/<part>/
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.5+E101-crossera'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv',
          '--defSource', E060 + '/defense-attributes-e060.csv', '--perGame']
P1 = ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv']
VARIANT = {
    'e101': ['--tailSource', D + '/attributes-e101.csv'],
    'e101z': ['--tailSource', D + '/attributes-e101z.csv'],
    'e101g': ['--tailSource', D + '/attributes-e101g.csv'],
    'e101w': ['--tailSource', D + '/attributes-e101w.csv'],
}
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}


def run_one(v, p):
    out = f'{D}/cards/{v}/P1/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    args = [sys.executable, '-I', '-B', D + '/calibrate-wing.py'] + COMMON + P1 + VARIANT[v] + PART[p] + ['--out', out]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    Path(out + '/run.log').write_text(' '.join(args[3:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return v, p, r.returncode, (r.stdout + r.stderr)[-300:]


if __name__ == '__main__':
    vs = sys.argv[1].split(',') if len(sys.argv) > 1 else ['e101', 'e101z', 'e101g', 'e101w']
    ps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=3) as ex:
        for v, p, rc, tail in ex.map(lambda a: run_one(*a), [(v, p) for v in vs for p in ps]):
            print(v, p, 'rc', rc, tail.strip().splitlines()[-1] if tail.strip() else '')
