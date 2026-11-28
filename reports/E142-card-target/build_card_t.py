"""E-142 Phase 0 c0：可換目標欄的 0.2.7c 卡片建置（K1 arm = --dropAttr physique），匯入 E-134 stage1 原程式。
只寫到 reports/E142-card-target/work/；stage1/work 與原卡片目錄唯讀。
換目標：swap_rapm(src_csv, dst_csv, cand) 把 --rapm 檔的 pooledNet/O/D 換成候選 {playerId:(net,O,D)}；cand=None 即 T0（原樣複製）。
用法（repo root）：python -I -B -X utf8 reports/E142-card-target/build_card_t.py c0 | hist <季>
  c0       2025-26 原點，ranking sha 必須等於 K1_SHA
  hist <t> 歷史原點 T0（K0 arm，與 E-134 同法），t in 2022-23 2023-24 2024-25
  pipe <tag>  （內部）
"""
import csv, importlib.util, json, os, shutil, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
S1 = ROOT / 'reports/card-0.2.7c+E134-rolling-prior/stage1'
sys.path.insert(0, str(S1))
import run_t as RT   # noqa: E402
SW = S1 / 'work'
W = Path(os.environ['E142_WORK']) if os.environ.get('E142_WORK') else HERE / 'work'   # phase 1：每個候選一個獨立工作目錄
BJ = W if os.environ.get('E142_WORK') else HERE   # build-*.json 位置（預設維持第 0 階段的位置）
HDR = ['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss']


