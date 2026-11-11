"""E-186 c0：card-0.2.10/run_parts.py 的複本，只改路徑（calibrate_frozen.py 與 0.2.9a 凍結檔指向原處、輸出寫本資料夾 work/）。"""
"""card 0.2.10 第一層：用凍結係數的 calibrate_frozen.py 建三張部件卡。
用法：python -I -X utf8 run_parts.py <tag> <tail.csv>     輸出 work/<tag>/cards/<part>
tag=self（餵 0.2.9a 原 tail，自我檢查）／U（餵 tail-U.csv）"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E164W = ROOT / 'reports/card-0.2.9+E164-no-stamina/work/base-S-2025-26/c0'
MPG = ROOT / 'reports/card-0.2.7c+E134-rolling-prior/stage1/work/c0p/mpg'
A29 = ROOT / 'reports/card-0.2.9a/cards/K6'
SRC = {'attr': 'reports/card-0.2.0+E070-foul-volume/attributes-w075/attributes-new.csv',
       'def': 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work/def-new.csv',
       'press': 'reports/card-0.2.0+E071-pressure/force-pressure-source.csv',
       'tail': 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv'}


def main(tag, tail):
    W = HERE / 'work' / tag / 'cards'
    def one(p):
        out = W / p; out.mkdir(parents=True, exist_ok=True)
        pa = ['--rapm', str(E164W / 'rapm-R.csv')] if p == 'primary' else \
             ['--rapm', str(E164W / f'split/rapm-{p[-1]}.csv'), '--possScale', '0.5', '--mpgSource', str(MPG / f'mpg-{p[-1]}.csv')]
        a = [sys.executable, '-I', '-X', 'utf8', str(ROOT / 'reports/card-0.2.10/calibrate_frozen.py'), '--direction', 'H1', '--capMargin', '0', '--attrSource', SRC['attr'],
             '--defSource', SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', SRC['press'], '--tailSource', tail] + pa + \
            ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', str(E164W / f'def-L-{p}.csv'), '--defPossFactor', '0.5',
             '--dropAttr', 'physique', '--dropAttr', 'stamina',
             '--frozenSummary', str(A29 / p / 'summary.json'), '--frozenPergame', str(A29 / p / 'pergame-summary.json'), '--out', str(out)]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', E134_CFG=str(E164W / f'calib-{p}.json'))
        r = subprocess.run(a, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, stdin=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=1800)
        (out / 'run.log').write_text(' '.join(a[3:]) + '\n' + r.stdout + '\n' + r.stderr, encoding='utf-8')
        return p, r.returncode, r.stderr[-500:]
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(one, ['primary', 'fitA', 'fitB']))
    print(res)
    return 1 if any(r[1] for r in res) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
