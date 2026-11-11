"""E-190 步驟 2（c0 第二部分）：逐球重算 creation（舊定義＝全部出手）與 creationJ（三分＋>10 呎兩分）。

逐球載入與助攻加權照抄 reports/ovr-v60-drive-split-2025-26/build_drive.py（load_shots／unassisted_rates／aggregate 的 weighted 規則）：
  進球被助攻→0、進球沒被助攻→1、失手→該 (subType, descriptor) 類別進球中沒被助攻的比例（比例在同一個計入集合內算）。
唯一延伸：load_shots 同時收 3pt（build_drive 只收 2pt，因為 drive 只看 2 分）。
窗口、池、to_attribute 照舊 creation（calibrate_wing_t.attach_creation）：分鐘／GP＝season-league-E2 JSON observed 全季合計，
池＝GP≥30 且 MPG≥20，to_attribute 同式。舊欄來源：tail-U.csv（＝tail-e123a.csv）的 creation 欄，四原點共用（L-091）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10c+E190-creation-jumper/build_creation_jumper.py
輸出：work/creation-c0.json、work/creation-recompute.csv（只寫本目錄）。"""
import csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEAGUE = ROOT / 'reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json'   # calibrate_wing_t.LEAGUE 預設（E134_CFG 未改 league 於 2025-26）
MANIFEST = ROOT / 'data/defense-a-source/manifest.json'
TAIL = ROOT / 'reports/card-0.2.10/tail-U.csv'
VALIDATION = ROOT / 'reports/player-impact-v41/2025-26-player-validation.csv'
DIST = 10.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def to_attribute(x, pool):
    pct = 100 * (sum(v < x for v in pool) + 0.5 * sum(v == x for v in pool)) / len(pool)
    return max(40, min(99, 40 + (pct - 1) * 30 / 49 if pct < 50 else 70 + (pct - 50) * 29 / 49))


def load_shots(files):
    shots = []
    for gid in sorted(files):
        for a in json.loads(Path(files[gid]).read_text(encoding='utf-8'))['data']['game']['actions']:
            if a['actionType'] not in ('2pt', '3pt'):
                continue
            shots.append({'pid': a['personId'], 'three': a['actionType'] == '3pt', 'made': a.get('shotResult') == 'Made',
                          'dist': a.get('shotDistance') or 0.0, 'sub': a.get('subType') or '', 'desc': a.get('descriptor') or '',
                          'assisted': a.get('assistPersonId') is not None})
    return shots


def cls(s):
    return (s['sub'], s['desc'] or '(none)')


def weighted(shots, keep):
    made, un = Counter(), Counter()
    for s in shots:
        if s['made'] and keep(s):
            made[cls(s)] += 1
            un[cls(s)] += (not s['assisted'])
    pu = {k: un[k] / made[k] for k in made}
    n = defaultdict(float)
    for s in shots:
        if not keep(s):
            continue
        if s['made']:
            if s['assisted']:
                continue
            w = 1.0
        else:
            w = pu.get(cls(s), 1.0)
        n[s['pid']] += w
    return n, pu


