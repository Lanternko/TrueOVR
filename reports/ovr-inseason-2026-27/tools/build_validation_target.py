"""P3：2024-25 全季 OVR 目標（preregistration-v2.md §1.2 P3、§3.2）。

凍結 v58 H1-m0 管線吃 2024-25 全季能力值（data/prior-2024-25.json，與先驗同一 builder），
prior_cards = data/prior-2023-24.json（提供 pos／MIN／pids；2024-25 驗證季的先驗季是 2023-24），
RAPM = data/rapm-2022-23-24.csv（P2；刻意排除 2024-25 自身，避免目標季 RAPM 進答案）。

125 名 prior-2023-24 有卡、2024-25 沒有卡（已查：2024-25 上場 0 分鐘）的球員保留先驗能力值，
只為讓凍結管線有完整聯盟；他們 2024-25 MIN=0，不可能進 P24。
輸出 v2/validation/target-2024-25-ovr.csv。
用法：python reports/ovr-inseason-2026-27/tools/build_validation_target.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ovr_common import ATTRS, DATA, ROOT, load_json, sha256_file, write_json
import season_attrs as SA
import v2_common as V2
from ovr_pipeline import OVRPipeline

PRIOR_23 = DATA / 'prior-2023-24.json'
PRIOR_24 = DATA / 'prior-2024-25.json'
RAPM = DATA / 'rapm-2022-23-24.csv'
OUT = V2.V2_VALIDATION / 'target-2024-25-ovr.csv'


def main():
    p23 = {c['playerId']: c for c in load_json(PRIOR_23)['players']}
    p24 = {c['playerId']: c for c in load_json(PRIOR_24)['players']}
    pipe = OVRPipeline(V2.FROZEN_SUMMARY, RAPM, p23)
    attrs = {}
    for pid in p23:
        src = p24.get(pid, p23[pid])
        attrs[pid] = {a: float(src[a]) for a in ATTRS}
    pred = pipe.predict(attrs)
    minutes = {pid: sum(r['MIN'] for r in b['rows'])
               for pid, b in SA.load_season('2024-25', with_pbp=False)['box'].items()}

    V2.V2_VALIDATION.mkdir(parents=True, exist_ok=True)
    head = (['playerId', 'name', 'pos', 'ovr', 'pred', 'pred0', 'bonus', 'align',
             'MIN_2023_24', 'MIN_2024_25', 'attrSource'] + ATTRS)
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for pid in sorted(p23):
            r = pred[pid]
            w.writerow([pid, p23[pid].get('name', ''), p23[pid]['pos'], round(r['ovr'], 4),
                        round(r['pred'], 6), round(r['pred0'], 6), round(r['bonus'], 6),
                        round(r['align'], 6), round(float(p23[pid]['observed']['MIN']), 1),
                        round(minutes.get(pid, 0.0), 1),
                        'card-2024-25' if pid in p24 else 'prior-2023-24-kept']
                       + [round(attrs[pid][a], 4) for a in ATTRS])
    ovrs = [pred[p]['ovr'] for p in p23]
    meta = {
        'file': str(OUT.relative_to(ROOT)),
        'rows': len(p23),
        'playersWith2024_25Card': sum(1 for p in p23 if p in p24),
        'playersKeptPrior': [p for p in sorted(p23) if p not in p24],
        'inputs': {
            'prior_cards': {'file': 'data/prior-2023-24.json', 'sha256': sha256_file(PRIOR_23)},
            'fullSeason2024_25': {'file': 'data/prior-2024-25.json', 'sha256': sha256_file(PRIOR_24)},
            'rapm': {'file': 'data/rapm-2022-23-24.csv', 'sha256': sha256_file(RAPM)},
            'pipeline': {'file': str(V2.FROZEN_SUMMARY.relative_to(ROOT)),
                         'sha256': sha256_file(V2.FROZEN_SUMMARY)},
        },
        'ovrRange': {'min': round(min(ovrs), 4), 'max': round(max(ovrs), 4),
                     'median': round(V2.quantile(ovrs, 0.5), 4)},
        'capIterations': pred['_capIterations'],
    }
    write_json(V2.V2_VALIDATION / 'target-2024-25-ovr.meta.json', meta)
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
