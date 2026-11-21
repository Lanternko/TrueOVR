"""E-142 Phase 0 c0d：整理 T4 DARKO、T5 BPM 到 data/external-impact/，只算覆蓋與對齊，不印、不分析任何候選目標的值。
用法：python -I reports/E142-card-target/c0d_collect.py
輸出：data/external-impact/{darko,bpm}/<季>.csv、README.md；reports/E142-card-target/c0d-coverage.json
"""
import csv, html, json, re, sys, unicodedata, hashlib, datetime
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / 'data/external-impact'
SEASONS = ['2018-19', '2019-20', '2020-21', '2022-23', '2023-24', '2024-25', '2025-26']
END = {s: int(s[:4]) + 1 for s in SEASONS}      # 2018-19 -> 2019
PG = {s: ROOT / ('data/season-source/player-games.json' if s == '2025-26' else f'data/defense-seventh/{s}/player-games.json') for s in SEASONS}

def norm(n):
    n = unicodedata.normalize('NFKD', html.unescape(n)).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r"[.']", '', n); n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n); return re.sub(r'[^a-z]', '', n)

def population(s, min_cut=500):
    d = json.loads(PG[s].read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    mins, names = defaultdict(float), {}
    for r in d['rowSet']:
        if r[h['MIN']]:
            mins[r[h['PLAYER_ID']]] += r[h['MIN']]; names[r[h['PLAYER_ID']]] = r[h['PLAYER_NAME']]
    return {p: names[p] for p, m in mins.items() if m >= min_cut}, {p: names[p] for p in mins}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# ---------- DARKO ----------
def darko_parse(path):
    s = open(path, encoding='utf-8', errors='ignore').read()
    a = s.find('players:{keys:['); seg = s[a:]
    ke = seg.find('],values:')
    keys = json.loads(seg[seg.find('keys:[') + 5:ke + 1]); rest = seg[ke + 9:]
    ins = esc = False; d = 0
    for i, c in enumerate(rest):
        if ins:
            if esc: esc = False
            elif ord(c) == 92: esc = True
            elif c == '"': ins = False
            continue
        if c == '"': ins = True
        elif c == '[': d += 1
        elif c == ']':
            d -= 1
            if d == 0: break
    txt = re.sub(r'(?<=[,\[])(-?)\.(\d)', r'\g<1>0.\2', rest[:i + 1])
    txt = re.sub(r'\bundefined\b|\bNaN\b', 'null', txt)
    cols = json.loads(txt)
    return keys, cols

def build_darko(fetch_date):
    out = {}
    for s in SEASONS:
        raw = EXT / f'darko/raw/darko_season{END[s]}.html'
        keys, cols = darko_parse(raw)
        ix = {k: keys.index(k) for k in ['nba_id', 'player_name', 'season', 'dpm', 'o_dpm', 'd_dpm', 'box_dpm']}
        assert set(cols[ix['season']]) == {END[s]}
        rows = [[cols[ix[k]][j] for k in ['nba_id', 'player_name', 'dpm', 'o_dpm', 'd_dpm', 'box_dpm']] for j in range(len(cols[0]))]
        with open(EXT / f'darko/darko_{s}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh); w.writerow(['playerId', 'name', 'dpm', 'o_dpm', 'd_dpm', 'box_dpm']); w.writerows(rows)
        out[s] = {int(r[0]): r for r in rows}
    return out

# ---------- BPM ----------
BF = ['games', 'mp', 'bpm', 'obpm', 'dbpm', 'vorp']
def bpm_parse(path):
    s = open(path, encoding='utf-8').read(); i = s.find('id="advanced"'); s = s[i:s.find('</table>', i)]; out = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', s, re.S):
        m = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)*([^<]+)', row) or re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row)
        if not m: continue
        nm = html.unescape(m.group(1)); k = norm(nm)
        if k in out: continue                    # 第一列＝TOT
        v = {}
        for f in BF:
            x = re.search(rf'data-stat="{f}"[^>]*>(.*?)</td>', row, re.S)   # L-102：聯盟第一包在 <strong> 裡，先去標籤
            v[f] = re.sub(r'<[^>]+>', '', x.group(1)).strip() if x else ''
        out[k] = (nm, v)
    return out

def build_bpm(pop_all):
    out = {}
    for s in SEASONS:
        y = END[s]; ent = bpm_parse(EXT / f'bpm/adv{y}.html')
        byn = defaultdict(list)
        for pid, nm in pop_all[s].items(): byn[norm(nm)].append(pid)
        rows, un_src = [], []
        for k, (nm, v) in ent.items():
            ps = byn.get(k, [])
            if len(ps) == 1: rows.append([ps[0], nm] + [v[f] for f in BF])
            else: un_src.append(nm)
        with open(EXT / f'bpm/bpm_{s}.csv', 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh); w.writerow(['playerId', 'name'] + BF); w.writerows(rows)
        out[s] = {int(r[0]): r for r in rows if r[4] != ''}
    return out

def main():
    pop, pop_all = {}, {}
    for s in SEASONS: pop[s], pop_all[s] = population(s)
    fetch_date = '2026-10-31'
    D = build_darko(fetch_date); B = build_bpm(pop_all)
    cov = {}
    for tag, src in [('T4_DARKO', D), ('T5_BPM', B)]:
        cov[tag] = {}
        for s in SEASONS:
            have = [p for p in pop[s] if p in src[s]]
            miss = sorted(pop[s][p] for p in pop[s] if p not in src[s])
            cov[tag][s] = {'population_min500': len(pop[s]), 'matched': len(have), 'coverage': round(len(have) / len(pop[s]), 4), 'unmatched_names': miss}
    (ROOT / 'reports/E142-card-target/c0d-coverage.json').write_text(json.dumps({'fetchDate': fetch_date, 'coverage': cov}, ensure_ascii=False, indent=1), encoding='utf-8')
    for tag in cov:
        print(tag, {s: (v['matched'], v['population_min500'], v['coverage']) for s, v in cov[tag].items()})

if __name__ == '__main__':
    main()
