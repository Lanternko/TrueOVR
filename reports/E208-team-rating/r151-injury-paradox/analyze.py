"""讀 out-q1.json / out-bos.json → 每個變體的 Net（ortg−drtg，每 100 回合，未扣聯盟平均常數；差值不受影響）平均與標準誤、對 c 的成對差（同 rep 同種子）。"""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
snap = json.loads((HERE / 'snapshot-team-ratings.json').read_text(encoding='utf-8'))
ab = {t: r['abbr'] for t, r in snap['teams'].items()}


def net(r):
    return 100 * r['pf'] / r['pof'] - 100 * r['pa'] / r['poa']


def ms(x):
    n = len(x); m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1)) if n > 1 else float('nan')
    return m, sd / math.sqrt(n), sd


def table(phase):
    d = json.loads((HERE / f'out-{phase}.json').read_text(encoding='utf-8'))
    by = {}
    for r in d['res']:
        by.setdefault((r['team'], r['ver']), {})[r['rep']] = net(r)
    lines = []
    for team in sorted({t for t, _ in by}, key=lambda t: ab[t]):
        base = by[(team, 'c')]
        for (t, v), reps in by.items():
            if t != team:
                continue
            ks = sorted(reps); m, se, sd = ms([reps[k] for k in ks])
            diff = [reps[k] - base[k] for k in ks]
            dm, dse, dsd = ms(diff)
            lines.append((ab[team], v, len(ks), m, se, dm, dse, dsd, reps[0] - base[0]))
    return lines


for ph in sys.argv[1:]:
    print(f'## {ph}')
    print('| 隊 | 變體 | rep數 | Net 均值 | SE | 對 c 差 | 差 SE | 差 t | rep0 差(＝每日版) |')
    print('|---|---|---|---|---|---|---|---|---|')
    for ab_, v, n, m, se, dm, dse, dsd, d0 in table(ph):
        t = dm / dse if dse and not math.isnan(dse) and dse > 0 else float('nan')
        print(f'| {ab_} | {v} | {n} | {m:.2f} | {se:.2f} | {dm:+.2f} | {dse:.2f} | {t:+.1f} | {d0:+.2f} |')
