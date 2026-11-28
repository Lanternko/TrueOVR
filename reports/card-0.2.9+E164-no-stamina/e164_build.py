"""E-164 建卡驅動。
  cards <Kc|S> <原點>  ：用本資料夾 calibrate_wing_t.py 複本重建三張部件卡（路徑同 E-153 K6：e153_build，候選 pkl＝T6）。
                         Kc＝不加旗標（c0d：部件卡要和 E-153 K6 逐位元相同）；S＝多加 --dropAttr stamina。
                         （原檔旗標 --dropAttr 已存在、可重複，複本與原檔逐位元相同，未改一字；run_t.run_calib 寫死 physique，這裡換成含 stamina 的版本。）
  run <K|S> <原點>     ：Y0 用人層（同 E-162 的 K：設計矩陣 [1,p,L,a,y,v,y·L,v·L]）。K 用 E-153 K6 現成的卡（唯讀）；S 用 cards S 的卡。
  pipe <tag>           ：（內部）
用法（repo root）：python -I -B -X utf8 <本檔> ...
"""
import importlib.util, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
E142 = ROOT / 'reports/E142-card-target'
W = HERE / 'work'
CAL = HERE / 'calibrate_wing_t.py'


def run_calib_factory(RT, extra_drop):
    def run_calib(tag, cdir, parts):
        def one(p):
            cfgp, pargs, defr = parts[p]
            out = Path(cdir) / p
            out.mkdir(parents=True, exist_ok=True)
            a = [sys.executable, '-I', str(CAL), '--direction', 'H1', '--capMargin', '0', '--attrSource', RT.SRC['attr'],
                 '--defSource', RT.SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', RT.SRC['press'], '--tailSource', RT.SRC['tail']] + pargs + \
                ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', str(defr), '--defPossFactor', '0.5', '--dropAttr', 'physique']
            for d in extra_drop:
                a += ['--dropAttr', d]
            a += ['--out', str(out)]
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
    BC.RT.run_calib = run_calib_factory(BC.RT, ['stamina'] if arm == 'S' else [])
    sys.argv = ['e153_build.py', 'build', t, str(wd), '1', str(pk)]
    # e153_build.main 內的 run_pipe 會以 __file__ 開 pipe 子程序；__file__ 指向 e153_build.py（模組載入時設定），可用
    return e153.main()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'cards':
        sys.exit(cards(sys.argv[2], sys.argv[3]))
    # run / pipe：沿用 E-162 的 run／pipe，只換 W 與 bdir
    spec = importlib.util.spec_from_file_location('e162b', E162 / 'e162_build.py')
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
    E.W = W
    E.bdir = lambda arm, t: E.kdir(t) if arm == 'K' else W / f'base-{arm}-{t}'
    # E-162 的 run 以 sys.argv[0]/__file__ 開 pipe 子程序，要指向本檔
    E.__file__ = str(Path(__file__).resolve())
    if sys.argv[1] == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(E.pipe(sys.argv[2]))
    sys.exit(E.run(sys.argv[2], sys.argv[3]))
