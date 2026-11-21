"""card 0.2.12 第二層（用人層）：e162_build.pipe 的複本（Y0 設計、連續 d），加「凍結」。
  capture：不凍結，跑在 0.2.9a 部件卡上，存下 coef['card']（WLS）、r_repl、兩段映射錨 -> <out>/captured.json
  frozen ：用 frozen.json 的 WLS 係數、r_repl、錨（皆取自 0.2.9a），只換部件卡 pred；最後 ovr 以凍結值重算
用法：python -I -X utf8 use_layer.py <capture|frozen> <cards_dir> <out_dir> [frozen.json] [mpg.csv]
  card 0.2.12：mpg.csv（playerId,mpg；E-185 的窗口 MPG_hat，c=82）給了就把 g 的 MPG 換成它（沒列者維持卡內值），ranking 的 mpg 欄也換；不給＝0.2.10 行為（逐位元相同）。
cards_dir 內要有 primary／fitA／fitB 的 pred.csv、ranking.csv、pergame-summary.json、pergame-repl.csv。"""
import csv, importlib.util, json, os, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E142 = ROOT / 'reports/E142-card-target'
E162 = ROOT / 'reports/card-0.2.9+E162-per-volume'
E164W = ROOT / 'reports/card-0.2.9+E164-no-stamina/work/base-S-2025-26/c0'


def main(mode, cards, out, frozen_path=None, mpg_path=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    os.environ['E134_CFG'] = str(E164W.parent.parent / 'S-2025-26-e094cfg.json')
    os.environ.setdefault('E142_WORK', str(HERE / 'work'))
    sys.path.insert(0, str(E142))
    import build_card_t as BC
    s = importlib.util.spec_from_file_location('e094t', BC.S1 / 'e094_t.py')
    M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
    M.HERE, M.W, M.CARDS = out, out / 'work', out / 'cards'
    M.load_data()
    pool_cards = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/cards/c0'
    M.set_card_dir(pool_cards)
    pools = M.build_pools()
    M.set_card_dir(cards)
    # 凍結模式：fit 卡 summary 的 rRepl 是 0.2.9a 凍結值；e094 的一致性斷言（PR10 of pred）只在重擬合時成立，改用本次 pred 的重算值（只影響半季評估欄，不進卡）
    for _h in 'AB':
        _fs = M.D['fitsum'][_h] if hasattr(M, 'D') else None
        if _fs and 'rRepl_if_refit_on_this_pred' in _fs:
            _fs['rRepl_PR10_of_pred'] = _fs['rRepl_if_refit_on_this_pred']
    sys.path.insert(0, str(E162))
    import e153_helpers as H
    tgp = M._P('teamGames', 'data/season-source/team-games.json')
    tgp = tgp if Path(str(tgp)).is_absolute() else ROOT / tgp
    tb = H.team_badness(M, tgp)
    ORIG = M.scope_feats
    cap = {'full': None, 'wls': []}
    def sf3(*a):
        r = ORIG(*a)
        r['d'] = np.array([tb[t]['d'] if t is not None else 0.0 for t in r['main']])
        if a[0] == 'full':
            cap['full'] = r
        return r
    M.scope_feats = sf3
    FZ = json.loads(Path(frozen_path).read_text(encoding='utf-8')) if mode == 'frozen' else None
    OW = M.wls
    def wls2(X, y, w):
        c = OW(X, y, w)
        cap['wls'].append(np.asarray(c).tolist())
        if FZ is not None and len(cap['wls']) == 3:   # 第三次呼叫 = coef['card']
            return np.array(FZ['use_layer']['wls_card'])
        return c
    M.wls = wls2
    def design0(sf, sel, k, p=None):
        p = sf['p'][sel] if p is None else p
        L, a, y, v = (sf[c][sel] for c in 'L a y v'.split())
        return np.column_stack([np.ones_like(p), p, L, a, y, v, y * L, v * L])
    M.design = design0
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(ROOT / BC.RT.E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    assert len(cap['wls']) == 3 and len(cap['wls'][2]) == 8
    aux = r_['_aux']
    rows = [dict(r) for r in aux['rows23']]
    sf = cap['full']
    names = aux['names']; idx = {n: i for i, n in enumerate(names)}
    info = {'mode': mode, 'wls_card': cap['wls'][2], 'r_repl_this_run': r_['card']['r_repl'], 'anchors_this_run': r_['card']['anchors']}
    if FZ is not None:
        r0, an = FZ['use_layer']['r_repl'], FZ['use_layer']['anchors']
        pred = aux['pred_new']
        mp_use = np.array(sf['mp'], float)
        mp_new = {}
        if mpg_path:
            mp_new = {int(r['playerId']): float(r['mpg']) for r in csv.DictReader(open(mpg_path, encoding='utf-8'))}
            for i_, q_ in enumerate(sf['pids']):
                if q_ in mp_new:
                    mp_use[i_] = mp_new[q_]
        g = (pred - r0) * M.wmin(mp_use)
        ovr = M.two_segment(g, an['PR1'], an['PR50'], an['PR99'])
        # 依原組裝方式：以 primary ranking.csv 順序為底、依 ovr 穩定排序
        base_order = [r['name'] for r in M.D['base']]
        key = {n: float(f"{ovr[idx[n]]:.1f}") for n in names}
        order = sorted(base_order, key=lambda n: -float(ovr[idx[n]]))
        byname = {r['name']: r for r in rows}
        rows = []
        for k_, n in enumerate(order, 1):
            r = dict(byname[n]); r['rank'] = str(k_)
            r['ovr'] = f"{ovr[idx[n]]:.1f}"; r['gRepl'] = f"{g[idx[n]]:.4f}"
            if mpg_path:
                r['mpg'] = f"{mp_use[idx[n]]:.2f}"
            rows.append(r)
        info['frozen_used'] = {'r_repl': r0, 'anchors': an}
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = BC.RT.fmt1(pdnew[r['name']])
    M.write_rank(out / 'ranking.csv', aux['cols23'], rows)
    info['sha256'] = BC.RT.sha(out / 'ranking.csv'); info['rows'] = len(rows)
    (out / 'captured.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(*sys.argv[1:])