def main():
    man = json.loads(MANIFEST.read_text(encoding='utf-8'))
    files = {s['id']: ROOT / s['file'] for s in man['sources']}
    shots = load_shots(files)
    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    tot = defaultdict(lambda: {'FGA': 0.0, 'MIN': 0.0, 'GP': 0, 'name': None})
    for t in league['teams']:
        for p in t['roster']:
            x = tot[int(p['playerId'])]
            x['name'] = p['name']
            for k in ('FGA', 'MIN', 'GP'):
                x[k] += p['observed'][k]
    regular = [pid for pid, t in tot.items() if t['GP'] >= 30 and t['MIN'] / t['GP'] >= 20]
    keep_old = lambda s: True
    keep_J = lambda s: s['three'] or s['dist'] > DIST
    n_old, _ = weighted(shots, keep_old)
    n_J, puJ = weighted(shots, keep_J)
    raw = {}
    for tag, n in (('old', n_old), ('J', n_J)):
        raw[tag] = {pid: n.get(pid, 0.0) / max(t['MIN'], 1) * 36 for pid, t in tot.items()}
    # 現行公式（attach_creation）在同一份 league JSON 上重算，用來說明舊欄的真正來源
    dep = {r['name']: float(r['creationDependence_sourceRole']) for r in csv.DictReader(open(VALIDATION, encoding='utf-8-sig'))}
    raw['formula'] = {pid: (1 - dep.get(t['name'], 0.0)) * t['FGA'] / max(t['MIN'], 1) * 36 for pid, t in tot.items()}
    attr = {tag: {pid: to_attribute(v[pid], [v[q] for q in regular]) for pid in tot} for tag, v in raw.items()}
    tail = {int(r['playerId']): r for r in csv.DictReader(open(TAIL, encoding='utf-8'))}
    pids = sorted(p for p in tail if p in tot)
    old_col = np.array([float(tail[p]['creation']) for p in pids])
    out = {'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (LEAGUE, MANIFEST, TAIL, VALIDATION, Path(__file__))},
           'games': len(files), 'shots': len(shots), 'players_tail': len(tail), 'players_compared': len(pids), 'pool_n': len(regular)}
    for tag in ('old', 'formula'):
        d = np.array([attr[tag][p] for p in pids]) - old_col
        out[f'diff_{tag}_vs_tail'] = {'max_abs': float(np.max(np.abs(d))), 'mean_abs': float(np.mean(np.abs(d))),
                                      'n_gt_1e-6': int(np.sum(np.abs(d) > 1e-6)), 'n_gt_5': int(np.sum(np.abs(d) > 5)),
                                      'pearson_r': float(np.corrcoef(old_col, old_col + d)[0, 1])}
    # 逐球「舊定義」的 raw 未助攻比例 vs 外部 1−creationDependence（同樣只看 MIN≥500）
    big = [p for p in pids if tot[p]['MIN'] >= 500]
    selfshare_pbp = np.array([n_old.get(p, 0.0) / max(tot[p]['FGA'], 1) for p in big])
    selfshare_dep = np.array([1 - dep.get(tot[p]['name'], 0.0) for p in big])
    out['MIN500'] = {'n': len(big), 'mean_selfshare_pbp': float(selfshare_pbp.mean()), 'mean_selfshare_dep': float(selfshare_dep.mean()),
                     'r_selfshare': float(np.corrcoef(selfshare_pbp, selfshare_dep)[0, 1])}
    worst = sorted(pids, key=lambda p: -abs(attr['old'][p] - float(tail[p]['creation'])))[:10]
    out['worst_old_vs_tail'] = [{'name': tot[p]['name'], 'MIN': tot[p]['MIN'], 'tail': float(tail[p]['creation']), 'pbp_old': attr['old'][p],
                                 'formula': attr['formula'][p], 'selfshare_pbp': n_old.get(p, 0.0) / max(tot[p]['FGA'], 1),
                                 'selfshare_dep': 1 - dep.get(tot[p]['name'], 0.0)} for p in worst]
    (HERE / 'work').mkdir(exist_ok=True)
    with open(HERE / 'work/creation-recompute.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['playerId', 'name', 'MIN', 'GP', 'creation_tail', 'creation_formula', 'creation_pbp_old', 'creationJ',
                    'raw_formula', 'raw_pbp_old', 'raw_J'])
        for p in pids:
            w.writerow([p, tot[p]['name'], tot[p]['MIN'], tot[p]['GP'], tail[p]['creation'], repr(attr['formula'][p]), repr(attr['old'][p]),
                        repr(attr['J'][p]), repr(raw['formula'][p]), repr(raw['old'][p]), repr(raw['J'][p])])
    (HERE / 'work/creation-c0.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
