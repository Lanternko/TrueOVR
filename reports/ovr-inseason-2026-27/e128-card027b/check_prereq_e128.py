"""E-128 前置條件 (c0)(c1)(u)(z)(L1)(h)(t)(s)（e128-card027b/preregistration.md §2 ＋ errata-1/2/3）。任一不過 → 停，不看 (1)(2)。

用法（repo 根目錄；三步各自一個程序、不開子程序）：
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e128-card027b/check_prereq_e128.py worker 025
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e128-card027b/check_prereq_e128.py worker 027b
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e128-card027b/check_prereq_e128.py final
worker：以該 CARD_MODE 載入 run_c4_live.py（只呼叫 setup()，不跑 main），算 2025-26 整季視窗值（(s) 用）。
final：彙整成 prereq.json。(h) 要 rookie_defense（在 live/），final 內以 sys.path 插入 live/ 後 import。
"""
import ast
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
LIVE = REPORT / 'live'
ROOT = HERE.parents[2]
E101D = ROOT / 'reports/card-0.2.5+E101-crossera'
E125 = ROOT / 'reports/card-0.2.7+E125-pass-volume'
E111 = REPORT / 'e111-card027'
CARD = ROOT / 'reports/card-0.2.7b'
RB = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rj(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def load_live(mode):
    os.environ['CARD_MODE'] = mode
    spec = importlib.util.spec_from_file_location(f'run_c4_live_{mode}', LIVE / 'run_c4_live.py')
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    return L


def median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


# ------------------------------------------------------------------ worker：2025-26 整季視窗值（(s)）
def worker(mode):
    L = load_live(mode)
    L.setup()
    C, IC, SA = L.C, L.IC, L.SA
    prior_cards = C.load_card(L.PRIOR)[0]
    _, attrs0 = C.deployment('S*')
    sd = IC.load_target_season()
    bio = {int(r['PLAYER_ID']): r for r in SA.result_set(L.BIO25)}
    sdm = {'season': L.PRIOR, 'box': {p: b for p, b in sd['box'].items() if p in bio}, 'shots': sd['shots'],
           'teamRows': sd['teamRows']}
    w = IC.window_cards(sdm, 999, C.mapping_for(L.PRIOR), prior_cards, IC.received_prior(L.PRIOR))
    upd = [a for a in C.UPD if a not in ('pressure', 'drive')] + ['foulDraw']
    out = {}
    for pid, rec in w.items():
        if pid not in attrs0:
            continue
        pool = rec['GP'] >= 30 and rec['MIN'] / rec['GP'] >= 20
        ys = {}
        for a in upd:
            sa = 'drive' if a == 'foulDraw' else a
            if IC.sample_of(rec, sa) < SA.SEASON_MIN_SAMPLE[sa]:
                continue
            if a == 'foulDraw':
                if L.M26_MODE:
                    y = rec['foulDraw']
                else:
                    y = L.foul_draw_y(rec) if float(rec['sample']['fga']) > 0 and float(rec['sample']['min']) > 0 else None
            else:
                y = rec[a]
            if y is not None:
                ys[a] = float(y)
        out[str(pid)] = {'name': prior_cards[pid]['name'], 'pool': pool, 'GP': rec['GP'], 'MIN': rec['MIN'],
                         'y': ys, 'x0': {a: float(attrs0[pid][a]) for a in upd}}
    doc = {'mode': mode, 'priorCard': L.PRIOR_CARD.relative_to(ROOT).as_posix(), 'priorCardSha256': sha(L.PRIOR_CARD),
           'updAttrs': upd, 'players': out}
    (HERE / f's-worker-{mode}.json').write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8', newline='\n')
    print(mode, 'players', len(out), 'pool', sum(v['pool'] for v in out.values()))


# ------------------------------------------------------------------ final
def check_c0():
    """027：out-027-post（改碼後 CARD_MODE=027，走 live/run_c4_live_rookie.py 包裝）＝out-027-pre（改碼前）＝線上 live/2026-10-28。
    025：out-025-post（改碼後，plain script）＝out-025-head（HEAD 原碼，同一 plain script 路徑）。"""
    pub = LIVE / '2026-10-28'
    d27 = {f: {'post': sha(HERE / 'out-027-post' / f), 'pre': sha(HERE / 'out-027-pre' / f), 'published': sha(pub / f)}
           for f in ('ranking.csv', 'no-prior.csv')}
    d25 = {f: {'post': sha(HERE / 'out-025-post' / f), 'head': sha(HERE / 'out-025-head' / f)}
           for f in ('ranking.csv', 'no-prior.csv')}
    m_post, m_pub = rj(HERE / 'out-027-post/meta.json'), rj(pub / 'meta.json')
    ip = {k: v['sha256'] for k, v in m_post['inputs'].items()}
    iq = {k: v['sha256'] for k, v in m_pub['inputs'].items()}
    ok27 = all(len(set(v.values())) == 1 for v in d27.values())
    ok25 = all(len(set(v.values())) == 1 for v in d25.values())
    return {'pass': bool(ok27 and ok25 and ip == iq and m_post['dataCutoff'] == m_pub['dataCutoff']),
            'files027': d27, 'files025': d25, 'inputsSameAsPublished': ip == iq, 'dataCutoff': m_post['dataCutoff'],
            'publishedVersion': m_pub.get('version'), 'postVersion': m_post.get('version'),
            'note': ('預註冊 (c0)：CARD_MODE=027 輸出＝線上 inseason 0.2.7 快照（逐位元）。027 走 run_c4_live_rookie.py 包裝（與線上同一入口）；'
                     '025 包裝在 assert 擋下，改以 plain script 比 patched vs HEAD 原碼（兩者同一路徑）。meta.json 只差 gitHead、dict 鍵序（-I 隨機雜湊序）')}


def check_c1():
    v = (HERE / 'logs/npm-test.exit').read_text().strip()
    tail = (HERE / 'logs/npm-test.log').read_text(encoding='utf-8', errors='replace').strip().splitlines()
    summ = [x for x in tail if 'passed' in x and 'failed' in x]
    return {'pass': v == '0', 'exit': v, 'summary': summ[-1] if summ else None}


def e101_func(name):
    src = (E101D / 'work/build_e101.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {'math': math, 'CEIL': 150.0, 'K_SD': 1.96}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'build_e101.py#' + name, 'exec'), ns)
    return ns[name], ast.get_source_segment(src, fn)


def independent_pass_pool():
    """用 E-125 build_e101_p.py 的原始碼（ast 抽出 Pool、in_pool、window、season_vals、merged_percentile_pool）獨立重組 pass 池。"""
    import numpy as np
    path = E125 / 'work/build_e101_p.py'
    src = path.read_text(encoding='utf-8')
    tree = ast.parse(src)
    want = {'pct', 'Pool', 'in_pool', 'window', 'season_vals', 'merged_percentile_pool'}
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in want]
    assert {n.name for n in nodes} == want, [n.name for n in nodes]

    class _B:
        POOL = (30, 20)
        POOL41 = (15, 20)
    a0 = rj(E125 / 'a0-pass-P50.json')
    main = ['2022-23', '2023-24', '2024-25']
    ns = {'np': np, 'B': _B, 'MAIN': main, 'LONG': [], 'LONG_ATTRS': set(), 'CARD_SEASON': '2025-26', 'Z9990': 1.044,
          'raw': {'pass': {'pool': a0['pool']}},
          'SEAS': {s: rj(E125 / f'pool-P50/raw-{s}.json') for s in main}}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'build_e101_p.py#extract', 'exec'), ns)
    pool, per = ns['merged_percentile_pool']('pass', 'e101')
    return sorted(pool.v), per, sha(path)


