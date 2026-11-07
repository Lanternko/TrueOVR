"""inseason／card 0.2.10j（R-134／R-135，E-200）自檢：加能力值 gravity（無球外線引力）。
(1) c0：GRAVITY=0 的輸出夾 ranking.csv 與 0.2.10i 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號回 0.2.10i、三份資料截止日相同；
(2) 先驗卡 prior-2025-26-card0210j.json：gravity 等於 card-0.2.10j/gravity-attr.csv，其他屬性等於 _retired/prior-2025-26-card0210i.json；
    卡片端：card-0.2.10j/summary.json 記 c0（GRAVITY=0 重現 card 0.2.10i）與 equals_E198_KG_final 都成立；
(3) 0.2.10j 輸出 meta 版號、ranking 人數與 0.2.10i 相同、ranking 有 gravity 欄、gravity.json 存在；檢查 (a)（f=0、k→∞ 的 OVR 對卡片）< 1e-6；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名），卡片頁與新賽季頁各一份，＋前 25 名與 8 位射手／長人的名次、OVR、gravity。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0210j.py <0.2.10i 參考夾> <GRAVITY=0 夾> <0.2.10j 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHOW = ['Klay Thompson', 'Stephen Curry', 'Buddy Hield', 'Luke Kennard', 'Duncan Robinson', 'Sam Hauser', 'Myles Turner', 'Al Horford']
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'foulDraw']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(d):
    return {int(r['playerId']): r for r in csv.DictReader(open(Path(d) / 'ranking.csv', encoding='utf-8'))}


def meta(d):
    return json.loads((Path(d) / 'meta.json').read_text(encoding='utf-8'))


def r109(old, new, nm, label):
    ro = {p: int(r['rank']) for p, r in old.items()}
    rn = {p: int(r['rank']) for p, r in new.items()}
    t20i = [nm[p] for p in rn if rn[p] <= 20 and ro.get(p, 999) > 20]
    t20o = [nm[p] for p in ro if ro[p] <= 20 and rn.get(p, 999) > 20]
    mov = sorted((p for p in ro if ro[p] <= 100 and p in rn and abs(ro[p] - rn[p]) >= 10), key=lambda p: ro[p])
    print(f'\n(4) {label} 前 20 名 進：', t20i, '出：', t20o)
    print(f'    前 100 名（0.2.10i）移動 >=10 名：{len(mov)} 人（R-109 字母版上限 25）', [(nm[p], ro[p], rn[p]) for p in mov])
    return ro, rn, len(mov)


def table(old, new, ro, rn, nm, grav):
    f = lambda r, k: float(r[k]) if r.get(k) not in ('', None) else float('nan')
    show = [p for p in sorted(rn, key=rn.get) if rn[p] <= 25]
    show += [p for p in new if nm[p] in SHOW and p not in show]
    print(f"    {'球員':<26} 名次      OVR           GRV")
    for p in show:
        print(f"    {nm[p]:<26} {ro[p]:>3}->{rn[p]:<3} {f(old[p], 'ovr'):5.1f}->{f(new[p], 'ovr'):5.1f}  {grav(p):5.1f}")


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.10i', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    pn = {p['playerId']: p for p in json.loads((HERE / 'prior-2025-26-card0210j.json').read_text(encoding='utf-8'))['players']}
    po = {p['playerId']: p for p in json.loads((HERE / '_retired/prior-2025-26-card0210i.json').read_text(encoding='utf-8'))['players']}
    ga = {int(r['playerId']): float(r['gravity']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10j/gravity-attr.csv', encoding='utf-8'))}
    chk(set(pn) == set(po), f'(2) 先驗人數 {len(pn)}')
    dmax = max(abs(pn[p]['gravity'] - ga[p]) for p in pn)
    chk(dmax == 0.0, f'(2) 先驗 gravity 對 gravity-attr.csv max|diff| {dmax:.2e}')
    other = [(p, a) for p in pn for a in ATTRS if pn[p].get(a) != po[p].get(a)]
    chk(not other, f'(2) 其他屬性與 0210i 先驗相同（不同 {len(other)} 格）')
    cs = json.loads((ROOT / 'reports/card-0.2.10j/summary.json').read_text(encoding='utf-8'))
    chk(cs.get('version') == 'card 0.2.10j' and cs.get('equals_E198_KG_final') is True, '(2) 卡片 card 0.2.10j＝E-198 KG 定版逐位元相同')
    chk(all(cs.get('c0', {}).get(k) is True for k in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv', 'anchors')), '(2) 卡片 c0（GRAVITY=0）＝card 0.2.10i')

    mn = meta(new_dir)
    chk(mn['version'] in ('inseason 0.2.10j', 'inseason 0.2.11') and mn.get('priorCard') in ('card 0.2.10j', 'card 0.2.11'), f"(3) 新版號 {mn['version']}／{mn.get('priorCard')}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')
    chk('gravity' in next(iter(new.values())), '(3) ranking.csv 有 gravity 欄')
    chk((Path(new_dir) / 'gravity.json').exists(), '(3) gravity.json（GRV 提示卡用）存在')
    a0 = mn.get('sanity', {}).get('a_f0_kmax_maxAbsOvrDiff')
    chk(a0 is not None and a0 < 1e-6, f'(3) 檢查 (a) f=0 對卡片 OVR max|diff| {a0}')

    # 卡片頁
    c_old = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10i/ranking.csv', encoding='utf-8'))}
    c_new = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10j/ranking.csv', encoding='utf-8'))}
    gn = {r['name']: float(r['gravity']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10j/gravity-attr.csv', encoding='utf-8'))}
    cnm = {k: k for k in c_new}
    ro, rn, nmov_c = r109(c_old, c_new, cnm, '卡片頁（card 0.2.10i → 0.2.10j）')
    chk(nmov_c <= 25, '(4) 卡片頁 R-109 字母版')
    table(c_old, c_new, ro, rn, cnm, lambda p: gn.get(p, float('nan')))

    nm = {p: r['name'] for p, r in new.items()}
    ro, rn, nmov = r109(old, new, nm, '新賽季頁（inseason 0.2.10i → 0.2.10j）')
    chk(nmov <= 25, '(4) 新賽季頁 R-109 字母版')
    table(old, new, ro, rn, nm, lambda p: float(new[p]['gravity']) if new[p]['gravity'] else float('nan'))
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
