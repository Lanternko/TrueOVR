"""E-147 卡片 usage 層 d 改連續（同 live team_badness）。唯讀匯入 E-094 e094.py，路徑照 E-131 e131.py run_arm（cards/K1 能力值、rebase-027a c0 pools、presDisplay 覆寫）。
臂：K0（c0 逐位元＝card 0.2.7c）、D1（連續 d 重擬合）、D0（連續 d 套 K0 係數，只診斷）。
用法（repo 根目錄）：python -I -X utf8 reports/card-0.2.7c+E147-continuous-d/e147.py
"""
import csv, hashlib, html, importlib.util, json, math, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E94 = ROOT / 'reports/card-0.2.5+E094-defense-ceiling'
E131 = ROOT / 'reports/card-0.2.7b+E131-no-physique'
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
RB = E123 / 'rebase-027a'
C027C_SHA = '99466f369d53316a260f2b6d91ee056e2da8048e65d8283a68cec1322fef1655'
_spec = importlib.util.spec_from_file_location('e094', E94 / 'e094.py')
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
M.HERE, M.W, M.CARDS = HERE, HERE / 'work', HERE / 'cards'
ORIG_SF, ORIG_WLS = M.scope_feats, M.wls


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt1(x):
    s = f'{round(float(x), 1):.1f}'
    return s[:-2] if s.endswith('.0') else s


def team_badness():
    """同 run_c4_live_rookie.py:team_badness，資料用 2025-26 全季 team-games。"""
    tg = M.jload(ROOT / 'data/season-source/team-games.json')['data']['resultSets'][0]
    h = tg['headers']
    it, iw, ipm = h.index('TEAM_ID'), h.index('WL'), h.index('PLUS_MINUS')
    acc = {}
    for r in tg['rowSet']:
        a = acc.setdefault(r[it], [0, 0, 0.0])
        a[0] += 1
        a[1] += r[iw] == 'W'
        a[2] += float(r[ipm])
    out = {}
    for t, (gp, w, pm) in acc.items():
        nr, wp = pm / (gp + 10), (w + 5) / (gp + 10)
        s = 0.7 * (0.5 + 0.033 * nr) + 0.3 * wp
        out[t] = {'d': min(1.0, max(0.0, (0.40 - s) / 0.10)), 'gp': gp, 'W': w, 'nr': nr, 'wp': wp, 's': s}
    return out


def run_arm(arm, pools, pdnew, dcont=None, wls_replay=None):
    M.scope_feats = ORIG_SF
    if dcont is not None:
        def sf2(*a):
            r = ORIG_SF(*a)
            r['d'] = np.array([dcont[t]['d'] if t is not None else 0.0 for t in r['main']])
            return r
        M.scope_feats = sf2
    calls = []
    if wls_replay is None:
        def wls_log(X, y, w):
            c = ORIG_WLS(X, y, w)
            calls.append(c)
            return c
        M.wls = wls_log
    else:
        it = iter(wls_replay)
        M.wls = lambda X, y, w: next(it)
    M.set_card_dir(E131 / 'cards/K1')
    r_ = M.pipeline(M.BASE_OPTS, pools, 'season')
    M.wls, M.scope_feats = ORIG_WLS, ORIG_SF
    rows = [dict(r) for r in r_['_aux']['rows23']]
    for r in rows:
        if r['name'] in pdnew:
            r['presDisplay'] = fmt1(pdnew[r['name']])
    (HERE / arm).mkdir(exist_ok=True)
    M.write_rank(HERE / arm / 'ranking.csv', r_['_aux']['cols23'], rows)
    return r_, calls


def norm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r'[.\']', '', n); n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def salaries(f):   # 照 reports/salary-corr/corr.py
    s = open(f, encoding='utf-8').read(); rows = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row); y = re.search(r'data-stat="y1"[^>]*>\$?([\d,]+)', row)
        g = re.search(r'data-stat="remain_gtd"[^>]*>\$?([\d,]+)', row)
        if m and y: rows.setdefault(norm(m.group(1)), []).append((int(y.group(1).replace(',', '')), int(g.group(1).replace(',', '')) if g else 0))
    return {k: (v[0][0] if len(v) == 1 else min(v[0][0], min(x[1] for x in v))) for k, v in rows.items()}


