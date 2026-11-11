"""E-176 診斷：Jalen Williams 進攻分（OFF）拆解，對照實際數據與外部進攻指標。樣本內診斷，不改卡。"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import season_nav as SN
JW = 1631114
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live/2026-10-31/ranking.csv'

def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))

def rk(vals, v):  # 名次（1=最高）
    return int((np.array(vals) > v).sum() + 1)

# 1) 進攻分逐屬性拆解（用 season_nav 的位置別係數）
card = rows(SN.OD_CARD)
q = [r for r in card if float(r['MIN']) >= 500]
mu = {a: np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL}
coef = {}
for ps in {r['pos'] for r in card}:
    g = [r for r in card if r['pos'] == ps]
    X = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
    coef[ps] = dict(zip(SN.OD_ALL, np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0][1:]))
live = rows(LIVE)
jw = next(r for r in live if r['playerId'] == str(JW))
print('JW live pos', jw['pos'], 'MIN', jw['MIN'])
for ps in ['PF', 'SF', 'SG']:
    c = {a: coef[ps][a] * (float(jw[a]) - mu[a]) for a in SN.OD_OFF}
    print(ps, 'OFF', round(sum(c.values()), 2), {a: round(v, 2) for a, v in c.items()})
print('attrs', {a: jw[a] for a in SN.OD_OFF})
# 全聯盟 OFF 名次（live，MIN>=500）
od, _ = SN.off_def(live, 'playerId')
offs = [v[0] for k, v in od.items() if v[0] is not None]
print('live OFF', od[str(JW)], 'rank', rk(offs, od[str(JW)][0]), '/', len(offs))

# 2) 外部進攻指標名次（每季）
def ext(season):
    out = {}
    for name, f, col, mincol in [('OBPM', f'bpm/bpm_{season}.csv', 'obpm', None), ('DARKO_O', f'darko/darko_{season}.csv', 'o_dpm', None), ('EPM_O', f'epm_self/epm_{season}.csv', 'O', 'stintPoss')]:
        p = ROOT / 'data/external-impact' / f
        if not p.exists():
            continue
        rs = [r for r in rows(p) if r.get(col) not in ('', None)]
        if name == 'OBPM':
            rs = [r for r in rs if r.get('games') and int(float(r['games'])) >= 20]
        if mincol:
            rs = [r for r in rs if float(r[mincol]) >= 1500]
        vals = [float(r[col]) for r in rs]
        me = [float(r[col]) for r in rs if r['playerId'] == str(JW)]
        out[name] = (round(me[0], 2), rk(vals, me[0]), len(vals)) if me else None
    return out
for s in ['2022-23', '2023-24', '2024-25', '2025-26']:
    print(s, ext(s))

# 3) 2025-26 逐場：前段 vs 後段（受傷前後以缺賽空檔切）
d = json.load(open(ROOT / 'data/season-source/player-games.json', encoding='utf-8'))['data']['resultSets'][0]
H = d['headers']
g = sorted([dict(zip(H, x)) for x in d['rowSet'] if x[1] == JW], key=lambda r: r['GAME_DATE'])
dates = [r['GAME_DATE'] for r in g]
print('games', len(g), dates[0], '…', dates[-1])
import datetime as dt
gaps = [(dt.date.fromisoformat(dates[i]) - dt.date.fromisoformat(dates[i-1])).days for i in range(1, len(dates))]
print('gaps>10d', [(dates[i], gaps[i-1]) for i in range(1, len(dates)) if gaps[i-1] > 10])
def line(gs):
    m = sum(r['MIN'] for r in gs); f = lambda k: sum(r[k] for r in gs)
    ts = f('PTS') / (2 * (f('FGA') + 0.44 * f('FTA')))
    return dict(G=len(gs), MPG=round(m/len(gs),1), PTS36=round(36*f('PTS')/m,1), FGA36=round(36*f('FGA')/m,1), FTA36=round(36*f('FTA')/m,1), AST36=round(36*f('AST')/m,1), TOV36=round(36*f('TOV')/m,1), TS=round(ts,3), PM36=round(36*f('PLUS_MINUS')/m,1))
print('all', line(g))
cut = [i for i in range(1, len(dates)) if gaps[i-1] > 10]
segs = np.split(np.arange(len(g)), cut)
for sg in segs:
    print(dates[sg[0]], '→', dates[sg[-1]], line([g[i] for i in sg]))
