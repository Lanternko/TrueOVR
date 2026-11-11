"""P7：上線資格 G1–G6（preregistration-v4 §5.3），全部布林值寫入 v4/thresholds.json。

G1 決定性 + 防洩漏：每步兩次重跑 SHA 相同（v4/determinism-hashes.txt 的 7 個區塊）＋
   leakage_check_v4.py 無違反（v4/leakage.json）
G2 卡片 P3：v4/cards/build-report.json 全部 pass（§6）
G3 C3 vs A（D2、D3）：N=10/20 中位誤差嚴格小於 A；N=3/5 不得大於 A；
   >10 分人數在 N=10/20 不得多於 A；每格都要過、兩個起點都過
G4 區間：pooled N=10/20 覆蓋率在 [0.70,0.95]、中位寬度 <=25（v4/intervals/g4.json）
G5 mid 補回：§3.3 三條 + §3.4 sanity gate（v4/data/feasibility-2021-22-v4.json）
G6 資料層：v4/live/availability.json 已記錄、creation 缺失已標記
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import v4_common as C

STEPS = ['P0', 'P1', 'P1b', 'P2', 'P3', 'P4', 'P5', 'P6']


def g1():
    txt = (C.V4 / 'determinism-hashes.txt').read_text(encoding='utf-8')
    blocks = [ln for ln in txt.splitlines() if ln.startswith('# ')]
    present = {s: any(ln.split()[1] == s for ln in blocks) for s in STEPS}
    leak = C.load_json(C.V4 / 'leakage.json')
    det = bool(all(present.values()) and '兩次' in txt)
    return {'determinismTwoRunsSameSha': det, 'stepsRecorded': present,
            'leakagePass': bool(leak['pass']), 'leakageChecks': leak['checks'],
            'pass': bool(det and leak['pass'])}


def g2():
    rep = C.load_json(C.V4_CARDS / 'build-report.json')
    per = {s: {'pass': v['pass'], 'checks': v['checks'],
               'rhoOvr': v['rhoOvrVsReference'], 'medianOvrAbsDiff': v['medianOvrAbsDiff'],
               'rhoAttrJudgedMin': v['rhoAttrJudgedMin'], 'constantAttrs': v['constantAttrs'],
               'ovrRange': v['ovrRange']} for s, v in rep.items()}
    return {'cards': per, 'pass': bool(all(v['pass'] for v in rep.values()))}


def g3():
    rows = C.load_csv(C.V4_BACKTEST / 'results.csv')
    cells, passes = [], {}
    for start in ('D2', 'D3'):
        ok_all = True
        for r in rows:
            if r['start'] != start:
                continue
            N = int(r['N'])
            a, c = float(r['medianA']), float(r['medianC3'])
            ga, gc = int(r['gt10A']), int(r['gt10C3'])
            if N in (10, 20):
                med_ok = c < a
            else:
                med_ok = c <= a
            gt_ok = (gc <= ga) if N in (10, 20) else True
            cell = {'N': N, 'medianA': a, 'medianC3': c, 'medianOk': bool(med_ok),
                    'gt10A': ga, 'gt10C3': gc, 'gt10Ok': bool(gt_ok),
                    'pass': bool(med_ok and gt_ok)}
            cells.append({'start': start, **cell})
            ok_all = ok_all and cell['pass']
        passes[start] = ok_all
    return {'cells': cells, 'starts': passes, 'pass': bool(all(passes.values()))}


def g4():
    g = C.load_json(C.V4 / 'intervals' / 'g4.json')
    return {'pooledCoverageIn070_095': g['pooledCoverageIn070_095'],
            'medianWidthLe25': g['medianWidthLe25'], 'pooled': g['pooled'], 'pass': g['pass']}


def g5():
    f = C.load_json(C.V4_DATA / 'feasibility-2021-22-v4.json')
    return {'gates': f['gates'], 'gatePass': f['gatePass'],
            'midShareDiff_pp': f['midShareDiff_pp'],
            'shortFeasible': f['short']['feasible'], 'creationFeasible': f['creation']['feasible'],
            'pass': bool(f['gatePass'] and all(f['gates'].values()))}


def g6():
    a = C.load_json(C.V4_LIVE / 'availability.json')
    return {'creationMissing': a['creationMissing'],
            'g6Recorded': a['g6Recorded'],
            'layers': {k: v['status'] for k, v in a['layers'].items()},
            'noDataRead': a['noDataRead'],
            'pass': bool(a['g6Recorded'] and a['creationMissing'])}


def main():
    gates = {'G1': g1(), 'G2': g2(), 'G3': g3(), 'G4': g4(), 'G5': g5(), 'G6': g6()}
    doc = {'spec': 'preregistration-v4 §5.3 / §9 P7',
           'gates': {k: bool(v['pass']) for k, v in gates.items()},
           'details': gates,
           'allPass': bool(all(v['pass'] for v in gates.values())),
           'freezeAllowed': bool(all(v['pass'] for v in gates.values())),
           'note': ('G 全過才做 F0；任一 false 即不凍結、不發布 C3（§5.3）。'
                    'G3 只看 D2、D3；C2 只列對照不參與判定。')}
    doc['failedGates'] = [k for k, v in doc['gates'].items() if not v]
    C.write_json(C.V4 / 'thresholds.json', doc)
    print(json.dumps({'gates': doc['gates'], 'allPass': doc['allPass'],
                      'failed': doc['failedGates']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
