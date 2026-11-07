"""E-186 建卡驅動：E-164 e164_build.py 的複本（S 臂流程：--dropAttr stamina、Y0 用人層、連續 d），差別只有三點：
  1. 工作目錄在本資料夾 work/（不寫 E-164 目錄）；
  2. 臂：K6／KR（歷史三原點與 2025-26 舊 tail）、K6U／KRU（2025-26，8 項屬性用 0.2.10 的 tail-U.csv，係數依各自目標重擬合；K6U 只當對照）。
     K6／K6U 的目標＝T6（E-142 候選 pkl），KR／KRU＝T6R（e186_cands.py）；
  3. U 臂的 --tailSource 換成 reports/card-0.2.10/tail-U.csv（環境變數 E186_TAIL，由臂名決定）。
用法（repo root）：python -I -B -X utf8 <本檔> cards <K6|KR|K6U|KRU> <原點>  |  run <臂> <原點>  |  pipe <tag>（內部）
每個 (臂, 原點) 一個獨立行程（build_card_t 的 W 取自環境變數 E142_WORK，匯入時固定）。"""
import importlib.util, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
E142 = ROOT / 'reports/E142-card-target'
W = HERE / 'work'
CAL = ROOT / 'reports/card-0.2.9+E164-no-stamina/calibrate_wing_t.py'
TAIL_U = ROOT / 'reports/card-0.2.10/tail-U.csv'


def pkl(arm, t):
    return W / 'cands' / f'T6R-{t}.pkl' if arm.startswith('KR') else E142 / f'phase1-work/cands/T6-{t}.pkl'


def run_calib_factory(RT, extra_drop):
    def run_calib(tag, cdir, parts):
        def one(p):
            cfgp, pargs, defr = parts[p]
            out = Path(cdir) / p
            out.mkdir(parents=True, exist_ok=True)
            a = [sys.executable, '-I', str(CAL), '--direction', 'H1', '--capMargin', '0', '--attrSource', RT.SRC['attr'],
                 '--defSource', RT.SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', RT.SRC['press'],
                 '--tailSource', os.environ.get('E186_TAIL') or RT.SRC['tail']] + pargs + \
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
    if arm.endswith('U'):
        assert t == '2025-26'
        os.environ['E186_TAIL'] = str(TAIL_U)
    spec = importlib.util.spec_from_file_location('e153b', E153 / 'e153_build.py')
    e153 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e153)
    os.environ['E142_WORK'] = str(wd)
    sys.path.insert(0, str(E142))
    import build_card_t as BC
    e153.BC = BC
    BC.RT.run_calib = run_calib_factory(BC.RT, ['stamina'])
    sys.argv = ['e153_build.py', 'build', t, str(wd), '1', str(pkl(arm, t))]
    return e153.main()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'cards':
        sys.exit(cards(sys.argv[2], sys.argv[3]))
    spec = importlib.util.spec_from_file_location('e162b', E162 / 'e162_build.py')
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
    E.W = W
    E.bdir = lambda arm, t: W / f'base-{arm}-{t}'
    E.__file__ = str(Path(__file__).resolve())
    if sys.argv[1] == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(E.pipe(sys.argv[2]))
    sys.exit(E.run(sys.argv[2], sys.argv[3]))
