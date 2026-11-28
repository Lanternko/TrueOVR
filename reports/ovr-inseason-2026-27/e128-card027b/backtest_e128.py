"""E-128 回測（預註冊 preregistration.md §1.8、§2；規則同 e128-card027b/backtest_e128.py，027 讀成 027b；errata-1～4）。

候選 RG1-027b：先驗卡、答案卡、賽中視窗都用 027 的映射（live/pool-027.json 合併池＋E-101 尾巴，run_c4_live.py 的 E-107／E-111 段 exec 共用），
OVR 層＝card 0.2.7 UL6 primary（屬性迴歸 formula＋UL 防守加成，errata-1 的 RAPM 名次同分規則），分鐘權重 W（scale 15）。
基準：(1) RA-027（同尺度先驗卡每場 OVR）；(2) E-095 的 RG1-sat15（e095-card025-minutes/predictions-sat15.csv）。

只 import 既有模組（backtest_e064、backtest_e095、v5/v4 tools），都不改；所有替換在記憶體裡做（同 run_c4_live.setup 的作法）。
c、k、δ²、w、rel 沿用 E-095 的 cache/fit.pkl（唯讀）；人群＝E-095 的人群（先驗季 MIN≥500、目標季 MIN≥500、窗口 MIN≥1、在舊答案卡內）。

各季 027 卡（先驗卡＝答案卡同一張，cards/prior-<季>-027.json）：
  以 v5 pathA 舊卡（v5/pathA/data/prior-<季>.json）為底，9 個合併池屬性（long、mid、short、ft、foulDraw、tovSkill、pass、rebound、creation）
  改成 m26_window_cards(該季整季, n=10^4, 該季單季 mapping, 舊卡, received 預設 0.5) 的值；foulDraw 合成值的 z 用該季自己的池（同 build_pool_027 §1.5）。
  其餘（stamina、drive、physique、onBall、help、heightInches、pressure、sample、observed）照舊卡。偏差見 deviations.json D14–D20。
答案 pred：m27 OVRPipeline(UL6 summary, pipe-<答案窗>.csv, 目標季 027 卡).predict → pred；UL 防守加成的 D 用 defL/def-L-<窗>.csv（fit_defL.py）。
錨點：E-095 sat15 的算法（backtest_e095.anchors_for），池＝card 0.2.7 ranking predictedPer36 × 2025-26 MPG（MIN≥500）。
閘門 bootstrap：照 E-095 gate() 的亂數順序（SEED_GATE，起點 Y1..D3 × N 3,5,10,20,82；沒算的格用 E-095 的人數照樣抽一次以推進亂數）。

用法（repo 根目錄）：python -I -B -X utf8 reports/ovr-inseason-2026-27/e128-card027b/backtest_e128.py
輸出（本資料夾）：results.json、predictions-027b.csv、cards/、backtest-check.json；live-compare.json 另由 --live 產生（不需回測）。
"""
import argparse
import csv
import hashlib
import json
import math
import pickle
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
ROOT = HERE.parents[2]
LIVE = REPORT / 'live'
sys.path.insert(0, str(REPORT / 'v5' / 'tools'))
sys.path.insert(0, str(REPORT / 'e095-card025-minutes'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np  # noqa: E402
import backtest_e064 as B  # noqa: E402
import backtest_pathA as BP  # noqa: E402
import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402
import v2_common as V2  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402
import backtest_e095 as E95  # noqa: E402
from ovr_common import ATTRS  # noqa: E402
from ovr_pipeline import OVRPipeline  # noqa: E402

if 'foulDraw' not in ATTRS:      # 同 run_c4_live：card 0.1.2 之後 16 屬性（drive 之後 foulDraw）
    ATTRS.insert(ATTRS.index('drive') + 1, 'foulDraw')

RUN_LIVE = LIVE / 'run_c4_live.py'
_src = RUN_LIVE.read_text(encoding='utf-8')
BLOCK = _src[_src.index('# ==== E-107 026 BEGIN ===='):_src.index('# ==== E-111 027 END ====')]
NS = {'SA': SA, 'IC': IC, 'math': math, 'json': json}
exec(compile(BLOCK, 'run_c4_live.py#E107+E111(E128)', 'exec'), NS)
m = type('M', (), NS)

E111 = REPORT / 'e111-card027'
E125 = ROOT / 'reports/card-0.2.7+E125-pass-volume'
CARD_SUMMARY = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/cards/e123a/primary/summary.json'
CARD027_RANKING = ROOT / 'reports/card-0.2.7b/ranking.csv'
CARD027_SUMMARY = ROOT / 'reports/card-0.2.7b/summary.json'
USAGE027 = LIVE / 'usage-2025-26-card027b.json'
POOL027 = LIVE / 'pool-027b.json'
PRIOR027 = LIVE / 'prior-2025-26-card027b.json'
E095 = REPORT / 'e095-card025-minutes'
FIT_CACHE = E095 / 'cache' / 'fit.pkl'
SAT15_PRED = E095 / 'predictions-sat15.csv'
DEFL = E111 / 'defL'       # 單季防守 D 檔只依 RAPM 窗與 λ，與卡片版本無關 → 重用 E-111 的（sha 記入 results.json／deviations.json）
CARDS = HERE / 'cards'
POOLED = ['long', 'mid', 'short', 'ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'creation']
MAIN = ['Y5', 'Y6']
SENS = ['Y3']                     # 只報告（E-107 §5 敏感度）；D1–D3 不做（偏差 D20）
RUN_STARTS = SENS + MAIN
N_LIST = BP.N_LIST                # 3, 5, 10, 20, 82
N_GRID = B.N_GRID                 # 3, 5, 10, 20
E095_STARTS = B.STARTS            # Y1..Y6, D1..D3（E-095 gate 的亂數順序）
SETS = {'main': MAIN, 'Y3': ['Y3']}
PLAYERS8 = ['Joel Embiid', 'Kon Knueppel', 'Neemias Queta', 'Ryan Rollins', 'Victor Wembanyama',
            'Giannis Antetokounmpo', 'Luka Dončić', 'Stephen Curry', 'Evan Mobley', 'Ausar Thompson', 'OG Anunoby', 'Trae Young',
            'Franz Wagner']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


# ------------------------------------------------------------------ 027 卡
def season_fz(sd, wvol, wrate):
    """foulDraw 合成值的 z：該季池（GP≥30 且 MPG≥20）FTA/MIN·36 與 FTA/FGA 的平均、母體標準差（同 build_pool_027）。"""
    stats = SA.aggregate(sd)
    pool = [p for p in stats if stats[p]['GP'] >= 30 and stats[p]['MPG'] >= 20]
    vol = [stats[p]['FTA'] / stats[p]['MIN'] * 36.0 for p in pool]
    rate = [stats[p]['FTA'] / stats[p]['FGA'] for p in pool]
    mv, mr = sum(vol) / len(vol), sum(rate) / len(rate)
    return {'vol': {'mean': mv, 'std': math.sqrt(sum((x - mv) ** 2 for x in vol) / len(vol))},
            'rate': {'mean': mr, 'std': math.sqrt(sum((x - mr) ** 2 for x in rate) / len(rate))},
            'wVol': wvol, 'wRate': wrate, 'poolN': len(pool)}


def build_card027(season, fz_w):
    old_path = PA.PA_DATA / f'prior-{season}.json'
    doc = json.loads(old_path.read_text(encoding='utf-8'))
    old = {int(c['playerId']): c for c in doc['players']}
    sd = C.load_target_season(season)
    mapping = C.mapping_for(season)
    fz = season_fz(sd, fz_w['wVol'], fz_w['wRate'])
    saved = M26_FZ = m.M26['foulDrawConstants']
    m.M26['foulDrawConstants'] = {k: fz[k] for k in ('vol', 'rate', 'wVol', 'wRate')}
    try:
        w = m.m26_window_cards(sd, 10 ** 4, mapping, old, {'__default__': 0.5})
    finally:
        m.M26['foulDrawConstants'] = saved
    assert m.M26['foulDrawConstants'] is M26_FZ
    raw = json.loads((E125 / f'pool-P50/raw-{season}.json').read_text(encoding='utf-8'))['attrs']['pass']   # E-125 該季 pass 值（v61_season(s,'c')、各季自己的 zs；errata-1 §4）
    pass_ent = m.M26['attrs']['pass']
    chk = {'players': len(old), 'inWindow': 0, 'passFromE125': 0, 'passNotInRaw': [], 'notInWindow': [], 'foulDrawFallback': [], 'sampleMismatch': 0,
           'staminaMaxAbsDiff': 0.0, 'driveMaxAbsDiff': 0.0, 'shortBaseMaxAbsDiff': 0.0}
    players = []
    for pid in sorted(old):
        c = dict(old[pid])
        rec = w.get(pid)
        if rec is None:          # 整季沒有 box 列（理論上不會）：保留舊卡，foulDraw 用底線
            chk['notInWindow'].append(pid)
            c['foulDraw'] = 40.0
            players.append(c)
            continue
        chk['inWindow'] += 1
        smp, so = rec['sample'], c['sample']
        if any(abs(float(smp[k]) - float(so[k])) > 1e-9 for k in ('fg3a', 'midA', 'shortA', 'fta', 'fga', 'min', 'gp')):
            chk['sampleMismatch'] += 1
        chk['staminaMaxAbsDiff'] = max(chk['staminaMaxAbsDiff'], abs(rec['stamina'] - float(c['stamina'])))
        chk['driveMaxAbsDiff'] = max(chk['driveMaxAbsDiff'], abs(rec['drive'] - float(c['drive'])))
        for a in POOLED:
            v = rec[a]
            if a == 'pass':
                if str(pid) in raw:      # E-125 該季值 → pool-027b 的 pass 映射（含 E-101 尾巴）
                    v = m.m26_pct_attr(float(raw[str(pid)]), pass_ent)
                    chk['passFromE125'] += 1
                else:
                    chk['passNotInRaw'].append(pid)
            if a == 'foulDraw' and v is None:      # FGA=0 或 MIN=0：E-070 合成值無定義 → 40（偏差 D17）
                v = 40.0
                chk['foulDrawFallback'].append(pid)
            c[a] = float(v)
        c['shortBase'] = float(rec['shortBase'])
        players.append(c)
    out = {'schemaVersion': 1, 'season': season, 'experiment': 'E-128',
           'note': 'v5 pathA 舊卡為底；9 個合併池屬性改 027b 映射（pool-027b＋E-101 尾巴，m26_window_cards 整季）；pass 改取 E-125 該季值（pool-P50/raw-<季>.json）再經 pool-027b 映射；foulDraw z 用該季自己的池；onBall、help、pressure 照舊卡（E-111 D15）',
           'base': {'file': rel(old_path), 'sha256': sha(old_path)}, 'pool027PayloadSha256': m.M26['payloadSha256'],
           'foulDrawSeasonZ': fz, 'pooledAttrs': POOLED, 'check': chk, 'players': players}
    CARDS.mkdir(exist_ok=True)
    path = CARDS / f'prior-{season}-027b.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    chk['n_foulDrawFallback'] = len(chk['foulDrawFallback'])
    chk['n_passNotInRaw'] = len(chk['passNotInRaw'])
    return path, chk, fz


# ------------------------------------------------------------------ 錨點
def pool_pairs_027():
    """E-095 pool_pairs 的同一算法，ranking 換成 card 0.2.7（predictedPer36 × 2025-26 observed MIN/GP，MIN≥500）。"""
    rk = rows(CARD027_RANKING)
    cd, _ = F.load_prior('2025-26')
    byname = {}
    for pid, c in cd.items():
        byname.setdefault(c['name'], []).append(pid)
    pool, miss = [], 0
    for r in rk:
        pids = byname.get(r['name'])
        if not pids:
            miss += 1
            continue
        o = cd[pids[0]]['observed']
        if o['MIN'] >= 500:
            pool.append((float(r['predictedPer36']), o['MIN'] / o['GP']))
    return pool, miss


# ------------------------------------------------------------------ 閘門（E-095 gate()，亂數順序照 E-095 全部起點）
def gate(Ec, Eb, starts, n095):
    rng = np.random.default_rng(B.SEED_GATE)
    results, Tb = [], {}
    for s in E095_STARTS:
        for N in N_LIST:
            if (s, N) not in Ec:
                n = n095[(s, N)]
                rng.integers(0, n, size=(BP.BOOT, n))     # 推進亂數（同 BP.boot 的抽法）
                continue
            eA, eC = Eb[(s, N)], Ec[(s, N)]
            mA, mC = BP.metrics(eA), BP.metrics(eC)
            T, b = BP.boot(rng, eA, eC)
            Tb[(s, N)] = T
            results.append({'start': s, 'N': N, 'T': mC['signedMedian'] - mA['signedMedian'],
                            'dMAE': mC['MAE'] - mA['MAE'], 'gt10C': mC['gt10'], 'gt10A': mA['gt10'],
                            'dMAE_hi': b['dMAE_hi'], 'dMAE_lo': b['dMAE_lo'], 'MAE_C': mC['MAE'], 'MAE_A': mA['MAE']})
    out = {'starts': starts, 'V1': {}, 'V2': {}, 'cells': [r for r in results if r['start'] in starts]}
    for N in (3, 5):
        Tbar = np.mean([Tb[(s, N)] for s in starts], axis=0)
        U = float(np.quantile(Tbar, 0.975, method='linear'))
        Ts = {s: next(r['T'] for r in results if r['start'] == s and r['N'] == N) for s in starts}
        out['V1'][N] = {'U_pool': U, 'T_s': Ts, 'pass': bool(U <= 0.50 and all(t <= 0.25 for t in Ts.values()))}
    for N in (10, 20):
        cells = {}
        for s in starts:
            r = next(x for x in results if x['start'] == s and x['N'] == N)
            ok = r['dMAE'] < 0 and r['gt10C'] <= r['gt10A']
            cells[s] = {'dMAE': r['dMAE'], 'gt10C': r['gt10C'], 'gt10A': r['gt10A'], 'ciHi': r['dMAE_hi'], 'pass': bool(ok)}
        out['V2'][N] = {'cells': cells, 'pass': all(c['pass'] for c in cells.values())}
    out['pass'] = bool(all(v['pass'] for v in out['V1'].values()) and all(v['pass'] for v in out['V2'].values()))
    return out


# ------------------------------------------------------------------ 線上頁 027 對 0.2.5a（只報告，§3）
def live_compare():
    a_path, b_path = HERE / 'out-027-post' / 'ranking.csv', HERE / 'out-027b' / 'ranking.csv'
    a = {r['playerId']: r for r in rows(a_path)}
    b = {r['playerId']: r for r in rows(b_path)}
    ids = sorted(set(a) & set(b))
    d = {i: float(b[i]['ovr']) - float(a[i]['ovr']) for i in ids}
    ad = sorted(abs(v) for v in d.values())
    top = lambda t: sorted(t.values(), key=lambda r: int(r['rank']))[:20]  # noqa: E731
    ta, tb = top(a), top(b)
    na, nb = {r['playerId'] for r in ta}, {r['playerId'] for r in tb}

    def ent(i):
        x, y = a.get(i), b.get(i)
        return {'name': (y or x)['name'], 'team': (y or x).get('team'), 'rank027': int(x['rank']) if x else None,
                'ovr027': float(x['ovr']) if x else None, 'rank027b': int(y['rank']) if y else None,
                'ovr027b': float(y['ovr']) if y else None}

    byname = {}
    for i in set(a) | set(b):
        byname.setdefault((b.get(i) or a.get(i))['name'], i)
    p8 = {}
    for nm in PLAYERS8:
        i = byname.get(nm)
        p8[nm] = ent(i) if i else None
    big = sorted(((abs(d[i]), i) for i in ids), reverse=True)
    return {
        'files': {'027': {'file': rel(a_path), 'sha256': sha(a_path)}, '027b': {'file': rel(b_path), 'sha256': sha(b_path)}},
        'n': len(ids), 'onlyIn027': len(set(a) - set(b)), 'onlyIn027b': len(set(b) - set(a)),
        'absDeltaMedian': float(np.median(ad)), 'absDeltaMax': ad[-1], 'gt10': sum(1 for x in ad if x > 10),
        'gt5': sum(1 for x in ad if x > 5), 'medianSigned': float(np.median(list(d.values()))),
        'largestAbsDelta10': [dict(ent(i), delta=round(d[i], 1)) for _, i in big[:10]],
        'top20_027old': [{'rank': int(r['rank']), 'name': r['name'], 'ovr': float(r['ovr'])} for r in ta],
        'top20_027b': [{'rank': int(r['rank']), 'name': r['name'], 'ovr': float(r['ovr'])} for r in tb],
        'enteredTop20': [ent(i) for i in sorted(nb - na, key=lambda i: int(b[i]['rank']))],
        'leftTop20': [ent(i) for i in sorted(na - nb, key=lambda i: int(a[i]['rank']))],
        'players8': p8,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='只產生 live-compare.json')
    args = ap.parse_args()
    if args.live:
        lc = live_compare()
        (HERE / 'live-compare.json').write_text(json.dumps(E95.tojson(lc), ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps(lc['players8'], ensure_ascii=False), flush=True)
        return 0
    t0 = time.time()
    res = {'experiment': 'E-128', 'version': 'inseason 0.2.7b (candidate)', 'inputs': {}}
    for k, p in {'preregistration': HERE / 'preregistration.md', 'errata-1': HERE / 'errata-1.md', 'errata-3': HERE / 'errata-3.md', 'errata-4': HERE / 'errata-4.md', 'passfreeze': HERE / 'passfreeze.json', 'run_c4_live.py': RUN_LIVE,
                 'UL6 summary': CARD_SUMMARY, 'card027 ranking': CARD027_RANKING, 'pool-027': POOL027, 'prior-2025-26-card027': PRIOR027,
                 'usage027': USAGE027, 'E-095 fit.pkl': FIT_CACHE, 'E-095 predictions-sat15.csv': SAT15_PRED,
                 'defL-summary (E-111)': E111 / 'defL-summary.json'}.items():
        res['inputs'][k] = {'file': rel(p), 'sha256': sha(p)}
    pre = json.loads((HERE / 'prereq.json').read_text(encoding='utf-8'))
    res['prereqAllPassFromPrereqJson'] = pre.get('allPass')
    assert pre.get('allPass') is True, '前置未全過，不跑回測'
    assert sha(HERE / 'preregistration.md').startswith('5536050e')
    assert sha(HERE / 'errata-4.md') == 'e5164d07057781f5403acc37389151474a3da26cfc1e32b2f38e73d4236ed292'

    # ---- 安裝（同 run_c4_live.setup 的 027 段）
    PA.install()
    m.m26_load_pool(POOL027)
    SA.zone_of = m.m26_zone_of
    m.m27_install_zone_filter()
    IC.window_cards = m.m26_window_cards
    C.clip = m.m26_clip
    V2.FROZEN_SUMMARY = CARD_SUMMARY
    fz_w = json.loads(PRIOR027.read_text(encoding='utf-8'))['foulDrawFreeze']
    defl = {}
    for s in RUN_STARTS:
        for k in ('pred', 'ans'):
            win = C.CHAIN[s][k]
            defl[str(PA.rapm_path(win).resolve())] = str(DEFL / f'def-L-{win}.csv')
    m.m27_install_ul(defl)
    res['defL'] = {rel(k): {'file': rel(v), 'sha256': sha(v)} for k, v in defl.items()}

    # ---- 027 卡（先驗＝答案同一張）
    seasons = sorted({C.CHAIN[s]['prior'] for s in RUN_STARTS} | {C.CHAIN[s]['target'] for s in RUN_STARTS})
    res['cards'] = {}
    for S in seasons:
        path, chk, fz = build_card027(S, fz_w)
        C.PRIOR_PATH[S] = path
        res['cards'][S] = {'file': rel(path), 'sha256': sha(path), 'check': {k: v for k, v in chk.items() if k not in ('foulDrawFallback', 'passNotInRaw')},
                           'foulDrawSeasonZ': fz}
        print('card', S, chk['inWindow'], chk['sampleMismatch'], round(chk['staminaMaxAbsDiff'], 9),
              round(chk['driveMaxAbsDiff'], 9), len(chk['foulDrawFallback']), f'{time.time() - t0:.0f}s', flush=True)
    F.CACHE.clear()
    C._PIPE_CACHE.clear()
    PW._CACHE.clear()
    for k in [k for k in C._CACHE if k[0] == 'win']:
        del C._CACHE[k]

    # ---- 錨點（E-095 sat15 算法，池換 card 0.2.7）
    pool, miss = pool_pairs_027()
    anc = E95.anchors_for('sat15', pool)
    RREPL = anc['rRepl']
    AR = anc['repl']
    ul = json.loads(USAGE027.read_text(encoding='utf-8'))
    res['anchors'] = {'poolN': len(pool), 'unmatchedNames': miss, 'sat15': anc,
                      'rule': 'E-095 anchors_for(sat15)：r_repl＝池 predictedPer36 第 10 百分位；repl 錨點＝W(m)·(pred−r_repl) 的 PR1/50/99',
                      'usage027ForReference': {k: ul.get(k) for k in ('anchors', 'rRepl', 'r_repl') if k in ul}}
    print('anchors', anc, f'{time.time() - t0:.0f}s', flush=True)

    # ---- 每格
    rel_ = V2.load_reliability()
    sel = json.load(open(B.E033 / 'fit.json', encoding='utf-8'))['selection']
    cfix = {s: float(sel[s]['c']) for s in E095_STARTS}
    fit = pickle.load(open(FIT_CACHE, 'rb'))
    base = {}
    for r in rows(SAT15_PRED):
        base[(r['start'], int(r['N']), int(r['playerId']))] = float(r['RG1']) - float(r['targetRepl'])
    n095 = {}
    for (s, N, _p) in base:
        n095[(s, N)] = n095.get((s, N), 0) + 1
    cells, ans_info = {}, {}
    for s in RUN_STARTS:
        prior, target = C.CHAIN[s]['prior'], C.CHAIN[s]['target']
        pw = PW.for_start(C, s)
        tcards, _ = C.load_card(target)
        tpipe = OVRPipeline(str(CARD_SUMMARY), str(PA.rapm_path(C.CHAIN[s]['ans'])), tcards)
        tp = tpipe.predict({pid: {a: float(c[a]) for a in ATTRS} for pid, c in tcards.items()})
        ap_ = {pid: tp[pid]['pred'] for pid in tcards}
        ans_info[s] = {'rapm': rel(PA.rapm_path(C.CHAIN[s]['ans'])), 'players': len(ap_), 'capIterations': tp['_capIterations'],
                       'pwCheck': pw.check, 'predRapm': rel(PA.rapm_path(C.CHAIN[s]['pred']))}
        mpg0, mpgT = B.season_mpg(prior), B.season_mpg(target)
        tg36 = PA.target_ovr(s)
        for N in N_LIST:
            B.POPS.setdefault(s, {})[N] = [p for p in C.population(prior, N) if p in tg36]
        for N in N_LIST:
            P = B.POPS[s][N]
            assert not [p for p in P if p not in ap_ or p not in mpgT], (s, N)
            assert len(P) == n095[(s, N)] and all((s, N, p) in base for p in P), ('人群與 E-095 不同', s, N)
            win, _ = F.windows_of(prior, N)
            g1, w1 = B.c4_run(s, N, fit, rel_, cfix[s], 1)
            pr = pw.predict(g1)
            hat = B.mpg_hat(mpg0, win, w1, P, True)
            cells[(s, N)] = {'P': P, 'ap': {p: ap_[p] for p in P}, 'mpgT': {p: mpgT[p] for p in P},
                             'mpg0': {p: mpg0.get(p, 0.0) for p in P}, 'hat': hat,
                             'pred': {p: pr[p]['pred'] for p in P}, 'ref': {p: pw.ref[p]['pred'] for p in P}}
            print('cell', s, N, len(P), f'{time.time() - t0:.0f}s', flush=True)
    res['answer'] = ans_info

    # ---- 評估
    gv = lambda d, mm: E95.gval('sat15', d, mm)  # noqa: E731
    E = {'RG1': {}, 'RA': {}, 'BASE': {}}
    pred_rows = []
    for (s, N), c in cells.items():
        P = c['P']
        tgR = {p: B.map_g(gv(c['ap'][p] - RREPL, c['mpgT'][p]), AR) for p in P}
        rg1 = {p: B.map_g(gv(c['pred'][p] - RREPL, c['hat'][p]), AR) for p in P}
        ra = {p: B.map_g(gv(c['ref'][p] - RREPL, c['mpg0'][p]), AR) for p in P}
        E['RG1'][(s, N)] = np.array([rg1[p] - tgR[p] for p in P])
        E['RA'][(s, N)] = np.array([ra[p] - tgR[p] for p in P])
        E['BASE'][(s, N)] = np.array([base[(s, N, p)] for p in P])
        for p in P:
            pred_rows.append({'start': s, 'N': N, 'playerId': p, 'targetRepl027b': round(tgR[p], 4), 'RA027b': round(ra[p], 4),
                              'RG1_027b': round(rg1[p], 4), 'errRG1_027b': round(rg1[p] - tgR[p], 4),
                              'errRG1_sat15': round(base[(s, N, p)], 4), 'predAns': round(c['ap'][p], 6),
                              'predG1': round(c['pred'][p], 6), 'predRef': round(c['ref'][p], 6),
                              'mpg0': round(c['mpg0'][p], 3), 'mpgHatG1': round(c['hat'][p], 3), 'mpgTarget': round(c['mpgT'][p], 3)})
    with open(HERE / 'predictions-027b.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(pred_rows[0].keys()))
        wr.writeheader()
        wr.writerows(pred_rows)

    # ---- (1) 閘門：RG1-027b 對 027 答案卡，基準 RA-027
    res['gates'] = {nm: gate(E['RG1'], E['RA'], ss, n095) for nm, ss in SETS.items()}

    # ---- (2) 8 格 MAE 差（對 E-095 RG1-sat15）
    def cmp_cells(ss):
        out = {}
        for s in ss:
            for N in N_GRID:
                k = (s, N)
                m27, m15 = float(np.abs(E['RG1'][k]).mean()), float(np.abs(E['BASE'][k]).mean())
                out[f'{s}/N{N}'] = {'n': len(cells[k]['P']), 'MAE_027': m27, 'MAE_sat15': m15, 'diff': m27 - m15,
                                    'pass': bool(m27 - m15 <= 0.05), 'signed_027': float(E['RG1'][k].mean()),
                                    'signed_sat15': float(E['BASE'][k].mean()), 'gt10_027': int(np.sum(np.abs(E['RG1'][k]) > 10)),
                                    'gt10_sat15': int(np.sum(np.abs(E['BASE'][k]) > 10))}
        cl = [(s, N) for s in ss for N in N_GRID]
        return {'cells': out, 'maxDiff': max(v['diff'] for v in out.values()), 'pass2': all(v['pass'] for v in out.values()),
                'boot90': B.paired_boot(E['RG1'], E['BASE'], cl)}
    res['cmp2'] = {nm: cmp_cells(ss) for nm, ss in SETS.items()}
    g1 = res['gates']['main']['pass']
    g2 = res['cmp2']['main']['pass2']
    res['verdict'] = {'1': g1, '2': g2,
                      'outcome': '(1)(2) 都過' if g1 and g2 else '(1) 過、(2) 不過' if g1 else '(1) 不過',
                      'rule': 'E-107 §4：(1)(2) 都過→交 role-audit 與使用者 G5；(1) 過 (2) 不過→交使用者選；(1) 不過→不採用'}

    # ---- 只報告：MPG0 三分位（N=5、10）、x0 > 99 者的平均 e
    ter = []
    for s in MAIN:
        for N in (5, 10):
            c = cells[(s, N)]
            m0 = np.array([c['mpg0'][p] for p in c['P']])
            lo, hi = np.quantile(m0, [1 / 3, 2 / 3])
            for g, mask in (('low', m0 <= lo), ('mid', (m0 > lo) & (m0 <= hi)), ('high', m0 > hi)):
                row = {'start': s, 'N': N, 'group': g, 'n': int(mask.sum()), 'mpg0_lo': float(m0[mask].min()),
                       'mpg0_hi': float(m0[mask].max())}
                for k, nm in (('RG1', '027'), ('BASE', 'sat15')):
                    e = E[k][(s, N)][mask]
                    row[f'signed_{nm}'] = float(e.mean())
                    row[f'MAE_{nm}'] = float(np.abs(e).mean())
                ter.append(row)
    res['tertile'] = ter
    top = {}
    for s in MAIN:
        pc, _ = C.load_card(C.CHAIN[s]['prior'])
        for N in (5, 10, 20):
            c = cells[(s, N)]
            idx = [i for i, p in enumerate(c['P']) if any(float(pc[p][a]) > 99 for a in POOLED)]
            top[f'{s}/N{N}'] = {'n': len(idx), 'meanE_027': float(E['RG1'][(s, N)][idx].mean()) if idx else None,
                                'meanE_sat15': float(E['BASE'][(s, N)][idx].mean()) if idx else None}
    res['x0Above99'] = top
    res['elapsedSec'] = round(time.time() - t0, 1)
    (HERE / 'results.json').write_text(json.dumps(E95.tojson(res), ensure_ascii=False, indent=1), encoding='utf-8')
    print('verdict', res['verdict'], f'{time.time() - t0:.0f}s', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
