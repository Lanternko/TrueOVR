"""E-131 卡片 OVR 迴歸拿掉 physique。由 reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/e123a.py 改寫：唯讀匯入 E-094 e094.py（pipeline、e089_eval 的 m1–m3 不改），
M.HERE／M.W／M.CARDS 指到本目錄。pools 照 e123a：用 card 0.2.7 卡（rebase-027a/cards/c0，唯讀沿用）建，K0／K1 共用同一組。presDisplay 覆寫照 e123a（E-123 work/presDisplay-new.csv）。
階段：
  python -I -X utf8 reports/card-0.2.7b+E131-no-physique/e131.py k0   # 只跑 K0 的 pipeline＋presDisplay 覆寫，c0：ranking.csv 與 reports/card-0.2.7b/ranking.csv 逐位元相同
  python -I -X utf8 reports/card-0.2.7b+E131-no-physique/e131.py k1   # c0 過了才准跑：K1 pipeline、覆寫、u1、m1–m3（K1 對 K0）
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
RB = E123 / 'rebase-027a'
C027B = ROOT / 'reports/card-0.2.7b/ranking.csv'
C027B_SHA = '361bcac61075dec1150c3b89b406ecd62dcaf4fdb5d738ccff68a0634de81105'
_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.HERE, M.W, M.CARDS = HERE, HERE / 'work', HERE / 'cards'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt1(x):
    s = f'{round(float(x), 1):.1f}'
    return s[:-2] if s.endswith('.0') else s   # 同 e123a／E-123 e123.py


def check_prereg():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert sha(HERE / 'preregistration.md') == want, 'E-131 預註冊 sha256 與凍結值不同'


def pools_and_pdnew():
    M.load_data()
    M.set_card_dir(RB / 'cards/c0')
    pools = M.build_pools()
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    return pools, pdnew


def run_arm(arm, pools, pdnew):
    M.set_card_dir(HERE / 'cards' / arm)
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    (M.W / arm).mkdir(parents=True, exist_ok=True)
    M.write_rank(M.W / arm / 'ranking.csv', r_['_aux']['cols23'], r_['_aux']['rows23'])
    rows = [dict(r) for r in r_['_aux']['rows23']]
    n_over = 0
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = fmt1(pdnew[r['name']])
            n_over += 1
    (HERE / arm).mkdir(exist_ok=True)
    M.write_rank(HERE / arm / 'ranking.csv', r_['_aux']['cols23'], rows)
    return r_, n_over


def k0_stage():
    check_prereg()
    assert sha(C027B) == C027B_SHA
    pools, pdnew = pools_and_pdnew()
    r0, n_over = run_arm('K0', pools, pdnew)
    got = sha(HERE / 'K0/ranking.csv')
    res = {'c0': {'sha256': got, 'want': C027B_SHA, 'pass': got == C027B_SHA}, 'presDisplay_overwritten': n_over,
           'work_ranking_sha256': sha(M.W / 'K0/ranking.csv'), 'anchors': r0['card']['anchors']}
    (HERE / 'work').mkdir(exist_ok=True)
    (HERE / 'work/c0-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + "\n", encoding='utf-8')
    print('c0', res['c0']['pass'], json.dumps(res, ensure_ascii=False, default=float))
    return 0 if res['c0']['pass'] else 1


def k1_stage():
    check_prereg()
    c0 = json.loads((HERE / 'work/c0-result.json').read_text(encoding='utf-8'))
    assert c0['c0']['pass'], 'c0 沒過，不往下'
    pools, pdnew = pools_and_pdnew()
    base, _ = run_arm('K0', pools, pdnew)
    assert sha(HERE / 'K0/ranking.csv') == C027B_SHA
    r_, n_over = run_arm('K1', pools, pdnew)
    ev = M.e089_eval(r_['_aux']['dirs'], base['_aux']['dirs'])
    res = {'base': 'K0（＝card 0.2.7b，c0 已驗逐位元相同）', 'presDisplay_overwritten': n_over, 'work_ranking_sha256': sha(M.W / 'K1/ranking.csv'),
           'final_ranking_sha256': sha(HERE / 'K1/ranking.csv'), 'eval': ev, 'anchors': r_['card']['anchors'], 'anchors_base': base['card']['anchors']}
    print({k: round(ev[k]['point'], 4) for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')},
          {k: [round(x, 4) for x in ev[k]['ci90']] for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')}, 'pd overwritten', n_over, flush=True)
    (HERE / 'work/cards-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + "\n", encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    stage = sys.argv[1]
    sys.exit({'k0': k0_stage, 'k1': k1_stage}[stage]())
