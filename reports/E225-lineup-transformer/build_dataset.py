"""E-225 資料準備：stints → 訓練列＋每季球員能力值表（不訓練、不看任何模型表現）。

位置（R-157）：每段 stint 依當下同邊五人推定——身高（heightInches）由矮到高排，平手時 pass+creation 高者排前，依序指派 PG,SG,SF,PF,C
（0-4，欄位 pa0..pa4／pb0..pb4 對應 a0..a4／b0..b4）；表外球員或身高缺值用該季表內身高中位數、pass／creation 缺值當 0。
上場時間：players-<季>.csv 的 mpg＝該球員該季 stints 總秒數／60／出賽場數（同季 box 等價量；與能力值同屬本季資訊，不含結果欄）。
用法（repo 根目錄）：python -I -X utf8 reports/E225-lineup-transformer/build_dataset.py
輸出：reports/E225-lineup-transformer/data/（.gitignore；大檔不進 git）
      reports/E225-lineup-transformer/manifest.json（輸入／輸出 sha256，進 git）
      reports/E225-lineup-transformer/inventory.json（每季計數，進 git）
純 Python，不開子程序。

訓練列（一段 stint 一列，兩邊都記；side a＝lineups[0]、b＝lineups[1]）：
  X 的進攻數據取自 teams[對方].opponent（該檔以防守方記帳），X 的進攻回合＝teams[對方].defensivePossessions；
  orbX＝對方記帳的 oreb＋teamOreb；drbX＝teams[X].opponent.dreb＋teamDreb（X 的防守籃板）。
切分（依 game id 雜湊，同一場所有 stints 同一組）：
  2025-26、2026-27 → split=forward（整季前向，主訓練完全不碰）。
  其他季：h=sha256('E225|test|'+gid) 前 8 位 mod 100 < 20 → split=test（主測試，凍結前不准看）；
  其餘 split=train，fold＝sha256('E225|fold|'+gid) mod 5（驗證集／k-fold 用）。
"""
import csv, gzip, hashlib, io, json, os, statistics
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data')
R = lambda *p: os.path.join(ROOT, *p)

STINTS = {
    **{s: R('reports', 'defense-seventh', s, 'stints-ff', 'stints.jsonl') for s in ('2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21')},
    '2021-22': R('reports', 'ovr-inseason-2026-27', 'v5', 'pathA', 'ff-2021-22', 'stints-ff', 'stints.jsonl'),
    **{s: R('reports', 'defense-seventh', s, 'stints', 'stints.jsonl') for s in ('2022-23', '2023-24', '2024-25', '2026-27')},
    '2025-26': R('reports', 'defense-b1', 'stints.jsonl'),
}
FORWARD = {'2025-26', '2026-27'}
# 能力值來源：v4 卡＝本季屬性＋OVR（OVR 的 RAPM 窗只用目標季以前，2021-22 無 RAPM）；e111＝本季屬性、無 OVR；2026-27＝live 最新日。
V4 = {s: R('reports', 'ovr-inseason-2026-27', 'v4', 'cards', f'{s}.csv') for s in ('2021-22', '2022-23', '2023-24', '2024-25', '2025-26')}
E111 = {s: R('reports', 'ovr-inseason-2026-27', 'e111-card027', 'cards', f'prior-{s}-027.json') for s in ('2017-18', '2018-19', '2019-20', '2020-21')}
LIVE_DIR = R('reports', 'ovr-inseason-2026-27', 'live')
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'help', 'stamina', 'creation', 'pressure', 'heightInches']
SIDE = ['poss', 'pts', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'ftm', 'tov', 'orb', 'drb', 'rebOpp']
SEASONS = sorted(STINTS)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def hmod(tag, gid, m):
    return int(hashlib.sha256(f'E225|{tag}|{gid}'.encode()).hexdigest()[:8], 16) % m


def live_ranking():
    days = sorted(d for d in os.listdir(LIVE_DIR) if len(d) == 10 and d[:4] == '2026' and os.path.exists(os.path.join(LIVE_DIR, d, 'ranking.csv')))
    return os.path.join(LIVE_DIR, days[-1], 'ranking.csv')