def check_u(L):
    top_tail, seg = e101_func('top_tail')
    bot_tail, seg_b = e101_func('bot_tail')
    ts = rj(E101D / 'tail-summary.json')['e101']
    rows, mx = [], 0.0
    for a, e in ts.items():
        if a.startswith('_') or 'S' not in e:
            continue
        S, r99 = e['S'], e['r99']
        for k in (0, 1, 3, 10, -1):
            x = r99 + k * S
            got, exp = L.m26_top_tail(x - r99, S), top_tail(x - r99, S)
            mx = max(mx, abs(got - exp))
            rows.append([a, k, got, exp])
        for k in (0, 1, 3, 10):
            d, sd_ = k * S, S
            got, exp = L.m26_bot_tail(d, sd_), bot_tail(d, sd_)
            mx = max(mx, abs(got - exp))
    exp_w = {0.0: 0.0, 36.0: 1.0, 5.0: 0.31175, 20.0: 0.80987}
    wd = {str(k): abs(L.sat_w(k) - v) for k, v in exp_w.items()}
    p27, p27b = rj(LIVE / 'pool-027.json')['attrs'], rj(LIVE / 'pool-027b.json')['attrs']
    eight = {}
    ok8 = True
    for a, e in p27.items():
        if a == 'pass':
            continue
        e2 = p27b[a]
        sd_ = max(abs(x - y) for x, y in zip(e['sorted'], e2['sorted'])) if len(e['sorted']) == len(e2['sorted']) else None
        an_ = max(abs(e['anchors'][k] - e2['anchors'][k]) for k in e['anchors'] if isinstance(e['anchors'][k], (int, float))
                  and not isinstance(e['anchors'][k], bool))
        same = sd_ == 0 and an_ == 0 and e['top'] == e2['top'] and e['bot'] == e2['bot'] and e['type'] == e2['type']
        eight[a] = {'nSorted': [len(e['sorted']), len(e2['sorted'])], 'maxSortedDiff': sd_, 'maxAnchorDiff': an_,
                    'topBotSame': e['top'] == e2['top'] and e['bot'] == e2['bot']}
        ok8 = ok8 and same
    extra_keys = sorted(set(p27b) - set(p27))
    vals, per, src_sha = independent_pass_pool()
    mine = p27b['pass']['sorted']
    pd = max(abs(x - y) for x, y in zip(vals, mine)) if len(vals) == len(mine) else None
    pass_ok = pd is not None and pd < 1e-9 and per == p27b['pass']['poolPerSeason']
    # 池檔 payload 雜湊
    pay = L.m26_payload_sha(rj(LIVE / 'pool-027b.json')) == rj(LIVE / 'pool-027b.json')['payloadSha256']
    return {'pass': bool(mx < 1e-9 and all(v < 1e-5 for v in wd.values()) and ok8 and pass_ok and pay),
            'tailMaxAbsDiff': mx, 'nTopPoints': len(rows), 'W': {str(k): L.sat_w(k) for k in exp_w}, 'WAbsDiff': wd,
            'eightNonPassPoolsEqualPool027': ok8, 'eightDetail': eight, 'newKeysIn027b': extra_keys,
            'passPoolIndependent': {'n': len(vals), 'nPool027b': len(mine), 'maxAbsDiff': pd, 'perSeason': per,
                                    'perSeasonPool027b': p27b['pass']['poolPerSeason'], 'source': 'E-125 build_e101_p.py#merged_percentile_pool',
                                    'sourceSha256': src_sha},
            'payloadShaOk': pay, 'e101TopTailSource': seg,
            'threshold': '尾巴 |差| < 1e-9；W |差| < 1e-5；8 項池與 pool-027 差 0；pass 池與 E-125 獨立重組 |差| < 1e-9'}


