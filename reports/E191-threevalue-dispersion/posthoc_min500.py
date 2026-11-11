"""事後診斷（不進預註冊判準，不改決定）：把尺度比的人群換成 2025-26 MIN>=500（任務背景 17.6→15.6 用的人群）。
預註冊 run.py 的尺度人群是 has 全 582 人（含低分鐘），這裡只換人群，其餘（臂、池、K）原樣照 run.py。
用法：python -I -X utf8 reports/E191-threevalue-dispersion/posthoc_min500.py"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import run as R  # noqa: E402

W10, SV, ROOT = R.W10, R.SV, R.ROOT


def main():
    W = W10.Win10()
    ix = {int(p): i for i, p in enumerate(W.D.pids)}
    cache = {}

    def raw(s):
        if s not in cache:
            cur, G = W.season_cur(s)
            n, a, mn = W.tv_raw(G, cur, s, G, 4)
            m_, a_ = W10.lg_total(W.T10[s])
            cache[s] = (n, a, mn, m_ / a_)
        return cache[s]

    def value(s, K):
        n, a, mn, mu = raw(s)
        acc = (n + K * mu) / (a + K)
        vol = np.where(mn > 0, a / np.where(mn > 0, mn, 1) * 36, np.nan)
        return vol * (acc - (mu - W10.THREE_REP_GAP))

    c_rows = {int(r['playerId']): r for r in csv.DictReader(open(R.TV10C, encoding='utf-8'))}
    d_rows = list(csv.DictReader(open(R.TV10D, encoding='utf-8')))
    tv26 = SV['2025-26']
    nl = json.loads((ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json').read_text(encoding='utf-8'))
    has = [int(r['playerId']) for r in d_rows if r['playerId'] in nl and r['playerId'] in tv26]

    def mapped(K, kind):
        v = value('2025-26', K)
        cv = {q: float(v[ix[q]]) for q in has if q in ix and not np.isnan(v[ix[q]])}
        if kind == 'U0':
            past = [float(x['value']) for s in R.PAST for x in SV[s].values() if (x['MIN'] or 0) >= 500]
        else:
            past = []
            for s in R.PAST:
                xs = value(s, K)
                past += [float(xs[ix[int(p)]]) for p, x in SV[s].items() if (x['MIN'] or 0) >= 500 and int(p) in ix and not np.isnan(xs[ix[int(p)]])]
        pool = past + [cv[q] for q in cv if (tv26[str(q)]['MIN'] or 0) >= 500]
        mp = R.W10.L.PctMapper(pool, R.TOP, R.BOT)
        qs = list(cv)
        return dict(zip(qs, map(float, mp(np.array([cv[q] for q in qs])))))

    q500 = [q for q in has if q in c_rows and (tv26[str(q)]['MIN'] or 0) >= 500]
    sd_c = float(np.std([float(c_rows[q]['tv_main']) for q in q500]))
    out = {'n_min500': len(q500), 'sd_0210c': sd_c}
    for name, (K, kind) in {'U0': (R.K0, 'U0'), 'P1': (R.K0, 'P1'), 'K0.5': (R.KS['K0.5'], 'P1'), 'K2': (R.KS['K2'], 'P1')}.items():
        m = mapped(K, kind)
        top50 = sorted((m[q] for q in q500), reverse=True)[:50]
        out[name] = {'sd': float(np.std([m[q] for q in q500])), 'ratio': float(np.std([m[q] for q in q500]) / sd_c),
                     'spearman_vs_0210c': float(spearmanr([m[q] for q in q500], [float(c_rows[q]['tv_main']) for q in q500])[0]),
                     'top50_median': float(np.median(top50)), 'top50_n_ge99': int(sum(v >= 99 for v in top50))}
    (H / 'posthoc_min500.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
