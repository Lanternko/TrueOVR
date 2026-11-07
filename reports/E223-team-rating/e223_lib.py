"""E-223 共用函式：資料載入、分鐘規則（直接呼叫 scripts/team_ratings_daily.py 的 rotation，R-151）、OVR z 值、指標。"""
import collections, csv, glob, gzip, json, math, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'reports/E208-team-rating'))
import team_ratings_daily as TRD  # noqa: E402  rotation()／candidate_minutes()／MINUTE_TABLE，不改

H, SIGMA = 2.5, 12.0          # E-208 凍結值
E208 = ROOT / 'reports/E208-team-rating'
CARDS = ROOT / 'reports/ovr-inseason-2026-27/v5/cards'
SEASONS = {'2425': dict(inputs='inputs-2425.json', base='base2324', raw='dnp-2024-25-raw', card='2023-24-v5-min.csv', variant='Q'),
           '2526': dict(inputs='inputs.json', base='base2425', raw='dnp-2025-26-raw', card='2024-25-v5-min.csv', variant='P')}
FRINGE_MIN = 500.0            # 卡片內 MIN_season ≤ 此值的人算「邊緣球員」，z_miss＝他們 z 的平均


def Phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def mins(s):
    m = re.fullmatch(r'PT(\d+)M([\d.]+)S', s or '')
    return int(m[1]) + float(m[2]) / 60 if m else 0.0


def load_card(path):
    """v5 -min 卡 → ({pid: z}, z_miss, info)。z＝(ovr−μ)/σ，μ、σ 以卡片自己的 MIN_season 為權重（賽前可得）。"""
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    o = {int(r['playerId']): float(r['ovr']) for r in rows}
    w = {int(r['playerId']): float(r['MIN_season'] or 0) for r in rows}
    sw = sum(w.values())
    mu = sum(w[p] * o[p] for p in o) / sw
    sd = math.sqrt(sum(w[p] * (o[p] - mu) ** 2 for p in o) / sw)
    z = {p: (o[p] - mu) / sd for p in o}
    fr = [z[p] for p in o if w[p] <= FRINGE_MIN]
    return z, sum(fr) / len(fr), dict(mu=mu, sd=sd, n=len(o), n_fringe=len(fr))


def load_season(key):
    """→ dict(games=[{i,id,date,home,away,hs,as,hm,am}], pre, inp)。hm／am＝{pid: 原始分鐘}（min>0）。"""
    c = SEASONS[key]
    inp = json.load(open(E208 / c['inputs'], encoding='utf-8'))
    games = []
    for g in inp['games']:
        f = ROOT / f"data/season-source/{c['raw']}/boxscore_{g['id']}.json.gz"
        bx = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']
        side = lambda t: {p['personId']: mins(p['statistics']['minutes']) for p in t['players'] if mins(p['statistics']['minutes']) > 0}
        bt = {bx['homeTeam']['teamId']: bx['homeTeam'], bx['awayTeam']['teamId']: bx['awayTeam']}   # 以 teamId 對（NBA Cup 決賽 inputs 的主客與 box 相反）
        assert set(bt) == {g['home'], g['away']}, g['id']
        games.append(dict(i=g['i'], id=g['id'], date=g['date'], home=str(g['home']), away=str(g['away']), hs=g['hs'], **{'as': g['as']},
                          hm=side(bt[g['home']]), am=side(bt[g['away']])))
    return dict(games=games, pre={t: v for t, v in inp['pre'].items()}, inp=inp)


def build_lineups(S, zmap, snap_games=()):
    """逐場、逐隊：今日陣容（拿掉「候選但這場沒出場」的人）的 R-151 輪替。回傳 (rots, snaps)。
    rots[(i, 'h'|'a')] = [[pid, min], …]；snaps[(i, side)] = A 線用的狀態（只存 snap_games 指定的 (i, side)）。"""
    logs = collections.defaultdict(list); hist = collections.defaultdict(list)
    rots, snaps = {}, {}
    for g in S['games']:
        for sd, tk, mk in (('h', 'home', 'hm'), ('a', 'away', 'am')):
            t, played = g[tk], g[mk]
            prior = hist[t][-10:]
            roster = set(played)
            cands = TRD.candidate_minutes(prior, logs, roster)[0] if prior else {}
            excluded = frozenset(p for p in cands if p not in played)
            fb = S['pre'][t]
            rots[(g['i'], sd)] = TRD.rotation(prior, fb, excluded, logs, roster, ovr=zmap)
            if (g['i'], sd) in snap_games:
                need = {p for r in prior for p, _ in r} | roster
                snaps[(g['i'], sd)] = dict(prior=[[list(x) for x in r] for r in prior], roster=sorted(roster), excluded=sorted(excluded), fallback=fb,
                                          logs={p: list(logs[p]) for p in need})
        for tk, mk in (('home', 'hm'), ('away', 'am')):
            hist[g[tk]].append([[p, m] for p, m in g[mk].items()])
            for p, m in g[mk].items():
                logs[p].append(m)
    return rots, snaps


def rot_removed(st, extra, zmap):
    """A 線：從快照狀態再多拿掉 extra（pid），重算輪替。"""
    logs = st['logs']
    return TRD.rotation(st['prior'], st['fallback'], frozenset(st['excluded']) | {extra}, logs, set(st['roster']), ovr=zmap)


def s_term(rot, zmap, zmiss):
    """M1 的陣容項 Σ (min/240)·z。"""
    return sum(m / 240.0 * zmap.get(p, zmiss) for p, m in rot)


def metrics(dh, y, home, away, ids):
    """dh＝預測主減客分差（含主場）。回傳逐場 Brier 與 p。"""
    import numpy as np
    p = np.clip(np.vectorize(Phi)(np.asarray(dh) / SIGMA), 1e-6, 1 - 1e-6)
    return (p - y) ** 2, p


def wins_mae(p, y, home, away, ids, idx=None):
    import numpy as np
    idx = np.arange(len(y)) if idx is None else idx
    pw = {t: 0.0 for t in ids}; aw = {t: 0.0 for t in ids}
    for i in idx:
        pw[home[i]] += p[i]; pw[away[i]] += 1 - p[i]; aw[home[i]] += y[i]; aw[away[i]] += 1 - y[i]
    return float(np.mean([abs(pw[t] - aw[t]) for t in ids]))
