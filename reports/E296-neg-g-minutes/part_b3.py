"""E-296 B3：Yang 11/7 的單場評分 rt 在本季 C、MIN≥20 場次的百分位；並用「球員本季 MIN≥20 場次平均 rt ↔ OVR」換算這場相當於多少 OVR。"""
import json, csv, glob
from pathlib import Path
import numpy as np
EXP = Path(__file__).resolve().parent; ROOT = EXP.parents[1]
L = ROOT / 'reports/ovr-inseason-2026-27/live/2026-11-08'
rk = {r['playerId']: r for r in csv.DictReader(open(L / 'ranking.csv', encoding='utf8'))}
games = []
for f in sorted(glob.glob(str(L / 'games-box-*.json'))):
    d = json.load(open(f, encoding='utf8'))
    for gid, g in d['games'].items():
        for side in ('home', 'away'):
            for p in g.get(side, []) if isinstance(g.get(side), list) else []:
                if p.get('rt') is not None: games.append(dict(gid=gid, **p))
print('場次列', len(games))
C = [p for p in games if str(p['pid']) in rk and rk[str(p['pid'])]['pos'] == 'C' and p['min'] >= 20]
rts = np.array([p['rt'] for p in C])
print('C MIN>=20 場次', len(rts), '中位 rt', np.median(rts), 'Yang 5.2 百分位', (rts < 5.2).mean() * 100 + (rts == 5.2).mean() * 50)
# 球員平均 rt（MIN>=20 場次 ≥3 場）↔ OVR
by = {}
for p in games:
    if p['min'] >= 20 and str(p['pid']) in rk: by.setdefault(str(p['pid']), []).append(p['rt'])
xs = [(np.mean(v), float(rk[k]['ovr']), rk[k]['pos']) for k, v in by.items() if len(v) >= 3]
x = np.array([a for a, _, _ in xs]); y = np.array([b for _, b, _ in xs])
b1, b0 = np.polyfit(x, y, 1); print('全體 n', len(x), f'OVR ≈ {b0:.1f} + {b1:.2f}·rt', '→ rt 5.2 ≈', round(b0 + b1 * 5.2, 1), 'ρ', round(np.corrcoef(x, y)[0, 1], 3))
xc = np.array([a for a, _, p in xs if p == 'C']); yc = np.array([b for _, b, p in xs if p == 'C'])
c1, c0 = np.polyfit(xc, yc, 1); print('C n', len(xc), f'OVR ≈ {c0:.1f} + {c1:.2f}·rt', '→ rt 5.2 ≈', round(c0 + c1 * 5.2, 1), '；C 平均 rt', round(xc.mean(), 2), '平均 OVR', round(yc.mean(), 1))
