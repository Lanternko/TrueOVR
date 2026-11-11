"""inseason／card 0.2.12（R-139，E-203）自檢：tovSkill 改看持球時間。
(1) c0：TOV_POSS=0 的輸出夾 ranking.csv 與 0.2.11 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號回 0.2.11、三份資料截止日相同；
(2) 卡片：card-0.2.12-tov/ranking.csv sha＝E-202 KT 定版 29ca32eb…；summary.json 記 equals_E202_KT_final 與 c0（TOV_POSS=0 重現 card 0.2.11）都成立；
    先驗卡 prior-2025-26-card0212-tov.json 的 tovSkill＝卡片 ranking.csv 的 tovSkill（四捨五入到 ranking 的位數內）；
(3) 0.2.12 輸出 meta 版號、ranking 人數與 0.2.11 相同、檢查 (a)（f=0、k→∞ 的 OVR 對卡片）< 1e-6；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名），卡片頁與新賽季頁各一份，＋前 10 名與指定球員的 TO、TO 名次、OVR 名次。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0212tov.py <0.2.11 參考夾> <TOV_POSS=0 夾> <0.2.12 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
KT_SHA = '29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5'
SHOW = ['Jalen Brunson', 'Cade Cunningham', 'James Harden', 'Luka Dončić', 'Nikola Jokić', 'Sam Hauser',
        'Tim Hardaway Jr.', 'Luke Kornet', 'Jarrett Allen']


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


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.11', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    card = ROOT / 'reports/card-0.2.12-tov'
    chk(sha(card / 'ranking.csv') == KT_SHA, f"(2) 卡片 ranking.csv＝E-202 KT 定版 {sha(card / 'ranking.csv')[:12]}")
    cs = json.loads((card / 'summary.json').read_text(encoding='utf-8'))
    chk(cs.get('version') == 'card 0.2.12' and cs.get('equals_E202_KT_final') is True, '(2) summary：equals_E202_KT_final')
    chk(all(cs.get('c0', {}).get(k) is True for k in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv', 'anchors')), '(2) 卡片 c0（TOV_POSS=0）＝card 0.2.11')
    pn = {p['name']: p for p in json.loads((HERE / 'prior-2025-26-card0212-tov.json').read_text(encoding='utf-8'))['players']}
    cr = {r['name']: float(r['tovSkill']) for r in csv.DictReader(open(card / 'ranking.csv', encoding='utf-8'))}
    common = set(pn) & set(cr)
    dmax = max(abs(pn[p]['tovSkill'] - cr[p]) for p in common)
    chk(len(common) > 500 and dmax < 0.06, f'(2) 先驗 tovSkill 對卡片 ranking.csv：{len(common)} 人 max|diff| {dmax:.3f}')

    mn = meta(new_dir)
    chk(mn['version'] in ('inseason 0.2.12', 'inseason 0.2.12a') and mn.get('priorCard') == 'card 0.2.12', f"(3) 新版號 {mn['version']}／{mn.get('priorCard')}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')
    a0 = mn.get('sanity', {}).get('a_f0_kmax_maxAbsOvrDiff')
    chk(a0 is not None and a0 < 1e-6, f'(3) 檢查 (a) f=0 對卡片 OVR max|diff| {a0}')

    c_old = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10j/ranking.csv', encoding='utf-8'))}
    c_new = {r['name']: r for r in csv.DictReader(open(card / 'ranking.csv', encoding='utf-8'))}
    cnm = {k: k for k in c_new}
    ro, rn, nmov_c = r109(c_old, c_new, cnm, '卡片頁（card 0.2.11 → 0.2.12）')
    table(c_old, c_new, ro, rn, cnm)
    nm = {p: r['name'] for p, r in new.items()}
    ro, rn, nmov = r109(old, new, nm, '新賽季頁（inseason 0.2.11 → 0.2.12）')
    table(old, new, ro, rn, nm)
    print(f'\n(4) 前 100 名移動 >=10 名：卡片頁 {nmov_c} 人、新賽季頁 {nmov} 人（R-139 已知上限：E-202 回報 34 人）')
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
