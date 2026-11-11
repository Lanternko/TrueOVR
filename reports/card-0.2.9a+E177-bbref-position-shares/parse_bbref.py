"""E-177：解析 work/bbref/ 的 BBRef play-by-play 頁 → pos-shares-{季}.csv，並算 s0／s1（預註冊 §3）。
- 每位球員取一列；換隊者取合併列（team_name_abbr 為 2TM／3TM…）。pct_1…pct_5＝PG、SG、SF、PF、C（顯示的整數 %）。
- playerId：BBRef 名字（norm）對卡片人群（E-164 S 臂各原點的部件卡 pred.csv）；對不到、BBRef 重名或人群重名 → 空白（建卡時退回現行標籤 one-hot）。
- 用法（repo root）：python -I -B -X utf8 reports/card-0.2.9a+E177-bbref-position-shares/parse_bbref.py
"""
import csv, html, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E164 = ROOT / 'reports/card-0.2.9+E164-no-stamina'
SEAS = {'2022-23': 2023, '2023-24': 2024, '2024-25': 2025, '2025-26': 2026}
POS = ['PG', 'SG', 'SF', 'PF', 'C']


def norm(n):   # 同 reports/E142-card-target/c0l_check.py::norm（卡片人群既有對名方式）
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n)
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def cell(row, stat):
    m = re.search(r'data-stat="%s"[^>]*>(.*?)</(?:td|th)>' % stat, row, re.S)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else None


def parse_page(path):
    h = Path(path).read_text(encoding='utf-8')
    rows = []
    for tr in re.findall(r'<tr[ >].*?</tr>', h, re.S):
        if 'data-stat="pct_1"' not in tr or 'data-stat="name_display"' not in tr:
            continue
        slug = re.search(r'data-append-csv="([^"]+)"', tr)
        if not slug:   # 表頭列
            continue
        d = {'bbref_id': slug.group(1), 'name': html.unescape(cell(tr, 'name_display')), 'team': cell(tr, 'team_name_abbr'),
             'MP': cell(tr, 'mp')}
        for k in range(1, 6):
            v = cell(tr, f'pct_{k}')
            d[f'p_{POS[k - 1]}'] = int(v) if v not in (None, '') else 0
        rows.append(d)
    by = defaultdict(list)
    for r in rows:
        by[r['bbref_id']].append(r)
    out = []
    for slug, rs in by.items():
        tm = [r for r in rs if re.fullmatch(r'\d+TM', r['team'] or '')]
        out.append(tm[0] if tm else rs[0])
    return out


def population(t):
    """E-164 S 臂該原點部件卡的 pred.csv：playerId→name（三張卡聯集）。"""
    d = E164 / 'work' / f'base-S-{t}' / ('c0' if t == '2025-26' else t) / 'cards/K0'
    pop = {}
    for part in ('primary', 'fitA', 'fitB'):
        for r in csv.DictReader(open(d / part / 'pred.csv', encoding='utf-8')):
            pop[int(r['playerId'])] = r['name']
    return pop


def main():
    res = {}
    for t, y in SEAS.items():
        rows = parse_page(ROOT / f'work/bbref/NBA_{y}_play-by-play.html')
        pop = population(t)
        pn = defaultdict(list)
        for pid, nm in pop.items():
            pn[norm(nm)].append(pid)
        bn = defaultdict(int)
        for r in rows:
            bn[norm(r['name'])] += 1
        for r in rows:
            k = norm(r['name'])
            ids = pn.get(k, [])
            r['match'] = 'dup_bbref' if bn[k] > 1 else ('none' if not ids else ('dup_pop' if len(ids) > 1 else 'ok'))
            r['playerId'] = ids[0] if r['match'] == 'ok' else ''
        cols = ['playerId', 'name', 'bbref_id', 'team', 'MP'] + [f'p_{p}' for p in POS] + ['match']
        with open(HERE / f'pos-shares-{t}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, cols); w.writeheader()
            for r in sorted(rows, key=lambda r: r['bbref_id']):
                w.writerow({c: r[c] for c in cols})
        # s0／s1：卡片人群（ranking-S MIN>=500）
        byid = {r['playerId']: r for r in rows if r['playerId'] != ''}
        rk = [r for r in csv.DictReader(open(E164 / f'ranking-S-{t}.csv', encoding='utf-8-sig')) if float(r['MIN']) >= 500]
        n = len(rk); found = usable = diff = 0; ex = []
        for r in rk:
            ids = pn.get(norm(r['name']), [])
            s = byid.get(ids[0]) if len(ids) == 1 else None
            if s is None:
                continue
            found += 1
            v = [s[f'p_{p}'] for p in POS]
            if int(s['MP'].replace(',', '') or 0) >= 200 and sum(v) > 0:
                usable += 1
                if POS[max(range(5), key=lambda i: v[i])] != r['pos']:
                    diff += 1
                    if len(ex) < 8:
                        ex.append((r['name'], r['pos'], v))
        res[t] = {'bbref_rows': len(rows), 'pop_cards': len(pop), 'card_MIN500': n, 'found': found, 'found_pct': found / n, 'usable': usable,
                  'usable_pct': usable / n, 'argmax_differs_from_label': diff, 'argmax_differs_pct_of_usable': diff / max(usable, 1),
                  'match_status': {m: sum(1 for r in rows if r['match'] == m) for m in ('ok', 'none', 'dup_bbref', 'dup_pop')}, 'examples': ex}
    jw = next(r for r in parse_page(ROOT / 'work/bbref/NBA_2026_play-by-play.html') if r['name'] == 'Jalen Williams')
    res['selfcheck_JW_2025-26'] = [jw[f'p_{p}'] for p in POS]
    assert res['selfcheck_JW_2025-26'] == [0, 18, 51, 31, 0], res['selfcheck_JW_2025-26']
    res['s0_pass'] = res['2025-26']['usable_pct'] >= 0.95 and res['2025-26']['found_pct'] >= 0.95
    (HERE / 's0_s1.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: (v if not isinstance(v, dict) else {a: b for a, b in v.items() if a != 'examples'}) for k, v in res.items()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
