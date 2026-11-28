"""inseason／card 0.2.13（E-258，使用者「做進卡片」）自檢：加能力值 pnr（擋拆持球），卡片全部係數在 W246 重擬合。
(1) c0：PNR=0 的輸出夾 ranking.csv 與 0.2.12e 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號回 0.2.12e、三份資料截止日相同；
(2) 卡片：card-0.2.13 summary 版號與 ranking sha；先驗卡 prior-2025-26-card0213.json 的 pnr＝card-0.2.13/pnr-attr.csv（＝凍結池 c=0 值）；
(3) 0.2.13 輸出 meta 版號／priorCard、ranking 人數與 0.2.12e 相同、檢查 (a)（f=0、k→∞ 的 OVR 對卡片）< 1e-6、pnr.json 存在；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名），卡片頁（0.2.12c → 0.2.13）與新賽季頁（0.2.12e → 0.2.13）各一份，＋前 10 名與指定球員的 PNR、OVR 名次。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0213.py <0.2.12e 參考夾> <PNR=0 夾> <0.2.13 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHOW = ['Jalen Brunson', 'Deni Avdija', 'Cam Thomas', 'Paolo Banchero', 'Pascal Siakam', 'Nickeil Alexander-Walker',
        'Jeremy Sochan', 'Kon Knueppel', 'Jaden McDaniels', 'Trae Young', 'Tyrese Haliburton', 'Rudy Gobert', 'Nikola Jokić',
        'Shai Gilgeous-Alexander', 'Luka Dončić', 'Cade Cunningham', 'Victor Wembanyama']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(d, key='playerId'):
    rows = list(csv.DictReader(open(Path(d) / 'ranking.csv', encoding='utf-8')))
    return {(int(r[key]) if key == 'playerId' else r[key]): r for r in rows}


def meta(d):
    return json.loads((Path(d) / 'meta.json').read_text(encoding='utf-8'))


def r109(old, new, nm, label):
    ro = {p: int(r['rank']) for p, r in old.items()}
    rn = {p: int(r['rank']) for p, r in new.items()}
    t20i = [nm[p] for p in rn if rn[p] <= 20 and ro.get(p, 999) > 20]
    t20o = [nm[p] for p in ro if ro[p] <= 20 and rn.get(p, 999) > 20]
    mov = sorted((p for p in ro if ro[p] <= 100 and p in rn and abs(ro[p] - rn[p]) >= 10), key=lambda p: ro[p])
    print(f'\n(4) {label} 前 20 名 進：', t20i, '出：', t20o)
    print(f'    前 100 名移動 >=10 名：{len(mov)} 人', [(nm[p], ro[p], rn[p]) for p in mov])
    return ro, rn, len(t20i), len(mov)


def table(old, new, ro, rn, nm, pnr):
    f = lambda r, k: float(r[k])
    show = [p for p in sorted(rn, key=rn.get) if rn[p] <= 10]
    show += [p for p in new if nm[p] in SHOW and p not in show]
    print(f"    {'球員':<26} OVR名次   OVR           PNR")
    for p in show:
        pv = pnr.get(p)
        print(f"    {nm[p]:<26} {ro.get(p, 0):>3}->{rn[p]:<3} {f(old[p], 'ovr') if p in old else 0:5.1f}->{f(new[p], 'ovr'):5.1f}  "
              f"{'' if pv is None else round(float(pv))}")


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.12e', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    card = ROOT / 'reports/card-0.2.13'
    cs = json.loads((card / 'summary.json').read_text(encoding='utf-8'))
    chk(cs.get('version') == 'card 0.2.13' and cs.get('ranking_csv_sha256') == sha(card / 'ranking.csv'), f"(2) card-0.2.13 summary 版號與 sha {cs.get('version')}")
    pa = {r['name']: float(r['pnr']) for r in csv.DictReader(open(card / 'pnr-attr.csv', encoding='utf-8'))}
    pn = {p['name']: p for p in json.loads((HERE / 'prior-2025-26-card0213.json').read_text(encoding='utf-8'))['players']}
    common = [n for n in pn if n in pa and 'pnr' in pn[n]]
    dmax = max(abs(pn[n]['pnr'] - pa[n]) for n in common)
    chk(len(common) > 500 and dmax < 0.051, f'(2) 先驗 pnr 對 card-0.2.13/pnr-attr.csv：{len(common)} 人 max|diff| {dmax:.4f}')

    mn = meta(new_dir)
    chk(mn['version'] == 'inseason 0.2.13' and mn.get('priorCard') == 'card 0.2.13', f"(3) 新版號 {mn['version']}／{mn.get('priorCard')}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')
    a0 = mn.get('sanity', {}).get('a_f0_kmax_maxAbsOvrDiff')
    chk(a0 is not None and a0 < 1e-6, f'(3) 檢查 (a) f=0 對卡片 OVR max|diff| {a0}')
    pj = Path(new_dir) / 'pnr.json'
    chk(pj.exists() and 'pnr' in next(iter(new.values())), f'(3) pnr.json 存在、ranking.csv 有 pnr 欄')

    c_old = load(ROOT / 'reports/card-0.2.12c', 'name')
    c_new = load(card, 'name')
    cnm = {k: k for k in c_new}
    ro, rn, ti_c, nmov_c = r109(c_old, c_new, cnm, '卡片頁（card 0.2.12c → 0.2.13）')
    table(c_old, c_new, ro, rn, cnm, pa)
    nm = {p: r['name'] for p, r in new.items()}
    ro, rn, ti, nmov = r109(old, new, nm, '新賽季頁（inseason 0.2.12e → 0.2.13）')
    table(old, new, ro, rn, nm, {p: r.get('pnr') for p, r in new.items()})
    print(f'\n(4) 前 20 名換人：卡片頁 {ti_c}、新賽季頁 {ti}；前 100 名移動 >=10 名：卡片頁 {nmov_c} 人、新賽季頁 {nmov} 人'
          f'{"（前 20 名換超過 3 人 → 要重跑 G4）" if max(ti_c, ti) > 3 else ""}')
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
