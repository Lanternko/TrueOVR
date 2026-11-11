"""E-107 前置條件 (c0)(c1)(u)(z)(L1)(s)（預註冊 §4）。任一不過 → 停，不看 (1)(2)。

用法（repo 根目錄；三步依序跑，各自一個程序、不開子程序）：
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e107-card026/check_prereq.py worker 025
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e107-card026/check_prereq.py worker 026
  python -I -B -X utf8 reports/ovr-inseason-2026-27/e107-card026/check_prereq.py final
worker：以該 CARD_MODE 載入 run_c4_live.py（只呼叫 setup()，不跑 main），算 2025-26 整季視窗值（(s) 用）；
        026 另算 (L1) 診斷（x0 改用 E-101 未四捨五入的能力值時的差，只供解釋，不改判定）。
final：彙整成 prereq.json。
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


# ------------------------------------------------------------------ worker：2025-26 整季視窗值
def worker(mode):
    L = load_live(mode)
    L.setup()
    C, IC, SA = L.C, L.IC, L.SA
    prior_cards = C.load_card(L.PRIOR)[0]
    _, attrs0 = C.deployment('S*')
    sd = IC.load_target_season()          # 2025-26（026：setup 已換 zone_of）
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
    if L.M26_MODE:
        doc['L1diag'] = l1_diag(L, attrs0, prior_cards)
    (HERE / f's-worker-{mode}.json').write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8', newline='\n')
    print(mode, 'players', len(out), 'pool', sum(v['pool'] for v in out.values()))


def l1_diag(L, attrs0, prior_cards):
    """(L1) 不過時的原因診斷（只報告）：x0 取 ranking.csv（1 位小數）vs E-101 attributes-e101.csv（未四捨五入）。"""
    import pointwise_pipeline as PWM
    from ovr_common import ATTRS
    unr = {int(r['playerId']): r for r in csv.DictReader((E101D / 'attributes-e101.csv').open(encoding='utf-8'))}
    a2 = {p: {**a, **{k: float(unr[p][k]) for k in ATTRS if p in unr and k in unr[p]}} for p, a in attrs0.items()}
    usage, ucoef, _ = L.load_usage()
    anc, rr = L.e064_anchors()
    formal = {r['name']: r for r in L.C.load_csv(L.FORMAL_RANKING)}
    res = {}
    for tag, A in (('x0_rankingCsv', attrs0), ('x0_unrounded_attributes_e101', a2)):
        pw = PWM.PointwisePipeline(L.C.pipeline_for('S*'), A)
        ref = L.apply_usage(pw.ref, usage, ucoef)
        d = []
        for pid, e in ref.items():
            if not isinstance(e, dict):
                continue
            nm = prior_cards[pid]['name']
            if nm not in formal:
                continue
            o = L.e064_map((e['pred'] - rr) * L.sat_w(float(formal[nm]['mpg'])), anc)
            d.append((o - float(formal[nm]['ovr']), nm, e['predP']))
        d.sort(key=lambda t: -abs(t[0]))
        res[tag] = {'n': len(d), 'maxAbs': abs(d[0][0]), 'nGt0.1': sum(abs(t[0]) > 0.1 for t in d),
                    'nGt0.05': sum(abs(t[0]) > 0.05 for t in d), 'worst': [[t[1], t[0], t[2]] for t in d[:8]]}
    res['maxAbsAttrRoundingDiff'] = {k: max(abs(a2[p][k] - attrs0[p][k]) for p in attrs0) for k in ATTRS}
    res['note'] = ('最差 5 人的 pred（用人層前）都等於同一個封頂值 T（pointwise_pipeline：bonus+align>0 的人被封在 RAPM 名次更前者的 pred），'
                   'x0 四捨五入讓那位球員的 pred 移動 ~0.019，T 跟著移，5 人一起偏 0.11–0.16 OVR。')
    return res


# ------------------------------------------------------------------ final
def check_c0():
    a, b, pub = HERE / 'out-025', HERE / 'out-025-pre', LIVE / '2026-10-28'
    d = {f: {'after': sha(a / f), 'beforePatch': sha(b / f), 'published': sha(pub / f)} for f in ('ranking.csv', 'no-prior.csv')}
    ma, mp = rj(a / 'meta.json'), rj(pub / 'meta.json')
    ia = {k: v['sha256'] for k, v in ma['inputs'].items()}
    ip = {k: v['sha256'] for k, v in mp['inputs'].items()}
    same = all(len(set(v.values())) == 1 for v in d.values())
    return {'pass': bool(same and ia == ip and ma['dataCutoff'] == mp['dataCutoff'] == '2026-10-28'),
            'files': d, 'inputsSameAsPublished': ia == ip, 'dataCutoff': ma['dataCutoff'],
            'publishedDataSha256': mp.get('dataSha256'),
            'metaKeysOnlyInPublished': sorted(set(mp) - set(ma)),
            'note': 'out-025＝改碼後 CARD_MODE=025；out-025-pre＝改碼前；published＝live/2026-10-28（inseason 0.2.5a）'}


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


def check_u(L):
    top_tail, seg = e101_func('top_tail')
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
    exp_w = {0.0: 0.0, 36.0: 1.0, 5.0: 0.31175, 20.0: 0.80987}
    wd = {str(k): abs(L.sat_w(k) - v) for k, v in exp_w.items()}
    # 只報告：pool-026 的錨點對 E-101 tail-summary（同一套規則、不同資料來源與筆數）
    pool = rj(LIVE / 'pool-026.json')['attrs']
    cmp_ = {a: {'poolN026': pool[a]['anchors']['poolN'], 'poolN_E101': ts[a]['poolN'],
                'r99_026': pool[a]['anchors']['r99'], 'r99_E101': ts[a]['r99'], 'S_026': pool[a]['anchors']['S'],
                'S_E101': ts[a]['S'], 'top026': pool[a]['top'], 'topE101': ts[a].get('topTail'),
                'bot026': pool[a]['bot'], 'botE101': ts[a].get('botTail')}
            for a in pool if a in ts}
    return {'pass': bool(mx < 1e-9 and all(v < 1e-5 for v in wd.values())), 'tailMaxAbsDiff': mx, 'nPoints': len(rows),
            'points': rows, 'W': {str(k): L.sat_w(k) for k in exp_w}, 'WAbsDiff': wd,
            'e101TopTailSource': seg, 'reportOnly_pool026VsE101': cmp_,
            'threshold': '尾巴 |差| < 1e-9；W 同 E-095 check_u（|差| < 1e-5）'}


def check_z(L):
    z26 = rj(HERE / 'zones-026.json')['seasons']['2025-26']
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
            mism.append({'playerId': p, 'midA026': a[0], 'midA_E101': b[0], 'shortA026': a[2], 'shortA_E101': b[2]})
    tot26 = [sum(v[i] for v in z26.values()) for i in range(4)]
    tot101 = [sum(v[i] for v in e101.values()) for i in range(4)]
    # 2026-27 已有場次：shotDistance < 8 卻判 mid（同 IC.load_target_season 的出手篩選）
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
            'mismatchSample': sorted(mism, key=lambda m: -abs(m['midA026'] - m['midA_E101']) - abs(m['shortA026'] - m['shortA_E101']))[:15],
            'totals026': dict(zip(('midA', 'midM', 'shortA', 'shortM'), tot26)),
            'totalsE101': dict(zip(('midA', 'midM', 'shortA', 'shortM'), tot101)),
            'e101Source': 'reports/card-0.2.5+E101-crossera/history/pbp-zones-2025-26.csv.gz（逐場，依 playerId 加總）',
            'season2026_27': {'pbpFiles': len(files), 'twoPtFGA': n_all, 'withArea': n_area, 'noShotDistance': n_nodist,
                              'shotDistLt8': n_lt8, 'shotDistLt8JudgedMid': n_lt8_mid}}


def check_L1():
    meta = rj(HERE / 'out-026/meta.json')
    card = rj(E101D / 'cards/e101/e084/results.json')['card']
    anc = [card['anchors'][k] for k in ('PR1', 'PR50', 'PR99')]
    anc_diff = max(abs(x - y) for x, y in zip(meta['e064Anchors'], anc))
    rr_diff = abs(meta['e064RRepl'] - card['r_repl'])
    l1 = meta['e107']['L1_refVsCard026']
    rows = list(csv.DictReader((HERE / 'out-026/ranking.csv').open(encoding='utf-8')))
    d = sorted(((abs(float(r['lastOVR']) - float(r['formalOVR'])), r['name'], r['lastOVR'], r['formalOVR'])
                for r in rows if r['formalOVR'] != ''), reverse=True)
    diag = rj(HERE / 's-worker-026.json').get('L1diag')
    return {'pass': bool(l1['maxAbs'] <= 0.1 + 1e-9 and d[0][0] <= 0.1 + 1e-9 and anc_diff == 0.0 and rr_diff == 0.0
                         and meta['cardMode'] == '026'),
            'unrounded_allCardPlayers': l1, 'nGt0.1_unrounded': (diag or {}).get('x0_rankingCsv', {}).get('nGt0.1'),
            'E095style_rounded_rankedPlayers': {'n': len(d), 'maxAbs': d[0][0], 'top5': [list(x) for x in d[:5]],
                                                'nGt0.1': sum(x[0] > 0.1 + 1e-9 for x in d)},
            'anchorsMaxAbsDiff': anc_diff, 'rReplDiff': rr_diff, 'anchors': meta['e064Anchors'], 'rRepl': meta['e064RRepl'],
            'diagnosis_reportOnly': diag,
            'threshold': '卡內每人 |ref OVR − card 0.2.6 ovr| ≤ 0.1（未四捨五入全卡 582 人與 E-095 式四捨五入兩種都算）；錨點、r_repl 差 0'}


def check_s():
    W = {m: rj(HERE / f's-worker-{m}.json') for m in ('025', '026')}
    upd = W['026']['updAttrs']
    common = [p for p in W['026']['players'] if p in W['025']['players']
              and W['026']['players'][p]['pool'] and W['025']['players'][p]['pool']]
    res, ok = {}, True
    for a in upd:
        row = {}
        for m in ('025', '026'):
            P = W[m]['players']
            ps = [p for p in common if a in P[p]['y']]
            k = max(1, math.ceil(0.05 * len(ps)))
            top = sorted(ps, key=lambda p: -P[p]['x0'][a])[:k]
            row[m] = {'nAll': len(ps), 'medAll': median([P[p]['y'][a] - P[p]['x0'][a] for p in ps]),
                      'nTop5': len(top), 'medTop5': median([P[p]['y'][a] - P[p]['x0'][a] for p in top]),
                      'top5': [[P[p]['name'], round(P[p]['x0'][a], 2), round(P[p]['y'][a], 2)] for p in top]}
        pa = abs(row['026']['medAll']) <= abs(row['025']['medAll']) + 2.0
        pt = abs(row['026']['medTop5']) <= abs(row['025']['medTop5']) + 2.0
        row['passAll'], row['passTop5'] = bool(pa), bool(pt)
        ok = ok and pa and pt
        res[a] = row
    return {'pass': bool(ok), 'nCommonPool': len(common), 'attrs': res,
            'definition': ('2025-26 池（整季 GP≥30 且 MPG≥20，兩模式都在池內者）；y＝整季視窗映射值（window_cards，用人調整前）；'
                           '025：IC.window_cards（2025-26 單季映射、夾 [40,99]）＋foul_draw_y，x0＝card 0.2.2；'
                           '026：m26_window_cards（pool-026＋尾巴），x0＝card 0.2.6；樣本 < SEASON_MIN_SAMPLE 的不計；'
                           '「x0 前 5%」＝各模式依自己的 x0 取前 ceil(5%)'),
            'threshold': '|中位差₀₂₆| ≤ |中位差₀₂₅| + 2.0（全部、x0 前 5% 兩組）'}


def final():
    L = load_live('026')
    pre = {'c0': check_c0(), 'c1': check_c1(), 'u': check_u(L), 'z': check_z(L), 'L1': check_L1(), 's': check_s()}
    pre['allPass'] = all(pre[k]['pass'] for k in ('c0', 'c1', 'u', 'z', 'L1', 's'))
    pre['failed'] = [k for k in ('c0', 'c1', 'u', 'z', 'L1', 's') if not pre[k]['pass']]
    (HERE / 'prereq.json').write_text(json.dumps(pre, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    for k in ('c0', 'c1', 'u', 'z', 'L1', 's'):
        print(k, 'PASS' if pre[k]['pass'] else 'FAIL')
    print('failed', pre['failed'])
    return 0 if pre['allPass'] else 3


if __name__ == '__main__':
    if sys.argv[1] == 'worker':
        worker(sys.argv[2])
    else:
        raise SystemExit(final())
