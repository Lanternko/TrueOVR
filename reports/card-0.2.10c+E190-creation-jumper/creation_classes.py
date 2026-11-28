"""E-190 errata-1 步驟 3：creation 兩版＋各類出手數總表（2025-26）。
輸入 work/history/shots-all-2025-26.csv.gz（extract_classes.py，每筆出手已依 errata-1 歸 R／D／J 一類）。
助攻加權照 build_drive.py：進球被助攻→0、沒被助攻→1、失手→同一計入集合內該 (subType|descriptor) 類別進球中未助攻比例。
  creationKP＝全部出手（R＋D＋J，舊定義的逐球版）；creationJ＝只 J 類。
換算照 attach_creation：分鐘／GP＝season-league-E2 JSON 全季合計，池＝GP≥30 且 MPG≥20，to_attribute；四原點共用同一值（L-091）。
輸出：work/creation-KP-KJ.csv、work/shot-classes.json；tail 檔 work/tails/tail-{KP,KJ}-{U,A}.csv。"""
import csv, gzip, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'
SHOTS = HERE / 'work/history/shots-all-2025-26.csv.gz'
DRIVE_D = HERE / 'work/drive-D.csv'
TAIL_U = ROOT / 'reports/card-0.2.10/tail-U.csv'
TAIL_A = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv'
RANK = ROOT / 'reports/card-0.2.10c/ranking.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def to_attribute(x, pool):
    pct = 100 * (sum(v < x for v in pool) + 0.5 * sum(v == x for v in pool)) / len(pool)
    return max(40, min(99, 40 + (pct - 1) * 30 / 49 if pct < 50 else 70 + (pct - 50) * 29 / 49))


def weighted(shots, keep):
    made, un = Counter(), Counter()
    for s in shots:
        if keep(s) and s['made']:
            made[s['cls']] += 1
            un[s['cls']] += not s['assisted']
    pu = {k: un[k] / made[k] for k in made}
    n = defaultdict(float)
    for s in shots:
        if not keep(s) or (s['made'] and s['assisted']):
            continue
        n[s['pid']] += 1.0 if s['made'] else pu.get(s['cls'], 1.0)
    return n


def main():
    shots = [{'pid': int(r['playerId']), 'made': int(r['made']), 'assisted': int(r['assisted']), 'type': r['type'], 'k': r['klass'], 'cls': r['cls']}
             for r in csv.DictReader(gzip.open(SHOTS, 'rt', encoding='utf-8'))]
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    tot = defaultdict(lambda: {'FGA': 0.0, 'MIN': 0.0, 'GP': 0})
    for t in league['teams']:
        for p in t['roster']:
            x = tot[int(p['playerId'])]
            for k in ('FGA', 'MIN', 'GP'):
                x[k] += p['observed'][k]
    regular = [p for p, t in tot.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    n = {'KP': weighted(shots, lambda s: True), 'KJ': weighted(shots, lambda s: s['k'] == 'J')}
    raw = {a: {p: n[a].get(p, 0.0) / max(t['MIN'], 1) * 36 for p, t in tot.items()} for a in n}
    attr = {a: {p: to_attribute(raw[a][p], [raw[a][q] for q in regular]) for p in tot} for a in n}
    # 出手分類總表
    min500 = {int(r['playerId']) if 'playerId' in r else None for r in []}
    rk = list(csv.DictReader(open(RANK, encoding='utf-8')))
    tailU = {int(r['playerId']): r for r in csv.DictReader(open(TAIL_U, encoding='utf-8'))}
    name2pid = {r['name']: int(r['playerId']) for r in tailU.values()}
    min500 = {name2pid[r['name']] for r in rk if float(r['MIN']) >= 500 and r['name'] in name2pid}

    def table(sel):
        c = Counter()
        for s in shots:
            if sel(s):
                key = (s['k'], s['type'])
                c[key + ('att',)] += 1
                c[key + ('made',)] += s['made']
                c[key + ('unast_made',)] += s['made'] and not s['assisted']
        return {f'{k}|{ty}|{m}': v for (k, ty, m), v in sorted(c.items())}
    top_desc = Counter((s['k'], s['type'], s['cls']) for s in shots)
    summary = {'n_shots': len(shots), 'league': table(lambda s: True), 'MIN500': table(lambda s: s['pid'] in min500), 'n_MIN500': len(min500),
               'top_classes': [{'klass': k, 'type': ty, 'cls': c, 'att': v} for (k, ty, c), v in top_desc.most_common(40)],
               'pool_n': len(regular), 'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (LEAGUE, SHOTS, TAIL_U, TAIL_A, RANK, DRIVE_D, Path(__file__))}}
    (HERE / 'work/shot-classes.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    with open(HERE / 'work/creation-KP-KJ.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['playerId', 'MIN', 'GP', 'raw_KP', 'raw_J', 'creationKP', 'creationJ'])
        for p in sorted(tot):
            w.writerow([p, tot[p]['MIN'], tot[p]['GP'], repr(raw['KP'][p]), repr(raw['KJ'][p]), repr(attr['KP'][p]), repr(attr['KJ'][p])])
    # tails：KP 只換 creation；KJ 換 creation＋drive（U＝tail-U 用 drive_D_U；A＝tail-e123a 用 drive_D_V）
    dd = {int(r['playerId']): r for r in csv.DictReader(open(DRIVE_D, encoding='utf-8'))}
    (HERE / 'work/tails').mkdir(exist_ok=True)
    for src, tag, dcol in ((TAIL_U, 'U', 'drive_D_U'), (TAIL_A, 'A', 'drive_D_V')):
        rows = list(csv.DictReader(open(src, encoding='utf-8')))
        for arm in ('KP', 'KJ'):
            with open(HERE / f'work/tails/tail-{arm}-{tag}.csv', 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                w.writerow(list(rows[0].keys()))
                for r in rows:
                    p = int(r['playerId'])
                    o = dict(r)
                    o['creation'] = repr(float(attr[arm][p]))
                    if arm == 'KJ':
                        o['drive'] = dd[p][dcol]
                    w.writerow([o[k] for k in rows[0].keys()])
    print(json.dumps({k: summary[k] for k in ('n_shots', 'league', 'MIN500', 'n_MIN500', 'pool_n')}, indent=1))


if __name__ == '__main__':
    main()
