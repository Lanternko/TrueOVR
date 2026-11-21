"""E-227 資料建置：(1) 重切 2025-26（同 E-225 雜湊規則）並只輸出 split=train 的 stint；(2) 球員能力值表；(3) 統計向量表與涵蓋率。
來源：stints／players 取自 E-225 的 data/（不改 E-225）；統計取自 reports/defense-tenth/step4-t2/raw/<季>/0-*.json（聯盟層級，TeamID=0），
box（STL/BLK/PF/OREB/DREB）與出賽分鐘取自各季 player-games.json（場次紀錄加總）。2021-22 的 hustle／rim／three／matchups／advanced 取不到
（stats.nba.com 本機與 5090 皆連線逾時，見 fetch-2021-22.md）→ 該類欄位全部缺值（mask=0）；box 五欄 2021-22 仍可由 player-games 算出。
禁用欄位（DEF_RATING、OFF_RATING、NET_RATING、PIE、PLUSMINUS、W/L 與任何同場得失分欄）不讀。
用法（在本目錄）：python -I -X utf8 build_data.py"""
import csv, gzip, hashlib, io, json, os
from collections import Counter, defaultdict

from e227_common import ATTRS, DATA, HERE, SEASONS, STAT_CLASSES, STATS, MIN_MINUTES

ROOT = os.path.dirname(os.path.dirname(HERE))
E225 = os.path.join(ROOT, 'reports', 'E225-lineup-transformer', 'data')
RAW = os.path.join(ROOT, 'reports', 'defense-tenth', 'step4-t2', 'raw')
PG = {s: os.path.join(ROOT, 'data', 'defense-seventh', s, 'player-games.json') for s in SEASONS[:-1]}
PG['2025-26'] = os.path.join(ROOT, 'data', 'season-source', 'player-games.json')


