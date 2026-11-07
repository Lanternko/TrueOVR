"""C4：單調收縮（preregistration-v5-errata-c4 §2）與等價檢定（§6 第 1 步）。

  n = IC.sample_of(rec, a)
  k = c · k_eff(δ²_a, σ²_a, n^p, nRef_a)
  b = n / (n + k)
  f = min(N / G, 1)          G = 該隊該季例行賽場數（2019-20 用各隊實際場數、2020-21=72）
  w = f + (1 − f) · b
  x̂ = clip(x0 + w · (y_adj − x0))
低於 SEASON_MIN_SAMPLE、沒有先驗卡、沒有視窗紀錄 → x0；δ² 未定義、pressure 凍結 → x0（同 C2 慣例）。

等價檢定（任一失敗即停止）：
  T1 f=0、k=50·nRef（k_eff 上界）：C4 與 A 逐球員 OVR 差 <0.5（N=3/5/10/20 判定，N=82 只記錄）
     OVR 用逐點管線（pointwise_pipeline，揭露見 v5/pathA/disclosure-pointwise-ovr.md）；
     原名次耦合管線的差另記 legacyMaxAbsOvrDiff。
  T2 f=0、c=1：C4 ≡ fit_w_grid_v4.c2_predict（逐球員逐屬性差 <1e-9）
  T3 f=1：可更新項 ≡ fit_w_grid_v4.raw_predict（逐球員逐屬性差 <1e-9；δ² 未定義/凍結的項除外，另列）
輸出 v5/pathA/backtest/c4-equiv.json。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pathA_common as PA  # noqa: E402
from pathA_common import base as C, SA  # noqa: E402
import fit_w_grid_v4 as F  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402
import v2_common as V2  # noqa: E402
import pointwise_pipeline as PW  # noqa: E402

C_GRID = [0.25, 0.35, 0.5, 0.7, 1, 1.4, 2, 2.8, 4]
_TEAM = {}


def first_team(season):
    """球員目標季第一場的球隊（2019-20 的 G 依此取該隊實際場數）。"""
    if season not in _TEAM:
        sd = C.load_target_season(season)
        out = {}
        for pid, b in sd['box'].items():
            rows = sorted(b['rows'], key=lambda r: (r['GAME_DATE'], r['GAME_ID']))
            if rows:
                out[pid] = rows[0]['TEAM_ID']
        _TEAM[season] = out
    return _TEAM[season]


def G_of(start, pid):
    target = C.CHAIN[start]['target']
    if target == '2019-20':
        team = first_team(target).get(pid)
        cnt = PA.games_per_team(target)
        return float(cnt.get(team, 82)) if team is not None else 82.0
    return float(PA.G_SEASON[target])


def c4_predict(start, N, delta2, rel, c, undefined=(), frozen=(), f_force=None,
               k_max=False, diag=None):
    prior = C.CHAIN[start]['prior']
    prior_cards, _ = F.load_prior(prior)
    _, attrs0 = C.deployment(start)
    w, _ = F.windows_of(prior, N)
    usg = C.usg_prior(prior)
    out = {}
    for pid, x0 in attrs0.items():
        rec = w.get(pid)
        pc = prior_cards.get(pid)
        f = f_force if f_force is not None else min(N / G_of(start, pid), 1.0)
        vals = {}
        for a in C.UPD:
            if pc is None or a in undefined or a in frozen:
                vals[a] = x0[a]
                continue
            if rec is None or IC.sample_of(rec, a) < SA.SEASON_MIN_SAMPLE[a]:
                vals[a] = x0[a]
                continue
            y = F.y_adj_of(pc, rec, a, usg.get(pid, 0.0))
            n = IC.sample_of(rec, a)
            if k_max:
                k = 50.0 * rel[a]['nRef']
            else:
                k = c * V2.k_eff(delta2[a], rel[a]['sigma2'], V2.sample_n(pc, a), rel[a]['nRef'])
            b = n / (n + k)
            wt = f + (1.0 - f) * b
            vals[a] = C.clip(x0[a] + wt * (y - x0[a]))
            if diag is not None:
                diag.append({'pid': pid, 'attr': a, 'n': n, 'k': k, 'b': b, 'f': f, 'w': wt})
        out[pid] = {**x0, **vals}
    return out


def delta2_info(start):
    """δ² 由 E(s) 的配對估（errata §3：照 C2 的 drift 估法，只用嚴格更早的起點）。"""
    d = F.delta2_from_pairs(start)
    undefined = sorted(a for a, v in d.items() if not v['defined'])
    return {a: v['delta2'] for a, v in d.items()}, undefined, d


def equivalence(starts, n_list=(3, 5, 10, 20, 82), pressure_frozen=None):
    rel = V2.load_reliability()
    rep = {'T1': [], 'T2': [], 'T3': []}
    for s in starts:
        delta2, undefined, _ = delta2_info(s)
        frozen = ['pressure'] if (pressure_frozen or {}).get(s, True) else []
        pipe = C.pipeline_for(s)
        pw = PW.for_start(C, s)
        cards, x0 = C.deployment(s)
        ovrA = pw.ref
        for N in n_list:
            a1 = c4_predict(s, N, delta2, rel, 1.0, undefined, frozen, f_force=0.0, k_max=True)
            o1 = pw.predict(a1)
            d1 = max(abs(o1[p]['ovr'] - ovrA[p]['ovr']) for p in x0)
            ol = pipe.predict(a1)
            dl = max(abs(ol[p]['ovr'] - ovrA[p]['ovr']) for p in x0)
            rep['T1'].append({'start': s, 'N': N, 'maxAbsOvrDiff': d1, 'gate': N != 82,
                              'pass': d1 < 0.5, 'legacyMaxAbsOvrDiff': dl})
            a2 = c4_predict(s, N, delta2, rel, 1.0, undefined, frozen, f_force=0.0)
            r2 = F.c2_predict(s, N, delta2, rel, undefined=undefined, frozen=frozen)
            d2 = max(abs(a2[p][a] - r2[p][a]) for p in x0 for a in C.UPD)
            rep['T2'].append({'start': s, 'N': N, 'maxAbsAttrDiff': d2, 'pass': d2 < 1e-9})
            a3 = c4_predict(s, N, delta2, rel, 1.0, undefined, frozen, f_force=1.0)
            r3 = F.raw_predict(s, N)
            skip = set(undefined) | set(frozen)
            d3 = max((abs(a3[p][a] - r3[p][a]) for p in x0 for a in C.UPD
                      if a not in skip and p in cards), default=0.0)
            rep['T3'].append({'start': s, 'N': N, 'maxAbsAttrDiff': d3, 'excluded': sorted(skip),
                              'pass': d3 < 1e-9})
        print(s, 'T1', [round(r['maxAbsOvrDiff'], 4) for r in rep['T1'] if r['start'] == s],
              'T2', max(r['maxAbsAttrDiff'] for r in rep['T2'] if r['start'] == s),
              'T3', max(r['maxAbsAttrDiff'] for r in rep['T3'] if r['start'] == s), flush=True)
    rep['pass'] = bool(all(r['pass'] for r in rep['T1'] if r['gate'])
                       and all(r['pass'] for r in rep['T2'])
                       and all(r['pass'] for r in rep['T3']))
    rep['T1_N82_info'] = [r for r in rep['T1'] if not r['gate']]
    return rep


def main():
    PA.install()
    PA.PA_BACKTEST.mkdir(parents=True, exist_ok=True)
    starts = sys.argv[1:] or [s for s in PA.BUILT]
    rep = equivalence(starts)
    rep['spec'] = 'errata-c4 §6 step 1 + disclosure-pointwise-ovr'
    C.write_json(PA.PA_BACKTEST / 'c4-equiv.json', rep)
    print(json.dumps({'pass': rep['pass'],
                      'T1_N82': [(r['start'], round(r['maxAbsOvrDiff'], 4)) for r in rep['T1_N82_info']]},
                     ensure_ascii=False))
    return 0 if rep['pass'] else 4


if __name__ == '__main__':
    raise SystemExit(main())
