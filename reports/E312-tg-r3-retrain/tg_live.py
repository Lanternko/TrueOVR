"""E-312：2026-27 live 特徵表（e229_live.build 的輸出）的 blk36 欄換成 AG（E-307 TG 的 live 版，prereg.md）。
AG 本季＝本季 box 蓋帽/36 × rS − gt36S（E-307 凍結收縮強度；本季聯盟取回率用該日之前 pbp，每分鐘干擾率五季平均），
再照 box 規則混 2025-26 AG：w＝本季分鐘/(本季分鐘＋500)；z 人群與 blk36 相同（2025-26 表內、該欄有值者）。不讀比分。
資料（pbp、live 夾）在主 checkout（E312_MAIN），E-307 計數與 feat 在本 worktree。"""
import csv, importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(os.path.dirname(HERE))
MAIN = os.environ.get('E312_MAIN', r'D:\Projects\CODING\basketball-autochess')
E307 = os.path.join(WT, 'reports', 'E307-blk-quality')
PBP = os.path.join(MAIN, 'data', 'defense-seventh', '2026-27', 'pbp')
PRI = json.load(open(os.path.join(E307, 'data', 'priors.json'), encoding='utf-8'))
K_R, K_GT = PRI['k']['k_r'], PRI['k']['K_gt']
LAM = PRI['league']['2026-27']['gtPerMin']          # 五季平均每分鐘干擾率
K_PRIOR_MIN = 500.0


def prior_ag():
    out = {}
    for r in csv.DictReader(open(os.path.join(E307, 'data', 'feat-2025-26.csv'), encoding='utf-8')):
        if r['AG'] != '':
            out[str(r['pid'])] = float(r['AG'])
    return out


def pbp_by_game(cache=None):
    """{gid: {pid: [known, retained, gt]}}，規則同 scripts/rim_blk_live._cur_events（E-307 parse_blocks outcome）。"""
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    spec = importlib.util.spec_from_file_location('e307_parse', os.path.join(E307, 'parse_blocks.py'))
    PB = importlib.util.module_from_spec(spec); spec.loader.exec_module(PB)
    out = {}
    for fn in sorted(os.listdir(PBP)):
        if not fn.startswith('00') or not fn.endswith('.json'):
            continue
        a = PB.actions(os.path.join(PBP, fn)); agg = {}
        for i, x in enumerate(a):
            t = x['actionType']
            if t == 'violation' and x.get('subType') == 'defensive goaltending' and x.get('personId'):
                agg.setdefault(str(x['personId']), [0, 0, 0])[2] += 1
            if t != 'block' or not x.get('personId'):
                continue
            de = x['teamId']; of = x.get('possession')
            if of == de or not of:
                of = next((y['teamId'] for y in reversed(a[max(0, i - 6):i]) if y['actionType'] in ('2pt', '3pt')), None)
            r, _ = PB.outcome(a, i, de, of)
            if r is None:
                continue
            v = agg.setdefault(str(x['personId']), [0, 0, 0]); v[0] += 1; v[1] += int(r)
        out[fn[:10]] = agg
    if cache:
        json.dump(out, open(cache, 'w'))
    return out


def cur_events(per_game, dates, today):
    agg = {}
    for gid, d in per_game.items():
        if dates.get(gid, '9999') >= today:
            continue
        for p, v in d.items():
            a = agg.setdefault(p, [0.0, 0.0, 0.0])
            for k in range(3):
                a[k] += v[k]
    n = sum(v[0] for v in agg.values())
    return agg, (sum(v[1] for v in agg.values()) / n if n else PRI['league']['2026-27']['r'])


def ag_mixed(cur_box, per_game, dates, today, pag=None):
    """{pid: AG 混合值}（給有本季分鐘或有 2025-26 AG 的人）＋資訊。cur_box＝e229_live.season_box(today)。"""
    pag = prior_ag() if pag is None else pag
    mean_p = float(np.mean(list(pag.values())))
    ev, r_lg = cur_events(per_game, dates, today)
    out = dict(pag); cur_ag = {}
    for p, a in cur_box.items():
        mc = a['MIN']
        if mc <= 0:
            continue
        e = ev.get(p, [0.0, 0.0, 0.0])
        rS = (e[1] + K_R * r_lg) / (e[0] + K_R)
        gt36 = (e[2] + K_GT * LAM) / (mc + K_GT) * 36
        ag = a['BLK'] * 36.0 / mc * rS - gt36; cur_ag[p] = ag
        w = mc / (mc + K_PRIOR_MIN)
        out[p] = w * ag + (1 - w) * pag.get(p, mean_p)
    return out, dict(leagueR=r_lg, nCur=len(cur_ag), nEvGames=sum(1 for g in per_game if dates.get(g, '9999') < today), curAG=cur_ag)


def patch(B, prior_pids, agm, blk_j):
    """B[pid]=(vals, mask) 的 blk36 欄換成 z(AG 混合)；遮罩不變；z 人群＝2025-26 表內、blk36 遮罩為 1 者（同 build 的 smu）。"""
    pop = [p for p in prior_pids if p in B and B[p][1][blk_j] == 1.0 and p in agm]
    v = np.array([agm[p] for p in pop]); mu, sd = float(v.mean()), float(v.std())
    out, miss = {}, 0
    for p, (vals, mask) in B.items():
        v2 = vals.copy()
        if mask[blk_j] == 1.0:
            if p in agm:
                v2[blk_j] = (agm[p] - mu) / sd
            else:
                miss += 1      # 不應發生：有 blk36 卻沒有 AG
        out[p] = (v2, mask.copy())
    return out, dict(popN=len(pop), mu=mu, sd=sd, missing=miss)
