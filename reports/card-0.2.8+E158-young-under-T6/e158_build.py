"""E-158 建卡驅動。三臂只動 usage 層（e094_t.pipeline）；校準（primary／fitA／fitB 三張部件卡）和 E-153 K6 完全相同，直接重用 K6 work 目錄的卡，唯讀。
  K  ：原樣重跑 K6 的 pipe（c0 要和 E-153 K6 ranking 逐位元相同）
  Y1 ：rapm1-A／B 的 net／O／D 換成該原點的 T6 季值（poss 不動；做法同 errata-1 對 fitA／fitB 的 swap_rapm），usage 層重擬合
  Y0 ：設計矩陣刪掉最後一欄 y·d·L，重擬合；rapm1 不換
用法（repo root）：python -I -B -X utf8 <本檔> run <臂> <原點>      （跑一個臂一個原點）
                 python -I -B -X utf8 <本檔> pipe <tag>           （內部）
"""
import csv, json, os, pickle, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
E153W = ROOT / 'reports/card-0.2.7d+E153-t6-target/work'
W = HERE / 'work'
HDR = ['playerId', 'name', 'net', 'O', 'D', 'poss']


def kdir(t):
    return E153W / f'K6-{t}'


def k_specs(t):
    """K6 原點的 pipe spec／cfg 路徑（歷史原點與 2025-26 檔名不同）。"""
    if t == '2025-26':
        return kdir(t) / 'c0-pipe.json', kdir(t) / 'c0-e094cfg.json'
    return kdir(t) / f'{t}-pipe.json', kdir(t) / f'{t}-e094cfg.json'


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
    sp, cp = k_specs(t)
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
    sys.path.insert(0, str(HERE))
    import e153_helpers as H
    tgp = M._P('teamGames', 'data/season-source/team-games.json')
    tgp = tgp if Path(str(tgp)).is_absolute() else ROOT / tgp
    tb = H.team_badness(M, tgp)
    ORIG = M.scope_feats
    dump = {'full': None, 'wls': []}
    def sf3(*a):
        r = ORIG(*a)
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
    if dump['full']:
        pass
    (out / 'usage-dump.json').write_text(json.dumps(dump, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'sha256': BC.RT.sha(out / 'ranking.csv'), 'rows': len(rows), 'ncoef': [len(c) for c in dump['wls']]}))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == 'pipe':
        os.environ.setdefault('E142_WORK', str(W))
        sys.exit(pipe(sys.argv[2]))
    sys.exit(run(sys.argv[2], sys.argv[3]))
