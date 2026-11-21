"""E-123 疊到 card 0.2.7a（合併版 e123a）。由 ../e123.py 與 E-125 work/e125.py 改寫：唯讀匯入 E-094 e094.py（pipeline、e089_eval 的 m1–m3 不改），
M.HERE／M.W／M.CARDS 指到本目錄。pools 用 card 0.2.7 卡（c0 arm）建，同 E-125（它的 P0），這樣 c0a 才能逐位元重現 E-125 P50 ＝ card 0.2.7a。
階段：
  python -I -X utf8 .../rebase-027a/e123a.py c0     # 只重建 c0a（只放 E-125），驗 ranking.csv 與 reports/card-0.2.7a/ranking.csv 逐位元相同
  python -I -X utf8 .../rebase-027a/e123a.py cards  # 跑 e123a 的 pipeline、依名字覆寫 presDisplay（E-123 work/presDisplay-new.csv）、m1–m3 對 c0a（＝card 0.2.7a）
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E123 = HERE.parent
E125 = ROOT / 'reports/card-0.2.7+E125-pass-volume'
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'
C027_SHA = 'aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6'
C027A = ROOT / 'reports/card-0.2.7a/ranking.csv'
C027A_PREFIX = '04a9c266'
_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.HERE, M.W, M.CARDS = HERE, HERE / 'work', HERE / 'cards'

PARTS = ('primary', 'fitA', 'fitB')
CARD_FILES = ('pred.csv', 'ranking.csv', 'pergame-main.csv', 'pergame-repl.csv', 'pergame-summary.json')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt1(x):
    s = f'{round(float(x), 1):.1f}'
    return s[:-2] if s.endswith('.0') else s   # 同 E-123 e123.py


def check_prereg():
    want = (E123 / 'preregistration.sha256').read_text().split()[0]
    assert sha(E123 / 'preregistration.md') == want, 'E-123 預註冊 sha256 與凍結值不同'


def c0_stage():
    check_prereg()
    assert sha(C027) == C027_SHA
    assert sha(C027A).startswith(C027A_PREFIX), 'card 0.2.7a ranking.csv sha 開頭不符'
    M.load_data()
    M.set_card_dir(HERE / 'cards/c0')
    pools = M.build_pools()
    r0 = M.pipeline(M.BASE_OPTS, pools, 'season')
    (M.W / 'c0').mkdir(parents=True, exist_ok=True)
    M.write_rank(M.W / 'c0/ranking.csv', r0['_aux']['cols23'], r0['_aux']['rows23'])
    M.set_card_dir(HERE / 'cards/c0a')
    ra = M.pipeline(M.BASE_OPTS, pools, 'season')
    (M.W / 'c0a').mkdir(parents=True, exist_ok=True)
    M.write_rank(M.W / 'c0a/ranking.csv', ra['_aux']['cols23'], ra['_aux']['rows23'])
    res = {'c0_card027': {'sha256': sha(M.W / 'c0/ranking.csv'), 'want': C027_SHA, 'pass': sha(M.W / 'c0/ranking.csv') == C027_SHA},
           'c0a_card027a': {'sha256': sha(M.W / 'c0a/ranking.csv'), 'card027a_sha256': sha(C027A),
                            'E125_P50_work_sha256': sha(E125 / 'work/P50/ranking.csv')}}
    res['c0a_card027a']['pass'] = bool(res['c0a_card027a']['sha256'] == res['c0a_card027a']['card027a_sha256'] == res['c0a_card027a']['E125_P50_work_sha256'])
    res['c0a_cards_vs_E125_P50'] = {p: {f: sha(HERE / 'cards/c0a' / p / f) == sha(E125 / 'cards/P50' / p / f) for f in CARD_FILES} for p in PARTS}
    res['c0_cards_vs_E123_c0'] = {p: {f: sha(HERE / 'cards/c0' / p / f) == sha(E123 / 'cards/c0' / p / f) for f in CARD_FILES} for p in PARTS}
    res['pass'] = bool(res['c0_card027']['pass'] and res['c0a_card027a']['pass'])
    (HERE / 'work/c0-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
    print('c0', res['pass'], json.dumps(res, ensure_ascii=False))
    return 0 if res['pass'] else 1


def cards_stage():
    check_prereg()
    c0 = json.loads((HERE / 'work/c0-result.json').read_text(encoding='utf-8'))
    assert c0['pass'], 'c0 沒過，不往下'
    M.load_data()
    M.set_card_dir(HERE / 'cards/c0')
    pools = M.build_pools()
    M.set_card_dir(HERE / 'cards/c0a')
    base = M.pipeline(M.BASE_OPTS, pools, 'season')   # 基準 ＝ card 0.2.7a
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    M.set_card_dir(HERE / 'cards/e123a')
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    (M.W / 'e123a').mkdir(parents=True, exist_ok=True)
    M.write_rank(M.W / 'e123a/ranking.csv', r_['_aux']['cols23'], r_['_aux']['rows23'])
    rows = [dict(r) for r in r_['_aux']['rows23']]
    n_over = 0
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = fmt1(pdnew[r['name']])
            n_over += 1
    (HERE / 'e123a').mkdir(exist_ok=True)
    M.write_rank(HERE / 'e123a/ranking.csv', r_['_aux']['cols23'], rows)
    ev = M.e089_eval(r_['_aux']['dirs'], base['_aux']['dirs'])
    res = {'base': 'c0a（＝card 0.2.7a，c0 已驗逐位元相同）', 'presDisplay_overwritten': n_over, 'work_ranking_sha256': sha(M.W / 'e123a/ranking.csv'),
           'final_ranking_sha256': sha(HERE / 'e123a/ranking.csv'), 'eval': ev, 'anchors': r_['card']['anchors'], 'anchors_base': base['card']['anchors']}
    print({k: round(ev[k]['point'], 4) for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')},
          {k: [round(x, 4) for x in ev[k]['ci90']] for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')}, 'pd overwritten', n_over, flush=True)
    (HERE / 'work/cards-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + "\n", encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    stage = sys.argv[1] if len(sys.argv) > 1 else 'c0'
    sys.exit({'c0': c0_stage, 'cards': cards_stage}[stage]())
