"""E-107：由 reports/card-0.2.5+E106-defense-bonus-monotone/run_cards.py 複製，組別換成 B6、UL6（預註冊 §2.2）；
  兩組都加 --tailSource E-101 attributes-e101.csv（放在 P1 之後、PART 之前，同 E-101）。B6 不帶 --bonusShape（taper 預設，參數列和 E-101 相同）；
  UL6 = B6 ＋ --bonusShape none --defWindow season --defRapm E-104 的 def-L-<part>.csv --defPossFactor 0.5。
  另有 c0c 組（預註冊 §3）：不帶 --tailSource、用 E-106 UL 的參數，只跑 primary。
E-106：由 reports/card-0.2.5+E104-defense-pergame-decay/run_cards.py 複製，組別換成 T、U、UL（預註冊 §2.2）；
  U = --bonusShape none；UL = none ＋ --defWindow season --defRapm E-104 的 def-L-<part>.csv --defPossFactor 0.5。
E-104：由 reports/card-0.2.5+E094-defense-ceiling/run_cards.py 複製，組別換成 T、TL、TH（預註冊 §2.3）；
  TL／TH = T ＋ --defWindow season --defRapm def-<L|H>-<part>.csv --defPossFactor <平均權重>。
以下為 E-094 原說明：
E-094：card 0.2.2 P1 的三張卡（primary、fitA、fitB）× 四組（off、T、S、TS）。從 repo 根目錄執行。子程序一律 CREATE_NO_WINDOW。
  python -I reports/card-0.2.5+E094-defense-ceiling/run_cards.py [<arm>[,<arm>]] [<part>[,<part>]]
COMMON／P1／PART 照 reports/card-0.2.2/run_cards.py，一字不改；只換成本目錄的 calibrate-wing.py 並加 ARM 開關（preregistration.md §2）。
輸出：reports/card-0.2.5+E094-defense-ceiling/cards/<arm>/<part>/
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = 'reports/card-0.2.6+E107-defense-UL'
TAIL = ['--tailSource', 'reports/card-0.2.5+E101-crossera/attributes-e101.csv']
E104 = 'reports/card-0.2.5+E104-defense-pergame-decay'
E071 = 'reports/card-0.2.0+E071-pressure'
E070 = 'reports/card-0.2.0+E070-foul-volume'
E060 = 'reports/card-0.1.1+E060-onball-targeting'
E064 = 'reports/card-0.1.2+E064-pergame'
E081 = 'reports/card-0.2.3+E081-age-residual'
V58 = 'reports/ovr-v58-holdout-2025-26'
COMMON = ['--direction', 'H1', '--capMargin', '0', '--attrSource', E070 + '/attributes-w075/attributes-new.csv',
          '--defSource', E060 + '/defense-attributes-e060.csv', '--perGame']
P1 = ['--pressure', 'force', '--pressureSource', E071 + '/force-pressure-source.csv']
PART = {
    'primary': [],
    'fitA': ['--rapm', V58 + '/rapm-A.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-A.csv'],
    'fitB': ['--rapm', V58 + '/rapm-B.csv', '--possScale', '0.5', '--mpgSource', E064 + '/mpg-B.csv'],
}
FACTOR = {'L': '0.5', 'H': '0.338'}   # 預註冊 §2.3：L × 1/2、H × 0.338


def arm_args(a, p):
    if a == 'B6':
        return []
    return ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', f'{E104}/def-L-{p}.csv', '--defPossFactor', FACTOR['L']]   # UL6、c0c


def run_one(a, p):
    out = f'{D}/cards/{a}/{p}'
    Path(out).mkdir(parents=True, exist_ok=True)
    args = [sys.executable, '-I', D + '/calibrate-wing.py'] + COMMON + P1 + ([] if a == 'c0c' else TAIL) + PART[p] + arm_args(a, p) + ['--out', out]
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    Path(out + '/run.log').write_text(' '.join(args[2:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
    return a, p, r.returncode, time.time() - t, (r.stdout + r.stderr)[-300:]


if __name__ == '__main__':
    arms = sys.argv[1].split(',') if len(sys.argv) > 1 else ['B6', 'UL6']
    ps = sys.argv[2].split(',') if len(sys.argv) > 2 else ['primary', 'fitA', 'fitB']
    with ThreadPoolExecutor(max_workers=4) as ex:
        for a, p, rc, dt, tail in ex.map(lambda x: run_one(*x), [(a, p) for a in arms for p in ps]):
            print(a, p, 'rc', rc, f'{dt:.0f}s', tail.strip().splitlines()[-1] if tail.strip() else '')
