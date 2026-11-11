"""P0：2021-22 可行性 + 座標分區規則驗證（preregistration-v4 §3.3、§3.4、§3.5）。

掃原始 pbp（只讀）：
  1. 2022-23 全季：座標規則 vs 官方 area 的一致率、哨兵佔比、mid 佔比。
  2. 2021-22 全季：2pt 數、哨兵佔比、規則 mid 佔比。
門檻（§3.3 寫死）：非哨兵一致率 >=0.98、全體一致率 >=0.95、哨兵佔比 <=5.0%；
sanity gate（§3.4）：|midShare_rule(2021-22) − midShare_rule(2022-23)| <= 3.0pp。
§3.5 的 short/creation 三項 (i)(ii)(iii) 布林值一併輸出。
輸出 v4/data/feasibility-2021-22-v4.json。
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import season_attrs_v4 as SA
from ovr_common import load_json

OUT = C.V4_DATA / 'feasibility-2021-22-v4.json'
# prepare-origin.mjs 對 descriptor / assistPersonId 是 null-safe（`?? ''`、`?1:0`），
# 所以只有這 5 個是必要欄位；另兩個只記錄覆蓋率。
SHORT_REQUIRED = ['actionType', 'xLegacy', 'yLegacy', 'subType', 'shotResult']
SHORT_OPTIONAL = ['descriptor', 'assistPersonId']
SHORT_FIELDS = SHORT_REQUIRED + SHORT_OPTIONAL


def coord_zone(x, y):
    if x == 0 and y == 0:
        return 'short'
    return 'short' if (abs(x) <= 80 and y <= 138) else 'mid'


def scan(season, count_fields=False):
    P = SA.season_paths(season)
    n2 = sentinel = 0
    agree_sent = agree_non = 0
    n_non = 0
    mid_rule = mid_off = 0
    field_present = Counter()
    bad = []
    for path in sorted(P['pbp'].glob('*.json')):
        try:
            actions = load_json(path)['data']['game']['actions']
        except Exception as exc:
            bad.append({'file': path.name, 'error': str(exc)})
            continue
        for a in actions:
            if count_fields and a.get('isFieldGoal') == 1:
                for k in SHORT_FIELDS:
                    if a.get(k) is not None:
                        field_present[k] += 1
            if a.get('isFieldGoal') != 1:
                continue
            if a.get('shotResult') not in ('Made', 'Missed') or a.get('actionType') != '2pt':
                continue
            x, y = a.get('xLegacy'), a.get('yLegacy')
            n2 += 1
            z = coord_zone(x, y)
            if z == 'mid':
                mid_rule += 1
            area = a.get('area')
            if area:
                off = 'mid' if area == 'Mid-Range' else 'short'
                if off == 'mid':
                    mid_off += 1
                if x == 0 and y == 0:
                    sentinel += 1
                    agree_sent += int(z == off)
                else:
                    n_non += 1
                    agree_non += int(z == off)
            else:
                if x == 0 and y == 0:
                    sentinel += 1
    out = {'season': season, 'twoPointers': n2, 'sentinel': sentinel,
           'sentinelShare': round(sentinel / n2, 6) if n2 else None,
           'midShare_rule': round(mid_rule / n2, 6) if n2 else None,
           'midShare_official': (round(mid_off / n2, 6) if mid_off else None),
           'agree_nonSentinel': round(agree_non / n_non, 6) if n_non else None,
           'n_nonSentinel': n_non,
           'agree_overall': round((agree_non + agree_sent) / (n_non + sentinel), 6)
           if (n_non + sentinel) else None,
           'games': len(sorted(P['pbp'].glob('*.json'))), 'badFiles': bad}
    if count_fields:
        out['fieldCoverage'] = {k: field_present[k] for k in SHORT_FIELDS}
        out['fieldGoalActions'] = max(field_present.values()) if field_present else 0
    return out


def main():
    s22 = scan('2022-23')
    s21 = scan('2021-22', count_fields=True)

    gates = {
        'agreeNonSentinel>=0.98': s22['agree_nonSentinel'] >= 0.98,
        'agreeOverall>=0.95': s22['agree_overall'] >= 0.95,
        'sentinel<=5.0%': s21['sentinelShare'] <= 0.05,
    }
    mid_share_pp = abs(s21['midShare_rule'] - s22['midShare_rule']) * 100.0
    gates['midShareDiff<=3.0pp'] = mid_share_pp <= 3.0

    # ---- §3.5 short(sTilde) / creation(dependence) 的 (i)(ii)(iii)
    fg = s21['fieldGoalActions'] or 1
    cov = {k: s21['fieldCoverage'][k] / fg for k in SHORT_FIELDS}
    short_i = all(cov[k] >= 0.99 for k in SHORT_REQUIRED)
    dep = load_json(C.ROOT / 'reports/player-impact-v30/dependence-audit.json')
    dep_seasons = sorted(s['season'] for s in dep['seasons'])
    tracking = C.ROOT / 'data/defense-seventh/2021-22/tracking/manifest.json'
    short = {
        'i_fieldsComplete': bool(short_i),
        'i_evidence': {'coverageOverFieldGoalActions': {k: round(v, 6) for k, v in cov.items()},
                       'requiredFields': SHORT_REQUIRED,
                       'optionalNullSafeFields': SHORT_OPTIONAL,
                       'optionalNote': "prepare-origin.mjs 用 a.descriptor ?? '' 與 "
                                       'a.assistPersonId?1:0，缺鍵不影響；assistPersonId 只在'
                                       '有助攻的進球出現、descriptor 只在部分事件出現',
                       'builderInputs': ['actionType', 'xLegacy', 'yLegacy', 'descriptor',
                                          'subType', 'shotResult', 'assistPersonId'],
                       'builder': 'reports/ovr-v55-finisher-fix-2025-26/prepare-origin.mjs',
                       'areaIsOnlyMissingField': True},
        'ii_builderRunnable': bool(short_i),
        'ii_evidence': {'plan': 'v4/tools/prepare_origin_2021_22.py（新檔，不改 v55）可產生同 schema '
                                'shot-origin-2021-22.json；本版未實作（§3.5 明列不做）',
                        'feasibleNotRun': True},
        'iii_definitionConsistent': False,
        'iii_evidence': {'status': 'not run this version',
                         'reason': '§3.5：需先跑 (i)(ii) 與 2022-23–2024-25 的 ±5pp／中位差<=0.03 檢定；'
                                   '另 v55 幾何門檻(y<=142.5, hypot<=40)與 v4 mid 規則(y<=138)不同'},
        'feasible': False,
        'decision': 'W-missing（延後；只影響 D1 的 short 一項 w）',
    }
    creation = {
        'i_fieldsComplete': False,
        'i_evidence': {'dependenceSeasons': dep_seasons,
                       'missing': '2021-22 無 dependence-audit 列、無 player-impact-v28 contexts/exposures'},
        'ii_builderRunnable': False,
        'ii_evidence': {'tracking2021_22': tracking.exists(),
                        'missingTracking': not tracking.exists(),
                        'chain': 'dependence-audit <- player-impact-v28 contexts <- prepare-contexts.mjs '
                                 '<- stints + on-court-truth + shot-exposures + 防守錨點(tracking)'},
        'iii_definitionConsistent': False,
        'iii_evidence': {'status': 'not runnable'},
        'feasible': False,
        'decision': 'W-missing（不可行）',
    }

    all_pass = all(gates.values())
    out = {
        'schemaVersion': 1,
        'season': '2021-22',
        'spec': 'preregistration-v4 §3.3 / §3.4 / §3.5 / P0',
        'generatedBy': 'reports/ovr-inseason-2026-27/v4/tools/p0_feasibility_v4.py',
        'coordinateRule': {'units': '0.1 ft, origin at rim center, baseline y=-52.5',
                           'paintHalfWidth': 80, 'paintFrontY': 138,
                           'sentinel': 'xLegacy==0 and yLegacy==0 -> short'},
        'validate2022_23': s22,
        'apply2021_22': s21,
        'midShareDiff_pp': round(mid_share_pp, 4),
        'gates': {k: bool(v) for k, v in gates.items()},
        'gatePass': bool(all_pass),
        'short': short,
        'creation': creation,
        'conclusion': ('座標規則可用於 2021-22（mid 補回）；short 延後、creation 不可行，兩者維持 W-missing'
                       if all_pass else '座標規則門檻未過 → 不得用於 2021-22'),
        'inputs': {f'pbp-{s}': {'dir': str(SA.season_paths(s)['pbp'].relative_to(C.ROOT)),
                                 'files': n} for s, n in (('2022-23', s22['games']),
                                                          ('2021-22', s21['games']))},
    }
    C.write_json(OUT, out)
    print(json.dumps({'out': str(OUT.relative_to(C.ROOT)), 'gates': out['gates'],
                      'v2022_23': {k: s22[k] for k in ('twoPointers', 'sentinel', 'sentinelShare',
                                                      'midShare_rule', 'midShare_official',
                                                      'agree_nonSentinel', 'agree_overall')},
                      'v2021_22': {k: s21[k] for k in ('twoPointers', 'sentinel', 'sentinelShare',
                                                      'midShare_rule')},
                      'midShareDiff_pp': out['midShareDiff_pp'],
                      'short_iiii': [short['i_fieldsComplete'], short['ii_builderRunnable'],
                                     short['iii_definitionConsistent']]},
                     ensure_ascii=False, indent=1))
    return 0 if all_pass else 3


if __name__ == '__main__':
    raise SystemExit(main())
