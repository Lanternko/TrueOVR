"""inseason／card 0.2.15（E-303 MRG5，使用者 2026-11-10「合併做進卡片」）自檢：CRT＋PNR 合成「持球進攻」放 creation 欄，pnr 不再是獨立特徵，全部係數在 W246 重擬合。
(1) c0：CRTPNR=0 的輸出夾 ranking.csv 與 0.2.14d 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號 0.2.14d、三份資料截止日相同；
(2) 卡片：card-0.2.15 summary 版號與 ranking sha；card-0.2.15-base 的 creation＝凍結 crtpnr（四捨五入）；crtpnr_live.check_card 逐位元；
(3) 0.2.15 輸出 meta 版號／priorCard、ranking 人數與 0.2.14d 相同、ranking 沒有 pnr 欄、crt.json 存在且每人都有；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名），卡片頁（0.2.14c → 0.2.15）與新賽季頁（0.2.14d → 0.2.15）各一份，＋前 10 名與指定球員的 CRT、OVR 名次。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0215.py <0.2.14d 參考夾> <CRTPNR=0 夾> <0.2.15 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
SHOW = ['Luka Dončić', 'Shai Gilgeous-Alexander', 'Jalen Brunson', 'Cade Cunningham', 'Tyrese Haliburton', 'Zion Williamson',
        'Nikola Jokić', 'Giannis Antetokounmpo', 'Kevin Durant', 'DeMar DeRozan', 'Pascal Siakam', 'Joel Embiid', 'Evan Mobley']


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
    mov = sorted((p for p in ro if (ro[p] <= 100 or rn.get(p, 999) <= 100) and p in rn and abs(ro[p] - rn[p]) >= 10), key=lambda p: ro[p])
    drop30 = [(nm[p], ro[p], rn[p]) for p in ro if p in rn and ro[p] <= 300 and rn[p] - ro[p] >= 30]
    print(f'\n(4) {label} 前 20 名 進：', t20i, '出：', t20o)
    print(f'    前 100 名移動 >=10 名：{len(mov)} 人', [(nm[p], ro[p], rn[p]) for p in mov])
    print(f'    前 300 名掉 >=30 名：{drop30}')
    return ro, rn, len(t20i), len(mov)


def table(old, new, ro, rn, nm):
    f = lambda r, k: float(r[k])
    show = [p for p in sorted(rn, key=rn.get) if rn[p] <= 10]
    show += [p for p in new if nm[p] in SHOW and p not in show]
    print(f"    {'球員':<26} OVR名次   OVR           CRT")
    for p in show:
        print(f"    {nm[p]:<26} {ro.get(p, 0):>3}->{rn[p]:<3} {f(old[p], 'ovr') if p in old else 0:5.1f}->{f(new[p], 'ovr'):5.1f}  "
              f"{float(old[p]['creation']) if p in old else 0:5.1f}->{f(new[p], 'creation'):5.1f}")


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.14d', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    import crtpnr_live as CPL
    card, base = ROOT / 'reports/card-0.2.15', ROOT / 'reports/card-0.2.15-base'
    cs = json.loads((card / 'summary.json').read_text(encoding='utf-8'))
    chk(cs.get('version') == 'card 0.2.15' and cs.get('ranking_csv_sha256') == sha(card / 'ranking.csv'), f"(2) card-0.2.15 summary 版號與 sha {cs.get('version')}")
    F = CPL.frozen()
    br = list(csv.DictReader(open(base / 'ranking.csv', encoding='utf-8')))
    pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(card / 'crt-attr.csv', encoding='utf-8'))}
    dmax = max(abs(float(r['creation']) - round(F['card'][pid[r['name']]]['crtpnr'], 1)) for r in br)
    chk(len(br) == 582 and dmax < 0.051, f'(2) card-0.2.15-base creation 對凍結 crtpnr：{len(br)} 人 max|diff| {dmax:.4f}')
    try:
        CPL.check_card()
        chk(True, '(2) crtpnr_live.check_card 逐位元')
    except AssertionError:
        chk(False, '(2) crtpnr_live.check_card 逐位元')

    mn = meta(new_dir)
    chk(mn['version'] == 'inseason 0.2.15' and mn.get('priorCard') == 'card 0.2.15', f"(3) 新版號 {mn['version']}／{mn.get('priorCard')}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')
    chk('pnr' not in next(iter(new.values())), '(3) ranking.csv 沒有 pnr 欄')
    cj = Path(new_dir) / 'crt.json'
    cd = json.loads(cj.read_text(encoding='utf-8'))['players'] if cj.exists() else {}
    miss = [new[p]['name'] for p in new if str(p) not in cd]
    chk(cj.exists() and not miss, f'(3) crt.json 存在、每人都有（缺 {miss[:5]}）')
    bad = [new[p]['name'] for p in new if str(p) in cd and abs(round(cd[str(p)]['crtpnr'], 1) - float(new[p]['creation'])) > 0.051]
    chk(not bad, f'(3) crt.json crtpnr＝ranking creation（不符 {bad[:5]}）')

    c_old = load(ROOT / 'reports/card-0.2.14c', 'name')
    c_new = load(card, 'name')
    cnm = {k: k for k in c_new}
    ro, rn, ti_c, nmov_c = r109(c_old, c_new, cnm, '卡片頁（card 0.2.14c → 0.2.15）')
    table(c_old, c_new, ro, rn, cnm)
    nm = {p: r['name'] for p, r in new.items()}
    ro, rn, ti, nmov = r109(old, new, nm, '新賽季頁（inseason 0.2.14d → 0.2.15）')
    table(old, new, ro, rn, nm)
    print(f'\n(4) 前 20 名換人：卡片頁 {ti_c}、新賽季頁 {ti}；前 100 名移動 >=10 名：卡片頁 {nmov_c} 人、新賽季頁 {nmov} 人')
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
