"""inseason 0.2.10i（R-130／R-132）自檢：drive→drive_D、creation→creationJ。
(1) c0：SPLIT_DC=0 的輸出夾 ranking.csv 與 0.2.10h 參考夾（git HEAD 版程式同資料跑出）逐位元組相同、meta 版號回 0.2.10h；
(2) 先驗卡 prior-2025-26-card0210i.json：drive、creation 等於 card-0.2.10i/tail-U.csv，其他屬性等於 _retired/prior-2025-26-card0210d.json；
(3) 0.2.10i 輸出 meta 版號、ranking 人數與 0.2.10h 相同；
(4) R-109 版號統計（前 20 名進出、前 100 名移動 ≥10 名）＋前 25 名與 E-190 15 人的名次、OVR、drive、creation。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0210i.py <0.2.10h 參考夾> <SPLIT_DC=0 夾> <0.2.10i 夾>
全部通過 exit 0，否則 exit 1。"""
import csv
import hashlib
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E190_15 = ['Nikola Jokić', 'Shai Gilgeous-Alexander', 'Luka Dončić', 'Giannis Antetokounmpo', 'Victor Wembanyama', 'Jalen Brunson', 'Anthony Edwards',
           'Tyrese Maxey', 'Cade Cunningham', 'Donovan Mitchell', 'Stephen Curry', 'Devin Booker', 'Ja Morant', 'Zion Williamson', 'Jamal Murray']
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'foulDraw']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(d):
    return {int(r['playerId']): r for r in csv.DictReader(open(Path(d) / 'ranking.csv', encoding='utf-8'))}


def meta(d):
    return json.loads((Path(d) / 'meta.json').read_text(encoding='utf-8'))


def main(ref_dir, c0_dir, new_dir):
    ok = True

    def chk(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(('PASS ' if cond else 'FAIL ') + msg)

    s_ref, s_c0 = sha(Path(ref_dir) / 'ranking.csv'), sha(Path(c0_dir) / 'ranking.csv')
    chk(s_ref == s_c0, f'(1) c0 ranking.csv 逐位元組相同 {s_ref[:12]} / {s_c0[:12]}')
    chk(meta(c0_dir)['version'] == meta(ref_dir)['version'] == 'inseason 0.2.10h', f"(1) c0 版號 {meta(c0_dir)['version']}")
    chk(meta(c0_dir).get('dataCutoff') == meta(ref_dir).get('dataCutoff') == meta(new_dir).get('dataCutoff'), f"(1) 三份資料截止日相同 {meta(new_dir).get('dataCutoff')}")

    pn = {p['playerId']: p for p in json.loads((HERE / 'prior-2025-26-card0210i.json').read_text(encoding='utf-8'))['players']}
    po = {p['playerId']: p for p in json.loads((HERE / '_retired/prior-2025-26-card0210d.json').read_text(encoding='utf-8'))['players']}
    tail = {int(r['playerId']): r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.10i/tail-U.csv', encoding='utf-8'))}
    chk(set(pn) == set(po), f'(2) 先驗人數 {len(pn)}')
    dmax = max(abs(pn[p][a] - float(tail[p][a])) for p in pn for a in ('drive', 'creation'))
    chk(dmax < 1e-9, f'(2) 先驗 drive／creation 對 tail-U max|diff| {dmax:.2e}')
    other = [(p, a) for p in pn for a in ATTRS if a not in ('drive', 'creation') and pn[p].get(a) != po[p].get(a)]
    chk(not other, f'(2) 其他屬性與 0210d 先驗相同（不同 {len(other)} 格）')

    mn = meta(new_dir)
    chk(mn['version'] == 'inseason 0.2.10i', f"(3) 新版號 {mn['version']}")
    old, new = load(c0_dir), load(new_dir)
    chk(set(old) == set(new), f'(3) ranking 人數 {len(old)} / {len(new)}')

    ro = {p: int(r['rank']) for p, r in old.items()}
    rn = {p: int(r['rank']) for p, r in new.items()}
    nm = {p: r['name'] for p, r in new.items()}
    t20i = [nm[p] for p in rn if rn[p] <= 20 and ro.get(p, 999) > 20]
    t20o = [nm[p] for p in ro if ro[p] <= 20 and rn.get(p, 999) > 20]
    mov = sorted((p for p in ro if ro[p] <= 100 and p in rn and abs(ro[p] - rn[p]) >= 10), key=lambda p: ro[p])
    print('\n(4) 前 20 名 進：', t20i, '出：', t20o)
    print(f'    前 100 名（0.2.10h）移動 >=10 名：{len(mov)} 人（R-109 字母版上限 25）', [(nm[p], ro[p], rn[p]) for p in mov])
    chk(len(mov) <= 25, '(4) R-109 字母版')
    show = [p for p in sorted(rn, key=rn.get) if rn[p] <= 25]
    show += [p for p in new if nm[p] in E190_15 and p not in show]
    f = lambda r, k: float(r[k]) if r[k] not in ('', None) else float('nan')
    print(f"\n    {'球員':<26} 名次      OVR           DRV           CRE")
    for p in show:
        o, n = old[p], new[p]
        print(f"    {nm[p]:<26} {ro[p]:>3}->{rn[p]:<3} {f(o, 'ovr'):5.1f}->{f(n, 'ovr'):5.1f}  {f(o, 'drive'):5.1f}->{f(n, 'drive'):5.1f}  {f(o, 'creation'):5.1f}->{f(n, 'creation'):5.1f}")
    print('\n全部通過' if ok else '\n有項目未過')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(*sys.argv[1:4]))
