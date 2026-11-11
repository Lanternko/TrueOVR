"""修前（DERIVE_ZONES=False，mid／short 本季零資料）vs 修後（True）的 8 項窗口值；本季無法判斷比例。
用法：python -I -X utf8 before_after.py → 寫 before-after.json"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'live'))
import window8 as W  # noqa: E402

w = W.Win8()
res = {}
out = {}
for flag in (False, True):
    W.DERIVE_ZONES = flag
    tabs, gd = w.cur_tabs()
    out[flag] = (w.attrs_at(gd, tabs), w.day0(tabs), w.n_zoned, gd)
before, day0, nz0, gd = out[False]
after, day0b, nz1, _ = out[True]
assert all(abs(day0[p][a] - day0b[p][a]) < 1e-9 for p in day0 for a in ('mid', 'short'))
pl = json.loads((W.DATA26 / 'player-games.json').read_text(encoding='utf-8'))['data']['resultSets']
pl = pl[0] if isinstance(pl, list) else pl
ih = pl['headers'].index
name = {r[ih('PLAYER_ID')]: r[ih('PLAYER_NAME')] for r in pl['rowSet']}
res['games'] = gd
res['n2pt_total'] = nz1[0]
res['zoned_before'] = nz0[1]; res['zoned_after'] = nz1[1]
res['undetermined_share'] = 1 - nz1[1] / nz1[0]
for a in ('mid', 'short'):
    d0 = np.array([abs(before[p][a] - day0[p][a]) for p in before])
    d1 = np.array([abs(after[p][a] - day0[p][a]) for p in after])
    res[f'{a}_mean_abs_change_day0_to_now_before'] = float(d0.mean())
    res[f'{a}_mean_abs_change_day0_to_now_after'] = float(d1.mean())
    res[f'{a}_max_abs_change_after'] = float(d1.max())
    res[f'{a}_n_players'] = len(after)
    top = sorted(after, key=lambda p: -abs(after[p][a] - day0[p][a]))[:5]
    res[f'{a}_top5_moved'] = [{'pid': p, 'name': name.get(p), 'day0': day0[p][a], 'before': before[p][a], 'after': after[p][a]} for p in top]
S = 1629014
res['simons'] = {a: {'name': name.get(S), 'day0': day0[S][a], 'before': before[S][a], 'after': after[S][a]} for a in ('mid', 'short')}
print(json.dumps(res, ensure_ascii=False, indent=1))
(HERE / 'before-after.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
