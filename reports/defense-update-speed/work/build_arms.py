"""defense-update-speed：建回測輸入（輕量，本機）。
每季、每隊第 10／20 場（leaguegamelog 官方場序）的日期 D 做快照：
- 老將 onBall／help＝四季逐場遞減窗口（rookie_defense.veteran 的同一套算式，季別與本季權重倍數 k 參數化）；
  本季＝DateTo=D 的追蹤表＋逐場 boxscorematchupsv3 累加到 D 的 matchups。A0 k=1、A1 k=2、A2 k=4。
- 引擎差值＝窗口值 − card 0.2.7b 先驗卡（prior-2025-26-card027b.json，＝2025-26 單季同公式），同 team_ratings_daily 的 live − 卡片做法。
- 輪替＝E-208 (c)：該隊 D 當天（含）以前最多 10 場 box 分鐘平均（minutes_rules.rule_c）。
- 實際：D 之後該隊剩餘賽季 DRtg（leaguegamelog，回合＝兩隊 FGA−OREB+TOV+0.44FTA 平均）。
- 次要：剩餘賽季單季表（DateFrom=D+1 ＋ D 之後逐場 matchups）算出的 onBall／help。
用法：python -I -X utf8 build_arms.py [--check] [季 ...] [--desc]   （--check：k=1、2026-27 本季表時與 rookie_defense.veteran 逐人一致）"""
import gzip, json, sys, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
sys.path.insert(0, str(ROOT / 'reports/E208-team-rating'))
import rookie_defense as RD  # noqa: E402
from minutes_rules import rule_c  # noqa: E402

DATA = BASE / 'data'
E208 = ROOT / 'reports/E208-team-rating'
ARMS = {'A0': 1.0, 'A1': 2.0, 'A2': 4.0}
PASTS = {'2024-25': ('2020-21', '2021-22', '2022-23', '2023-24'),
         '2025-26': ('2021-22', '2022-23', '2023-24', '2024-25')}
E208IN = {'2024-25': ('inputs-2425.json', 'Q'), '2025-26': ('inputs.json', 'P')}
NS = (10, 20)
KEYS = ('c3', 'min', 'ppu', 'load', 'pp', 'tx0', 'tx1')
# 逐場 boxscorematchupsv3 的列 [隊, 球員, 對位球員, PARTIAL_POSS, MATCHUP_FGA]；方向由 orient() 對 leagueseasonmatchups 季總計決定（預註冊 §2）
ORIENT = {}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def past_tabs(s):
    d = RD.PAST_RAW / s if (RD.PAST_RAW / s / '0-rim.json').exists() else DATA / 'raw' / s
    return {k: RD.table(d / f'0-{k}.json') for k in RD.KINDS}


def window_weights(c, past, cur, k):
    """RD.window_weights 的季別參數化版；本季權重再乘 k（k=1 與原式相同）。"""
    w = {}
    if c > 0:
        w[cur] = k * (RD.WIN - c / 2) / RD.WIN
    for i, s in enumerate(reversed(past), 1):
        b = RD.WIN - c - RD.SLOTS * (i - 1)
        a = b - RD.SLOTS
        w[s] = (max(b, 0) ** 2 - max(a, 0) ** 2) / (2 * RD.WIN * RD.SLOTS)
    return {s: v / 2.0 for s, v in w.items()}


def veteran(c, parts, cur, k, scale, st):
    """RD.veteran 第 268–301 行逐行搬來，只把 parts／權重改成參數。parts＝[(季, 表)]，由舊到新、本季在最後。"""
    ww = window_weights(c, [s for s, _ in parts if s != cur], cur, k)
    ww = {s: ww[s] for s, _ in parts if s in ww}
    units = {s: ww[s] * (c / RD.SLOTS if s == cur else 1.0) for s in ww}
    rim, rim_f = {}, {}
    for s, tabs in parts:
        for r in tabs['rim']:
            n, dd = r.get('FGA_LT_06'), r.get('PLUSMINUS')
            if n and n > 0 and dd is not None:
                pid = r['CLOSE_DEF_PERSON_ID']
                x = rim.setdefault(pid, [0.0, 0.0])
                x[0] += ww[s] * n; x[1] += ww[s] * n * dd
                f = rim_f.setdefault(pid, [0.0, 0.0]); f[0] += units[s]; f[1] = max(f[1], ww[s])
    out = {}
    for pid, (n, nd) in rim.items():
        if n > 0:
            n_eff = n / max(rim_f[pid])
            out.setdefault(pid, {})['help'] = RD.help_map((nd / n) * n_eff / (n_eff + RD.K_HELP))
    accs = [(s, RD.onball_acc(tabs)) for s, tabs in parts]
    acc = RD.acc_sum([(ww[s], a) for s, a in accs])
    ob_f = {}
    for s, a in accs:
        for pid in a:
            f = ob_f.setdefault(pid, [0.0, 0.0]); f[0] += units[s]; f[1] = max(f[1], ww[s])
    for pid, m in acc.items():
        for key in KEYS:
            m[key] /= max(ob_f[pid])
    for pid, r in RD.r_of_acc(acc, st).items():
        out.setdefault(pid, {})['onBall'] = scale(r)
    return out, ww