def swap_rapm(src, dst, cand=None):
    rows = list(csv.DictReader(open(src, encoding='utf-8-sig')))
    kept = 0
    with open(dst, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(HDR)
        for r in rows:
            if cand is None:
                w.writerow([r[h] for h in HDR])
                kept += 1
            elif int(r['playerId']) in cand:
                net, o, d = cand[int(r['playerId'])]
                w.writerow([r['playerId'], r['name'], net, o, d, r['pooledPoss']])
                kept += 1
    return {'in': len(rows), 'out': kept}


def pipe(tag):
    spec = json.loads((W / f'{tag}-pipe.json').read_text(encoding='utf-8'))
    out = Path(spec['out'])
    s = importlib.util.spec_from_file_location('e094t', S1 / 'e094_t.py')
    M = importlib.util.module_from_spec(s)
    s.loader.exec_module(M)
    M.HERE, M.W, M.CARDS = out, out / 'work', out / 'cards'
    M.load_data()
    M.set_card_dir(spec['poolCards'] if spec.get('poolCards') else spec['cards'])
    pools = M.build_pools()
    M.set_card_dir(spec['cards'])
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(ROOT / RT.E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    rows = [dict(r) for r in r_['_aux']['rows23']]
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = RT.fmt1(pdnew[r['name']])
    M.write_rank(out / 'ranking.csv', r_['_aux']['cols23'], rows)
    print(json.dumps({'sha256': RT.sha(out / 'ranking.csv'), 'rows': len(rows)}))


def run_pipe(tag, out, cards, cfg, pool_cards=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    RT.jw(W / f'{tag}-pipe.json', {'out': str(out), 'cards': str(cards), 'poolCards': str(pool_cards) if pool_cards else None})
    cfgp = W / f'{tag}-e094cfg.json'
    RT.jw(cfgp, cfg)
    rc, sec, err = RT.sub_run([sys.executable, '-I', '-B', '-X', 'utf8', str(HERE / 'build_card_t.py'), 'pipe', tag], {'E134_CFG': str(cfgp)}, out / 'pipe.log')
    if rc:
        raise SystemExit(f'{tag} pipe failed: {err}')
    return RT.sha(out / 'ranking.csv'), sec


def c0(cand=None, name='c0'):
    t0 = time.time()
    O = W / name
    O.mkdir(parents=True, exist_ok=True)
    for p in RT.PARITY:                     # def-L 檔與目標無關，直接用 stage1 已驗證產物
        shutil.copy(SW / 'c0' / f'def-L-{p}.csv', O / f'def-L-{p}.csv')
    c0p = SW / 'c0p'
    sp = {}
    (O / 'split').mkdir(exist_ok=True)
    for p in ('A', 'B'):
        sp[p] = swap_rapm(c0p / f'split/rapm-{p}.csv', O / f'split/rapm-{p}.csv', cand)
    pa = {'primary': [],
          'fitA': ['--rapm', str(O / 'split/rapm-A.csv'), '--possScale', '0.5', '--mpgSource', str(c0p / 'mpg/mpg-A.csv')],
          'fitB': ['--rapm', str(O / 'split/rapm-B.csv'), '--possScale', '0.5', '--mpgSource', str(c0p / 'mpg/mpg-B.csv')]}
    parts = {p: (None, pa[p], O / f'def-L-{p}.csv') for p in pa}
    cards_sha, ptimes = RT.run_calib(name, O / 'cards/K0', parts)
    e131 = {p: RT.sha(ROOT / RT.E131 / 'cards/K1' / p / 'ranking.csv') for p in pa}
    cfg = {'dnp': str(c0p / 'dnp-2025-26.json'), 'mpgDir': str(c0p / 'mpg'), 'splitDir': str(O / 'split'), 'rapm1Dir': str(c0p / 'rapm1')}
    got, sec = run_pipe(name, O, O / 'cards/K0', cfg, pool_cards=ROOT / RT.RB / 'cards/c0')
    res = {'origin': '2025-26', 'swap': 'T0' if cand is None else 'custom', 'splitRows': sp, 'part_card_sha256': cards_sha,
           'part_equal_E131_K1': {p: cards_sha[p] == e131[p] for p in pa}, 'ranking_sha256': got, 'want': RT.K1_SHA,
           'pass': got == RT.K1_SHA, 'seconds': round(time.time() - t0, 1)}
    RT.jw(BJ / f'build-{name}.json', res)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res['pass'] else 1


def hist(t, cand=None):
    """歷史原點 K0：輸入（league、split、mpg、dnp、def-L）唯讀自 stage1/work，--rapm 檔經 swap_rapm 寫到本目錄。"""
    t0 = time.time()
    s, d = SW / t, W / t
    d.mkdir(parents=True, exist_ok=True)
    for f in ['league-A.json', 'target-primary.csv', 'target-fitA.csv', 'target-fitB.csv', 'def-L-primary.csv', 'def-L-fitA.csv', 'def-L-fitB.csv']:
        shutil.copy(s / f, d / f)
    (d / 'split').mkdir(exist_ok=True)
    sw = {'primary': swap_rapm(s / 'rapm-R.csv', d / 'rapm-R.csv', cand)}
    rp = {'primary': d / 'rapm-R.csv'}
    for p, x in (('fitA', 'A'), ('fitB', 'B')):
        sw[p] = swap_rapm(SW / f'{t}-split/rapm-{x}.csv', d / f'split/rapm-{x}.csv', cand)
        rp[p] = d / f'split/rapm-{x}.csv'
    mp = {'fitA': SW / f'{t}-mpg/mpg-A.csv', 'fitB': SW / f'{t}-mpg/mpg-B.csv'}
    parts = {}
    for p in rp:
        cfg = d / f'calib-{p}.json'
        RT.jw(cfg, {'league': str(d / 'league-A.json'), 'target': str(d / f'target-{p}.csv'), 'alpha': 1})
        args = ['--rapm', str(rp[p])] if p == 'primary' else ['--rapm', str(rp[p]), '--possScale', '0.5', '--mpgSource', str(mp[p])]
        parts[p] = (cfg, args, d / f'def-L-{p}.csv')
    cdir = d / 'cards/K0'
    cards_sha, ptimes = RT.run_calib(t, cdir, parts)
    dd = ROOT / 'data/defense-seventh' / t
    cfg = {'dnp': str(SW / f'{t}-dnp.json'), 'mpgDir': str(SW / f'{t}-mpg'), 'splitDir': str(d / 'split'),
           'rapm1Dir': str(SW / f'{t}-rapm1'), 'playerGames': str(dd / 'player-games.json'), 'teamGames': str(dd / 'team-games.json'),
           'bio': str(dd / 'bio.json'), 'newPools': True, 'skipR': True}
    got, sec = run_pipe(t, d / 'out/K0', cdir, cfg)
    ref = json.loads((s / 'hist-K0.json').read_text(encoding='utf-8'))
    res = {'origin': t, 'swap': 'T0' if cand is None else 'custom', 'swapRows': sw, 'part_card_sha256': cards_sha,
           'ranking_sha256': got, 'stage1_ranking_sha256': ref['ranking_sha256'], 'equals_stage1': got == ref['ranking_sha256'],
           'part_equals_stage1': {p: cards_sha[p] == ref['card_sha256'][p] for p in cards_sha}, 'seconds': round(time.time() - t0, 1)}
    RT.jw(BJ / f'build-{t}.json', res)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    m = sys.argv[1]
    if m == 'c0':
        sys.exit(c0())
    if m == 'hist':
        sys.exit(hist(sys.argv[2]))
    if m == 'pipe':
        pipe(sys.argv[2])
        sys.exit(0)
    if m == 'cand':    # cand <pickle路徑> <原點>：候選 {playerId:(net,O,D)} 由 phase1_cands.py 產生；T0 傳 none
        import pickle
        cand = None if sys.argv[2] == 'none' else pickle.load(open(sys.argv[2], 'rb'))
        sys.exit(c0(cand, 'c0') if sys.argv[3] == '2025-26' else hist(sys.argv[3], cand))
    raise SystemExit('unknown')
