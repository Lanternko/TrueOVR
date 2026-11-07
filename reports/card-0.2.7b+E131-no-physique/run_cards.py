"""E-131：由 reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/run_cards.py 複製，只跑 arm e123a 的 tail／def 輸入（唯讀沿用 rebase-027a/work/tail-e123a.csv 與 E-123 work/def-new.csv，不重新 merge）。
  K0 = 不帶 --dropAttr（要和 card 0.2.7b 逐位元相同）；K1 = --dropAttr physique。calibrate-wing.py 用本目錄的複本。其餘參數、旗標、順序一字不改。
用法（repo 根目錄）：python -I -X utf8 reports/card-0.2.7b+E131-no-physique/run_cards.py run [<arm>[,<arm>]] [<part>[,<part>]]
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
D = 'reports/card-0.2.7b+E131-no-physique'
RB = 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a'
E123 = 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
TAIL_E123A = RB + '/work/tail-e123a.csv'
E104 = 'reports/card-0.2.5+E104-defense-pergame-decay'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
DEF_CUR = E060 + '/defense-attributes-e060.csv'
DEF_NEW = E123 + '/work/def-new.csv'
ARMS = {  # arm -> (tailSource, defSource, extra args)
    'K0': (TAIL_E123A, DEF_NEW, []),
    'K1': (TAIL_E123A, DEF_NEW, ['--dropAttr', 'physique']),
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


def arm_args(p):   # E-107 UL6 原樣
    return ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', f'{E104}/def-L-{p}.csv', '--defPossFactor', FACTOR]


def run_one(a, p):
    out = f'{D}/cards/{a}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    tail, dsrc, extra = ARMS[a]
    common = COMMON[:6] + ['--defSource', dsrc] + COMMON[6:]
    args = [sys.executable, '-I', D + '/calibrate-wing.py'] + common + P1 + ['--tailSource', tail] + PART[p] + arm_args(p) + extra + ['--out', out]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW, timeout=1500)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return a, p, r.returncode, time.time() - t, (r.stdout + r.stderr)[-300:]


def run():
    arms = sys.argv[2].split(',') if len(sys.argv) > 2 else ['K0', 'K1']
    ps = sys.argv[3].split(',') if len(sys.argv) > 3 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=4) as ex:
        for a, p, rc, dt, tail in ex.map(lambda x: run_one(*x), [(a, p) for a in arms for p in ps]):
            print(a, p, 'rc', rc, f'{dt:.0f}s', tail.strip().splitlines()[-1] if tail.strip() else '', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit({'run': run}[sys.argv[1]]())
