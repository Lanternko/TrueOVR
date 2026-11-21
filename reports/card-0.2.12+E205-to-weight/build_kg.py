"""E-198（card 0.2.10j+E198）：自 reports/card-0.2.10d/build.py 複本，差別：CAL 換本目錄 calibrate_wing_t.py（E-181 版，不帶旗標逐位元同 E-180）；
臂 KAU（＝0.2.10i 部件卡）或 KG（多 --offBallSource gravity-attr.csv --offBallCols gravity，主效應）；只用 cards 子命令。
以下原說明。
card 0.2.10d（E-185）：自 reports/card-0.2.10a+E187-rebase/build.py 複本（KAU 臂＝card 0.2.10c 的建法），差別：
  1. 只留 KAU 臂；e162_build 用本資料夾的複本（多 E185_MPG 覆寫）；
  2. 8 項屬性的 long／creation 來源改環境變數 E185_TAIL_U（預設 reports/card-0.2.12/tail-U.csv）；
  3. 預測 MPG 改環境變數 E185_MPG（預設 reports/card-0.2.12/mpg-c82.csv；設空字串＝不覆寫）；
  4. 工作目錄可由 E185_WORK 指定（自我檢查用）。
原說明（0.2.10a+E187-rebase）：E-187 改疊 0.2.10a（L-102 修好的 T6）：自 E-187 e187_build.py 複本，差別只有 pkl() 換成修正後 T6／T6R、pass 共用斜率只在 KA／KJ 臂帶；臂 K6U（只重擬合）、KAU、KRU、KJU。
原說明：E-187 建卡驅動（自 E-186 e186_build.py 複本）：E-164 e164_build.py 的複本（S 臂流程：--dropAttr stamina、Y0 用人層、連續 d），差別只有三點：
  1. 工作目錄在本資料夾 work/（不寫 E-164 目錄）；
  2. 臂：KJ／KJU（目標 T6R、pass 共用斜率）、KA／KAU（目標 T6、pass 共用斜率）；U 結尾＝2025-26，8 項屬性用 0.2.10 的 tail-U.csv。
     K6 沿用 E-186 的重現卡，不在此建；
  3. U 臂的 --tailSource 換成 reports/card-0.2.10/tail-U.csv（環境變數 E187_TAIL，由臂名決定）。
用法（repo root）：python -I -B -X utf8 <本檔> cards <KJ|KA|KJU|KAU> <原點>  |  run <臂> <原點>  |  pipe <tag>（內部）
每個 (臂, 原點) 一個獨立行程（build_card_t 的 W 取自環境變數 E142_WORK，匯入時固定）。"""
import importlib.util, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E162 = HERE   # 本資料夾的 e162_build.py 複本
E142 = ROOT / 'reports/E142-card-target'
W = Path(os.environ['E185_WORK']) if os.environ.get('E185_WORK') else HERE / 'work'
CAL = HERE / 'calibrate_wing_t.py'   # E-198：E-181 版（不帶 --offBallCols 時與 E-180 逐位元同）
GRAV = HERE / 'gravity-attr.csv'   # E-164 複本＋--dropInteract（E-180）；不帶旗標時與 E-164 相同
ARM = ''
TAIL_U = Path(os.environ.get('E185_TAIL_U') or ROOT / 'reports/card-0.2.12/tail-U.csv')
if 'E185_MPG' not in os.environ:
    os.environ['E185_MPG'] = str(ROOT / 'reports/card-0.2.12/mpg-c82.csv')


def pkl(arm, t):
    return E142 / f'phase1-work/cands/T6-{t}.pkl'   # 修正後（L-102）T6


def run_calib_factory(RT, extra_drop):
    def run_calib(tag, cdir, parts):
        def one(p):
            cfgp, pargs, defr = parts[p]
            out = Path(cdir) / p
            out.mkdir(parents=True, exist_ok=True)
            a = [sys.executable, '-I', str(CAL), '--direction', 'H1', '--capMargin', '0', '--attrSource', RT.SRC['attr'],
                 '--defSource', RT.SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', RT.SRC['press'],
                 '--tailSource', os.environ.get('E187_TAIL') or RT.SRC['tail']] + pargs + \
                ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', str(defr), '--defPossFactor', '0.5', '--dropAttr', 'physique']
            for d in extra_drop:
                a += ['--dropAttr', d]
            if ARM in ('KAU', 'KG'):
                a += ['--dropInteract', 'pass']   # E-180 臂 A：傳球全位置共用斜率
            if ARM == 'KG':
                a += ['--offBallSource', str(GRAV), '--offBallCols', 'gravity']   # E-198
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
    global ARM
    assert arm in ('KAU', 'KG')
    ARM = arm
    wd = W / f'base-{arm}-{t}'
    wd.mkdir(parents=True, exist_ok=True)
    if True:
        assert t == '2025-26'
        os.environ['E187_TAIL'] = str(TAIL_U)
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
