"""inseason 0.2.10h（E-193、R-129）自檢：y、v 改用開季當天年齡。比 0.2.10g（AGE_START=0）與 0.2.10h 兩份 ranking.csv。
列出：(1) age_start 與本季 bio AGE 不同的人；(2) y 或 v 因此改變的人與 OVR／名次變化；(3) 前 20 名進出、前 100 名移動 ≥10 名人數（R-109）；(4) Allen／Gordon／Kuzma／Martin 的 age_start。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0210h.py <0.2.10g 的輸出夾> <0.2.10h 的輸出夾>"""
import csv
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import window11 as W  # noqa: E402


def load(d):
    return {int(r['playerId']): r for r in csv.DictReader(open(Path(d) / 'ranking.csv', encoding='utf-8'))}


def main(old_dir, new_dir):
    Wn = W.Win11()
    old, new = load(old_dir), load(new_dir)
    print('開季日', Wn.season_start, '有 DOB', len(Wn.age_start))
    names = {p: r['name'] for p, r in {**old, **new}.items()}
    for f in (W.ROOT / 'data/benchmark-source/bio.json', Wn.data26 / 'bio.json', W.ROOT / 'data/defense-seventh/2026-27/roster.json'):
        rs = json.loads(f.read_text(encoding='utf-8'))['data']['resultSets']
        rs = rs[0] if isinstance(rs, list) else rs
        h = rs['headers']
        i, j = (h.index('PLAYER_ID'), h.index('PLAYER_NAME')) if 'PLAYER_ID' in h else (h.index('PERSON_ID'), h.index('DISPLAY_FIRST_LAST'))
        for r in rs['rowSet']:
            names.setdefault(int(r[i]), r[j])
    diff = []
    for p, a in Wn.age_start.items():
        b = Wn.age_cur.get(p)
        if b is not None and int(b) != a:
            diff.append((p, a, b))
    print(f'\n(1) age_start != 本季 bio AGE：{len(diff)} 人（bio 是 {Wn.age_cur and "抓取當下"}年齡）')
    for p, a, b in sorted(diff, key=lambda x: names.get(x[0], '')):
        print(f'  {names.get(p, p)} ({p}) age_start={a} bioAGE={b}')
    flips = []
    for p, a in Wn.age_start.items():
        b = Wn.age_cur.get(p, Wn.age25.get(p))   # 0.2.10g 的舊行為：沒有本季 bio（本季還沒上場）的人用 2025-26 bio，年紀少一歲
        if b is None:
            continue
        oy, ov = b <= W.AGE_Y, b >= W.AGE_V
        ny, nv = a <= W.AGE_Y, a >= W.AGE_V
        if (oy, ov) != (ny, nv):
            flips.append((p, b, a, oy, ny, ov, nv))
    print(f'\n(2) y 或 v 改變：{len(flips)} 人')
    for p, b, a, oy, ny, ov, nv in flips:
        o, n = old.get(p), new.get(p)
        print(f'  {names.get(p, p)} {"(本季 bio)" if p in Wn.age_cur else "(2025-26 bio，本季未上場)"} bio={b} start={a} y {int(oy)}->{int(ny)} v {int(ov)}->{int(nv)}',
              f"OVR {o['ovr']}->{n['ovr']} 名次 {o['rank']}->{n['rank']}" if o and n else '（不在 ranking）')
    ro = {p: int(r['rank']) for p, r in old.items()}
    rn = {p: int(r['rank']) for p, r in new.items()}
    t20o = {p for p, k in ro.items() if k <= 20}
    t20n = {p for p, k in rn.items() if k <= 20}
    mov = [p for p in ro if ro[p] <= 100 and p in rn and abs(ro[p] - rn[p]) >= 10]
    print('\n(3) 前 20 名進：', [names[p] for p in t20n - t20o], '出：', [names[p] for p in t20o - t20n])
    print('    前 100 名（舊）移動 >=10 名：', len(mov), [(names[p], ro[p], rn[p]) for p in mov])
    chg = [p for p in ro if p in rn and ro[p] != rn[p]]
    print('    名次有變的人', len(chg), '/', len(ro))
    print('\n(4) 四人 age_start：')
    for key in ('Allen', 'Gordon', 'Kuzma', 'Martin'):
        for p, nm in names.items():
            if nm.endswith(' ' + key) or nm.endswith(key):
                print(f'  {nm} ({p}) age_start={Wn.age_start.get(p)} bio={Wn.age_cur.get(p)} y/v 舊={W.AGE_V <= (Wn.age_cur.get(p) or 0)} 新={W.AGE_V <= (Wn.age_start.get(p) or 0)}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(*sys.argv[1:3])
