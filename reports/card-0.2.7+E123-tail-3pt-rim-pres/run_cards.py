"""E-123：由 reports/card-0.2.6+E107-defense-UL/run_cards.py 複製（UL6 組的參數一字不改），組別換成 c0、e123、e123h、e123p（預註冊 §5.1）。
  c0   = UL6 原樣（--tailSource 指向現行 attributes-e101.csv，--defSource 為 E-060 原檔）：重建 card 0.2.7（§5.2 c0）。
  e123 = --tailSource 換成 work/tail-new.csv（pressure 欄換成合併池值，其餘 12 欄原樣）＋ --defSource 換成 work/def-new.csv（new_help 換成合併池值，1 位小數，D7）。
  e123h = 只換 defSource；e123p = 只換 tailSource。
用法（repo 根目錄）：python -I reports/card-0.2.7+E123-tail-3pt-rim-pres/run_cards.py [<arm>[,<arm>]] [<part>[,<part>]]
子程序一律 CREATE_NO_WINDOW。輸出：<D>/cards/<arm>/<part>/
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
TAIL_CUR = 'reports/card-0.2.5+E101-crossera/attributes-e101.csv'
TAIL_NEW = D + '/work/tail-new.csv'
E104 = 'reports/card-0.2.5+E104-defense-pergame-decay'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
DEF_CUR = E060 + '/defense-attributes-e060.csv'
DEF_NEW = D + '/work/def-new.csv'
ARMS = {  # arm -> (tailSource, defSource)
    'c0': (TAIL_CUR, DEF_CUR),
    'e123': (TAIL_NEW, DEF_NEW),
    'e123h': (TAIL_CUR, DEF_NEW),
    'e123p': (TAIL_NEW, DEF_CUR),
}
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv', '--perGame']
P1 = ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv']
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}
FACTOR = '0.5'


def arm_args(p):   # E-107 UL6 原樣
    return ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', f'{E104}/def-L-{p}.csv', '--defPossFactor', FACTOR]


def run_one(a, p):
    out = f'{D}/cards/{a}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    tail, dsrc = ARMS[a]
    # 參數順序同 E-107：COMMON（含 --defSource 在 --attrSource 之後、--perGame 之前）＋ P1 ＋ TAIL ＋ PART ＋ arm 參數
    common = COMMON[:6] + ['--defSource', dsrc] + COMMON[6:]
    args = [sys.executable, '-I', D + '/calibrate-wing.py'] + common + P1 + ['--tailSource', tail] + PART[p] + arm_args(p) + ['--out', out]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return a, p, r.returncode, time.time() - t, (r.stdout + r.stderr)[-300:]


if __name__ == '__main__':
    arms = sys.argv[1].split(',') if len(sys.argv) > 1 else ['c0']
    ps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=4) as ex:
        for a, p, rc, dt, tail in ex.map(lambda x: run_one(*x), [(a, p) for a in arms for p in ps]):
            print(a, p, 'rc', rc, f'{dt:.0f}s', tail.strip().splitlines()[-1] if tail.strip() else '')
