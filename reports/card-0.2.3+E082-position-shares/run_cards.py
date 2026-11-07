"""E-082：card 0.2.2 run_cards.py 的 P1 參數（COMMON + VARIANT['P1'] + PART）不變，換成本目錄的 calibrate-wing.py。
  python -I reports/card-0.2.3+E082-position-shares/run_cards.py [off|on][,..] [primary,fitA,fitB]
off = 不帶 --posShares（須逐位元重現 card 0.2.2 P1）；on = --posShares pos-shares.csv。
從 repo 根目錄執行。子程序一律 CREATE_NO_WINDOW。輸出：<D>/cards/<mode>/<part>/
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.3+E082-position-shares'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv',
          '--defSource', E060 + '/defense-attributes-e060.csv', '--perGame']
P1 = ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv']
MODE = {'off': [], 'on': ['--posShares', D + '/pos-shares.csv']}
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}


def run_one(m, p):
    out = f'{D}/cards/{m}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    args = [sys.executable, '-I', D + '/calibrate-wing.py'] + COMMON + P1 + MODE[m] + PART[p] + ['--out', out]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return m, p, r.returncode, (r.stdout + r.stderr)[-300:]


if __name__ == '__main__':
    ms = sys.argv[1].split(',') if len(sys.argv) > 1 else ['off', 'on']
    ps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=3) as ex:
        for m, p, rc, tail in ex.map(lambda a: run_one(*a), [(m, p) for m in ms for p in ps]):
            print(m, p, 'rc', rc, tail.strip().splitlines()[-1] if tail.strip() else '')