def check_z(L):
    """分區：pool-027b 的 8 項非 pass 池與 pool-027 逐位相同（(u)），zones 只依 2025-26 pbp，沿用 e111 的 zones-027.json。"""
    z26 = rj(E111 / 'zones-027.json')['seasons']['2025-26']
    e101 = {}
    with gzip.open(E101D / 'history/pbp-zones-2025-26.csv.gz', 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            t = e101.setdefault(r['playerId'], [0, 0, 0, 0])
            for i, k in enumerate(('midA', 'midM', 'shortA', 'shortM')):
                t[i] += int(r[k])
    pids = sorted(set(z26) | set(e101), key=int)
    mism = []
    for p in pids:
        a, b = z26.get(p, [0, 0, 0, 0]), e101.get(p, [0, 0, 0, 0])
        if a[0] != b[0] or a[2] != b[2]:
            mism.append({'playerId': p, 'midA027': a[0], 'midA_E101': b[0], 'shortA027': a[2], 'shortA_E101': b[2]})
    n_lt8_mid = n_lt8 = n_all = n_nodist = n_area = 0
    files = sorted((L.DATA26 / 'pbp').glob('*.json'))
    for f in files:
        for a in rj(f)['data']['game']['actions']:
            if a.get('isFieldGoal') != 1 or a.get('personId') in (None, 0):
                continue
            if a.get('shotResult') not in ('Made', 'Missed') or a.get('actionType') != '2pt':
                continue
            n_all += 1
            n_area += bool(a.get('area'))
            if a.get('shotDistance') is None:
                n_nodist += 1
            if (a.get('shotDistance') or 0.0) < 8.0:
                n_lt8 += 1
                n_lt8_mid += L.m26_zone_of(a) == 'mid'
    return {'pass': bool(not mism and n_lt8_mid == 0), 'nPlayersCompared': len(pids), 'nMismatch': len(mism),
            'mismatchSample': mism[:15],
            'zonesSource': 'e111-card027/zones-027.json（2025-26 pbp 分區計數與 pool-027b 無關；mid／short 池與 pool-027 差 0 見 (u)）',
            'season2026_27': {'pbpFiles': len(files), 'twoPtFGA': n_all, 'withArea': n_area, 'noShotDistance': n_nodist,
                              'shotDistLt8': n_lt8, 'shotDistLt8JudgedMid': n_lt8_mid}}


def check_L1(L):
    meta = rj(HERE / 'out-027b-plain/meta.json')
    anc_ref = rj(RB / 'work/cards-result.json')['anchors']
    anc = [anc_ref[k] for k in ('PR1', 'PR50', 'PR99')]
    us = rj(LIVE / 'usage-2025-26-card027b.json')
    anc_diff = max(abs(x - y) for x, y in zip(meta['e064Anchors'], anc))
    rr_diff = abs(meta['e064RRepl'] - us['rRepl'])
    e128 = meta['e128']
    l1 = e128['L1_refVsCard027b']
    ul = e128['ulBonus']
    ul_ok = ul['vsCard027DefenseBonus3dp']['maxAbs'] <= 1e-9 and ul['refBonusEqualsUl'] <= 1e-9
    # pass／help／pressure／presDisplay：先驗卡 x0 對 card 0.2.7b ranking.csv
    card = {}
    for r in csv.DictReader((CARD / 'ranking.csv').open(encoding='utf-8')):
        card[r['name']] = r
    prior = {p['name']: p for p in rj(L.PRIOR_CARD)['players']}
    cols = {}
    ok_cols = True
    for c in ('pass', 'help', 'pressure', 'presDisplay'):
        d = []
        for n, r in card.items():
            if n in prior and prior[n].get(c) is not None and r.get(c) not in (None, ''):
                d.append((abs(float(prior[n][c]) - float(r[c])), n))
        d.sort(reverse=True)
        miss = sum(1 for n in card if n not in prior)
        cols[c] = {'n': len(d), 'maxAbs': d[0][0] if d else None, 'worst': [[n, x] for x, n in d[:3]],
                   'nGt0.05': sum(x > 0.05 + 1e-9 for x, _ in d), 'cardNotInPrior': miss}
        ok_cols = ok_cols and bool(d) and d[0][0] <= 0.05 + 1e-9
    # pass 獨立重現：E-125 a0-pass-P50.json 的 r 經 pool-027b 的 pass 映射
    a0 = rj(E125 / 'a0-pass-P50.json')
    ent = L.M26['attrs']['pass']
    pid2 = {int(p['playerId']): p for p in prior.values()}
    dp = []
    for k, rv in a0['r'].items():
        p = pid2.get(int(k))
        if p is not None:
            dp.append(abs(L.m26_pct_attr(float(rv), ent) - float(p['pass'])))
    cols['passFromA0r_vs_priorX0'] = {'n': len(dp), 'maxAbs': max(dp) if dp else None}
    return {'pass': bool(l1['maxAbs'] <= 0.1 + 1e-9 and anc_diff <= 1e-9 and rr_diff <= 1e-9 and ul_ok and ok_cols
                         and meta['cardMode'] == '027b' and meta['version'] == 'inseason 0.2.7b'),
            'ovr_refVsCard027b': l1, 'anchorsMaxAbsDiff': anc_diff, 'rReplDiff': rr_diff,
            'anchors': meta['e064Anchors'], 'rRepl': meta['e064RRepl'], 'ulBonus': ul, 'columns': cols,
            'evidenceRun': 'out-027b-plain（plain script 的 N=0；包裝 run_c4_live_rookie.py 會改 bonus／ref，故 L1 不用 out-027b）',
            'threshold': 'ref OVR 對 card 0.2.7b ranking ovr 每人 ≤0.1；錨點、r_repl、UL 加成 ≤1e-9；pass／help／pressure／presDisplay ≤0.05'}


def check_h(R):
    """(h)（errata-3）：help 由卡片來源 data/benchmark-source/defense-rim.json 重算，對 card 0.2.7b ranking.csv 的 help 每人 ≤0.05；
    onBall 對 card 逐人吻合（≤0.05，同門檻）。step4-t2 raw 只報告。"""
    card = {r['name']: r for r in csv.DictReader((CARD / 'ranking.csv').open(encoding='utf-8'))}
    prior = {p['name']: p for p in rj(R.PRIOR_CARD)['players']}
    pid = {n: prior[n]['playerId'] for n in prior}
    over99 = ['Isaiah Stewart', 'Chet Holmgren', 'Victor Wembanyama', 'Ryan Kalkbrenner']

    def run(rimpath, tabs=None):
        rim = R.table(rimpath)
        hp = R.help_of(rim)
        dh = [(abs(hp[pid[n]] - float(card[n]['help'])), n) for n in card if n in pid and pid[n] in hp]
        dh.sort(reverse=True)
        o = {'n': len(dh), 'maxAbs': dh[0][0], 'nGt0.05': sum(x > 0.05 + 1e-9 for x, _ in dh),
             'worst': [[n, round(hp[pid[n]], 5), card[n]['help'], prior[n]['help'], round(x, 5)] for x, n in dh[:8]],
             'cardNotInRaw': sorted(n for n in card if n in pid and pid[n] not in hp),
             'over99': {n: [round(hp[pid[n]], 3), card[n]['help']] for n in over99 if n in pid and pid[n] in hp}}
        return o, hp

    res_card, hp = run(R.ROOT / 'data/benchmark-source/defense-rim.json')
    raw = R.ROOT / 'reports/defense-tenth/step4-t2/raw/2025-26'
    tabs = {k: R.table(raw / f'0-{k}.json') for k in R.KINDS}
    res_t2, _ = run(raw / '0-rim.json')
    rr = R.onball_r(tabs, R.frozen_stats())
    sc = R.OnBallScale()
    do_c = sorted(((abs(sc(rr[pid[n]]) - float(card[n]['onBall'])), n) for n in card if n in pid and pid[n] in rr), reverse=True)
    do_p = sorted(((abs(sc(rr[pid[n]]) - float(prior[n]['onBall'])), n) for n in card if n in pid and pid[n] in rr), reverse=True)
    ok = (res_card['maxAbs'] <= 0.05 + 1e-9 and res_card['nGt0.05'] == 0 and do_c[0][0] <= 0.05 + 1e-9
          and len(res_card['over99']) == 4 and all(float(v[1]) > 99 for v in res_card['over99'].values()))
    return {'pass': bool(ok), 'helpVsCard_fromCardSource': res_card,
            'onBallVsCard': {'n': len(do_c), 'maxAbs': do_c[0][0], 'nGt0.05': sum(x > 0.05 + 1e-9 for x, _ in do_c),
                             'worst': [[n, x] for x, n in do_c[:3]]},
            'onBallVsPrior': {'n': len(do_p), 'maxAbs': do_p[0][0]},
            'reportOnly_helpVsCard_fromStep4T2': res_t2,
            'note': '既有來源不一致，027 也有（errata-3）：step4-t2 raw 的 rim 表與卡片來源 data/benchmark-source/defense-rim.json 不同；PAST_RAW 不改',
            'threshold': 'help 每人 ≤0.05（卡片來源 defense-rim.json），含 4 個 >99；onBall 逐人 ≤0.05'}


def check_t(L):
    """(t)：N=0（把 2026-27 逐場檔視為空）的 threeValue 對 card 0.2.7b three-value.csv 的 tv_main，每人 ≤0.05；剛好 99 的 0 人。"""
    rows = list(csv.DictReader((CARD / 'three-value.csv').open(encoding='utf-8')))
    ids = [int(r['playerId']) for r in rows]
    orig = L._gamelog_sums
    p26 = L.DATA26 / 'player-games.json'

    def patched(path):
        return {} if Path(path) == Path(p26) else orig(path)
    L._gamelog_sums = patched
    try:
        cols, info = L.three_value_columns(ids)
    finally:
        L._gamelog_sums = orig
    d, n99, missing = [], 0, []
    for r in rows:
        c = cols[int(r['playerId'])]
        tv = c['threeValue']
        if tv is None:
            missing.append(r['name'])
            continue
        d.append((abs(tv - float(r['tv_main'])), r['name'], tv, float(r['tv_main'])))
        if abs(tv - 99.0) < 1e-9:
            n99 += 1
    d.sort(reverse=True)
    n99_card = sum(abs(float(r['tv_main']) - 99.0) < 1e-9 for r in rows)
    return {'pass': bool(d and d[0][0] <= 0.05 + 1e-9 and n99 == 0 and not missing),
            'n': len(d), 'maxAbs': d[0][0], 'nGt0.05': sum(x[0] > 0.05 + 1e-9 for x in d), 'worst': [list(x) for x in d[:6]],
            'nExactly99': n99, 'nExactly99InCardCsv': n99_card, 'missing': missing, 'info': info,
            'method': '_gamelog_sums 對 2026-27 player-games.json 回空（N=0）；acc 先驗＝csv acc；池＝凍結四季池＋頂端尾巴、底端 40；沒資料 70',
            'threshold': '|threeValue − tv_main| ≤ 0.05；剛好 99 的 0 人'}


def check_s():
    W = {m: rj(HERE / f's-worker-{m}.json') for m in ('025', '027b')}
    upd = W['027b']['updAttrs']
    common = [p for p in W['027b']['players'] if p in W['025']['players']
              and W['027b']['players'][p]['pool'] and W['025']['players'][p]['pool']]
    res, ok = {}, True
    for a in upd:
        row = {}
        for m in ('025', '027b'):
            P = W[m]['players']
            ps = [p for p in common if a in P[p]['y']]
            k = max(1, math.ceil(0.05 * len(ps)))
            top = sorted(ps, key=lambda p: -P[p]['x0'][a])[:k]
            row[m] = {'nAll': len(ps), 'medAll': median([P[p]['y'][a] - P[p]['x0'][a] for p in ps]),
                      'nTop5': len(top), 'medTop5': median([P[p]['y'][a] - P[p]['x0'][a] for p in top]),
                      'top5': [[P[p]['name'], round(P[p]['x0'][a], 2), round(P[p]['y'][a], 2)] for p in top]}
        pa = abs(row['027b']['medAll']) <= abs(row['025']['medAll']) + 2.0
        pt = abs(row['027b']['medTop5']) <= abs(row['025']['medTop5']) + 2.0
        row['passAll'], row['passTop5'] = bool(pa), bool(pt)
        row['judged'] = a != 'stamina'
        if row['judged']:
            ok = ok and pa and pt
        res[a] = row
    return {'pass': bool(ok), 'nCommonPool': len(common), 'attrs': res,
            'definition': ('2025-26 池（整季 GP≥30 且 MPG≥20，兩模式都在池內者）；y＝整季視窗映射值；025＝IC.window_cards＋foul_draw_y，x0＝card 0.2.2；'
                           '027b＝m26_window_cards（pool-027b，pass 量×率、不收縮），x0＝card 0.2.7b 未四捨五入；樣本 < SEASON_MIN_SAMPLE 不計；'
                           '「x0 前 5%」＝各模式依自己的 x0 取前 ceil(5%)；stamina 只報告'),
            'threshold': '|中位差₀₂₇b| ≤ |中位差₀₂₅| + 2.0（全部、x0 前 5% 兩組；stamina 不判）'}


def final():
    L = load_live('027b')
    L.setup()
    sys.path.insert(0, str(LIVE))
    import rookie_defense as R
    keys = ('c0', 'c1', 'u', 'z', 'L1', 'h', 's')   # errata-4：刪除 (t)
    pre = {'c0': check_c0(), 'c1': check_c1(), 'u': check_u(L), 'z': check_z(L), 'L1': check_L1(L), 'h': check_h(R),
           's': check_s()}
    pre['allPass'] = all(pre[k]['pass'] for k in keys)
    pre['failed'] = [k for k in keys if not pre[k]['pass']]
    (HERE / 'prereq.json').write_text(json.dumps(pre, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    for k in keys:
        print(k, 'PASS' if pre[k]['pass'] else 'FAIL')
    print('failed', pre['failed'])
    return 0 if pre['allPass'] else 3


if __name__ == '__main__':
    if sys.argv[1] == 'worker':
        worker(sys.argv[2])
    else:
        raise SystemExit(final())
