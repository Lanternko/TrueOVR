"""card 0.2.10d：自 reports/card-0.2.9+E162-per-volume/e162_build.py 複本，差別只有 pipe()：
  1. e153_helpers 仍從原 E-162 目錄匯入；
  2. 環境變數 E185_MPG（csv: playerId,mpg）給定時，只把 scope 'full' 的 mp（g／錨用的預測 MPG）換成窗口值；L 與設計矩陣不動；未給＝與原版逐位元相同。
原說明：E-162 建卡驅動（複製 E-158 e158_build.py 的 Y0 臂，只改 spec 來源）。
  K       ：重跑 E-158 Y0（用 E-153 K6 的部件卡）；c0 要和 card-0.2.9／E-158 ranking-Y0 逐位元相同
  P15/P30 ：先用 E-153 的 e153_build 以 work/cands/<臂>-<季>.pkl 重建部件卡（primary／fitA／fitB 的 --rapm 全換，同 errata-1），
            再接 Y0 用人層（設計矩陣拿掉 y·d·L）
用法（repo root）：python -I -B -X utf8 <本檔> cards <臂> <原點>   |  run <臂> <原點>  |  pipe <tag>（內部）
"""
import csv, json, os, pickle, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
E153 = ROOT / 'reports/card-0.2.7d+E153-t6-target'
E153W = ROOT / 'reports/card-0.2.7d+E153-t6-target/work'
W = HERE / 'work'
HDR = ['playerId', 'name', 'net', 'O', 'D', 'poss']


def kdir(t):
    return E153W / f'K6-{t}'


def bdir(arm, t):
    return kdir(t) if arm == 'K' else W / f'base-{arm}-{t}'


def k_specs(arm, t):
    d = bdir(arm, t)
    n = 'c0' if t == '2025-26' else t
    return d / f'{n}-pipe.json', d / f'{n}-e094cfg.json'


def cards(arm, t):
    """用 E-153 e153_build 重建部件卡（K6 路徑），候選 pkl 換成 P15／P30。"""
    wd = bdir(arm, t); wd.mkdir(parents=True, exist_ok=True)
    pk = W / 'cands' / f'{arm}-{t}.pkl' if arm != 'T6' else E142 / f'phase1-work/cands/T6-{t}.pkl'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(E153 / 'e153_build.py'), 'build', t, str(wd), '1', str(pk)], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, stdin=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=3000)
    print(arm, t, 'rc', r.returncode, r.stdout.strip()[-600:], r.stderr[-400:])
    return r.returncode


def swap_rapm1(src_dir, dst_dir, cand):
    dst_dir.mkdir(parents=True, exist_ok=True)
    info = {}
    for h in 'AB':
        rows = list(csv.DictReader(open(src_dir / f'rapm1-{h}.csv', encoding='utf-8')))
        kept = 0
        with open(dst_dir / f'rapm1-{h}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh); w.writerow(HDR)
            for r in rows:
                pid = int(r['playerId'])
                if pid in cand:
                    net, o, d = cand[pid]
                    w.writerow([r['playerId'], r['name'], net, o, d, r['poss']]); kept += 1
        info[h] = {'in': len(rows), 'out': kept}
    return info


def run(arm, t):
    W.mkdir(parents=True, exist_ok=True)
    tag = f'{arm}-{t}'
    sp, cp = k_specs(arm if arm != 'K' else 'K', t)
    base = arm
    arm = 'Y0'
    spec = json.loads(sp.read_text(encoding='utf-8'))
    cfg = json.loads(cp.read_text(encoding='utf-8'))
    out = W / tag / 'out'
    out.mkdir(parents=True, exist_ok=True)
    spec['out'] = str(out)
    spec['arm'] = arm
    swap = None
    if arm == 'Y1':
        cand = pickle.load(open(E142 / f'phase1-work/cands/T6-{t}.pkl', 'rb'))
        swap = swap_rapm1(Path(cfg['rapm1Dir']), W / tag / 'rapm1', cand)
        cfg['rapm1Dir'] = str(W / tag / 'rapm1')
    (W / f'{tag}-pipe.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding='utf-8')
    (W / f'{tag}-e094cfg.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', E134_CFG=str(W / f'{tag}-e094cfg.json'), E142_WORK=str(W))
    t0 = time.time()
    r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(Path(__file__).resolve()), 'pipe', tag], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=3000)
    (out / 'pipe.log').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
    if r.returncode:
        print(tag, 'FAILED', r.stderr[-800:]); return 1
    print(tag, r.stdout.strip().splitlines()[-1], 'swap', swap, round(time.time() - t0, 1), 's')
    return 0


