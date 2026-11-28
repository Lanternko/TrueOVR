"""0.2.10f 的 3PT 欄（E-191b P1m）核對：
 (1) TV_P1M=0 的 three_value_columns 與 git HEAD（0.2.10e）的 run_c4_live 逐位元相同（cols、info 全部）；
 (2) TV_P1M=1：池＝近三季窗口值＋本季窗口值（poolSize、poolPast 對得上），逐人值＝同一個映射套在這個池上；
 (3) 2025-26 季末（s＝2025-26，前三季＝2022-23／23-24／24-25，本季限 has）用 live 的映射式重算，對 reports/card-0.2.10f/three-value.csv 的 tv_main。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_tv_p1m_0210f.py（需先把 git HEAD 版 run_c4_live.py 存成 live/_head_run_c4_live.py；跑完刪掉）"""
import csv, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_c4_live as N                    # noqa: E402
import _head_run_c4_live as O              # noqa: E402
import window10 as W10                     # noqa: E402
ROOT = N.ROOT


def dump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, allow_nan=True)


def live_map(pool):
    """run_c4_live.three_value_columns 內 pct／attr／attr_open 的同式（pool 換成 P1m 池）。"""
    an = N.m26_anchors(pool)
    pct = lambda x: 100 * (sum(v < x for v in pool) + .5 * sum(v == x for v in pool)) / len(pool)
    attr = lambda p: max(40, min(99, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))
    return lambda x: N.m26_top_tail(x - an['r99'], an['S']) if pct(x) >= 99 else attr(pct(x))


def main():
    W = W10.Win10(N.DATA26)
    prior_ids = sorted(W.D.pidx)
    # (1) 關閉＝0.2.10e
    N.TV_P1M = False
    off, off_info = N.three_value_columns(prior_ids)
    ho, ho_info = O.three_value_columns(prior_ids)
    same1 = dump(off) == dump(ho) and dump(off_info) == dump(ho_info)
    print('(1) TV_P1M=0 vs HEAD 0.2.10e：cols', len(off), 'info 相同' if dump(off_info) == dump(ho_info) else 'info 不同', '→', '逐位元相同' if same1 else '不同')
    assert same1
    # (2) 開啟
    N.TV_P1M = True
    N.WIN8.clear()
    on, on_info = N.three_value_columns(prior_ids)
    past = N.win8_load()['tvpast']
    npast = sum(len(d) for d in past.values())
    print('(2) 過去季人數', {t: len(d) for t, d in past.items()}, 'poolPast', on_info['poolPast'], 'poolSize', on_info['poolSize'], '關閉時 poolSize', off_info['poolSize'])
    assert on_info['poolPast'] == npast and on_info['poolSize'] == npast + off_info['poolSize']
    cur_pool = [c['value'] for c in off.values() if c['ok'] and c['minAll'] >= N.THREE_POOL_MIN]
    mp = live_map([v for d in past.values() for v in d.values()] + cur_pool)
    d2 = max(abs(on[p]['threeValue'] - mp(on[p]['value'])) for p in on if on[p]['ok'])
    assert all(on[p]['value'] == off[p]['value'] for p in on if on[p]['ok'])
    print('    逐人 threeValue 對手算映射 最大差', d2, '；value 欄與關閉時相同')
    assert d2 == 0
    # (3) 2025-26 季末對 card 的 tv_main
    s = '2025-26'
    mem = json.loads(W10.TV_MEMBERS.read_text(encoding='utf-8'))['seasons']
    past26 = W.tv_past_pool(s, mem)
    cur, G = W.season_cur(s)
    n, a, mn = W.tv_raw(G, cur, s, G, 4)
    m_, a_ = W10.lg_total(W.T10[s])
    _, _, val = W.tv_value(n, a, mn, m_ / a_)
    d_rows = list(csv.DictReader((ROOT / 'reports/card-0.2.10d/three-value.csv').open(encoding='utf-8')))
    nl = json.loads(N.THREE_PRIOR.read_text(encoding='utf-8'))
    sv26 = {int(p) for p in mem[s]}
    has = {int(r['playerId']) for r in d_rows if r['playerId'] in nl and int(r['playerId']) in sv26}
    ix = W.D.pidx
    curv = {q: float(val[ix[q]]) for q in sv26 if q in ix and not np.isnan(val[ix[q]]) and q in has and mn[ix[q]] >= W10.TV_POOL_MIN}
    pool = [v for d in past26.values() for v in d.values()] + list(curv.values())
    mp = live_map(pool)
    card = {int(r['playerId']): r for r in csv.DictReader((ROOT / 'reports/card-0.2.10f/three-value.csv').open(encoding='utf-8'))}
    cand = {int(r['playerId']): r for r in csv.DictReader((ROOT / 'reports/E191-threevalue-dispersion/three-value-candidate.csv').open(encoding='utf-8'))}
    qs = [q for q in card if q in has and q in ix and not np.isnan(val[ix[q]])]
    diffs = [abs(mp(float(val[ix[q]])) - float(card[q]['tv_main'])) for q in qs]
    print('(3) 2025-26 季末：過去季人數', {t: len(d) for t, d in past26.items()}, '本季', len(curv), '池', len(pool), '；比對', len(qs), '人，最大差', max(diffs), '，>1e-9 者', sum(d > 1e-9 for d in diffs))
    print('    card tv_main 與候選檔一致：', all(card[q]['tv_main'] == cand[q]['tv_main'] for q in card))
    for q in qs:
        if card[q]['name'] in ('Stephen Curry', 'Nikola Jović', 'Lonzo Ball', "De'Andre Hunter", 'Domantas Sabonis', 'Alperen Sengun'):
            print('   ', card[q]['name'], 'live 映射', round(mp(float(val[ix[q]])), 4), 'card', round(float(card[q]['tv_main']), 4))
    return 0 if max(diffs) < 1e-9 else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
