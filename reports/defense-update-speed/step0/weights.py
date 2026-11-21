"""第 0 步-1：2026-11-01 時老將 onBall／help 四季窗口裡本季的有效權重（以 76 人主力為例）。
只讀現行 rookie_defense.py（不改）。c＝聯盟已賽場數／1230·82（同 run_c4_live_rookie.vet_defense）。
用法：python -I -X utf8 weights.py <聯盟已賽場數>"""
import json, sys
from pathlib import Path
LIVE = Path(__file__).resolve().parents[2] / 'ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
import rookie_defense as RD

games = int(sys.argv[1])
c = games / 1230 * 82
ww = RD.window_weights(c)
units = {s: ww[s] * (c / 82 if s == '2026-27' else 1.0) for s in ww}
cur_share_league = units['2026-27'] / sum(units.values())
d = RD.ROOT / 'data/defense-seventh/2026-27/tracking'
adv = RD.table(d / 'advanced.json')
phi = {r['PLAYER_ID']: (r['PLAYER_NAME'], r['GP'], r['MIN']) for r in adv if r['TEAM_ABBREVIATION'] == 'PHI'}
parts = [(s, {k: RD.table(RD.PAST_RAW / s / f'0-{k}.json') for k in RD.KINDS}) for s in RD.PAST]
parts.append(('2026-27', {k: RD.table(d / f'{k}.json') for k in RD.KINDS}))
accs = {s: RD.onball_acc(t) for s, t in parts}
rim = {s: {r['CLOSE_DEF_PERSON_ID']: r.get('FGA_LT_06') or 0 for r in t['rim']} for s, t in parts}
vd, _ = RD.veteran(c, '2026-27')
v0, _ = RD.veteran(c, '2026-27', cur=False)
ins = RD.inseason('2026-27')
rows = []
for pid, (nm, gp, mn) in sorted(phi.items(), key=lambda x: -x[1][2]):
    pp = {s: accs[s].get(pid, {}).get('pp', 0.0) for s in ww}
    rf = {s: rim[s].get(pid, 0) for s in ww}
    sh_pp = ww['2026-27'] * pp['2026-27'] / max(1e-9, sum(ww[s] * pp[s] for s in ww))
    sh_rim = ww['2026-27'] * rf['2026-27'] / max(1e-9, sum(ww[s] * rf[s] for s in ww))
    rows.append(dict(pid=pid, name=nm, gp=gp, min=round(mn), curPP=round(pp['2026-27']), curRimFGA=rf['2026-27'],
                     onBallShare=round(sh_pp, 4), helpShare=round(sh_rim, 4),
                     onBall_noCur=v0.get(pid, {}).get('onBall'), onBall_live=vd.get(pid, {}).get('onBall'),
                     help_noCur=v0.get(pid, {}).get('help'), help_live=vd.get(pid, {}).get('help'),
                     onBall_cur_only=ins.get(pid, {}).get('onBall'), help_cur_only=ins.get(pid, {}).get('help')))
out = dict(games=games, c=c, seasonWeights=ww, units=units, curShareLeagueAvgPlayer=cur_share_league, phi=rows)
json.dump(out, open(Path(__file__).with_name('weights.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(f"c={c:.3f} ww={ {k: round(v,4) for k,v in ww.items()} } curShare={cur_share_league:.4f}")
for r in rows[:10]:
    f = lambda x: '-' if x is None else f'{x:.1f}'
    print(f"{r['name'][:18]:18} gp{r['gp']} pp{r['curPP']:4} rim{r['curRimFGA']:3} obSh{r['onBallShare']:.3f} hSh{r['helpShare']:.3f} "
          f"onBall {f(r['onBall_noCur'])}->{f(r['onBall_live'])} (cur {f(r['onBall_cur_only'])}) help {f(r['help_noCur'])}->{f(r['help_live'])} (cur {f(r['help_cur_only'])})")
