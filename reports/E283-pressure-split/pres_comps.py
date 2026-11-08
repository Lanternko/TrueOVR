"""E-283：每個原點 t 的壓迫分量（stl、defl、chg、mtov、pf），四季窗口 t-3..t（資料最早 2022-23）把 (n, d) 直接相加，
再以窗口聯盟比率收縮（k＝E-071 shrink.json；mtov 收縮目標 0）。輸出 pres-comps.json：{t: {nm(name): {p_stl,...}}}。
用法（repo root）：python -I -B -X utf8 reports/E283-pressure-split/pres_comps.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
s = importlib.util.spec_from_file_location('pres_drive', LIVE / 'pres_drive.py'); PD = importlib.util.module_from_spec(s); s.loader.exec_module(PD)
s = importlib.util.spec_from_file_location('dx_stats', ROOT / 'reports/E280-blk-weight/dx_stats.py'); DXS = importlib.util.module_from_spec(s); s.loader.exec_module(DXS)
SEAS = ['2022-23', '2023-24', '2024-25', '2025-26']
COMPS = ['stl', 'defl', 'chg', 'mtov', 'pf']


def main():
    per = {x: PD.p_comps(x) for x in SEAS}
    out, info = {}, {}
    for i, t in enumerate(SEAS):
        win = SEAS[max(0, i - 3):i + 1]
        acc, name = {}, {}
        for x in win:
            raw, comps = per[x]
            for pid, r in raw.items():
                name[pid] = r['name']
                a = acc.setdefault(pid, {c: [0.0, 0.0] for c in COMPS})
                for c in COMPS:
                    a[c][0] += comps[pid][c][0]; a[c][1] += comps[pid][c][1]
        m = {c: (0.0 if c == 'mtov' else sum(a[c][0] for a in acc.values()) / sum(a[c][1] for a in acc.values())) for c in COMPS}
        rows = {}
        for pid, a in acc.items():
            rows[DXS.nm(name[pid])] = {f'p_{c}': (a[c][0] + PD.KS[c] * m[c]) / (a[c][1] + PD.KS[c]) for c in COMPS}
        out[t] = rows
        info[t] = {'window': win, 'n': len(rows), 'm': m}
    (HERE / 'pres-comps.json').write_text(json.dumps({'k': PD.KS, 'info': info, 'vals': out}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
