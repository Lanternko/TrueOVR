"""E-142 Phase 0 c0l：薪水（errata-1 的 M_sal 合約年次）可算性與 2K 歷代評分覆蓋。不算任何指標值，只數覆蓋。
用法：python -I c0l_check.py   輸出 c0l.json
"""
import csv, glob, html, json, re, unicodedata
from collections import defaultdict
from pathlib import Path
here = Path(__file__).resolve().parent
R = here.parents[1]
SRC = R / 'reports/salary-corr/source'
PAGE = {'2021-22': 'contracts2022.html', '2022-23': 'contracts2023.html', '2023-24': 'contracts2024.html',
        '2024-25': 'contracts2025.html', '2025-26': 'bref2526.html', '2026-27': 'bref.html'}
ORDER = list(PAGE)
CARD = ['2022-23', '2023-24', '2024-25', '2025-26']
PG = {s: R / ('data/season-source/player-games.json' if s == '2025-26' else f'data/defense-seventh/{s}/player-games.json') for s in CARD}
TX = {'2020-21': 'tx2021.html', '2021-22': 'tx2022.html', '2022-23': 'tx2023.html', '2023-24': 'tx2024.html', '2024-25': 'tx2025.html', '2025-26': 'tx2026.html'}
TEAMFIX = {'BRK': 'BKN', 'PHO': 'PHX', 'CHO': 'CHA'}


def norm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n)
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    return re.sub(r'[^a-z]', '', n)


def money(row, stat):
    m = re.search(r'data-stat="%s"[^>]*>\$?([\d,]+)' % stat, row)
    return int(m.group(1).replace(',', '')) if m else None


def contracts(season):
    s = (SRC / PAGE[season]).read_text(encoding='utf-8')
    out = defaultdict(list)
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row)
        if not m or money(row, 'y1') is None:
            continue
        t = re.search(r'data-stat="team_id"[^>]*>(?:<a[^>]*>)?([A-Z]{3})', row)
        sched = [money(row, f'y{i}') for i in range(1, 7)]
        n = 0
        for v in sched:
            if v is None:
                break
            n += 1
        out[norm(m.group(1))].append({'team': TEAMFIX.get(t.group(1), t.group(1)) if t else None, 'sched': sched[:n]})
    return out


def draft_years():
    out = {}
    for f in glob.glob(str(R / 'data/**/bio.json'), recursive=True):
        try:
            d = json.loads(Path(f).read_text(encoding='utf-8'))['data']['resultSets'][0]
        except Exception:
            continue
        h = {k: i for i, k in enumerate(d['headers'])}
        if 'DRAFT_YEAR' not in h:
            continue
        for r in d['rowSet']:
            out[r[h['PLAYER_ID']]] = (r[h['DRAFT_YEAR']], r[h['DRAFT_ROUND']])
    return out


