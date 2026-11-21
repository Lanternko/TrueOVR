"""新舊分鐘規則／預測勝場對照（spec-minutes-return.md 的回報）。
用法：python -I -X utf8 reports/E208-team-rating/minutes_return_compare.py <舊 team-ratings.json> <新 team-ratings.json>
輸出：近況版輪替差最多的 5 隊（sum|Δ分鐘|；誰進、誰出、分鐘變化）、因 15 分鐘門檻補回的人、今日陣容預測勝場（整季缺陣→逐場回歸日）變最多的 5 隊。
"""
import json
import sys

old = json.load(open(sys.argv[1], encoding='utf-8'))
new = json.load(open(sys.argv[2], encoding='utf-8'))


def rot(t, v):
    return {r['pid']: (r['name'], r['min']) for r in t[v]['rotation']}


def diff(a, b):
    ks = set(a) | set(b)
    return sum(abs((a.get(k) or (0, 0))[1] - (b.get(k) or (0, 0))[1]) for k in ks)


for v, label in (('c', '近況'), ('today', '今日陣容')):
    rows = sorted(((diff(rot(old['teams'][k], v), rot(new['teams'][k], v)), k) for k in new['teams']), reverse=True)
    print(f'\n== {label}版輪替差最多的 5 隊（Σ|Δ分鐘|）')
    for d, k in rows[:5]:
        a, b = rot(old['teams'][k], v), rot(new['teams'][k], v)
        t = new['teams'][k]
        ins = [f'{b[p][0]} {b[p][1]:.1f}' for p in b if p not in a]
        outs = [f'{a[p][0]} {a[p][1]:.1f}' for p in a if p not in b]
        chg = sorted(((b[p][1] - a[p][1], b[p][0], a[p][1], b[p][1]) for p in a if p in b), key=lambda x: -abs(x[0]))[:3]
        print(f"{t['abbr']} Σ{d:.1f}　進：{'、'.join(ins) or '—'}　出：{'、'.join(outs) or '—'}　最大變動：" + '、'.join(f'{n} {x:.1f}→{y:.1f}' for _, n, x, y in chg))
    print(f'（{label}版 30 隊平均 Σ|Δ| {sum(d for d, _ in rows) / 30:.1f} 分鐘）')

print('\n== 15 分鐘門檻補回的人（近況版輪替內）')
n = 0
for k, t in sorted(new['teams'].items(), key=lambda kv: kv[1]['abbr']):
    for r in t.get('restored', []):
        n += 1
        print(f"{t['abbr']} {r['name']} {r['min']:.1f} 分")
print(f'共 {n} 人')

print('\n== 今日陣容預測勝場變最多的 5 隊（整季缺陣 → 逐場回歸日；同一份新資料內對照）')
rows = sorted(((t['today']['predWins'] - t['today']['predWinsAllSeason'], k) for k, t in new['teams'].items()), key=lambda x: -abs(x[0]))
for d, k in rows[:5]:
    t = new['teams'][k]
    print(f"{t['abbr']} {t['today']['predWinsAllSeason']:.1f} → {t['today']['predWins']:.1f}（{d:+.1f}；陣容 {t['today']['lineupStates']} 種狀態）")
print('\n== 與上一版網站（舊分鐘規則＋整季缺陣）相比，今日陣容預測勝場變最多的 5 隊')
rows = sorted(((new['teams'][k]['today']['predWins'] - old['teams'][k]['today']['predWins'], k) for k in new['teams']), key=lambda x: -abs(x[0]))
for d, k in rows[:5]:
    print(f"{new['teams'][k]['abbr']} {old['teams'][k]['today']['predWins']:.1f} → {new['teams'][k]['today']['predWins']:.1f}（{d:+.1f}）")
