"""附錄：W-mid 敏感度（preregistration-v4 §10.2；不參與判定）。

把 W 的 mid 配對整批移除（W 的 x0 用座標規則、答案用官方 area，定義不完全一致），
重跑 w 網格，其他規則不變（21 點網格、非遞減 4 元組、ΣM 最小、平手取小）。
輸出 v4/fit/w-sensitivity-noWmid.json。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v4_common as C
import fit_w_grid_v4 as F


def main():
    base = C.load_json(C.V4_FIT / 'w-grid.json')
    out = {'spec': 'preregistration-v4 §10.2 敏感度（不參與判定）',
           'variant': 'W 的 mid 配對整批移除（x0 座標、答案官方 area 的定義差）',
           'starts': {}}
    for s in C.HIST + ['S*']:
        out['starts'][s] = {}
        for a in C.UPD:
            ms = {}
            counts = {}
            for N in C.N_LIST:
                rows = [r for r in F.pair_rows(s, a, N) if not (r['h'] == 'W' and a == 'mid')]
                counts[str(N)] = len(rows)
                ms[N] = {w: F.M_of(rows, a, w) for w in F.GRID}
            base_w = base['w'][s]['attrs'][a]['w']
            if all(v is None for v in ms[3].values()):
                w = {str(N): 0.0 for N in C.N_LIST}
                note = 'H empty -> 0'
            else:
                ws, _ = F.choose_tuple(ms)
                w = {str(N): ws[i] for i, N in enumerate(C.N_LIST)}
                note = ''
            out['starts'][s][a] = {'w': w, 'baseW': base_w,
                                   'same': all(abs(w[str(N)] - base_w[str(N)]) < 1e-12
                                               for N in C.N_LIST),
                                   'pairCounts': counts, 'note': note}
    C.write_json(C.V4_FIT / 'w-sensitivity-noWmid.json', out)
    diff = {s: {a: v['w'] for a, v in d.items() if not v['same']} for s, d in out['starts'].items()}
    print(json.dumps({'changed': {s: {a: {'base': out['starts'][s][a]['baseW'],
                                          'noWmid': out['starts'][s][a]['w']}
                                      for a in diff[s]} for s in diff if diff[s]},
                      'nChanged': {s: len(diff[s]) for s in diff}}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