def population(s):
    d = json.loads(PG[s].read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    mins, names, games = defaultdict(float), {}, defaultdict(lambda: defaultdict(int))
    for r in d['rowSet']:
        if r[h['MIN']]:
            p = r[h['PLAYER_ID']]
            mins[p] += r[h['MIN']]
            names[p] = r[h['PLAYER_NAME']]
            games[p][r[h['TEAM_ABBREVIATION']]] += 1
    return {p: (names[p], max(games[p], key=games[p].get)) for p, m in mins.items() if m >= 500}


def same_contract(prev, cur):
    """prev 為前一季的 y1..；cur 為當季的 y1..；前季往後的年份要和當季前綴一致。"""
    if len(prev) < 2:
        return False
    n = min(len(prev) - 1, len(cur))
    return all(abs(prev[i + 1] - cur[i]) <= 0.01 * cur[i] + 1 for i in range(n))


def pick(rows, team):
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    same = [r for r in rows if r['team'] == team]
    return same[0] if same else max(rows, key=lambda r: r['sched'][0])


def tx_events():
    ev = defaultdict(list)
    for win, f in TX.items():
        s = (SRC / f).read_text(encoding='utf-8')
        for d, body in re.findall(r'<li[^>]*>\s*<span>([^<]+)</span>(.*?)</li>', s, re.S):
            for p in re.findall(r'<p>(.*?)</p>', body, re.S):
                t = html.unescape(re.sub('<[^>]+>', '', p))
                m = re.search(r'signed (.+?) to (a|an) (multi-year contract|contract extension)\.$', t)
                if not m:
                    continue
                mo = re.match(r'([A-Za-z]+) (\d+), (\d{4})', d)
                if not mo:
                    continue
                import datetime
                dt = datetime.datetime.strptime(f'{mo.group(1)} {mo.group(2)} {mo.group(3)}', '%B %d %Y').date()
                for nm in re.split(r', and |, | and ', m.group(1)):
                    ev[norm(nm)].append((dt, 'ext' if 'extension' in m.group(3) else 'fa'))
    return ev


def start_year_of_fa(dt):
    return dt.year if dt.month >= 7 else dt.year - 1


def main():
    pages = {s: contracts(s) for s in ORDER}
    drafts = draft_years()
    ev = tx_events()
    res = {}
    for t in CARD:
        pop = population(t)
        ti = ORDER.index(t)
        cat = defaultdict(int)
        names = defaultdict(list)
        newsign = 0
        for pid, (nm, team) in pop.items():
            k = norm(nm)
            dy, rd = drafts.get(pid, (None, None))
            try:
                D = int(dy)
            except Exception:
                D = None
            rookie = D is not None and str(rd) == '1' and 0 <= int(t[:4]) - D <= 3
            row = pick(pages[t].get(k), team)
            if rookie:
                cat['rookie_excluded'] += 1
                continue
            if row is None:
                cat['no_salary_row'] += 1
                names['no_salary_row'].append(nm)
                continue
            cur = row['sched']
            # 往回找合約起點
            start = ORDER[ti]
            censored = False
            j = ti
            while True:
                if j == 0:
                    censored = True
                    break
                nxt = None
                for cand in pages[ORDER[j - 1]].get(k, []):
                    if same_contract(cand['sched'], cur):
                        nxt = cand
                        break
                if nxt is None:
                    break
                cur = nxt['sched']
                j -= 1
            start = ORDER[j]
            ends = int(t[:4]) + len(row['sched']) - 1
            dated = None
            if censored:
                # 左端截斷（起點 <= 2021-22）：靠 tx 簽約事件補
                evs = [e for e in ev.get(k, []) if e[0].year >= 2020]
                fa = [e for e in evs if e[1] == 'fa']
                if fa:
                    dated = 'fa'
                    start_season = start_year_of_fa(fa[-1][0])
                elif evs:
                    dated = 'ext'
                else:
                    cat['undated_censored'] += 1
                    names['undated_censored'].append(nm)
                    continue
                cat['year_computable_via_tx'] += 1
            else:
                cat['year_computable_via_pages'] += 1
                sy = int(start[:4])
                near = [e for e in ev.get(k, []) if sy - 1 <= e[0].year <= sy + 1]
                cat['  of which has_tx_signing_date'] += 1 if near else 0
            if ti + 1 < len(ORDER):
                nrows = pages[ORDER[ti + 1]].get(k, [])
                if nrows and not any(same_contract(row['sched'], c['sched']) for c in nrows) and len(row['sched']) > 0:
                    newsign += 1
        n = len(pop)
        computable = cat['year_computable_via_pages'] + cat['year_computable_via_tx']
        res[t] = {'pop': n, **dict(cat), 'newContractAfter_reportOnly': newsign,
                  'cov_yearComputable_among_nonrookie': round(computable / (n - cat['rookie_excluded']), 4),
                  'cov_determined_incl_rookie_excluded': round((computable + cat['rookie_excluded']) / n, 4),
                  'undatedNames': names['undated_censored'][:60], 'noSalaryRowNames': names['no_salary_row'][:60]}
        print(t, {k: v for k, v in res[t].items() if 'Names' not in k})
    # 2K 歷代
    k2 = {norm(r['name']): r for r in csv.DictReader(open(R / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv', encoding='utf-8'))}
    MAP = {'2018-19': '2K20', '2019-20': '2K21', '2020-21': '2K22', '2022-23': '2K24', '2023-24': '2K25', '2024-25': '2K26', '2025-26': '2K27'}
    twok = {}
    for s, col in MAP.items():
        pg = PG.get(s) or (R / f'data/defense-seventh/{s}/player-games.json')
        d = json.loads(pg.read_text(encoding='utf-8'))['data']['resultSets'][0]
        h = {k: i for i, k in enumerate(d['headers'])}
        mins, nm = defaultdict(float), {}
        for r in d['rowSet']:
            if r[h['MIN']]:
                mins[r[h['PLAYER_ID']]] += r[h['MIN']]
                nm[r[h['PLAYER_ID']]] = r[h['PLAYER_NAME']]
        pop = [nm[p] for p, m in mins.items() if m >= 500]
        miss = [n for n in pop if not (k2.get(norm(n), {}).get(col) or '').strip()]
        twok[s] = {'edition': col, 'pop': len(pop), 'covered': len(pop) - len(miss), 'coverage': round(1 - len(miss) / len(pop), 4), 'missingNames': miss[:40]}
        print(s, col, twok[s]['coverage'])
    (here / 'c0l.json').write_text(json.dumps({'salary': res, 'twoK': twok}, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
