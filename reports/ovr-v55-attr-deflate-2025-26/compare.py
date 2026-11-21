"""v55 attr-deflate: compare D1 (and reference boards) against 2K27 / RAPM.

Reuses reports/ovr-v55-2k27-compare/merged.csv for name -> archetype / rank2k /
rapmPooledRank / rapmLastRank / MIN (already built and validated by that report;
not re-scraped here). Reuses existing board ranking.csv files as baselines.

python reports/ovr-v55-attr-deflate-2025-26/compare.py
"""
import csv, json, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent

BOARDS = {
    'v53': ROOT / 'reports/ovr-calibrated-2025-26/ranking.csv',
    'v54': ROOT / 'reports/ovr-v55-finisher-fix-2025-26/card/v54/ranking.csv',
    'B12': ROOT / 'reports/ovr-v55-finisher-fix-2025-26/card/B12/ranking.csv',
    'C1': ROOT / 'reports/ovr-v55-card-origin-attr-2025-26/card-C1/ranking.csv',
    'D1': OUT / 'card/D1/ranking.csv',
}

NAMED_PLAYERS = ['Karlo Matković', 'Jalen Smith', 'John Collins', 'Isaiah Stewart',
                  'Luka Garza', 'Neemias Queta', 'Rudy Gobert']
V53_BASELINE_RANK = {'Karlo Matković': 7, 'John Collins': 29, 'Isaiah Stewart': 32, 'Luka Garza': 33,
                      'Neemias Queta': 51, 'Rudy Gobert': 68, 'Jalen Smith': 104}


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def load_board(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    return {norm(r['name']): {'rank': int(r['rank']), 'MIN': float(r.get('MIN', 0) or 0)} for r in rows}


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    rx = rankdata(xs); ry = rankdata(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx); vy = sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5 if vx > 0 and vy > 0 else None


def rankdata(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def main():
    merged = list(csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/merged.csv', encoding='utf-8-sig')))
    ref = {norm(r['name']): r for r in merged}
    boards = {k: load_board(p) for k, p in BOARDS.items() if p.exists()}

    # 7-named-player table
    named_table = []
    for name in NAMED_PLAYERS:
        key = norm(name)
        row = {'name': name, 'v53Rank': V53_BASELINE_RANK[name]}
        for b, data in boards.items():
            row[b + 'Rank'] = data.get(key, {}).get('rank')
        row['dropVsV53_D1'] = (row.get('D1Rank') - row['v53Rank']) if row.get('D1Rank') else None
        named_table.append(row)

    buckets = [('<800', lambda m: m < 800), ('800-1300', lambda m: 800 <= m < 1300),
               ('1300+', lambda m: m >= 1300), ('all', lambda m: True)]

    correlations = {}
    for b, data in boards.items():
        correlations[b] = {}
        for metric, refkey in [('2k27', 'rank2k'), ('rapmMulti', 'rapmPooledRank'), ('rapmSingle', 'rapmLastRank')]:
            correlations[b][metric] = {}
            for bname, pred in buckets:
                xs, ys = [], []
                for key, d in data.items():
                    r = ref.get(key)
                    if not r or not pred(d['MIN']):
                        continue
                    rv = r.get(refkey)
                    if not rv:
                        continue
                    xs.append(d['rank']); ys.append(float(rv))
                correlations[b][metric][bname] = {'rho': spearman(xs, ys), 'n': len(xs)}

    archetype_medians = {}
    for b, data in boards.items():
        archetype_medians[b] = {}
        for arch in ['吃餅長人', '持球創造', '3D', '其他']:
            ranks = sorted(d['rank'] for key, d in data.items() if ref.get(key, {}).get('archetype') == arch)
            if ranks:
                n = len(ranks)
                med = ranks[n // 2] if n % 2 else (ranks[n // 2 - 1] + ranks[n // 2]) / 2
                archetype_medians[b][arch] = {'median': med, 'n': n}

    # pass/fail
    d1 = {norm(r['name']): r for r in [row for row in named_table]}
    checks = []
    karlo_drop = next(r['dropVsV53_D1'] for r in named_table if r['name'] == 'Karlo Matković')
    checks.append({'criterion': 'Karlo Matković 至少下降 10 名', 'value': karlo_drop, 'pass': karlo_drop is not None and karlo_drop >= 10})
    for name in ['John Collins', 'Isaiah Stewart', 'Luka Garza']:
        d = next(r['dropVsV53_D1'] for r in named_table if r['name'] == name)
        checks.append({'criterion': f'{name} 名次顯著下降（>0）', 'value': d, 'pass': d is not None and d > 0})
    for name in ['Neemias Queta', 'Rudy Gobert', 'Jalen Smith']:
        d = next(r['dropVsV53_D1'] for r in named_table if r['name'] == name)
        checks.append({'criterion': f'{name} 下降不超過 15 名（無誤傷）', 'value': d, 'pass': d is not None and d <= 15})
    rho_d1_2k = correlations.get('D1', {}).get('2k27', {}).get('all', {}).get('rho')
    rho_b12_2k = correlations.get('B12', {}).get('2k27', {}).get('all', {}).get('rho')
    rho_d1_rapm = correlations.get('D1', {}).get('rapmMulti', {}).get('all', {}).get('rho')
    rho_b12_rapm = correlations.get('B12', {}).get('rapmMulti', {}).get('all', {}).get('rho')
    checks.append({'criterion': 'D1 vs 2K27 ρ >= B12 vs 2K27 ρ', 'value': [rho_d1_2k, rho_b12_2k], 'pass': rho_d1_2k is not None and rho_b12_2k is not None and rho_d1_2k >= rho_b12_2k})
    checks.append({'criterion': 'D1 vs 多季RAPM ρ >= B12 vs 多季RAPM ρ', 'value': [rho_d1_rapm, rho_b12_rapm], 'pass': rho_d1_rapm is not None and rho_b12_rapm is not None and rho_d1_rapm >= rho_b12_rapm})
    fed_d1 = archetype_medians.get('D1', {}).get('吃餅長人', {}).get('median')
    fed_v53 = archetype_medians.get('v53', {}).get('吃餅長人', {}).get('median')
    checks.append({'criterion': '吃餅長人原型中位名次下降（相對 v53）', 'value': [fed_d1, fed_v53], 'pass': fed_d1 is not None and fed_v53 is not None and fed_d1 > fed_v53})
    create_d1 = archetype_medians.get('D1', {}).get('持球創造', {}).get('median')
    create_v53 = archetype_medians.get('v53', {}).get('持球創造', {}).get('median')
    checks.append({'criterion': '持球創造原型中位名次未惡化（相對 v53，數值未變大）', 'value': [create_d1, create_v53], 'pass': create_d1 is not None and create_v53 is not None and create_d1 <= create_v53})

    summary = {'namedPlayerTable': named_table, 'correlations': correlations,
               'archetypeMedians': archetype_medians, 'acceptanceChecks': checks}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    with open(OUT / 'ranking.csv', 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        cols = ['name', 'v53Rank'] + [b + 'Rank' for b in boards] + ['dropVsV53_D1']
        wr.writerow(cols)
        for row in named_table:
            wr.writerow([row.get(c, '') for c in cols])

    print(json.dumps(checks, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