def num(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def load_players(season):
    """回傳 (dict pid->row, 來源路徑, 是否有 OVR)。"""
    if season in V4:
        src, rows = V4[season], list(csv.DictReader(open(V4[season], encoding='utf-8')))
        pid, ovr = 'playerId', 'ovr'
    elif season in E111:
        src, rows = E111[season], json.load(open(E111[season], encoding='utf-8'))['players']
        pid, ovr = 'playerId', None
    elif season == '2026-27':
        src = live_ranking(); rows = list(csv.DictReader(open(src, encoding='utf-8')))
        pid, ovr = 'playerId', 'ovr'
    else:
        return {}, None, False
    out = {}
    for r in rows:
        p = r.get(pid)
        if p in (None, ''):
            continue
        out[int(float(p))] = {'pid': int(float(p)), 'name': r.get('name', ''), 'pos': r.get('pos', ''),
                              'ovr': num(r[ovr]) if ovr else None, **{a: num(r.get(a)) for a in ATTRS}}
    return out, src, ovr is not None


POS_NAMES = ['PG', 'SG', 'SF', 'PF', 'C']


def infer_positions(pids, players, med_h):
    """同邊五人 → 5 個位置索引（依輸入順序回傳）。身高升冪，平手 pass+creation 高者在前，再平手用 pid。"""
    def key(p):
        r = players.get(p) or {}
        h = r.get('heightInches'); h = med_h if h is None else h
        pc = (r.get('pass') or 0.0) + (r.get('creation') or 0.0)
        return (h, -pc, p)
    order = sorted(range(len(pids)), key=lambda i: key(pids[i]))
    pos = [0] * len(pids)
    for rank, i in enumerate(order):
        pos[i] = rank
    return pos


def stint_rows(season, path, players=None):
    med_h = statistics.median([r['heightInches'] for r in players.values() if r['heightInches'] is not None]) if players else 78.0
    for line in open(path, encoding='utf-8'):
        s = json.loads(line); t = s['teams']; gid = s['id']
        row = {'season': season, 'gid': gid, 'period': s['period'], 'sec': s['seconds']}
        if season in FORWARD:
            row['split'], row['fold'] = 'forward', -1
        elif hmod('test', gid, 100) < 20:
            row['split'], row['fold'] = 'test', -1
        else:
            row['split'], row['fold'] = 'train', hmod('fold', gid, 5)
        for k, X in ((0, 'a'), (1, 'b')):
            ps = sorted(s['lineups'][k])
            for j, p in enumerate(ps):
                row[f'{X}{j}'] = p
            for j, q in enumerate(infer_positions(ps, players or {}, med_h)):
                row[f'p{X}{j}'] = q
            row[f'team{X}'] = t[k]['teamId']
        for k, X in ((0, 'a'), (1, 'b')):
            o, own = t[1 - k]['opponent'], t[k]['opponent']   # o：X 進攻時對方記的帳；own：X 防守時自己記的帳
            row[f'poss{X}'] = round(t[1 - k]['defensivePossessions'], 4)
            row[f'pts{X}'] = o['points']
            if 'fga' in o:
                row.update({f'fga{X}': o['fga'], f'fgm{X}': o['fgm'], f'fg3a{X}': o['longA'], f'fg3m{X}': o['longM'],
                            f'fta{X}': o['fta'], f'ftm{X}': o['ftm'], f'tov{X}': o['tov'],
                            f'orb{X}': o['oreb'] + o.get('teamOreb', 0), f'drb{X}': own['dreb'] + own.get('teamDreb', 0),
                            f'rebOpp{X}': o['reboundOpportunities']})
        yield row


def main():
    os.makedirs(OUT, exist_ok=True)
    cols = ['season', 'gid', 'period', 'sec', 'split', 'fold'] + [f'{X}{j}' for X in 'ab' for j in range(5)] + [f'p{X}{j}' for X in 'ab' for j in range(5)] + ['teama', 'teamb'] + [f'{c}{X}' for X in 'ab' for c in SIDE]
    inv, manifest = {}, {'inputs': {}, 'outputs': {}, 'splitRule': "test: sha256('E225|test|'+gid)[:8] mod 100 < 20; fold: sha256('E225|fold|'+gid)[:8] mod 5; forward seasons 2025-26, 2026-27"}
    for season in SEASONS:
        path = STINTS[season]
        players, psrc, has_ovr = load_players(season)
        i = SEASONS.index(season)
        prev_players = load_players(SEASONS[i - 1])[0] if i else {}   # 上一季能力值臂
        n = games = 0; poss = Counter(); splits = Counter(); gs = {}; seen = set()
        slot_sec = slot_hit = slot_prev = slot_ovr = 0.0; minutes = Counter(); gp = defaultdict(set)
        buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols, extrasaction='ignore'); w.writeheader()
        for row in stint_rows(season, path, players):
            w.writerow(row); n += 1; has_box = 'fgaa' in row
            p = row['possa'] + row['possb']; poss[row['split']] += p; splits[row['split']] += 1
            gs.setdefault(row['split'], set()).add(row['gid'])
            for X in 'ab':
                for j in range(5):
                    pid = row[f'{X}{j}']; seen.add(pid); minutes[pid] += row['sec'] / 60; gp[pid].add(row['gid'])
                    slot_sec += row['sec']; hit = players.get(pid)
                    slot_hit += row['sec'] * (hit is not None); slot_ovr += row['sec'] * (hit is not None and hit['ovr'] is not None)
                    slot_prev += row['sec'] * (pid in prev_players)
        fn = os.path.join(OUT, f'stints-{season}.csv.gz')
        with gzip.GzipFile(fn, 'wb', mtime=0) as g:
            g.write(buf.getvalue().encode('utf-8'))
        manifest['inputs'][f'stints-{season}'] = {'file': os.path.relpath(path, ROOT).replace('\\', '/'), 'sha256': sha(path)}
        manifest['outputs'][f'stints-{season}.csv.gz'] = sha(fn)
        attr_stats = {}
        if players:
            pfn = os.path.join(OUT, f'players-{season}.csv')
            with open(pfn, 'w', encoding='utf-8', newline='') as f:
                pw = csv.DictWriter(f, fieldnames=['pid', 'name', 'pos', 'ovr'] + ATTRS + ['mpg']); pw.writeheader()
                for pid in sorted(players):
                    pw.writerow({**players[pid], 'mpg': round(minutes[pid] / len(gp[pid]), 3) if gp.get(pid) else ''})
            manifest['inputs'][f'players-{season}'] = {'file': os.path.relpath(psrc, ROOT).replace('\\', '/'), 'sha256': sha(psrc)}
            manifest['outputs'][f'players-{season}.csv'] = sha(pfn)
            rot = [players[p] for p in players if minutes[p] >= 500]   # 輪替球員才看鑑別力
            for a in ATTRS:
                v = [r[a] for r in rot if r[a] is not None]
                if v:
                    mode_share = Counter(v).most_common(1)[0][1] / len(v)
                    attr_stats[a] = {'sd': round(statistics.pstdev(v), 2), 'modeShare': round(mode_share, 3)}
        inv[season] = {
            'stints': n, 'games': len(set().union(*gs.values())), 'possessions': round(sum(poss.values())),
            'possPerStint': round(sum(poss.values()) / n / 2, 2), 'splits': {k: {'stints': splits[k], 'games': len(gs[k]), 'poss': round(poss[k])} for k in splits},
            'hasBoxFields': has_box, 'players': len(seen),
            'abilitySource': os.path.relpath(psrc, ROOT).replace('\\', '/') if psrc else None, 'hasOvr': has_ovr,
            'pidCoverageBySeconds': round(slot_hit / slot_sec, 4), 'ovrCoverageBySeconds': round(slot_ovr / slot_sec, 4),
            'prevSeasonCoverageBySeconds': round(slot_prev / slot_sec, 4) if prev_players else 0.0,
            'attrDiscrimination500min': attr_stats,
        }
        print(season, n, inv[season]['games'], inv[season]['possessions'], inv[season]['pidCoverageBySeconds'], flush=True)
    json.dump(inv, open(os.path.join(HERE, 'inventory.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(manifest, open(os.path.join(HERE, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