def metrics(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    sal = salaries(ROOT / 'reports/salary-corr/source/bref2526.html')
    r2k = {norm(r['name']): float(r['overall2k']) for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv', encoding='utf-8')) if r['overall2k']}
    epm = {norm(r['name']): float(r['careerO']) + float(r['careerD']) for r in csv.DictReader(open(ROOT / 'reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8')) if r['careerO']}
    out = {}
    for tag, ext, agesel in (('M2K_all', r2k, None), ('M2K_y', r2k, 'y'), ('Msal_ge24', {k: math.log(v) for k, v in sal.items() if v > 0}, 'o'), ('Mepm_all', epm, None)):
        xs, ys = [], []
        for r in rows:
            if float(r['MIN']) < 500:
                continue
            age = M.D['age'].get(M.D['nm2pid'].get(r['name']))
            if agesel == 'y' and not (age is not None and age <= 23):
                continue
            if agesel == 'o' and not (age is not None and age >= 24):
                continue
            k = norm(r['name'])
            if k in ext:
                xs.append(float(r['ovr'])); ys.append(ext[k])
        out[tag] = {'n': len(xs), 'rho': float(spearmanr(xs, ys)[0])}
    return out


def main():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert sha(HERE / 'preregistration.md') == want, '預註冊 sha256 與凍結值不同'
    M.load_data()
    M.set_card_dir(RB / 'cards/c0')
    pools = M.build_pools()
    pdnew = {r['name']: r['presDisplay_new'] for r in csv.DictReader(open(E123 / 'work/presDisplay-new.csv', encoding='utf-8'))}
    k0, k0_calls = run_arm('K0', pools, pdnew)
    c0 = sha(HERE / 'K0/ranking.csv')
    res = {'c0': {'sha256': c0, 'want': C027C_SHA, 'pass': c0 == C027C_SHA}}
    if not res['c0']['pass']:
        print('c0 FAIL', c0); (HERE / 'results.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); return 1
    tb = team_badness()
    d1, _ = run_arm('D1', pools, pdnew, dcont=tb)
    d0, _ = run_arm('D0', pools, pdnew, dcont=tb, wls_replay=k0_calls)
    abbr = M.D['abbr']
    res['teams'] = {str(abbr.get(t, t)): {**v, 'd_binary': float(M.D['winrate'][t] < M.D_THR), 'winrate': M.D['winrate'][t]} for t, v in tb.items()}
    res['consistency'] = {'note': 'card d 取自同一 team_badness 字典；live team_badness 對 2025-26 全季 82 場', 'gp_all_82': all(v['gp'] == 82 for v in tb.values())}
    res['coef'] = {arm: r['coef']['card'] for arm, r in (('K0', k0), ('D1', d1))}
    res['metrics'] = {arm: metrics(HERE / arm / 'ranking.csv') for arm in ('K0', 'D1', 'D0')}
    res['eval_D1_vs_K0'] = M.e089_eval(d1['_aux']['dirs'], k0['_aux']['dirs'])
    res['eval_D0_vs_K0'] = M.e089_eval(d0['_aux']['dirs'], k0['_aux']['dirs'])
    for k in ('eval_D1_vs_K0', 'eval_D0_vs_K0'):
        res[k] = {'checks': {m: {'pass': v['pass'], 'point': v['value']['point'], 'ci90': v['value']['ci90']} for m, v in res[k]['checks'].items()}}
    rk = {arm: {r['name']: (int(r['rank']), float(r['ovr'])) for r in csv.DictReader(open(HERE / arm / 'ranking.csv', encoding='utf-8'))} for arm in ('K0', 'D1', 'D0')}
    a, b = rk['K0'], rk['D1']
    res['R064'] = {'top20_out': sorted(n for n in a if a[n][0] <= 20 and b[n][0] > 20), 'top20_in': sorted(n for n in b if b[n][0] <= 20 and a[n][0] > 20),
                   'top300_movers_ge10': sum(1 for n in a if a[n][0] <= 300 and abs(a[n][0] - b[n][0]) >= 10)}
    res['changes'] = sorted(([n, a[n][1], b[n][1], rk['D0'][n][1], a[n][0], b[n][0]] for n in a if abs(a[n][1] - b[n][1]) >= 2), key=lambda x: x[2] - x[1])
    res['sha'] = {arm: sha(HERE / arm / 'ranking.csv') for arm in ('K0', 'D1', 'D0')}
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(json.dumps({k: res[k] for k in ('c0', 'coef', 'metrics', 'eval_D1_vs_K0', 'R064')}, ensure_ascii=False, default=float))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
