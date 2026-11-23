"""E-307 第一步：從 pbp 逐季算每人蓋帽後的結果與防守干擾球（只讀 pbp，不碰任何驗收量）。
每個蓋帽事件：
  - 結果事件＝蓋帽之後第一個決定球權的事件（rebound／turnover／foul／violation／jumpball／FG／FT；period 結束＝不明，排除）。
    retained（防守方取得球權）：rebound 的 teamId＝防守方；進攻方 turnover；進攻方犯規／違例；jumpball 後 possession＝防守方。
  - ptsAfter＝蓋帽後到球權換到防守方之前，進攻方在同一回合再得的分數（possession 欄位＝進攻方的事件都算同回合；
    跳過 substitution／timeout／instant replay 等沒有球權意義的事件；period 結束停止；上限 80 個事件）。
  - goaltend＝violation subType 'defensive goaltending'（personId＝違例防守者）。
輸出 data/blk-events-<季>.csv（逐人逐季：blk_pbp, known, retained, ptsAfter, gt, ptsSq）與 data/parse-info.json。
用法（repo root）：python -I -X utf8 reports/E307-blk-quality/parse_blocks.py"""
import csv, glob, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DR = ROOT if (ROOT / 'data/defense-seventh/2022-23/pbp').exists() else ROOT.parents[2]
PBP = {'2021-22': DR / 'data/defense-seventh/2021-22/pbp', '2022-23': DR / 'data/defense-seventh/2022-23/pbp',
       '2023-24': DR / 'data/defense-seventh/2023-24/pbp', '2024-25': DR / 'data/defense-seventh/2024-25/pbp',
       '2025-26': DR / 'data/defense-a-source/pbp', '2026-27': DR / 'data/defense-seventh/2026-27/pbp'}
SKIP = {'substitution', 'timeout', 'instantreplay', 'stoppage', 'memo', 'block', 'ejection'}
POSS_EV = {'rebound', 'turnover', 'foul', 'violation', 'jumpball', '2pt', '3pt', 'freethrow', 'steal'}


def actions(f):
    d = json.loads(Path(f).read_text(encoding='utf-8'))['data']
    g = d['game'] if 'game' in d else d
    a = g['actions']
    if a and all('orderNumber' in x for x in a):   # 2026-27 部分檔案列表順序 ≠ orderNumber（蓋帽排在籃板後面）
        a = sorted(a, key=lambda x: x['orderNumber'])
    return a


def pts(x):
    if x.get('shotResult') != 'Made':
        return 0
    return {'2pt': 2, '3pt': 3, 'freethrow': 1}.get(x['actionType'], 0)


def outcome(a, i, de, of):
    """蓋帽 a[i] 之後第一個決定球權的事件 → True（防守方）／False（進攻方）／None（不明）。"""
    for j in range(i + 1, min(i + 40, len(a))):
        x = a[j]; t = x['actionType']
        if t == 'period' and x.get('subType') == 'end' or t == 'game':
            return None, 'periodEnd'
        if t in SKIP or t not in POSS_EV:
            continue
        tm = x.get('teamId')
        if t == 'rebound':
            return tm == de, 'rebound'
        if t == 'jumpball':
            return x.get('possession') == de, 'jumpball'
        if t in ('turnover', 'foul', 'violation'):
            if tm == of:
                return True, t
            if tm == de:
                return False, t
            continue
        if t == 'steal':
            return tm == de, 'steal'
        if t in ('2pt', '3pt', 'freethrow'):
            return tm == de, 'shot'   # 沒記籃板就直接出手
    return None, 'none'


def pts_after(a, i, de, of):
    s = 0
    for j in range(i + 1, min(i + 80, len(a))):
        x = a[j]; t = x['actionType']
        if t == 'period' and x.get('subType') == 'end' or t == 'game':
            break
        if t in SKIP:
            continue
        if x.get('possession') == de:
            break
        if x.get('teamId') == of:
            s += pts(x)
    return s


def season(s):
    agg = defaultdict(lambda: [0, 0, 0, 0, 0, 0])   # blk, known, retained, ptsAfter(known), gt, ptsAfter²
    info = defaultdict(int)
    files = sorted(glob.glob(str(PBP[s] / '00*.json')))
    for f in files:
        try:
            a = actions(f)
        except Exception:  # noqa: BLE001
            info['badFile'] += 1; continue
        if not a:
            info['emptyFile'] += 1; continue
        info['games'] += 1
        for i, x in enumerate(a):
            t = x['actionType']
            if t == 'violation' and x.get('subType') == 'defensive goaltending' and x.get('personId'):
                agg[x['personId']][4] += 1; info['gt'] += 1
            if t == '2pt' and 'pointsinthepaint' in (x.get('qualifiers') or []) and 'blocked' not in (x.get('description') or ''):
                info['paint2pa_nb'] += 1; info['paint2pm_nb'] += int(x.get('shotResult') == 'Made')   # P0：沒被蓋的禁區兩分
            if t != 'block' or not x.get('personId'):
                continue
            de = x['teamId']; of = x.get('possession')
            if of == de or not of:   # possession 欄位應為進攻方
                # 退回：找前一個出手事件的隊伍
                of = next((y['teamId'] for y in reversed(a[max(0, i - 6):i]) if y['actionType'] in ('2pt', '3pt')), None)
            info['blk'] += 1
            p = agg[x['personId']]; p[0] += 1
            r, kind = outcome(a, i, de, of)
            info['out_' + kind] += 1
            if r is None:
                continue
            p[1] += 1; p[2] += int(r)
            pa = pts_after(a, i, de, of)
            p[3] += pa; p[5] += pa * pa
            info['retained'] += int(r); info['known'] += 1; info['ptsAfter'] += pa
    with open(HERE / 'data' / f'blk-events-{s}.csv', 'w', encoding='utf-8', newline='') as fo:
        w = csv.writer(fo); w.writerow(['pid', 'blk_pbp', 'known', 'retained', 'ptsAfter', 'gt', 'ptsSq'])
        for pid, v in sorted(agg.items()):
            w.writerow([pid, *v])
    info['files'] = len(files)
    return dict(info)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    (HERE / 'data').mkdir(exist_ok=True)
    out = {}
    for s in PBP:
        out[s] = season(s)
        k = out[s]
        print(s, json.dumps(k), 'retain', round(k['retained'] / k['known'], 4), 'ptsAfter/blk', round(k['ptsAfter'] / k['known'], 4), flush=True)
    (HERE / 'data' / 'parse-info.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
