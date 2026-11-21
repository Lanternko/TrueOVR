"""E-196（R-133）建卡驅動。臂由環境變數 E196_ARM＝G|S|SP 決定（spec.md 凍結定義）：
  G ：0.2.10g 原樣（開關全關）。2025-26＝card-0.2.10d/build.py 的 KAU 部件卡（--dropInteract pass、tail＝card-0.2.12/tail-U.csv）
      ＋card-0.2.10g/e162_build.py 用人層（E192_USAGE、E185_MPG）＋E-188 OVR 映射；ranking 必須與 card-0.2.10g/ranking.csv 逐位元組相同。
  S ：G＋long 也做全位置共用斜率（多一個 --dropInteract long），全部係數重擬合。
  SP：S＋creation 欄換成 production（e196_prod.py 產的 tail-U-SP.csv）；production 不在 INTERACT（全位置共用斜率）；
      部件卡各自加 --floorCoef creation=<G 臂同一部件卡 creation 每點係數>（低於下限固定在下限、offset 重擬合其餘係數）。
  歷史原點（A 線，2022-23～2024-25）：沿用 E-181 的歷史設定（K0h：0.2.9a 底，tail-e123a.csv、--dropAttr stamina、card-0.2.9+E162 e162_build）。
      G＝K0h（必須與 card-0.2.9a+E177 ranking-K0-<t>.csv 逐位元組相同）；S＝＋--dropInteract long；SP＝＋tail-e123a-SP.csv＋同樣的係數下限。
用法（repo root）：E196_ARM=<臂> python -I -B -X utf8 <本檔> cards|run <原點>  |  pipe <tag>（內部）  |  final（2025-26 映射，三臂）"""
import csv, hashlib, importlib.util, json, os, shutil, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E142 = ROOT / 'reports/E142-card-target'
G10 = ROOT / 'reports/card-0.2.10g'
E162H = ROOT / 'reports/card-0.2.9+E162-per-volume'
W = HERE / 'work'
CAL = HERE / 'calibrate_wing_t.py'
ARM = os.environ.get('E196_ARM', 'G')
assert ARM in ('G', 'S', 'SP'), ARM
TAIL = {'2025-26': {'G': ROOT / 'reports/card-0.2.12/tail-U.csv', 'S': ROOT / 'reports/card-0.2.12/tail-U.csv', 'SP': HERE / 'tail-U-SP.csv'}}
TAIL_H_SP = HERE / 'tail-e123a-SP.csv'
USAGE = G10 / 'usage-window-c82.csv'
MPG = ROOT / 'reports/card-0.2.12/mpg-c82.csv'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cdir_name(t):
    return 'c0' if t == '2025-26' else t


def floor_of(t, part):
    sm = json.loads((W / f'base-G-{t}' / cdir_name(t) / 'cards/K0' / part / 'summary.json').read_text(encoding='utf-8'))
    return sm['valuePer10AttributePoints']['creation']['per36'] / 10


def run_calib_factory(RT, t):
    def run_calib(tag, cdir, parts):
        def one(p):
            cfgp, pargs, defr = parts[p]
            out = Path(cdir) / p
            out.mkdir(parents=True, exist_ok=True)
            tail = str(TAIL[t][ARM]) if t == '2025-26' else (str(TAIL_H_SP) if ARM == 'SP' else RT.SRC['tail'])
            a = [sys.executable, '-I', str(CAL), '--direction', 'H1', '--capMargin', '0', '--attrSource', RT.SRC['attr'],
                 '--defSource', RT.SRC['def'], '--perGame', '--pressure', 'force', '--pressureSource', RT.SRC['press'],
                 '--tailSource', tail] + pargs + \
                ['--bonusShape', 'none', '--defWindow', 'season', '--defRapm', str(defr), '--defPossFactor', '0.5', '--dropAttr', 'physique', '--dropAttr', 'stamina']
            if t == '2025-26':
                a += ['--dropInteract', 'pass']   # 0.2.10c 起（E-187 KAU）：傳球全位置共用斜率
            if ARM in ('S', 'SP'):
                a += ['--dropInteract', 'long']   # E-196 S：三分全位置共用斜率
            if ARM == 'SP':
                a += ['--floorCoef', f'creation={floor_of(t, p)!r}']
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


def cards(t):
    wd = W / f'base-{ARM}-{t}'
    wd.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('e153b', E153 / 'e153_build.py')
    e153 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e153)
    os.environ['E142_WORK'] = str(wd)
    sys.path.insert(0, str(E142))
    import build_card_t as BC
    e153.BC = BC
    BC.RT.run_calib = run_calib_factory(BC.RT, t)
    sys.argv = ['e153_build.py', 'build', t, str(wd), '1', str(E142 / f'phase1-work/cands/T6-{t}.pkl')]
    return e153.main()


def e162(t):
    if t == '2025-26':
        os.environ['E192_USAGE'] = str(USAGE)
        os.environ['E185_MPG'] = str(MPG)
        src = G10 / 'e162_build.py'
    else:
        os.environ.pop('E192_USAGE', None); os.environ.pop('E185_MPG', None)
        src = E162H / 'e162_build.py'
    spec = importlib.util.spec_from_file_location('e162x', src)
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
    E.W = W
    E.bdir = lambda arm, t_: W / f'base-{arm}-{t_}'
    E.__file__ = str(Path(__file__).resolve())
    return E


def final():
    """2025-26 三臂：同 card-0.2.10g/build_0210g.py real 的映射（E-188 apply_to_card，錨取本池）。"""
    s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
    AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)
    D, F = ROOT / 'reports/card-0.2.10d', ROOT / 'reports/card-0.2.10f'
    rel = lambda p: p.relative_to(ROOT).as_posix()
    out = {}
    for arm in ('G', 'S', 'SP'):
        pre, fo = W / f'final-{arm}/pre', W / f'final-{arm}/out'
        pre.mkdir(parents=True, exist_ok=True); fo.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(W / f'{arm}-2025-26/out/ranking.csv', pre / 'ranking.csv')
        for n in ('three-value.csv', 'rapm-T6.csv'):
            shutil.copyfile(D / n, pre / n)
        AC.main(rel(pre), rel(fo), f'E-196 {arm}')
        shutil.copyfile(fo / 'ranking.csv', HERE / f'ranking-{arm}.csv')
        out[arm] = sha(HERE / f'ranking-{arm}.csv')
    out['G_equals_0.2.10g'] = (HERE / 'ranking-G.csv').read_bytes() == (G10 / 'ranking.csv').read_bytes()
    out['0.2.10g'] = sha(G10 / 'ranking.csv')
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    cmd = sys.argv[1]
    if cmd == 'cards':
        sys.exit(cards(sys.argv[2]))
    if cmd == 'final':
        sys.exit(final())
    t = sys.argv[2][-7:] if cmd == 'pipe' else sys.argv[2]
    E = e162(t)
    if cmd == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(E.pipe(sys.argv[2]))
    sys.exit(E.run(ARM, t))
