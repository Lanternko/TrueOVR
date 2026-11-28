"""E-089 比對：inseason 0.2.1e（out-022，CARD_MODE=022）vs inseason 0.2.2（out-024，CARD_MODE=024），同一份資料。

只讀 out-022/、out-024/、live/usage-2025-26-card024.json、live/prior-2025-26-card022.json、reports/card-0.2.4/ranking.csv。
輸出：compare.md、compare.json。用法：python -I reports/ovr-inseason-2026-27/e089-card024/compare.py

ΔOVR 的拆解（依序疊加，不調參）：
  S0 舊 OVR = map_old((p − r_old)·MPGhat_old/36)
  S1 錨點：map_new((p − r_new)·MPGhat_old/36)        → 錨點／r_repl 換成 results.json card 段
  S2 用人項：map_new((predNew − r_new)·MPGhat_old/36) → p 換成 predNew（含 b1 縮放與 L、a、y、v、d 各項）
  S3 MPG0：map_new((predNew − r_new)·MPGhat_new/36)   → MPG0 改成 card 0.2.4 的 mpgAvail（= 新 OVR）
"""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'live'
ROOT = HERE.parents[2]
OLD, NEW = HERE / 'out-022', HERE / 'out-024'


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def rank_avg(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank_avg(a), rank_avg(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den


def mp(g, a):
    p1, p50, p99 = a
    return 40 + 30 * (g - p1) / (p50 - p1) if g <= p50 else 70 + 29 * (g - p50) / (p99 - p50)


def main():
    mo = json.loads((OLD / 'meta.json').read_text(encoding='utf-8'))
    mn = json.loads((NEW / 'meta.json').read_text(encoding='utf-8'))
    us = json.loads((LIVE / 'usage-2025-26-card024.json').read_text(encoding='utf-8'))
    ro, rn = rd(OLD / 'ranking.csv'), rd(NEW / 'ranking.csv')
    card = {r['name']: r for r in rd(ROOT / 'reports/card-0.2.4/ranking.csv')}
    prior = json.loads((LIVE / 'prior-2025-26-card022.json').read_text(encoding='utf-8'))
    old_mpg0_all = {p['playerId']: (p['observed']['MIN'] / p['observed']['GP'] if p['observed']['GP'] > 0 else 0.0) for p in prior['players']}
    pname = {p['playerId']: p['name'] for p in prior['players']}
    A0, R0 = mo['e064Anchors'], mo['e064RRepl']
    A1, R1 = mn['e064Anchors'], mn['e064RRepl']
    out = {'oldVersion': mo['version'], 'newVersion': mn['version'], 'n_old': len(ro), 'n_new': len(rn)}

    # ---- (c2)
    allfin = all(math.isfinite(float(r[k])) for r in rn for k in ('ovr', 'lastOVR', 'predNew', 'g'))
    names_n = [r['name'] for r in rn]
    last = [float(r['lastOVR']) for r in rn]
    cc = [float(card[r['name']]['ovr']) for r in rn]
    diffs = sorted(((abs(a - b), r['name'], a, b) for a, b, r in zip(last, cc, rn)), reverse=True)
    out['c2'] = {'allFinite': allfin, 'sameCount': len(ro) == len(rn), 'sameNames': set(r['name'] for r in ro) == set(names_n),
                 't1_a_f0_kmax_maxAbsOvrDiff': mn['sanity']['a_f0_kmax_maxAbsOvrDiff'],
                 'spearman_lastOVR_vs_card024': spearman(last, cc), 'nMatched': len(last),
                 'maxAbsDiff': diffs[0][0], 'top10Diff': [[n, a, b, round(d, 3)] for d, n, a, b in diffs[:10]],
                 'nDiffGt0.1': sum(1 for d in diffs if d[0] > 0.1 + 1e-9)}

    # ---- 逐人比對
    po = {int(r['playerId']): r for r in ro}
    pn = {int(r['playerId']): r for r in rn}
    rows = []
    chk = 0.0
    for pid, n in pn.items():
        o = po[pid]
        u = us['players'][str(pid)]
        p = float(o['predictedPer36'])
        assert abs(p - float(n['predictedPer36'])) < 1e-9, (pid, p, n['predictedPer36'])
        mo_, mn_ = float(o['MPGhat']), float(n['MPGhat'])
        pnew = float(n['predNew'])
        s0 = mp((p - R0) * mo_ / 36, A0)
        s1 = mp((p - R1) * mo_ / 36, A1)
        s2 = mp((pnew - R1) * mo_ / 36, A1)
        s3 = mp((pnew - R1) * mn_ / 36, A1)
        chk = max(chk, abs(s0 - float(o['ovr'])), abs(s3 - float(n['ovr'])))
        age = u['age']
        rows.append({'pid': pid, 'name': n['name'], 'team': n['team'], 'N': int(n['N']), 'age': age, 'old': float(o['ovr']), 'new': float(n['ovr']),
                     'd': float(n['ovr']) - float(o['ovr']), 'dAnchors': s1 - s0, 'dUsage': s2 - s1, 'dMpg': s3 - s2,
                     'mpg0Old': float(o['MPG0']), 'mpg0New': float(n['MPG0']), 'hat': mn_, 'p': p, 'predNew': pnew, 'has': u['has'],
                     'L': u['L'], 'y': u['y'], 'v': u['v'], 'dd': u['d'], 'a': u['a']})
    out['decompCheckMaxAbs'] = chk
    absd = [abs(r['d']) for r in rows]
    out['absDelta'] = {'median': statistics.median(absd), 'mean': statistics.mean(absd), 'max': max(absd),
                       'gt5': sum(1 for x in absd if x > 5), 'gt10': sum(1 for x in absd if x > 10),
                       'medianSigned': statistics.median(r['d'] for r in rows)}
    young = [r['d'] for r in rows if r['age'] is not None and r['age'] <= 23]
    old = [r['d'] for r in rows if r['age'] is not None and r['age'] >= 31]
    mid = [r['d'] for r in rows if r['age'] is not None and 23 < r['age'] < 31]
    noage = [r['d'] for r in rows if r['age'] is None]
    out['byAge'] = {'young<=23': {'n': len(young), 'median': statistics.median(young) if young else None},
                    'old>=31': {'n': len(old), 'median': statistics.median(old) if old else None},
                    'mid': {'n': len(mid), 'median': statistics.median(mid) if mid else None},
                    'noAge': {'n': len(noage), 'median': statistics.median(noage) if noage else None}}
    # 各項貢獻的中位數
    out['componentMedians'] = {k: statistics.median(r[k] for r in rows) for k in ('dAnchors', 'dUsage', 'dMpg')}
    out['componentAbsMedians'] = {k: statistics.median(abs(r[k]) for r in rows) for k in ('dAnchors', 'dUsage', 'dMpg')}

    def cause(r):
        comps = {'錨點': r['dAnchors'], '用人項': r['dUsage'], 'MPG0 口徑': r['dMpg']}
        k = max(comps, key=lambda z: abs(comps[z]))
        return k, comps

    movers = sorted(rows, key=lambda r: -abs(r['d']))[:10]
    out['movers'] = [{**{k: r[k] for k in ('name', 'team', 'N', 'age', 'old', 'new', 'd', 'mpg0Old', 'mpg0New', 'hat', 'dAnchors', 'dUsage', 'dMpg', 'has')},
                      'cause': cause(r)[0]} for r in movers]

    # ---- 前 20
    top_o = [r['name'] for r in ro[:20]]
    top_n = [r['name'] for r in rn[:20]]
    rko = {r['name']: (int(r['rank']), float(r['ovr'])) for r in ro}
    rkn = {r['name']: (int(r['rank']), float(r['ovr'])) for r in rn}
    out['top20'] = {'in': [[n, rkn[n][1], rkn[n][0], rko[n][0], rko[n][1]] for n in top_n if n not in top_o],
                    'out': [[n, rko[n][1], rko[n][0], rkn[n][0], rkn[n][1]] for n in top_o if n not in top_n],
                    'old': [[n, rko[n][1]] for n in top_o], 'new': [[n, rkn[n][1]] for n in top_n]}
    # rank 變動（前 50 內）
    out['rankSpearman_old_new'] = spearman([float(po[r['pid']]['ovr']) for r in rows], [r['new'] for r in rows])

    # ---- MPG0 口徑差：ranked 368 與卡內 582
    md = sorted(((abs(r['mpg0New'] - r['mpg0Old']), r['name'], r['mpg0Old'], r['mpg0New'], r['d']) for r in rows), reverse=True)
    out['mpg0Shift'] = {'ranked': {'n': len(md), 'gt3': sum(1 for x in md if x[0] > 3), 'median': statistics.median(x[0] for x in md),
                                   'top5': [[n, o, w, d, dv] for _, n, o, w, dv in [(a, b, c, d_, e) for a, b, c, d_, e in md[:5]] for d in [round(w - o, 2)]]}}
    all582 = []
    for pid, u in us['players'].items():
        pid = int(pid)
        if pid in old_mpg0_all:
            all582.append((abs(u['mpgAvail'] - old_mpg0_all[pid]), u['name'], old_mpg0_all[pid], u['mpgAvail']))
    all582.sort(reverse=True)
    out['mpg0Shift']['card582'] = {'n': len(all582), 'gt3': sum(1 for x in all582 if x[0] > 3), 'top5': [[n, round(o, 2), round(w, 2)] for _, n, o, w in all582[:5]]}
    # 舊 MPG0 重算＝out-022 MPG0
    out['mpg0OldRuleMatchesRun'] = max(abs(old_mpg0_all[r['pid']] - r['mpg0Old']) for r in rows)
    out['hasFalseRanked'] = sum(1 for r in rows if not r['has'])
    out['hasFalseCard'] = sum(1 for u in us['players'].values() if not u['has'])
    out['coef'] = us['coef']
    out['rRepl'] = {'old': R0, 'new': R1}
    out['anchors'] = {'old': A0, 'new': A1}
    (HERE / 'compare.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    # ---- compare.md
    L = []
    L.append(f"# E-089 比對：{out['oldVersion']}（out-022）→ {out['newVersion']}（out-024）\n")
    L.append(f"同一份資料（cutoff {mn['dataCutoff']}），{len(rows)} 人。|ΔOVR| 中位數 **{out['absDelta']['median']:.2f}**、平均 {out['absDelta']['mean']:.2f}、最大 {out['absDelta']['max']:.2f}；"
             f">5 分 {out['absDelta']['gt5']} 人、>10 分 {out['absDelta']['gt10']} 人；ΔOVR 有號中位數 {out['absDelta']['medianSigned']:+.2f}。拆解重現檢查最大差 {chk:.2e}。\n")
    L.append('## 前 20 名進出\n')
    L.append('| 方向 | 球員 | OVR（該版） | 名次（該版） | 名次（另一版） | OVR（另一版） |\n|---|---|---|---|---|---|')
    for n, a, b, c, d in out['top20']['in']:
        L.append(f'| 進 | {n} | {a:.1f} | {b} | {c} | {d:.1f} |')
    for n, a, b, c, d in out['top20']['out']:
        L.append(f'| 出 | {n} | {a:.1f} | {b} | {c} | {d:.1f} |')
    L.append('\n新版前 20：' + '、'.join(f'{n} {v:.1f}' for n, v in out['top20']['new']))
    L.append('\n舊版前 20：' + '、'.join(f'{n} {v:.1f}' for n, v in out['top20']['old']) + '\n')
    L.append('## ΔOVR 最大 10 人\n')
    L.append('| 球員 | 隊 | N | 年齡 | 舊 OVR | 新 OVR | Δ | 舊 MPG0 | mpgAvail(新) | 錨點 | 用人項 | MPG0 | 主因 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for m in out['movers']:
        L.append(f"| {m['name']} | {m['team']} | {m['N']} | {m['age'] if m['age'] is not None else '—'} | {m['old']:.1f} | {m['new']:.1f} | {m['d']:+.1f} | {m['mpg0Old']:.1f} | {m['mpg0New']:.1f} | {m['dAnchors']:+.1f} | {m['dUsage']:+.1f} | {m['dMpg']:+.1f} | {m['cause']} |")
    L.append('\n（錨點／用人項／MPG0 三欄依序疊加，加總＝Δ；用人項含 predNew 對 p 的整體縮放與 L、a、y、v、d 各項。）\n')
    L.append('## 年齡\n')
    L.append('| 組 | 人數 | ΔOVR 中位數 |\n|---|---|---|')
    for k, v in out['byAge'].items():
        L.append(f"| {k} | {v['n']} | {('%+.2f' % v['median']) if v['median'] is not None else '—'} |")
    L.append('\n各項貢獻中位數（有號／絕對值）：' + '；'.join(f"{k} {out['componentMedians'][k]:+.2f}／{out['componentAbsMedians'][k]:.2f}" for k in ('dAnchors', 'dUsage', 'dMpg')) + '\n')
    L.append('## MPG0 口徑差（|mpgAvail − 舊 MPG0|）\n')
    s = out['mpg0Shift']
    L.append(f"- 賽季榜 {s['ranked']['n']} 人：> 3 的 {s['ranked']['gt3']} 人，中位數 {s['ranked']['median']:.2f}。最大 5 人：" +
             '；'.join(f"{n}（舊 {o:.1f}→新 {w:.1f}，OVR {dv:+.1f}）" for n, o, w, d, dv in s['ranked']['top5']))
    L.append(f"- 卡內 {s['card582']['n']} 人：> 3 的 {s['card582']['gt3']} 人。最大 5 人：" + '；'.join(f'{n}（舊 {o}→新 {w}）' for n, o, w in s['card582']['top5']) + '\n')
    c2 = out['c2']
    L.append('## (c2)\n')
    L.append(f"- OVR/lastOVR/predNew/g 全有限：{c2['allFinite']}；人數 {len(ro)}→{len(rn)}，名單相同：{c2['sameNames']}")
    L.append(f"- f=0、k 上界檢查 (a)（t1）最大差 {c2['t1_a_f0_kmax_maxAbsOvrDiff']:.4f}（<0.5）")
    L.append(f"- lastOVR 對 card 0.2.4 ranking.csv ovr（{c2['nMatched']} 人同名配對）：Spearman {c2['spearman_lastOVR_vs_card024']:.6f}；最大差 {c2['maxAbsDiff']:.2f}（差 >0.1 的 {c2['nDiffGt0.1']} 人）")
    L.append('- 差最大 10 人：' + '；'.join(f'{n} {a:.1f} vs {b:.1f}' for n, a, b, d in c2['top10Diff']) + '\n')
    (HERE / 'compare.md').write_text('\n'.join(L), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('c2', 'absDelta', 'byAge', 'componentMedians', 'componentAbsMedians', 'decompCheckMaxAbs', 'mpg0Shift', 'hasFalseRanked', 'hasFalseCard', 'mpg0OldRuleMatchesRun', 'rankSpearman_old_new')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
