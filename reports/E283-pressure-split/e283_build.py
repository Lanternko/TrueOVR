"""E-283 建卡驅動（prereg.md 凍結後執行）。Q1／Q2 拿掉 pressure，Q3 保留；blk36 固定 0.3。
  python -I -B -X utf8 e283_build.py <臂> <原點>  → ranking-<臂>-<原點>.csv（calibrate 用 reports/E280-blk-weight/calibrate_wing_t_dx.py，env DX_*）
"""
import importlib.util, os, shutil, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'


def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def cards_pre_l102(B, t, arm=None):
    drop = ['stamina'] + (['pressure'] if ARMS[arm][1] else [])
    """同 e164_build.cards('S', t)，但候選 pkl 用 cands/pre-L102/（E-164 當時的 T6；0.2.11 修 BPM 解析後 cands/ 已重產，A0 才能逐位元重現 E-164 S 卡）。"""
    wd = B.W / f'base-S-{t}'
    wd.mkdir(parents=True, exist_ok=True)
    pk = B.E142 / f'phase1-work/cands/pre-L102/T6-{t}.pkl'
    spec = importlib.util.spec_from_file_location('e153b', B.E153 / 'e153_build.py')
    e153 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e153)
    os.environ['E142_WORK'] = str(wd)
    sys.path.insert(0, str(B.E142))
    import build_card_t as BC
    e153.BC = BC
    BC.RT.run_calib = B.run_calib_factory(BC.RT, drop)
    sys.argv = ['e153_build.py', 'build', t, str(wd), '1', str(pk)]
    return e153.main()


_P4 = 'p_stl,p_defl,p_mtov,p_chg'
ARMS = {'Q1': (_P4, True), 'Q2': (_P4 + ',p_pf', True), 'Q3': (_P4, False)}


def main():
    arm, t = sys.argv[1], sys.argv[2]
    ex = 'blk36,' + ARMS[arm][0]
    os.environ.update(DX_ARM=arm, DX_SEASON=t, DX_EXTRA=ex, DX_WINDOW='1', DX_NONNEG='0', DX_FIX='blk36:0.3')
    W = HERE / 'work' / arm
    W.mkdir(parents=True, exist_ok=True)
    B = load_mod('e164b', E164 / 'e164_build.py')
    B.W, B.CAL = W, ROOT / 'reports/E280-blk-weight/calibrate_wing_t_dx.py'
    rc = cards_pre_l102(B, t, arm)
    if rc:
        return rc
    E = load_mod('e162b', B.E162 / 'e162_build.py')
    E.W = W
    E.bdir = lambda a, tt: W / f'base-{a}-{tt}'
    E.__file__ = str(Path(__file__).resolve())
    rc = E.run('S', t)
    if rc:
        return rc
    shutil.copy(W / f'S-{t}' / 'out' / 'ranking.csv', HERE / f'ranking-{arm}-{t}.csv')
    return 0


def pipe(tag):
    arm = sys.argv[3] if len(sys.argv) > 3 else None
    B = load_mod('e164b', E164 / 'e164_build.py')
    W = Path(os.environ['E142_WORK'])
    E = load_mod('e162b', B.E162 / 'e162_build.py')
    E.W = W
    E.bdir = lambda a, tt: W / f'base-{a}-{tt}'
    E.__file__ = str(Path(__file__).resolve())
    return E.pipe(tag)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'pipe':
        sys.exit(pipe(sys.argv[2]))
    sys.exit(main())
