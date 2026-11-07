"""P2：v4 卡片 c_2021-22..c_2025-26（preregistration-v4 §6）。

卡 = 凍結 v58 H1-m0 管線（summary 固定）吃 prior-<season> 的全季能力值；
prior_cards 提供 pos／MIN／name／pids。RAPM 集（檔名即可看出最大季，全部 < 目標季）：
  2021-22  rapm-empty.csv（no-rapm）
  2022-23  rapm-2021-22.csv
  2023-24  rapm-2021-22_2022-23.csv
  2024-25  rapm-2021-22_2023-24.csv
  2025-26  data/rapm-2022-25.csv —— 正式卡 card-H1-m0 自己用的那組，讓 c_2025-26 與正式卡逐值對得上
           （§6「S* 的 x0 必須與正式卡對得上」）；S* 部署時的預測 RAPM 另用
           v4/data/rapm-2021-22_2024-25.csv（§5.1），x0 的屬性与這裡相同。

§6 驗收（程式判定）：人數 >=500；ρ_OVR >=0.90；|中位 OVR 差| <=1.0；15 屬性 ρ >=0.90
（pressure 排除）；OVR 範圍只記錄不判定；常數屬性列出。
參考卡：2021-22 用 v4 座標版 season-cards（同源，揭露）、2022-23..2024-25 用
data/season-cards-2022-25、2025-26 用正式卡 card-H1-m0/ranking.csv。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
from ovr_common import ATTRS, DATA, load_json
from ovr_pipeline import OVRPipeline

SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
RAPM_TAG = {
    '2021-22': None,
    '2022-23': '2021-22',
    '2023-24': '2021-22_2022-23',
    '2024-25': '2021-22_2023-24',
    '2025-26': 'formal-2022-25',
}


def rapm_file(season):
    if season == '2021-22':
        return C.V3_DATA / 'rapm-empty.csv'
    if season == '2025-26':
        return DATA / 'rapm-2022-25.csv'
    return C.V3_DATA / f'rapm-{RAPM_TAG[season]}.csv'


def spearman(xs, ys):
    from scipy.stats import spearmanr
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return float(spearmanr(xs, ys).statistic)


def build(season):
    doc = load_json(C.PRIOR_PATH[season])
    by_pid = {int(c['playerId']): c for c in doc['players']}
    rapm = rapm_file(season)
    pipe = OVRPipeline(str(C.V2.FROZEN_SUMMARY), str(rapm), by_pid)
    attrs = {pid: {a: float(c[a]) for a in ATTRS} for pid, c in by_pid.items()}
    pred = pipe.predict(attrs)

    rows = []
    for pid in sorted(by_pid):
        r = pred[pid]
        rows.append({
            'playerId': pid, 'name': by_pid[pid].get('name', ''), 'pos': by_pid[pid]['pos'],
            'ovr': round(r['ovr'], 4), 'pred': round(r['pred'], 6), 'pred0': round(r['pred0'], 6),
            'bonus': round(r['bonus'], 6), 'align': round(r['align'], 6),
            'MIN_prev': round(float(by_pid[pid]['observed']['MIN']), 1),
            'MIN_season': round(float(by_pid[pid]['observed']['MIN']), 1),
            'attrSource': 'season-card',
            **{a: round(attrs[pid][a], 4) for a in ATTRS},
        })
    out_csv = C.V4_CARDS / f'{season}.csv'
    C.write_csv(out_csv, rows)

    if season == '2025-26':
        # 參考＝正式卡發佈的 OVR（同一組 RAPM），直接比
        by_name, _ = C.formal_card_ovr()
        common = sorted(p for p in by_pid if by_pid[p]['name'] in by_name)
        ref_ovr = {p: by_name[by_pid[p]['name']]['ovr'] for p in common}
        pred_ovr = {p: pred[p]['ovr'] for p in common}
        sc_attrs = {p: {a: float(by_pid[p][a]) for a in ATTRS} for p in by_pid}
        rho_attr = {a: 1.0 for a in ATTRS}
        constant = []
        same_source = True
    else:
        sc = C.season_cards_cards(season)
        common = sorted(pid for pid in by_pid if pid in sc)
        sc_attrs = {p: {a: float(sc[p][a]) for a in ATTRS} if p in sc else attrs[p]
                    for p in by_pid}
        sc_pred = pipe.predict(sc_attrs)
        ref_ovr = {p: sc_pred[p]['ovr'] for p in common}
        pred_ovr = {p: pred[p]['ovr'] for p in common}
        rho_attr, constant = {}, []
        for a in ATTRS:
            r = spearman([attrs[p][a] for p in common], [float(sc[p][a]) for p in common])
            if r is None:
                constant.append(a)
            else:
                rho_attr[a] = round(r, 6)
        same_source = season == '2021-22'

    rho_ovr = spearman([pred_ovr[p] for p in common], [ref_ovr[p] for p in common])
    diffs = [pred_ovr[p] - ref_ovr[p] for p in common]
    med_diff = C.write_median = None  # placeholder to keep flake quiet
    import statistics
    med_diff = float(statistics.median(diffs))
    abs_med = abs(med_diff)

    ovrs = [r['ovr'] for r in rows]
    attr_vals = [r[a] for r in rows for a in ATTRS]
    attrs_in_range = bool(min(attr_vals) >= 40 and max(attr_vals) <= 99)
    rho_ex_pressure = {a: v for a, v in rho_attr.items() if a != 'pressure'}
    # 2021-22 的 mid 與 2025-26 全部是「同源」：ρ=1 不是證據（§6）
    rho_judge = {a: v for a, v in rho_ex_pressure.items()
                 if not (same_source and (season != '2021-22' or a == 'mid'))}
    meta = {
        'season': season,
        'file': str(out_csv.relative_to(C.ROOT)),
        'rows': len(rows),
        'playersPass500': len(rows) >= 500,
        'ovrRange': {'min': min(ovrs), 'max': max(ovrs)},
        'ovrRangeNote': '只記錄，不判定（v4 §6 移除 OVR 40–99 門檻）',
        'attrsIn40to99': attrs_in_range,
        'noRapm': season == '2021-22',
        'rapm': {'file': str(rapm.relative_to(C.ROOT)), 'sha256': C.sha256_file(rapm),
                 'note': ('formal card own set (2022-23..2024-25)'
                          if season == '2025-26' else 'max season < target')},
        'prior': {'file': str(C.PRIOR_PATH[season].relative_to(C.ROOT)),
                  'sha256': C.sha256_file(C.PRIOR_PATH[season])},
        'pipelineSummary': {'file': str(C.V2.FROZEN_SUMMARY.relative_to(C.ROOT)),
                            'sha256': C.sha256_file(C.V2.FROZEN_SUMMARY)},
        'reference': ('formal card card-H1-m0/ranking.csv' if season == '2025-26'
                      else f'season-cards-{season} attrs through same pipeline'),
        'sameSource': same_source,
        'rhoAttrVsReference': rho_attr,
        'rhoAttrMin': (min(rho_ex_pressure.values()) if rho_ex_pressure else None),
        'rhoAttrJudgedMin': (min(rho_judge.values()) if rho_judge else None),
        'constantAttrs': constant,
        'rhoOvrVsReference': None if rho_ovr is None else round(rho_ovr, 6),
        'medianOvrDiff': round(med_diff, 6),
        'medianOvrAbsDiff': round(abs_med, 6),
        'checks': {
            'rows>=500': len(rows) >= 500,
            'rhoOvr>=0.90': rho_ovr is not None and rho_ovr >= 0.90,
            'absMedianDiff<=1.0': abs_med <= 1.0,
            'rhoAttrJudged>=0.90': (min(rho_judge.values()) >= 0.90) if rho_judge else True,
        },
    }
    meta['pass'] = bool(all(meta['checks'].values()))
    C.write_json(C.V4_CARDS / f'{season}.json', meta)
    return meta


def main():
    out = {s: build(s) for s in SEASONS}
    C.write_json(C.V4_CARDS / 'build-report.json', out)
    print(__import__('json').dumps(
        {s: {k: v[k] for k in ('rows', 'ovrRange', 'rhoOvrVsReference', 'medianOvrAbsDiff',
                               'rhoAttrJudgedMin', 'constantAttrs', 'sameSource', 'pass')}
         for s, v in out.items()}, ensure_ascii=False, indent=1))
    return 0 if all(v['pass'] for v in out.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
