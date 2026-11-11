"""E-123 組卡與判定（預註冊 §5）。由 reports/card-0.2.6+E107-defense-UL/e107.py 改寫：唯讀匯入 E-094 e094.py（pipeline、e089_eval 的 m1–m3 不改），
只把它的 CARDS／W／HERE 指到本目錄。
階段（先 c0，過了才往下）：
  python -I -X utf8 reports/card-0.2.7+E123-tail-3pt-rim-pres/e123.py c0     # 只重建 c0 卡並驗 ranking.csv 與 card 0.2.7 逐位元相同
  python -I -X utf8 reports/card-0.2.7+E123-tail-3pt-rim-pres/e123.py cards  # 跑 e123／e123h／e123p 的 pipeline、覆寫 presDisplay、寫 <arm>/ranking.csv
"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E107 = ROOT / 'reports/card-0.2.6+E107-defense-UL'
C027 = ROOT / 'reports/card-0.2.7/ranking.csv'
C027_SHA = 'aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6'
_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.HERE, M.W, M.CARDS = HERE, HERE / 'work', HERE / 'cards'

PARTS = ('primary', 'fitA', 'fitB')
CARD_FILES = ('pred.csv', 'ranking.csv', 'pergame-main.csv', 'pergame-repl.csv', 'pergame-summary.json')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def same_cards(a, b):
    files = {f: sha(a / f) == sha(b / f) for f in CARD_FILES}
    return files


def check_prereg():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert sha(HERE / 'preregistration.md') == want, '預註冊 sha256 與凍結值不同'


def c0_stage():
    check_prereg()
    M.load_data()
    M.set_card_dir(HERE / 'cards/c0')
    pools = M.build_pools()
    base = M.pipeline(M.BASE_OPTS, pools, 'season')
    M.write_rank(M.W / 'c0/ranking.csv', base['_aux']['cols23'], base['_aux']['rows23'])
    cards_eq = {p: same_cards(E107 / 'cards/UL6' / p, HERE / 'cards/c0' / p) for p in PARTS}
    res = {'ranking_sha256': sha(M.W / 'c0/ranking.csv'), 'want': C027_SHA, 'card027_sha256_now': sha(C027),
           'cards_vs_E107_UL6': cards_eq}
    res['pass'] = bool(res['ranking_sha256'] == C027_SHA == res['card027_sha256_now'])
    res['cards_equal_E107_UL6'] = bool(all(all(v.values()) for v in cards_eq.values()))
    (HERE / 'work/c0-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding='utf-8')
    print('c0', res['pass'], res['ranking_sha256'], 'cards==E107 UL6:', res['cards_equal_E107_UL6'])
    return 0 if res['pass'] else 1


ARMS = ('e123', 'e123h', 'e123p')
PD_NEW = {'e123': True, 'e123h': False, 'e123p': True}   # presDisplay 只在改 tailSource 的組覆寫（e123h 只換 defSource）


def fmt1(x):
    s = f'{round(float(x), 1):.1f}'
    return s[:-2] if s.endswith('.0') else s   # 卡片格式：整數不帶 .0（如 99），其餘一位小數


def cards_stage():
    """跑三組 pipeline，寫 work/<arm>/ranking.csv，再依 PD_NEW 以 work/presDisplay-new.csv 覆寫 presDisplay（依姓名）寫 <arm>/ranking.csv；
    存 work/cards-result.json（e089_eval、r1、c0 比對）。npm test／evaluate.mjs 之後由 run_gates.py 跑，判定在 judge 階段。"""
    check_prereg()
    c0 = json.loads((HERE / 'work/c0-result.json').read_text(encoding='utf-8'))
    assert c0['pass'], 'c0 沒過，不往下'
    M.load_data()
    M.set_card_dir(HERE / 'cards/c0')
    pools = M.build_pools()
    base = M.pipeline(M.BASE_OPTS, pools, 'season')
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(HERE / 'work/presDisplay-new.csv', encoding='utf-8'))}
    res = {'arms': {}}
    for a in ARMS:
        M.set_card_dir(HERE / 'cards' / a)
        r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
        M.write_rank(M.W / a / 'ranking.csv', r_['_aux']['cols23'], r_['_aux']['rows23'])
        rows = [dict(r) for r in r_['_aux']['rows23']]
        n_over = 0
        if PD_NEW[a]:
            for r in rows:
                if r['name'] in pdnew:
                    r['presDisplay'] = fmt1(pdnew[r['name']])
                    n_over += 1
        M.write_rank(HERE / a / 'ranking.csv', r_['_aux']['cols23'], rows)
        ev = M.e089_eval(r_['_aux']['dirs'], base['_aux']['dirs'])
        res['arms'][a] = {'presDisplay_overwritten': n_over, 'work_ranking_sha256': sha(M.W / a / 'ranking.csv'),
                          'final_ranking_sha256': sha(HERE / a / 'ranking.csv'), 'eval': ev,
                          'anchors': r_['card']['anchors']}
        print(a, {k: round(ev[k]['point'], 4) for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')},
              {k: [round(x, 4) for x in ev[k]['ci90']] for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin')}, 'pd overwritten', n_over, flush=True)
    res['c0_work_ranking_sha256'] = sha(M.W / 'c0/ranking.csv')
    (HERE / 'work/cards-result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + "\n", encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    stage = sys.argv[1] if len(sys.argv) > 1 else 'c0'
    sys.exit({'c0': c0_stage, 'cards': cards_stage}[stage]())
