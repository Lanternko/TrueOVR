"""E-306 季末預測：重用 team_ratings_daily.compute（傷兵回歸日逐場陣容、剩餘賽程逐場勝率），只換權重與殘差強度 K。
不寫線上檔（輸出到 work/final-<tag>-<K>.json；殘差用 work/pred-today.json，不碰 today-margins.json）。
  python -I -X utf8 e306_final.py online,full,fullw3 none,K10"""
import collections, json, os, sys
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E229-transformer-vs-m0-forward'))
sys.path.insert(0, HERE)
import actual_blend as ab
import team_ratings_daily as M
import e229_live
import e306_pred

TODAY, LDIR = '2026-11-21', Path(ROOT) / 'reports/ovr-inseason-2026-27/live/2026-11-20'
WORK = os.path.join(HERE, 'work')
PT = json.load(open(os.path.join(WORK, 'pred-today.json'), encoding='utf-8'))
BaseCtx = e229_live.Ctx
G = ab.played_games()


def run(tag, klab):
    class Ctx(BaseCtx):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            if tag != 'online':
                self.nets = e306_pred.load_nets(tag)
    e229_live.Ctx = Ctx
    os.environ['ACTUAL_BLEND'] = '0' if klab == 'none' else '1'
    if klab != 'none':
        ab.K = float(klab[1:])
    ab.today_margins = lambda today, live_dir, log=None: dict(games={g: dict(date=e['date'], home=e['home'], away=e['away'], pfHome=e['p'][tag]['pf'],
                                                                         paHome=e['p'][tag]['pa'], mT=e['p'][tag]['mT']) for g, e in PT.items()})
    cap = {}
    orig = M.predict_wins

    def pw(wins, played, remaining, margin, tid, tids=None):
        if tids is not None:
            cap[tid] = (played, list(remaining), margin, list(tids))
        return orig(wins, played, remaining, margin, tid, tids)
    M.predict_wins = pw
    try:
        doc = M.compute(LDIR, fetch=False, today=TODAY, engine='t', out=Path(WORK) / f'final-{tag}-{klab}.json')
    finally:
        M.predict_wins = orig; e229_live.Ctx = BaseCtx
    assert doc['engineKind'] == 't', '退回了舊引擎'
    act = collections.defaultdict(lambda: [0, 0.0])
    for g in G.values():
        if g['date'] < TODAY:
            d = g['pts_home'] - g['pts_away']
            act[g['home']][0] += 1; act[g['home']][1] += d; act[g['away']][0] += 1; act[g['away']][1] -= d
    rows = []
    for tid, t in doc['teams'].items():
        played, rem, margin, tids = cap[tid]
        fut = 0.0
        for g in rem:
            h, a, d = str(g[0]), str(g[1]), g[2]
            opp = a if h == tid else h
            fut += margin(tid, d) - margin(opp, d) + (M.H if h == tid else -M.H)
        pool = 82 - played - len(rem)
        if pool > 0:
            fut += pool * (margin(tid, None) - sum(margin(o, None) for o in tids if o != tid) / 29)
        n, s = act[tid]
        rows.append(dict(tid=tid, abbr=t['abbr'], W=t['W'], L=t['L'], played=played, actualMargin=s / max(n, 1), nMarginGames=n,
                         rating=t['today']['margin'], ratingRecent=t['c']['margin'], predWins=t['today']['predWins'], predWinsRecent=t['c']['predWins'],
                         restMargin=fut / max(82 - played, 1), finalMargin=(s + fut) / 82, netShr=(t.get('actual') or {}).get('netShr', 0.0), nOut=t['nOut']))
    rows.sort(key=lambda r: -r['predWins'])
    json.dump(dict(tag=tag, K=klab, today=TODAY, liveDir=LDIR.name, blendOn=doc['actualBlend']['on'], teams=rows),
              open(os.path.join(WORK, f'season-{tag}-{klab}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(tag, klab, 'blendOn', doc['actualBlend']['on'], 'sumWins', round(sum(r['predWins'] for r in rows), 1), flush=True)
    for r in rows[:5] + rows[-3:]:
        print('  ', r['abbr'], f"{r['W']}-{r['L']}", round(r['predWins'], 1), round(r['finalMargin'], 2))


if __name__ == '__main__':
    for tag in sys.argv[1].split(','):
        for k in sys.argv[2].split(','):
            run(tag, k)
