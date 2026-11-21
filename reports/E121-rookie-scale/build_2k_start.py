"""E-121 路線 D 簡化版（R-073）：新秀開季起點＝2K 同順位新秀評分曲線換成本站尺度，再齊頭扣 SHIFT。
R-096（2026-10-31）起，目標改為使用者指定的 T(順位) = CURVE_A − CURVE_B·ln 順位（狀元 73、第 60 順位約 48.8，
「略為高估、靠賽中數據往下修」），不再用 2K 曲線 − SHIFT；2K 曲線值仍算出來記在 e121.twoK 供對照。

舊起點 OVR 目標（R-073）：T(順位) = Q(a + b·ln 順位) − SHIFT
  a、b：reports/rookie-growth/twok-by-pick.json 的 fitRecent3（2023–25 三屆 2K 新秀評分，落選不納入擬合；落選＝第 61 順位照代入）
  Q：2K26 → card 0.2.7 OVR 的分位數對應（同季 572 人；經驗分布中點分位、線性內插），只用老將和 2K 的關係
能力值：保留 E-116 的順位／位置形狀，15 項一起平移 δ（夾 [0,150]），二分法解 δ 使「沒有數據時的 OVR」= T。k、mpg0 不變。

輸出：
  live/rookie-prior-2026.json（覆寫；原 E-116 版先備份成 rookie-prior-2026-e116.json，已有備份就從備份讀）
  reports/E121-rookie-scale/start.csv           2026 新秀的 2K 曲線值、目標、δ、E-116 起點
  reports/E121-rookie-scale/backtest-results.json  2025 屆只報告（看過答案，R-007，不判定）
用法：python -I -X utf8 build_2k_start.py
"""
import bisect
import csv
import json
import math
import statistics
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
E116 = ROOT / 'reports/E116-rookie-prior'
sys.path.insert(0, str(LIVE))
import build_rookie_prior as BR            # noqa: E402
import run_c4_live_rookie as RW            # noqa: E402

SHIFT = 5.0                                # R-073「稍微齊頭式拉低」（R-096 起不用）
CURVE_A, CURVE_B = 73.0, 5.9               # R-096：T(順位) = 73 − 5.9·ln 順位
LO, HI = 0.0, 150.0
NS = (5, 10, 20)


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower() if c.isalnum())


def make_q():
    card = {norm(r['name']): float(r['ovr'])
            for r in csv.DictReader(open(ROOT / 'reports/card-0.2.7/ranking.csv', encoding='utf-8-sig'))}
    pairs = [(int(r['2K26']), card[norm(r['name'])])
             for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv', encoding='utf-8'))
             if r['2K26'] and norm(r['name']) in card]
    xs, ys = sorted(p[0] for p in pairs), sorted(p[1] for p in pairs)
    n = len(xs)

    def cdf(v):                             # 整數 2K 值的中點分位
        lo, hi = bisect.bisect_left(xs, v), bisect.bisect_right(xs, v)
        return (lo + hi) / 2 / n

    def q(v):
        f = math.floor(v)
        p = cdf(f) + (v - f) * (cdf(f + 1) - cdf(f))
        i = p * (n - 1)
        j = min(int(i), n - 2)
        return ys[j] + (i - j) * (ys[j + 1] - ys[j])
    return q, n


def shifted(x0, d):
    return {a: min(max(v + d, LO), HI) for a, v in x0.items()}