def hmod(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def table(path):
    d = json.load(open(path, encoding='utf-8'))
    d = d.get('data', d); t = d['resultSets']; t = t[0] if isinstance(t, list) else t
    return [dict(zip(t['headers'], r)) for r in t['rowSet']]


def mins(v):
    if v is None:
        return 0.0
    if isinstance(v, str) and ':' in v:
        a, b = v.split(':'); return int(a) + int(b) / 60
    return float(v)


def build_stints(report):
    for s in SEASONS:
        src = os.path.join(E225, f'stints-{s}.csv.gz'); out = []; n = Counter(); diff = 0
        with gzip.open(src, 'rt', encoding='utf-8') as f:
            rd = csv.DictReader(f); cols = rd.fieldnames
            for r in rd:
                gid = r['gid']
                sp = 'test' if hmod('test', gid, 100) < 20 else 'train'
                fo = hmod('fold', gid, 5) if sp == 'train' else -1
                if s != '2025-26' and (r['split'] != sp or (sp == 'train' and int(r['fold']) != fo)):
                    diff += 1
                n[sp] += 1
                if sp == 'train':
                    r['split'] = 'train'; r['fold'] = fo; out.append(r)
        fn = os.path.join(DATA, f'stints-train-{s}.csv.gz')
        buf = io.StringIO(); w = csv.writer(buf, lineterminator='\n'); w.writerow(cols)
        for r in out:
            w.writerow([r[c] for c in cols])
        with gzip.GzipFile(fn, 'wb', mtime=0) as g:
            g.write(buf.getvalue().encode('utf-8'))
        games = len({r['gid'] for r in out})
        report['stints'][s] = {'trainStints': n['train'], 'trainGames': games, 'testStintsWithheldNotWritten': n['test'],
                               'splitMismatchVsE225': diff, 'sha256': sha(fn)}
        print(s, dict(n), 'mismatch vs E225:', diff, flush=True)


def build_players(report):
    for s in SEASONS:
        src = os.path.join(E225, f'players-{s}.csv')
        with open(src, encoding='utf-8') as f, open(os.path.join(DATA, f'players-{s}.csv'), 'w', encoding='utf-8', newline='') as g:
            rd = csv.DictReader(f)
            w = csv.DictWriter(g, fieldnames=['pid', 'name', 'pos'] + ATTRS, extrasaction='ignore'); w.writeheader()
            for r in rd:
                w.writerow(r)


def stint_seconds(s):
    sec = Counter()
    with gzip.open(os.path.join(DATA, f'stints-train-{s}.csv.gz'), 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for x in 'ab':
                for j in range(5):
                    sec[r[f'{x}{j}']] += float(r['sec'])
    return sec


def build_stats(report):
    for s in SEASONS:
        pg = defaultdict(Counter); names = {}
        for r in table(PG[s]):
            p = str(r['PLAYER_ID']); m = mins(r['MIN'])
            if m <= 0:
                continue
            c = pg[p]; c['MIN'] += m; c['G'] += 1; names[p] = r['PLAYER_NAME']
            for k in ('STL', 'BLK', 'PF', 'OREB', 'DREB'):
                c[k] += r[k] or 0
        feats = defaultdict(dict); present = defaultdict(set)
        raw = os.path.join(RAW, s)
        have_raw = os.path.isdir(raw)
        mn = lambda p: pg[p]['MIN'] if p in pg else 0
        if have_raw:
            for r in table(os.path.join(raw, '0-hustle.json')):
                p = str(r['PLAYER_ID']); m = mn(p)
                present[p].add('hustle')
                if m >= MIN_MINUTES:
                    f = 36 / m
                    feats[p].update(deflections36=r['DEFLECTIONS'] * f, cont2pt36=r['CONTESTED_SHOTS_2PT'] * f, cont3pt36=r['CONTESTED_SHOTS_3PT'] * f,
                                    charges36=r['CHARGES_DRAWN'] * f, looseO36=r['OFF_LOOSE_BALLS_RECOVERED'] * f, looseD36=r['DEF_LOOSE_BALLS_RECOVERED'] * f,
                                    boxoutO36=r['OFF_BOXOUTS'] * f, boxoutD36=r['DEF_BOXOUTS'] * f, screenAst36=r['SCREEN_ASSISTS'] * f)
            rim = {str(r['CLOSE_DEF_PERSON_ID']): r for r in table(os.path.join(raw, '0-rim.json'))}
            three = {str(r['CLOSE_DEF_PERSON_ID']): r for r in table(os.path.join(raw, '0-three.json'))}
            for p in set(rim) | set(three):
                present[p].add('rimthree'); m = mn(p)
                if m >= MIN_MINUTES:
                    f = 36 / m
                    if p in rim and rim[p]['LT_06_PCT'] is not None and rim[p]['NS_LT_06_PCT'] is not None:
                        feats[p].update(rimDiff=rim[p]['LT_06_PCT'] - rim[p]['NS_LT_06_PCT'], rimFGA36=rim[p]['FGA_LT_06'] * f)
                    if p in three and three[p]['FG3_PCT'] is not None and three[p]['NS_FG3_PCT'] is not None:
                        feats[p].update(threeDiff=three[p]['FG3_PCT'] - three[p]['NS_FG3_PCT'], threeFGA36=three[p]['FG3A'] * f)
            mp = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
            for r in table(os.path.join(raw, '0-matchups.json')):
                a = mp[str(r['DEF_PLAYER_ID'])]
                a[0] += r['PLAYER_PTS'] or 0; a[1] += r['PARTIAL_POSS'] or 0; a[2] += r['MATCHUP_FGM'] or 0; a[3] += r['MATCHUP_FGA'] or 0
            for p, a in mp.items():
                present[p].add('matchup')
                if mn(p) >= MIN_MINUTES and a[1] > 0 and a[3] > 0:
                    feats[p].update(oppPtsPerPoss=a[0] / a[1], oppFGpct=a[2] / a[3])
            for r in table(os.path.join(raw, '0-advanced.json')):
                p = str(r['PLAYER_ID']); present[p].add('adv')
                if mn(p) >= MIN_MINUTES:
                    feats[p].update(usg=r['USG_PCT'], astPct=r['AST_PCT'], ts=r['TS_PCT'], orebPct=r['OREB_PCT'], drebPct=r['DREB_PCT'], tovPct=r['TM_TOV_PCT'])
        for p, c in pg.items():
            present[p].add('box')
            if c['MIN'] >= MIN_MINUTES:
                f = 36 / c['MIN']
                feats[p].update(stl36=c['STL'] * f, blk36=c['BLK'] * f, pf36=c['PF'] * f, oreb36=c['OREB'] * f, dreb36=c['DREB'] * f)
        pids = sorted(set(pg) | set(feats))
        with open(os.path.join(DATA, f'stats-{s}.csv'), 'w', encoding='utf-8', newline='') as g:
            w = csv.writer(g); w.writerow(['pid', 'name', 'minutes'] + STATS)
            for p in pids:
                w.writerow([p, names.get(p, ''), round(mn(p), 1)] + [('' if feats[p].get(k) is None else round(feats[p][k], 6)) for k in STATS])
        sec = stint_seconds(s); tot = sum(sec.values()); plist = list(sec)
        cov = {}
        for cl, cols in STAT_CLASSES.items():
            idf = sum(sec[p] for p in plist if cl in present.get(p, ())) / tot
            val = sum(sec[p] for p in plist if all(feats[p].get(k) is not None for k in cols)) / tot
            cov[cl] = {'idFoundBySeconds': round(idf, 4), 'validBySeconds_ge200min': round(val, 4)}
        pl = {r['pid'] for r in csv.DictReader(open(os.path.join(DATA, f'players-{s}.csv'), encoding='utf-8'))}
        cov['ability'] = {'idFoundBySeconds': round(sum(sec[p] for p in plist if p in pl) / tot, 4)}
        cov['playersInTrainStints'] = len(plist)
        cov['playersGE200min'] = sum(1 for p in plist if mn(p) >= MIN_MINUTES)
        cov['rawTrackingFilesAvailable'] = have_raw
        cov['matchMethod'] = 'playerId（所有統計檔皆有 playerId，未使用姓名比對）'
        cov['lt200minSecondsShare'] = round(sum(sec[p] for p in plist if mn(p) < MIN_MINUTES) / tot, 4)
        report['coverage'][s] = cov
        print(s, json.dumps(cov, ensure_ascii=False), flush=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    report = {'stints': {}, 'coverage': {}, 'note': 'test 場次只用來決定 split 標籤，從不寫出、從不評估'}
    build_stints(report); build_players(report); build_stats(report)
    json.dump(report, open(os.path.join(HERE, 'coverage.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
