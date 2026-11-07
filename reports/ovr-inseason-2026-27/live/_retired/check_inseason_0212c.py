"""inseason／card 0.2.12c（R-144，E-207）自檢：tovSkill 失誤率分母由持球分鐘改觸球次數（疊在 0.2.12b／W246 上）。
(1) c0：TOV_TOUCH=0 的輸出夾 ranking.csv 與 0.2.12b 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號回 0.2.12b、三份資料截止日相同；
(2) 卡片：card-0.2.12c-w246/ranking.csv sha＝W246 重擬合定版 224db781…；card-0.2.12c（W246）summary 版號、先驗卡 prior-2025-26-card0212c.json 的 tovSkill＝卡片 ranking.csv 的 tovSkill；
(3) 0.2.12c 輸出 meta 版號、ranking 人數與 0.2.12b 相同、檢查 (a)（f=0、k→∞ 的 OVR 對卡片）< 1e-6；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名），卡片頁與新賽季頁各一份，＋前 10 名與指定球員的 TO、TO 名次、OVR 名次；卡片頁 TO 榜前 30 持球/36 低於池中位數的人數（E-206 B 項）。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0212c.py <0.2.12b 參考夾> <TOV_TOUCH=0 夾> <0.2.12c 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W246_SHA = '224db7812a36fcd4855c157b81c81acb0f312b7fbe80d14642e777d4d5b5a90d'   # reports/card-0.2.12c-fit246/work/W246/final（W246 重擬合，2026-11-02）
SHOW = ['Shai Gilgeous-Alexander', 'Jalen Brunson', 'Cade Cunningham', 'James Harden', 'Luka Dončić', 'Nikola Jokić', 'Sam Hauser',
        'Tim Hardaway Jr.', 'Luke Kornet', 'Jarrett Allen', 'Austin Reaves', 'Kevin Porter Jr.', 'Tyrese Maxey']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(d):
    return {int(r['playerId']): r for r in csv.DictReader(open(Path(d) / 'ranking.csv', encoding='utf-8'))}


def meta(d):
    return json.loads((Path(d) / 'meta.json').read_text(encoding='utf-8'))


def to_rank(rows, key):
    order = sorted(rows, key=lambda p: -float(rows[p][key]))
    return {p: i + 1 for i, p in enumerate(order)}


def r109(old, new, nm, label):
    ro = {p: int(r['rank']) for p, r in old.items()}
    rn = {p: int(r['rank']) for p, r in new.items()}
    t20i = [nm[p] for p in rn if rn[p] <= 20 and ro.get(p, 999) > 20]
    t20o = [nm[p] for p in ro if ro[p] <= 20 and rn.get(p, 999) > 20]
    mov = sorted((p for p in ro if ro[p] <= 100 and p in rn and abs(ro[p] - rn[p]) >= 10), key=lambda p: ro[p])
    print(f'\n(4) {label} 前 20 名 進：', t20i, '出：', t20o)
    print(f'    前 100 名（0.2.11）移動 >=10 名：{len(mov)} 人', [(nm[p], ro[p], rn[p]) for p in mov])
    return ro, rn, len(mov)


def table(old, new, ro, rn, nm):
    f = lambda r, k: float(r[k])
    to_o, to_n = to_rank(old, 'tovSkill'), to_rank(new, 'tovSkill')
    show = [p for p in sorted(rn, key=rn.get) if rn[p] <= 10]
    show += [p for p in new if nm[p] in SHOW and p not in show]
    print(f"    {'球員':<22} OVR名次   OVR           TO值         TO名次")
    for p in show:
        print(f"    {nm[p]:<22} {ro[p]:>3}->{rn[p]:<3} {f(old[p], 'ovr'):5.1f}->{f(new[p], 'ovr'):5.1f}  "
              f"{f(old[p], 'tovSkill'):5.1f}->{f(new[p], 'tovSkill'):5.1f}  {to_o[p]:>3}->{to_n[p]:<3}")


def f143(card_dir):
    """E-206 B 項：卡片頁 TO 榜前 30 的持球/36 低於池中位數（MIN>=500）人數。"""
    import statistics
    pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.12c-w246/tov-raw.csv', encoding='utf-8'))}
    h = {int(r['playerId']): float(r['TIME_OF_POSS']) for r in csv.DictReader(open(ROOT / 'reports/handle-E069/handle.csv', encoding='utf-8')) if r['season'] == '2025-26'}
    rows = [r for r in csv.DictReader(open(Path(card_dir) / 'ranking.csv', encoding='utf-8')) if float(r['MIN']) >= 500]
    v = {r['name']: h[pid[r['name']]] / float(r['MIN']) * 36 for r in rows if r['name'] in pid and pid[r['name']] in h}
    med = statistics.median(v.values())
    top = sorted(rows, key=lambda r: -float(r['tovSkill']))[:30]
    return med, sum(1 for r in top if r['name'] in v and v[r['name']] < med), [r['name'] for r in top[:5]]


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.12b', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    w328 = ROOT / 'reports/card-0.2.12c-w246'
    chk(sha(w328 / 'ranking.csv') == W246_SHA, f"(2) W246 底 ranking.csv＝W246 重擬合定版 {sha(w328 / 'ranking.csv')[:12]}")
    card = ROOT / 'reports/card-0.2.12c'
    cs = json.loads((card / 'summary.json').read_text(encoding='utf-8'))
    chk(cs.get('version') == 'card 0.2.12c' and cs.get('ranking_csv_sha256') == sha(card / 'ranking.csv'), f"(2) card-0.2.12c summary 版號與 sha {cs.get('version')}")
    pn = {p['name']: p for p in json.loads((HERE / 'prior-2025-26-card0212c.json').read_text(encoding='utf-8'))['players']}
    cr = {r['name']: float(r['tovSkill']) for r in csv.DictReader(open(w328 / 'ranking.csv', encoding='utf-8'))}
    common = set(pn) & set(cr)
    dmax = max(abs(pn[p]['tovSkill'] - cr[p]) for p in common)
    chk(len(common) > 500 and dmax < 0.06, f'(2) 先驗 tovSkill 對 W246 底卡片 ranking.csv（先驗沿用 W246 底；賽中 vet 的 tovSkill 由窗口重算）：{len(common)} 人 max|diff| {dmax:.3f}')

    mn = meta(new_dir)
    chk(mn['version'] == 'inseason 0.2.12c' and mn.get('priorCard') == 'card 0.2.12c', f"(3) 新版號 {mn['version']}／{mn.get('priorCard')}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')
    a0 = mn.get('sanity', {}).get('a_f0_kmax_maxAbsOvrDiff')
    chk(a0 is not None and a0 < 1e-6, f'(3) 檢查 (a) f=0 對卡片 OVR max|diff| {a0}')

    c_old = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.12b/ranking.csv', encoding='utf-8'))}
    c_new = {r['name']: r for r in csv.DictReader(open(card / 'ranking.csv', encoding='utf-8'))}
    cnm = {k: k for k in c_new}
    ro, rn, nmov_c = r109(c_old, c_new, cnm, '卡片頁（card 0.2.12b → 0.2.12c）')
    table(c_old, c_new, ro, rn, cnm)
    nm = {p: r['name'] for p, r in new.items()}
    ro, rn, nmov = r109(old, new, nm, '新賽季頁（inseason 0.2.12b → 0.2.12c）')
    table(old, new, ro, rn, nm)
    for lab, d in (('0.2.12b', ROOT / 'reports/card-0.2.12b'), ('0.2.12c', card)):
        med, nb, top5 = f143(d)
        print(f'(4) 卡片頁 {lab} TO 前 30 持球/36 低於池中位數（{med:.3f}）：{nb} 人；榜首 {top5}')
    print(f'\n(4) 前 100 名移動 >=10 名：卡片頁 {nmov_c} 人、新賽季頁 {nmov} 人')
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
