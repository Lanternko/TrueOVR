"""戰力排行混入本季實際表現（R-171，E-253 K10）：每隊「實際 − T 預期」的累積殘差 ÷ (場數 + K)，加回評分。

- 線上預設（R-172，2026-11-07 起）：預期一律用「今天的 T」重算所有已完賽場次（today_margins）。OVR 是含本季的滑動窗口，
  對凍結的賽前預期算殘差會讓本季表現被 OVR 與殘差重複計入（L-129）。下面的賽前快取版保留作對照（residuals(live_dir=None)）。

- 賽前預期：每場已完賽比賽用「比賽日前最新的 live 資料夾」＋「該場實際上場名單、比賽日前的平均分鐘」做 T 預測（同 E-246／E-229b pred_t：
  5 seed、N=2000、rng [229, gid]），算一次就存進 `pregame-margins.json`，之後不再重算（之後的資料不會回頭改舊預測）。
- 殘差拆攻守：主場 off＝實得分 −(預期得分＋H/2)、def＝實失分 −(預期失分 − H/2)；off − def ＝ E-253 的分差殘差（分差單位，聯盟每場約 100 回合，直接當每 100 回合用）。
- 只用比賽日 < today 的比賽。K、H 事前定死（E-253 預註冊 e9ebda7，使用者 2026-11-07 採用 K10）。
回退：環境變數 ACTUAL_BLEND=0 → 評分不加殘差。"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/season-source-2026-27'
CACHE = SRC / 'pregame-margins.json'
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
E229 = ROOT / 'reports/E229-transformer-vs-m0-forward'
E246_SNAP = ROOT / 'reports/E246-t-tracking-blend/snap'      # 10-20～11-02 的 DateTo 快照（補算歷史場次用；之後用當下追蹤檔）
K = 10.0
H = 2.5
DRAWS = 2000


def enabled() -> bool:
    return os.environ.get('ACTUAL_BLEND', '1') != '0'


def _tab(f):
    d = json.loads((SRC / f).read_text(encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


def _folders():
    return sorted(x.name for x in LIVE.iterdir() if len(x.name) == 10 and x.name[:4] == '2026' and x.is_dir())


def played_games():
    """已完賽場次 {gid: dict(gid, date, home, away, pts_home, pts_away)}（team-games.json）。"""
    games = {}
    for r in _tab('team-games.json'):
        g = games.setdefault(r['GAME_ID'], dict(gid=r['GAME_ID'], date=r['GAME_DATE']))
        s = 'home' if 'vs.' in r['MATCHUP'] else 'away'
        g[s] = str(r['TEAM_ID']); g['pts_' + s] = r['PTS']
    return {k: v for k, v in games.items() if 'home' in v and 'away' in v and v.get('pts_home') is not None}


def _rotations(games: dict, folder: str | None = None):
    """同 E-246 prep.py：該場實際上場的人、比賽日前自己的平均分鐘（沒有就用 live 的 MPGhat），走 rotation() 的焦灼分鐘表。
    folder＝None：用比賽日前最新的 live 夾（舊的賽前版）；給定：MPGhat 後備與 OVR 排序都用該夾（今天的 T 版）。"""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import team_ratings_daily as M
    rows = [r for r in _tab('player-games.json') if r['MIN'] and r['MIN'] > 0]
    tot = collections.Counter()
    for r in rows:
        tot[(r['GAME_ID'], r['TEAM_ID'])] += r['MIN']
    plog = collections.defaultdict(list); played = collections.defaultdict(set)
    for r in rows:
        plog[r['PLAYER_ID']].append((r['GAME_DATE'], r['GAME_ID'], r['MIN'] * 240.0 / tot[(r['GAME_ID'], r['TEAM_ID'])]))
        played[(r['GAME_ID'], str(r['TEAM_ID']))].add(r['PLAYER_ID'])
    fl = _folders(); cache = {}

    def rk(f):
        if f not in cache:
            R = list(csv.DictReader(open(LIVE / f / 'ranking.csv', encoding='utf-8')))
            cache[f] = ({int(x['playerId']): float(x['MPGhat']) for x in R}, {int(x['playerId']): float(x['ovr']) for x in R})
        return cache[f]
    for g in games.values():
        d = g['date']; c = [f for f in fl if f < d]; g['folder'] = folder or (c[-1] if c else fl[0])
        mpg, ovr = rk(g['folder'])
        for side in ('home', 'away'):
            base = []
            for p in played[(g['gid'], g[side])]:
                a = M.own_avg([m for dd, _, m in plog[p] if dd < d])
                base.append([p, mpg.get(p, 8.0) if a is None else a])
            g['rot_' + side] = M.rotation([], base, ovr=ovr)
    return games


def update_cache(log=None) -> dict:
    """補算快取裡沒有的已完賽場次的 T 賽前預期，回傳整份快取。"""
    doc = json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {'note': 'E-253／R-171 賽前 T 預期（主場視角，每場）', 'games': {}}
    have = doc['games']; G = played_games()
    todo = {k: v for k, v in G.items() if k not in have}
    if not todo:
        return doc
    import numpy as np
    import torch
    sys.path.insert(0, str(E229))
    import e229_live
    from e227_model import predict
    torch.set_num_threads(4)
    _rotations(todo)
    byd = collections.defaultdict(list)
    for g in todo.values():
        byd[(g['date'], g['folder'])].append(g)
    pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    for (d, f), gs in sorted(byd.items()):
        names = {p: 1 for g in gs for s in ('home', 'away') for p, _ in g['rot_' + s]}
        snap = E246_SNAP / d
        C, _ = e229_live.make_ctx(d, str(LIVE / f), names, None, str(snap) if snap.is_dir() else None)
        for g in gs:
            Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
            rng = np.random.default_rng([229, int(g['gid'])])
            A, B = C.draw(Rh, lh, rh, rng, DRAWS), C.draw(Ra, la, ra, rng, DRAWS)
            X = torch.from_numpy(np.concatenate([np.concatenate([A, B], 1), np.concatenate([B, A], 1)], 0))
            T = [X, pos.expand(2 * DRAWS, -1), side.expand(2 * DRAWS, -1)]
            pf = pa = 0.0
            for m in C.nets:
                o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy()
                pf += 100.0 * 0.5 * (o[:DRAWS, 0].mean() + o[DRAWS:, 1].mean()) / len(C.nets)
                pa += 100.0 * 0.5 * (o[:DRAWS, 1].mean() + o[DRAWS:, 0].mean()) / len(C.nets)
            sc = C.avg_poss / 100
            have[g['gid']] = dict(date=d, home=g['home'], away=g['away'], folder=f, pfHome=float(pf * sc), paHome=float(pa * sc),
                                  mT=float((pf - pa) * sc), snap=snap.is_dir())
        if log:
            log.info('賽前 T 預期補算 %s：%d 場', d, len(gs))
    CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return doc


TODAY_CACHE = SRC / 'today-margins.json'


def today_margins(today: str, live_dir, log=None) -> dict:
    """R-172：用「今天的 T」（今天的 live 夾 OVR／特徵、今天的追蹤混合）重算所有比賽日 < today 的已完賽場次預期。
    名單＝該場實際上場的人＋比賽日前自己的平均分鐘（陣容是當天的事實），球員強度一律用今天的。
    同一天同一個 live 夾只算一次（存 today-margins.json，只補缺的場次）。回傳格式同 pregame 快取。"""
    live_dir = Path(live_dir); key = dict(today=today, folder=live_dir.name)
    doc = json.loads(TODAY_CACHE.read_text(encoding='utf-8')) if TODAY_CACHE.exists() else {}
    if {k: doc.get(k) for k in key} != key:
        doc = dict(note='R-172 今天的 T 對已完賽場次的預期（主場視角）', **key, games={})
    have = doc['games']
    todo = {k: v for k, v in played_games().items() if v['date'] < today and k not in have}
    if not todo:
        return doc
    import numpy as np
    import torch
    sys.path.insert(0, str(E229))
    import e229_live
    from e227_model import predict
    torch.set_num_threads(4)
    _rotations(todo, folder=live_dir.name)
    names = {p: 1 for g in todo.values() for s in ('home', 'away') for p, _ in g['rot_' + s]}
    C, _ = e229_live.make_ctx(today, str(live_dir), names)
    pos = torch.tensor(list(range(5)) * 2).unsqueeze(0); side = torch.tensor([0] * 5 + [1] * 5).unsqueeze(0)
    sc = C.avg_poss / 100
    for g in sorted(todo.values(), key=lambda x: x['gid']):
        Rh, lh, rh = C.prep(g['rot_home']); Ra, la, ra = C.prep(g['rot_away'])
        rng = np.random.default_rng([229, int(g['gid'])])
        A, B = C.draw(Rh, lh, rh, rng, DRAWS), C.draw(Ra, la, ra, rng, DRAWS)
        X = torch.from_numpy(np.concatenate([np.concatenate([A, B], 1), np.concatenate([B, A], 1)], 0))
        T = [X, pos.expand(2 * DRAWS, -1), side.expand(2 * DRAWS, -1)]
        pf = pa = 0.0
        for m in C.nets:
            o = predict(m, T, C.dev, bs=8192)[:, :, 0].numpy()
            pf += 100.0 * 0.5 * (o[:DRAWS, 0].mean() + o[DRAWS:, 1].mean()) / len(C.nets)
            pa += 100.0 * 0.5 * (o[:DRAWS, 1].mean() + o[DRAWS:, 0].mean()) / len(C.nets)
        have[g['gid']] = dict(date=g['date'], home=g['home'], away=g['away'], pfHome=float(pf * sc), paHome=float(pa * sc), mT=float((pf - pa) * sc))
    if log:
        log.info('今天的 T（%s，%s）重算已完賽場次：%d 場', today, live_dir.name, len(todo))
    TODAY_CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return doc


def residuals(today: str, doc: dict | None = None, log=None, live_dir=None) -> dict:
    """{tid: dict(n, off, def, net, offShr, defShr, netShr)}；Shr＝÷(n+K)。只用比賽日 < today 的場次。
    live_dir 給定（線上預設，R-172）：對「今天的 T」算殘差，避免本季表現同時被 OVR 更新與殘差重複計入；
    沒給：對凍結的賽前預期（舊 R-171 定義，留作對照）。"""
    if doc is None:
        doc = today_margins(today, live_dir, log) if live_dir is not None else update_cache(log)
    G = played_games(); acc = collections.defaultdict(lambda: [0, 0.0, 0.0])
    use = [(g, doc['games'][gid]) for gid, g in G.items() if gid in doc['games'] and g['date'] < today]
    # T 輸出的單隊得分是相對值（只有差值有意義）：用已完賽場次的平均得分補常數 b，攻守殘差各自置中，淨值不受影響
    b = sum(g['pts_home'] + g['pts_away'] - p['pfHome'] - p['paHome'] for g, p in use) / (2 * len(use)) if use else 0.0
    for g, p in use:
        oh = g['pts_home'] - (p['pfHome'] + b + H / 2); dh = g['pts_away'] - (p['paHome'] + b - H / 2)
        for t, o, d_ in ((g['home'], oh, dh), (g['away'], dh, oh)):
            a = acc[t]; a[0] += 1; a[1] += o; a[2] += d_
    out = {}
    for t, (n, o, d_) in acc.items():
        out[t] = dict(n=n, off=o / n, def_=d_ / n, net=(o - d_) / n, offShr=o / (n + K), defShr=d_ / (n + K), netShr=(o - d_) / (n + K))
    return out


if __name__ == '__main__':
    import datetime as dt
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    lg = logging.getLogger('actual_blend')
    R = residuals(sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat(), log=lg, live_dir=sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps({t: {k: round(v, 2) for k, v in r.items()} for t, r in sorted(R.items(), key=lambda x: -x[1]['netShr'])}, indent=0))