def single(tabs, scale, st):
    """單季表 → {pid: {'onBall','help'}}（同 RD.inseason）。"""
    out = {}
    for pid, v in RD.help_of(tabs['rim']).items():
        out.setdefault(pid, {})['help'] = v
    for pid, r in RD.onball_r(tabs, st).items():
        out.setdefault(pid, {})['onBall'] = scale(r)
    return out


def load_games(season):
    return [json.loads(l) for l in gzip.open(DATA / f'games-{season}.jsonl.gz', 'rt', encoding='utf-8')]


def to_rows(games, flip):
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for g in games:
        for _, p, m, pp, fga in g['rows']:
            d, o = (m, p) if not flip else (p, m)
            x = agg[(d, o)]; x[0] += pp or 0; x[1] += fga or 0
    return [{'DEF_PLAYER_ID': d, 'OFF_PLAYER_ID': o, 'PARTIAL_POSS': v[0], 'MATCHUP_FGA': v[1]} for (d, o), v in agg.items()]


def orient(season, games):
    """逐場累加的全季 matchups 對 leagueseasonmatchups 季總計：兩種方向各算配對層 PARTIAL_POSS 的絕對差總和，取小的；回傳 (flip, 稽核數字)。"""
    ref = {(r['DEF_PLAYER_ID'], r['OFF_PLAYER_ID']): r['PARTIAL_POSS'] or 0 for r in RD.table(RD.PAST_RAW / season / '0-matchups.json')}
    res = {}
    for flip in (False, True):
        got = {(r['DEF_PLAYER_ID'], r['OFF_PLAYER_ID']): r['PARTIAL_POSS'] for r in to_rows(games, flip)}
        keys = set(ref) | set(got)
        res[flip] = dict(absDiff=sum(abs(ref.get(q, 0) - got.get(q, 0)) for q in keys), refTotal=sum(ref.values()), gotTotal=sum(got.values()),
                         pairsRef=len(ref), pairsGot=len(got))
    flip = min(res, key=lambda f: res[f]['absDiff'])
    return flip, {str(k): v for k, v in res.items()}


def gamelog(season):
    d = json.load(open(DATA / f'gamelog-{season}.json', encoding='utf-8'))['data']['resultSets'][0]
    return [dict(zip(d['headers'], r)) for r in d['rowSet']]


def next_day(D):
    import datetime as dt
    return (dt.date.fromisoformat(D) + dt.timedelta(days=1)).isoformat()


def build(season, scale, st, card):
    past = PASTS[season]
    log = gamelog(season)
    gdate = {r['GAME_ID']: r['GAME_DATE'] for r in log}
    by_team = collections.defaultdict(list)
    for r in log:
        by_team[r['TEAM_ID']].append(r)
    by_game = collections.defaultdict(list)
    for r in log:
        by_game[r['GAME_ID']].append(r)
    poss = {g: sum(x['FGA'] - x['OREB'] + x['TOV'] + 0.44 * x['FTA'] for x in rs) / len(rs) for g, rs in by_game.items()}
    games = load_games(season)
    flip, orient_audit = orient(season, games)
    ORIENT[season] = dict(flip=flip, audit=orient_audit, nGames=len(games))
    inp = json.load(open(E208 / E208IN[season][0], encoding='utf-8'))
    pasts = [(s, past_tabs(s)) for s in past]
    snaps, dates = [], set()
    for ti, tid in enumerate(sorted(by_team)):
        g = sorted(by_team[tid], key=lambda r: (r['GAME_DATE'], r['GAME_ID']))
        for ni, N in enumerate(NS):
            D = g[N - 1]['GAME_DATE']; dates.add(D)
            rest = [r for r in g if r['GAME_DATE'] > D]
            pa = sum(r['PTS'] - r['PLUS_MINUS'] for r in rest); ps = sum(poss[r['GAME_ID']] for r in rest)
            prior = [x['hr'] if x['home'] == tid else x['ar'] for x in sorted(inp['games'], key=lambda x: (x['date'], x['i']))
                     if tid in (x['home'], x['away']) and x['date'] <= D][-10:]
            snaps.append(dict(team=tid, abbr=g[0]['TEAM_ABBREVIATION'], N=N, D=D, key=700 + ti + 30 * ni, nPrior=len(prior),
                              roster=rule_c(prior, inp['pre'][str(tid)]), drtgRem=100 * pa / ps, gRem=len(rest)))
    win, tgt, wts = {}, {}, {}
    for D in sorted(dates):
        c = len({g for g, d in gdate.items() if d <= D}) / 1230 * RD.SLOTS   # 同 run_c4_live_rookie：聯盟已賽場數／1230·82
        cut = {k: RD.table(DATA / 'cut' / season / f'to-{D}-{k}.json') for k in RD.KINDS if k != 'matchups'}
        cut['matchups'] = to_rows([x for x in games if gdate.get(x['gid'], '9') <= D], flip)
        win[D], wts[D] = {}, {'c': c}
        for arm, k in ARMS.items():
            v, ww = veteran(c, pasts + [(season, cut)], season, k, scale, st)
            win[D][arm] = v; wts[D][arm] = ww
        rem = {k: RD.table(DATA / 'cut' / season / f'from-{next_day(D)}-{k}.json') for k in RD.KINDS if k != 'matchups'}
        rem['matchups'] = to_rows([x for x in games if gdate.get(x['gid'], '0') > D], flip)
        t = single(rem, scale, st)
        mins = {r['PLAYER_ID']: r['MIN'] for r in rem['advanced']}
        for pid in t:
            t[pid]['minRem'] = mins.get(pid, 0)
        tgt[D] = t
    vets = {pid for _, tabs in pasts for pid in RD.onball_acc(tabs)} | {r['CLOSE_DEF_PERSON_ID'] for _, tabs in pasts for r in tabs['rim']}
    deltas = {D: {arm: {pid: [v.get('onBall', card[pid][0]) - card[pid][0], v.get('help', card[pid][1]) - card[pid][1]]
                        for pid, v in win[D][arm].items() if pid in card} for arm in ARMS} for D in win}
    return dict(season=season, variant=E208IN[season][1], past=past, snaps=snaps, weights=wts, orient=ORIENT[season],
                deltas=deltas), dict(season=season, win=win, tgt=tgt, vets=sorted(vets))


