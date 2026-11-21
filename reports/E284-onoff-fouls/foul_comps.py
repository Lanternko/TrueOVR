"""E-284：逐回合（pbp）犯規分類 → 每原點 t 四季窗口（t-3..t，最早 2021-22）每 36 分鐘、收縮後的有球／無球／一般犯規。
分類（只算防守方個人犯規；進攻犯規、技術犯規、惡性犯規、double 不算）：
  有球 f_on ＝ shooting、take、transition take、clear-path（犯在持球／投籃者身上）
  無球 f_off＝ loose ball、away-from-play（搶位、搶籃板、離球）
  一般 f_gen＝ personal 沒有 descriptor（一般阻擋／伸手，pbp 分不出有沒有球）
  f_ball ＝ f_on＋f_gen
分鐘取 E227 stats-<季>.csv（pid）；收縮 k＝500 分鐘，目標＝窗口聯盟率。輸出 foul-comps.json：{t: {nm(name): {...}}}。
用法（repo root）：python -I -B -X utf8 reports/E284-onoff-fouls/foul_comps.py"""
import csv, glob, importlib.util, json, sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('dx_stats', ROOT / 'reports/E280-blk-weight/dx_stats.py'); DXS = importlib.util.module_from_spec(s); s.loader.exec_module(DXS)
SEAS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
PBP = {x: ROOT / 'data/defense-seventh' / x / 'pbp' for x in SEAS[:-1]}
PBP['2025-26'] = ROOT / 'data/defense-a-source/pbp'
ON = {'shooting', 'take', 'transition take', 'clear-path'}
OFF = {'loose ball', 'away-from-play'}
K = 500.0
KEYS = ['f_on', 'f_off', 'f_gen']


def season_counts(x):
    cnt, kinds = defaultdict(Counter), Counter()
    for f in sorted(glob.glob(str(PBP[x] / '002*.json'))):
        d = json.load(open(f, encoding='utf-8'))['data']
        for a in (d['game']['actions'] if 'game' in d else d):
            if a.get('actionType') != 'foul' or a.get('subType') != 'personal' or not a.get('personId'):
                continue
            ds = a.get('descriptor')
            k = 'f_on' if ds in ON else 'f_off' if ds in OFF else 'f_gen' if ds is None else None
            kinds[str(ds)] += 1
            if k:
                cnt[int(a['personId'])][k] += 1
    return cnt, kinds


def main():
    per, info = {}, {}
    for x in SEAS:
        cnt, kinds = season_counts(x)
        mins = {int(r['pid']): (r['name'], float(r['minutes'] or 0)) for r in csv.DictReader(open(ROOT / f'reports/E227-lineup-transformer-r2/data/stats-{x}.csv', encoding='utf-8'))}
        per[x] = {p: (nm, m, cnt.get(p, Counter())) for p, (nm, m) in mins.items()}
        info[x] = {'kinds': dict(kinds.most_common()), 'games': len(glob.glob(str(PBP[x] / '002*.json'))),
                   'unmatchedFoulers': sum(1 for p in cnt if p not in mins)}
    out = {}
    for i, t in enumerate(SEAS):
        if t == '2021-22':
            continue
        win = SEAS[max(0, i - 3):i + 1]
        acc = defaultdict(lambda: [None, 0.0, Counter()])
        for x in win:
            for p, (nm, m, c) in per[x].items():
                a = acc[p]; a[0] = nm; a[1] += m; a[2].update(c)
        lg = {k: 36 * sum(a[2][k] for a in acc.values()) / sum(a[1] for a in acc.values()) for k in KEYS}
        out[t] = {DXS.nm(a[0]): {k: (a[2][k] * 36 + K * lg[k]) / (a[1] + K) for k in KEYS} for a in acc.values()}
        for v in out[t].values():
            v['f_ball'] = v['f_on'] + v['f_gen']   # 收縮是線性的，＝有球＋一般合併後再收縮（F3 臂：一般犯規當有球）
        info[t]['window'], info[t]['league36'] = win, lg
    (HERE / 'foul-comps.json').write_text(json.dumps({'k_minutes': K, 'info': info, 'vals': out}, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