def solve(ns, pw, anc, r_repl, rel, rk, target):
    def ovr(d):
        return RW.eval_rookie(ns, pw, anc, r_repl, dict(rk, x0=shifted(rk['x0'], d)), None, 'e116', rel)['ovr']
    lo, hi = -80.0, 80.0
    assert ovr(lo) < target < ovr(hi), (rk['name'], target)
    for _ in range(60):
        mid = (lo + hi) / 2
        if ovr(mid) < target:
            lo = mid
        else:
            hi = mid
    d = (lo + hi) / 2
    return d, ovr(d)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    fit2k = json.load(open(ROOT / 'reports/rookie-growth/twok-by-pick.json', encoding='utf-8'))['fitRecent3']
    q, nq = make_q()

    def target(pick):
        v = fit2k['a'] + fit2k['b_lnPick'] * math.log(pick)
        return v, CURVE_A - CURVE_B * math.log(pick)

    ns = RW.load_ns()
    C, F, IC, SA, V2 = ns['C'], ns['F'], ns['IC'], ns['SA'], ns['V2']
    sd26, mp = ns['setup']()
    rel = V2.load_reliability()
    pw = ns['PW'].for_start(C, 'S*')
    anc, r_repl = ns['e064_anchors']()

    # ---- 2026 新秀
    bak = LIVE / 'rookie-prior-2026-e116.json'
    if not bak.exists():
        bak.write_text((LIVE / 'rookie-prior-2026.json').read_text(encoding='utf-8'), encoding='utf-8')
    doc = json.load(open(bak, encoding='utf-8'))
    rows = []
    for rk in doc['players']:
        v2k, t = target(rk['pick'])
        base = RW.eval_rookie(ns, pw, anc, r_repl, rk, None, 'e116', rel)['ovr']
        d, got = solve(ns, pw, anc, r_repl, rel, rk, t)
        rk['x0'] = shifted(rk['x0'], d)
        rk['e121'] = {'twoK': round(v2k, 2), 'target': round(t, 2), 'delta': round(d, 3), 'ovrE116': round(base, 2)}
        rows.append({'name': rk['name'], 'pick': rk['pick'], 'pos': rk['pos'], 'twoK': round(v2k, 1),
                     'startE121': round(got, 1), 'startE116': round(base, 1), 'delta': round(d, 2)})
    doc.update({'experiment': 'E-121', 'shift': None, 'targetCurve': {'a': CURVE_A, 'b_lnPick': -CURVE_B, 'ruling': 'R-096'},
                'twoKFit': fit2k, 'quantilePairs': nq,
                'note': doc.get('note', '') + '；R-096：x0 齊頭平移到 73 − 5.9·ln 順位，形狀沿用 E-116'})
    json.dump(doc, open(LIVE / 'rookie-prior-2026.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(HERE / 'start.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # ---- 2025 屆只報告（同 E-116 backtest 人群）
    fit = json.load(open(E116 / 'fit.json', encoding='utf-8'))
    PRIOR = ns['PRIOR']
    sd25 = IC.load_target_season()
    bio25 = {int(r['PLAYER_ID']): r for r in SA.result_set(ns['BIO25'])}
    dep25 = {int(r['playerId']): r for s in ns['load_json'](IC.DEPENDENCE)['seasons']
             if s['season'] == PRIOR for r in s['rows']}
    box = {p: b for p, b in sd25['box'].items() if p in bio25}
    sdm = {'season': PRIOR, 'box': box, 'bio': bio25, 'dep': dep25, 'ff': {}, 'v3': {}, 'fed': {},
           'shots': sd25['shots'], 'teamRows': sd25['teamRows']}
    try:
        mapping = C.mapping_for('2024-25')
        assert mapping['priors']
    except Exception:
        mapping = mp['mapping']
    key = {}
    for r in C.load_csv(ns['FORMAL_RANKING']):
        key.setdefault(r['name'], r)
    prior_ids = set(F.load_prior(PRIOR)[0])
    pop = []
    for pid, b in sorted(bio25.items()):
        if str(b.get('DRAFT_YEAR')) != '2025' or pid not in prior_ids or b['PLAYER_NAME'] not in key:
            continue
        bx = box.get(pid)
        if not bx or sum(r['MIN'] for r in bx['rows']) < 500:
            continue
        pick = BR.pick_of(b)
        h = float(b['PLAYER_HEIGHT_INCHES'])
        pos = BR.height_pos(h)
        x = BR.design(pick, pos)
        x0, k = {}, {}
        for a in BR.ABIL:
            fa = fit['abilities'][a]
            x0[a] = min(max(fa['b0'] + fa['b1_lnPick'] * x[1] + fa['gF'] * x[2] + fa['gC'] * x[3], LO), HI)
            if fa['k'] is not None:
                k[a] = fa['k']
        rk = {'playerId': pid, 'name': b['PLAYER_NAME'], 'pick': pick, 'pos': pos, 'heightInches': h,
              'mpg0': fit['medians']['mpg0'], 'usg0': 0.0, 'x0': x0, 'k': k, 'ans': float(key[b['PLAYER_NAME']]['ovr'])}
        d, _ = solve(ns, pw, anc, r_repl, rel, rk, target(pick)[1])
        pop.append((rk, dict(rk, x0=shifted(x0, d))))
    res = {'targetCurve': [CURVE_A, -CURVE_B], 'nPlayers': len(pop), 'note': '看過答案的回看（R-007），只報告不判定；判定看 §3.4 前瞻檢查', 'mae': {}}
    for tag, idx in (('E116', 0), ('E121', 1)):
        st = [abs(RW.eval_rookie(ns, pw, anc, r_repl, p[idx], None, 'e116', rel)['ovr'] - p[0]['ans']) for p in pop]
        res['mae'].setdefault('start', {})[tag] = round(statistics.fmean(st), 2)
    for n in NS:
        wins = RW.rookie_windows(ns, sdm, mapping, [p[0] for p in pop], n)
        for tag, idx in (('E116', 0), ('E121', 1)):
            e = [abs(RW.eval_rookie(ns, pw, anc, r_repl, p[idx], wins.get(p[0]['playerId']), 'e116', rel)['ovr'] - p[0]['ans'])
                 for p in pop]
            res['mae'].setdefault(f'N{n}', {})[tag] = round(statistics.fmean(e), 2)
    json.dump(res, open(HERE / 'backtest-results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))
    for r in rows[:15]:
        print(r)


if __name__ == '__main__':
    main()
