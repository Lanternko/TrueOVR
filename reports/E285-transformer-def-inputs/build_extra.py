"""E-285：Transformer 新增輸入欄（逐季，不是四季窗口；和 E227 stats-<季>.csv 同口徑）。
  mtov36 ＝ 對位逼失誤（E-071 壓迫分量 mtov，(n+k·0)/(d+k)，k＝E-071 shrink.json；2021-22 無追蹤資料 → 空）
  fOn36  ＝ 有球犯規（shooting、take、transition take、clear-path）每 36 分
  fOff36 ＝ 無球犯規（loose ball、away-from-play）每 36 分
  fGen36 ＝ 一般犯規（personal 無 descriptor）每 36 分
犯規率以 500 分鐘收縮到該季聯盟率；上場 < 200 分鐘（E227 MIN_MINUTES）一律空值（遮罩）。
抄截、干擾、製造進攻犯規、總犯規、蓋帽本來就在 E227 stats 欄（stl36、deflections36、charges36、pf36、blk36），不重複加。
輸出 data/extra-<季>.csv。用法（repo root）：python -I -B -X utf8 reports/E285-transformer-def-inputs/build_extra.py"""
import csv, importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
E227D = ROOT / 'reports/E227-lineup-transformer-r2/data'
sys.path.insert(0, str(LIVE))


def mod(name, p):
    s = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


PD = mod('pres_drive', LIVE / 'pres_drive.py')
FC = mod('foul_comps', ROOT / 'reports/E284-onoff-fouls/foul_comps.py')
SEAS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
COLS = ['mtov36', 'fOn36', 'fOff36', 'fGen36']
K_FOUL, MIN_MIN = 500.0, 200.0


def main():
    (HERE / 'data').mkdir(exist_ok=True)
    info = {}
    for s in SEAS:
        mins = {r['pid']: float(r['minutes'] or 0) for r in csv.DictReader(open(E227D / f'stats-{s}.csv', encoding='utf-8'))}
        cnt, _ = FC.season_counts(s)
        tot = sum(mins.values())
        lg = {k: 36 * sum(cnt.get(int(p), {}).get(k, 0) for p in mins) / tot for k in FC.KEYS}
        mt = {}
        if s != '2021-22':
            raw, comps = PD.p_comps(s)
            kk = PD.KS['mtov']
            mt = {str(p): (comps[p]['mtov'][0]) / (comps[p]['mtov'][1] + kk) for p in raw}
        rows, nm = [], 0
        for p, m in mins.items():
            ok = m >= MIN_MIN
            c = cnt.get(int(p), {})
            f = {k: (c.get(k, 0) * 36 + K_FOUL * lg[k]) / (m + K_FOUL) for k in FC.KEYS}
            v = mt.get(p)
            nm += ok and v is not None
            rows.append({'pid': p, 'mtov36': '' if (not ok or v is None) else round(v, 5),
                         'fOn36': round(f['f_on'], 5) if ok else '', 'fOff36': round(f['f_off'], 5) if ok else '',
                         'fGen36': round(f['f_gen'], 5) if ok else ''})
        with open(HERE / 'data' / f'extra-{s}.csv', 'w', encoding='utf-8', newline='') as fo:
            w = csv.DictWriter(fo, ['pid'] + COLS); w.writeheader(); w.writerows(rows)
        info[s] = {'players': len(rows), 'ge200': sum(m >= MIN_MIN for m in mins.values()), 'mtovPresent': nm, 'league36': lg}
    (HERE / 'data' / 'extra-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