def check(scale, st):
    """k=1、四季 RD.PAST＋2026-27 本季表，與 RD.veteran(c) 逐人一致（c＝11-01 的 92 場）。"""
    c = 92 / 1230 * 82
    d = ROOT / 'data/defense-seventh/2026-27/tracking'
    parts = [(s, past_tabs(s)) for s in RD.PAST] + [('2026-27', {k: RD.table(d / f'{k}.json') for k in RD.KINDS})]
    mine, _ = veteran(c, parts, '2026-27', 1.0, scale, st)
    ref, _ = RD.veteran(c, '2026-27')
    diff = max(abs(mine[p].get(a, 0) - ref[p].get(a, 0)) for p in set(mine) | set(ref) for a in ('onBall', 'help')
               if p in mine and p in ref)
    res = dict(n=len(ref), sameKeys=set(mine) == set(ref), maxAbsDiff=diff)
    print(json.dumps(res))
    return res, parts, c


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    scale, st = RD.OnBallScale(), RD.frozen_stats()
    chk, parts26, c26 = check(scale, st)
    if '--check' in sys.argv:
        sys.exit(0 if chk['sameKeys'] and chk['maxAbsDiff'] < 1e-9 else 1)
    card = {p['playerId']: (float(p['onBall']), float(p['help'])) for p in json.load(open(RD.PRIOR_CARD, encoding='utf-8'))['players']}
    OUT = BASE / 'work/out'; OUT.mkdir(exist_ok=True)
    only = [a for a in sys.argv[1:] if a in PASTS]   # 可只建某季（2025-26 逐場資料還在抓時先建 2024-25）；算式不變
    for s in (only or PASTS):
        arms, attrs = build(s, scale, st, card)
        json.dump(arms, open(OUT / f'arms-{s}.json', 'w', encoding='utf-8'))
        with gzip.open(OUT / f'attrs-{s}.json.gz', 'wt', encoding='utf-8') as f:
            json.dump(attrs, f)
        print(s, 'snaps', len(arms['snaps']), 'dates', len(arms['deltas']), 'orient', json.dumps(arms['orient']))
    # 描述（不當證據）：2026-27 截至 11-01（92 場）各臂的 76 人 onBall／help 與引擎差值
    phi = {r['PLAYER_ID']: r['PLAYER_NAME'] for r in parts26[-1][1]['advanced'] if r['TEAM_ABBREVIATION'] == 'PHI'}
    desc = {'c': c26, 'arms': {}}
    for arm, k in ARMS.items():
        v, ww = veteran(c26, parts26, '2026-27', k, scale, st)
        desc['arms'][arm] = {'weights': ww, 'phi': {str(p): dict(name=phi[p], **v.get(p, {})) for p in phi},
                             'deltas': {str(p): [x.get('onBall', card[p][0]) - card[p][0], x.get('help', card[p][1]) - card[p][1]]
                                        for p, x in v.items() if p in card}}
    json.dump(desc, open(OUT / 'desc-2026-27.json', 'w', encoding='utf-8'), ensure_ascii=False)
    if only and '--desc' not in sys.argv:
        print('done (partial)'); sys.exit(0)
    man = {'check': chk, 'inputs': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sorted(
        list((DATA).rglob('*.json')) + list(DATA.glob('*.gz')) + [E208 / 'inputs-2425.json', E208 / 'inputs.json', RD.PRIOR_CARD,
                                                                  RD.E060 / 'stability.json'])},
           'code': {n: sha(HERE / n) for n in ('build_arms.py', 'run_arms.mjs', 'analyze.py') if (HERE / n).exists()}}
    json.dump(man, open(OUT / 'manifest.json', 'w', encoding='utf-8'), indent=1)
    print('done')
