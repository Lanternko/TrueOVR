"""card 0.2.2：card 0.2.0 + E-070（foulDraw w075）+ E-071 P1（pressure 事件式 force）。從 repo 根目錄執行。子程序一律 CREATE_NO_WINDOW。
  python -I reports/card-0.2.2/run_cards.py [<variant>[,<variant>]] [<part>[,<part>]]
variant：base（P1 開關全關；只有 E-070 w075）、P1（--pressure force）。part：primary、fitA、fitB（預設全跑）。
參數照 reports/card-0.2.0+E071-pressure/run_cards.py 的 COMMON／PART，只把 --attrSource 換成 E-070 w075；不准調（L-026）。
輸出：reports/card-0.2.2/cards/<variant>/<part>/
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.2'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv',
          '--defSource', E060 + '/defense-attributes-e060.csv', '--perGame']
VARIANT = {
    'base': [],
    'P1': ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv'],
}
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}


def run_one(v, p):
    out = f'{D}/cards/{v}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    args = [sys.executable, '-I', E071 + '/calibrate-wing.py'] + COMMON + VARIANT[v] + PART[p] + ['--out', out]
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return v, p, r.returncode, (r.stdout + r.stderr)[-300:]


if __name__ == '__main__':
    vs = sys.argv[1].split(',') if len(sys.argv) > 1 else ['base', 'P1']
    ps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=4) as ex:
        for v, p, rc, tail in ex.map(lambda a: run_one(*a), [(v, p) for v in vs for p in ps]):
            print(v, p, 'rc', rc, tail.strip().splitlines()[-1] if tail.strip() else '')
