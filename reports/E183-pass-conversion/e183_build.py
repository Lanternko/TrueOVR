"""E-183 建卡驅動（自 E-180 e180_build.py：部件卡 --dropAttr stamina；calibrate 用本目錄 calibrate_wing_t.py 複本，未改）。
  cards <K0|Q> <原點>：重建三張部件卡。K0＝0.2.9a 原樣（c0／c0h）；Q＝--tailSource 換成 work/tail-Q.csv（只有 pass 欄不同）。
  run <K0|Q> <原點>  ：Y0 用人層（同 E-164 S 臂）。輸出 work/base-<臂>-<原點>/out/ranking.csv。
  pipe <tag>         ：（內部）
用法（repo root）：python -I -B -X utf8 <本檔> ...
"""
import importlib.util, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
# 手動跑也不准閃黑窗：所有子程序預設帶 CREATE_NO_WINDOW
_popen_init = subprocess.Popen.__init__
def _popen_nowin(self, *a, **k):
    k['creationflags'] = k.get('creationflags', 0) | subprocess.CREATE_NO_WINDOW
    _popen_init(self, *a, **k)
subprocess.Popen.__init__ = _popen_nowin
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
E142 = ROOT / 'reports/E142-card-target'
W = HERE / 'work'
CAL = HERE / 'calibrate_wing_t.py'


def run_calib_factory(RT, extra):
    def run_calib(tag, cdir, parts):
        def one(p):
            cfgp, pargs, defr = parts[p]
            out = Path(cdir) / p
            out.mkdir(parents=True, exist_ok=True)
            a = [sys.executable, '-I', str(CAL), '--direction', 'H1', '--capMargin', '0', '--attrSource', RT.SRC['attr'],
                 '--defSource', RT.SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', RT.SRC['press'], '--tailSource', RT.SRC['tail']] + pargs + \
                ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', str(defr), '--defPossFactor', '0.5', '--dropAttr', 'physique',
                 '--dropAttr', 'stamina'] + extra + ['--out', str(out)]
            env = {'E134_CFG': str(cfgp)} if cfgp else {}
            rc, sec, err = RT.sub_run(a, env, out / 'run.log')
            return p, rc, sec, err
        with ThreadPoolExecutor(max_workers=3) as ex:
            res = list(ex.map(one, list(parts)))
        bad = [r for r in res if r[1] != 0]
        if bad:
            raise SystemExit(f'{tag} calibrate failed: {bad}')
        return {p: RT.sha(Path(cdir) / p / 'ranking.csv') for p in parts}, [(p, rc, sec) for p, rc, sec, _ in res]
    return run_calib


def cards(arm, t):
    wd = W / f'base-{arm}-{t}'
    wd.mkdir(parents=True, exist_ok=True)
    pk = E142 / f'phase1-work/cands/T6-{t}.pkl'
    spec = importlib.util.spec_from_file_location('e153b', E153 / 'e153_build.py')
    e153 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e153)
    os.environ['E142_WORK'] = str(wd)
    sys.path.insert(0, str(E142))
    import build_card_t as BC
    e153.BC = BC
    if arm == 'Q':
        BC.RT.SRC['tail'] = 'reports/E183-pass-conversion/work/tail-Q.csv'
    BC.RT.run_calib = run_calib_factory(BC.RT, [])
    sys.argv = ['e153_build.py', 'build', t, str(wd), '1', str(pk)]
    return e153.main()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'cards':
        sys.exit(cards(sys.argv[2], sys.argv[3]))
    spec = importlib.util.spec_from_file_location('e162b', E162 / 'e162_build.py')
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
    E.W = W
    E.bdir = lambda arm, t: E.kdir(t) if arm == 'K' else W / f'base-{arm}-{t}'
    E.__file__ = str(Path(__file__).resolve())
    if sys.argv[1] == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(E.pipe(sys.argv[2]))
    sys.exit(E.run(sys.argv[2], sys.argv[3]))