def pipe(tag):
    spec = json.loads((W / f'{tag}-pipe.json').read_text(encoding='utf-8'))
    arm, out = spec['arm'], Path(spec['out'])
    import importlib.util
    import numpy as np
    sys.path.insert(0, str(E142))
    import build_card_t as BC
    s = importlib.util.spec_from_file_location('e094t', BC.S1 / 'e094_t.py')
    M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
    M.HERE, M.W, M.CARDS = out, out / 'work', out / 'cards'
    M.load_data()
    M.set_card_dir(spec['poolCards'] if spec.get('poolCards') else spec['cards'])
    pools = M.build_pools()
    M.set_card_dir(spec['cards'])
    # 連續 d（E-147），同 e153_build
    sys.path.insert(0, str(ROOT / 'reports/card-0.2.9+E162-per-volume'))
    import e153_helpers as H
    tgp = M._P('teamGames', 'data/season-source/team-games.json')
    tgp = tgp if Path(str(tgp)).is_absolute() else ROOT / tgp
    tb = H.team_badness(M, tgp)
    ORIG = M.scope_feats
    dump = {'full': None, 'wls': []}
    mpg_f = os.environ.get('E185_MPG')
    mp_new = {int(x['playerId']): float(x['mpg']) for x in csv.DictReader(open(mpg_f, encoding='utf-8'))} if mpg_f else {}
    def sf3(*a):
        r = ORIG(*a)
        if mp_new and a[0] == 'full':
            r['mp'] = np.array([mp_new.get(int(q), v) for q, v in zip(r['pids'], r['mp'])], float)
        r['d'] = np.array([tb[t]['d'] if t is not None else 0.0 for t in r['main']])
        if a[0] == 'full':
            dump['full'] = {'pid': list(r['pids']), 'y': r['y'].tolist(), 'd': r['d'].tolist(), 'L': r['L'].tolist(), 'has': r['has'].tolist()}
        return r
    M.scope_feats = sf3
    OW = M.wls
    def wls2(X, y, w):
        c = OW(X, y, w); dump['wls'].append(np.asarray(c).tolist()); return c
    M.wls = wls2
    if arm == 'Y0':
        def design0(sf, sel, k, p=None):
            p = sf['p'][sel] if p is None else p
            L, a, y, v = (sf[c][sel] for c in 'L a y v'.split())
            return np.column_stack([np.ones_like(p), p, L, a, y, v, y * L, v * L])
        M.design = design0
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(ROOT / BC.RT.E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    rows = [dict(r) for r in r_['_aux']['rows23']]
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = BC.RT.fmt1(pdnew[r['name']])
    M.write_rank(out / 'ranking.csv', r_['_aux']['cols23'], rows)
    # 0.2.10d：另存用人層的凍結特徵＋本次重擬合的係數／r_repl／錨點（inseason 端 build_usage_0210d.py 讀；不影響 ranking.csv）
    coef_d = r_['coef']['card']
    assert 'b8_ydL' not in coef_d and len(coef_d) == 8
    coef = np.array([coef_d.get(k, 0.0) for k in M.COEF_NAMES])
    r_repl, anc = float(r_['card']['r_repl']), {k: float(v) for k, v in r_['card']['anchors'].items()}
    sf = M.scope_feats('full', M.D['prim'], M.classify(M.BASE_OPTS), M.BASE_OPTS)
    pred_new = np.where(sf['has'], M.design(sf, np.arange(sf['n']), 9) @ coef[:8], sf['p'])
    g = (pred_new - r_repl) * M.w_sat(sf['mp'])
    ovr = M.two_segment(g, anc['PR1'], anc['PR50'], anc['PR99'])
    rk_ = {r['name']: r for r in rows}
    pl = {}
    for i, q in enumerate(sf['pids']):
        nm = M.D['prim'][q]['name']
        pl[str(q)] = {'name': nm, 'has': bool(sf['has'][i]), 'L': float(sf['L'][i]), 'a': float(sf['a'][i]), 'y': float(sf['y'][i]), 'v': float(sf['v'][i]),
                      'd': float(sf['d'][i]), 'age': sf['age'][i], 'mpgAvail': float(sf['mp'][i]), 'p': float(sf['p'][i]), 'predNew': float(pred_new[i]),
                      'ovrCard': float(rk_[nm]['ovr']),
                      'ok': bool(f"{ovr[i]:.1f}" == rk_[nm]['ovr'] and f"{sf['mp'][i]:.2f}" == rk_[nm]['mpg'] and f"{g[i]:.4f}" == rk_[nm]['gRepl'])}
    (out / 'usage-features.json').write_text(json.dumps({'coef': dict(zip(M.COEF_NAMES, map(float, coef))), 'rRepl': r_repl, 'anchors': anc,
        'predNewVsPipeline': float(np.max(np.abs(pred_new - r_['_aux']['pred_new']))), 'players': pl}, ensure_ascii=False), encoding='utf-8')
    (out / 'usage-dump.json').write_text(json.dumps(dump, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'sha256': BC.RT.sha(out / 'ranking.csv'), 'rows': len(rows), 'ncoef': [len(c) for c in dump['wls']]}))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(pipe(sys.argv[2]))
    if sys.argv[1] == 'cards':
        sys.exit(cards(sys.argv[2], sys.argv[3]))
    sys.exit(run(sys.argv[2], sys.argv[3]))
