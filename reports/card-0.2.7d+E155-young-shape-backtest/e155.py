"""E-155 跨季回測：合併 RAPM 對年輕人的修正，斷崖（≤23）還是連續（max(0,25−年齡)）比較準。
不重做卡片；預測量 q＝T 季往回四季（缺季跳過）合併 RAPM net，答案＝T+1 單季 RAPM net（都不帶先驗，rapm.py CV 選 λ）。
修正係數用其他三個複製留一季外擬合（WLS，權重＝答案回合），套在留出季。
用法（repo 根目錄）：python -I -X utf8 "reports/card-0.2.7d+E155-young-shape-backtest/e155.py"
"""
import csv, hashlib, html, importlib.util, json, re, sys, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_spec = importlib.util.spec_from_file_location('rapm', ROOT / 'reports/impact-rapm/rapm.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
ALL = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2022-23', '2023-24', '2024-25']
REPS = [('2018-19', '2019-20'), ('2019-20', '2020-21'), ('2022-23', '2023-24'), ('2023-24', '2024-25')]
MIN_POSS_ANS, MIN_POSS_POOL, YOUNG_MAX = 2000, 2000, 24
B, SEED = 2000, 155


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    s = unicodedata.normalize('NFKD', html.unescape(s)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s.replace('-', ' '))
    return ' '.join(w for w in s.split() if w not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def ages(season):
    """bref 進階頁的年齡（該季 1/31），姓名對 bpm_<季>.csv 的 playerId（同 README 規則：唯一對上才算）。"""
    end = int(season[:4]) + 1
    page = (ROOT / f'data/external-impact/bpm/adv{end}.html').read_text(encoding='utf-8')
    by = {}
    for nm, a in re.findall(r'data-stat="name_display"[^>]*>(?:<a [^>]*>)?([^<]+)(?:</a>)?</td>\s*<td[^>]*data-stat="age"\s*>(\d+)<', page):
        by.setdefault(norm(nm), set()).add(int(a))
    out = {}
    for r in csv.DictReader(open(ROOT / f'data/external-impact/bpm/bpm_{season}.csv', encoding='utf-8')):
        s = by.get(norm(r['name']))
        if s and len(s) == 1:
            out[int(r['playerId'])] = next(iter(s))
    return out


def fit(seasons):
    obs = list(R.observations(seasons))
    players = sorted({p for o in obs for p in o[2] + o[3]})
    return R.fit_rapm(obs, players)


def feats(age):
    return {'step': np.array([1.0 if a <= 23 else 0.0 for a in age]),
            'cont': np.array([max(0.0, 25.0 - a) for a in age]),
            'vet': np.array([1.0 if a >= 31 else 0.0 for a in age])}


def main():
    want = (HERE / 'preregistration.sha256').read_text().split()[0]
    assert sha(HERE / 'preregistration.md') == want, '預註冊被改過'
    data = {}
    for T, A in REPS:
        win = [s for s in ALL if ALL.index(s) <= ALL.index(T) and int(s[:4]) >= int(T[:4]) - 3]
        pool, pi = fit(win)
        ans, ai = fit([A])
        ag = ages(T)
        rows = [(p, ag[p], pool[p]['net'], ans[p]['net'], ans[p]['poss']) for p in pool
                if p in ans and p in ag and pool[p]['poss'] >= MIN_POSS_POOL and ans[p]['poss'] >= MIN_POSS_ANS]
        data[T] = {'window': win, 'answer': A, 'lambda_pool': pi['lambda'], 'lambda_ans': ai['lambda'], 'rows': rows}
        print(T, A, win, len(rows), pi['lambda'], ai['lambda'], flush=True)
    res = {'prereg_sha': want, 'reps': {}}
    rng = np.random.default_rng(SEED)
    for T in data:
        tr = [r for t in data if t != T for r in data[t]['rows']]
        f = feats([r[1] for r in tr]); y = np.array([r[3] - r[2] for r in tr]); w = np.array([r[4] for r in tr])
        coef = {}
        for form in ('step', 'cont'):
            X = np.column_stack([np.ones(len(tr)), f[form], f['vet']])
            coef[form] = np.linalg.lstsq(X * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
        te = data[T]['rows']
        g = feats([r[1] for r in te]); q = np.array([r[2] for r in te]); ans = np.array([r[3] for r in te])
        pred = {k: q + c[1] * g[k] + c[2] * g['vet'] for k, c in coef.items()}
        young = np.array([r[1] <= YOUNG_MAX for r in te])

        def blk(sel):
            idx = np.where(sel)[0]
            rho = lambda i, k: spearmanr(pred[k][i], ans[i])[0]
            bs = []
            for _ in range(B):
                i = rng.choice(idx, len(idx))
                bs.append(rho(i, 'cont') - rho(i, 'step'))
            return {'n': int(len(idx)), 'rho_step': float(rho(idx, 'step')), 'rho_cont': float(rho(idx, 'cont')),
                    'rho_raw': float(spearmanr(q[idx], ans[idx])[0]),
                    'delta': float(rho(idx, 'cont') - rho(idx, 'step')), 'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]}
        res['reps'][T] = {'answer': data[T]['answer'], 'window': data[T]['window'], 'lambda': [data[T]['lambda_pool'], data[T]['lambda_ans']],
                          'coef': {k: list(map(float, c)) for k, c in coef.items()},
                          'all': blk(np.ones(len(te), bool)), 'young': blk(young),
                          'young_resid_by_age': {str(a): round(float(np.mean([r[3] - r[2] for r in te if r[1] == a])), 3) for a in sorted({r[1] for r in te}) if a <= 26}}
    dy = [v['young']['delta'] for v in res['reps'].values()]
    da = [v['all']['delta'] for v in res['reps'].values()]
    res['summary'] = {'young_delta_mean': float(np.mean(dy)), 'young_delta_pos': int(sum(d > 0 for d in dy)), 'all_delta_mean': float(np.mean(da))}
    res['pass'] = bool(np.mean(dy) >= 0.01 and sum(d > 0 for d in dy) >= 3 and np.mean(da) >= -0.005)
    (HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': res['summary'], 'pass': res['pass']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
