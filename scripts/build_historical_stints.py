"""Build RAPM stints for seasons the cdn.nba.com liveData feed does not cover (2010-11 .. 2020-21).

Sources (both are mirrors of NBA official data, fetched from raw.githubusercontent.com):
  play-by-play  shufinskiy/nba_data  datasets/nbastats_<startYear>.tar.xz  (stats.nba.com playbyplayv2)
  box scores    NocturneBear/NBA-Data-2010-2024  regular_season_box_scores_2010_2024_part_{1,2,3}.csv
                (stats.nba.com boxscoretraditionalv3: personId, position = starter flag, minutes mm:ss)

  python3 -I scripts/build_historical_stints.py --pbp <nbastats_YYYY.csv> --box <dir with box csvs> \
      --season 2016-17 --out <dir>

Writes <out>/stints.jsonl in the same shape as scripts/prepare_defense_b1.js, so
reports/impact-rapm/rapm.py can read it, plus <out>/preparation.json (validation) and
<out>/player-minutes.csv (official box minutes per player, team and game).

Lineups: period 1 starters come from the box score; later periods are inferred from who acts
or is subbed out before being subbed in. A period still short of five is completed with the
team player whose reconstructed minutes fall furthest below the box score. A game is kept only
if every player's reconstructed seconds are within the tolerance of the box score and both
final scores match, the same all-or-nothing rule prepare_defense_b1.js uses.

Possessions are integer possession ends credited to the stint where they happen: made field
goal (not followed by an and-one free throw), final free throw of a trip (technical, flagrant
and clear-path trips excluded), defensive rebound of a live miss, turnover, period end.
prepare_defense_b1.js instead prorates possessions by clock overlap, so stint-level counts
differ slightly; season totals agree (see preparation.json and the overlap check).
"""
import argparse, csv, glob, hashlib, json, os, re, sys
from collections import defaultdict

TOL = 2.1  # seconds; box minutes here are whole seconds and older box scores carry ±2 s rounding fixes


def clock(s):
    m, sec = s.split(':')
    return int(m) * 60 + float(sec)


def period_len(p):
    return 720 if p <= 4 else 300


def mmss(v):
    if not v:
        return 0.0
    m = re.match(r'^(\d+):(\d+)$', v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r'^PT(\d+)M([\d.]+)S$', v)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    return float(v) * 60


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_box(box_dir, season):
    games = defaultdict(lambda: defaultdict(dict))  # gid -> team -> pid -> row
    files = sorted(glob.glob(os.path.join(box_dir, 'regular_season_box_scores_*.csv')))
    for f in files:
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if r['season_year'] != season:
                continue
            games[int(r['gameId'])][int(r['teamId'])][int(r['personId'])] = r
    return games, files


def desc(r):
    return ' '.join(x for x in (r['HOMEDESCRIPTION'], r['NEUTRALDESCRIPTION'], r['VISITORDESCRIPTION']) if x)


def team_of(r, home, away):
    t = r['PERSON1TYPE']
    if t in ('2', '4'):
        return home
    if t in ('3', '5'):
        return away
    return None


FT_RE = re.compile(r'Free Throw (Technical|Flagrant|Clear Path)?.*?(\d) of (\d)', re.I)


def build_game(gid, events, box):
    teams = list(box.keys())
    if len(teams) != 2:
        return None, ['box teams != 2']
    # Home team: PERSON1TYPE 4 players belong to it.
    home = away = None
    for r in events:
        if r['PERSON1TYPE'] in ('4', '5') and r['PLAYER1_TEAM_ID']:
            t = int(r['PLAYER1_TEAM_ID'])
            if t in box:
                home = t if r['PERSON1TYPE'] == '4' else [x for x in teams if x != t][0]
                break
    if home is None:
        return None, ['no home team']
    away = [x for x in teams if x != home][0]
    ids = [home, away]
    roster = {t: set(box[t]) for t in ids}
    box_sec = {t: {p: mmss(box[t][p]['minutes']) for p in box[t]} for t in ids}
    starters = {t: [p for p, r in box[t].items() if r['position']] for t in ids}
    errors = []
    if any(len(starters[t]) != 5 for t in ids):
        return None, ['starters != 5']
    by_period = defaultdict(list)
    for r in events:
        by_period[int(r['PERIOD'])].append(r)

    def pteam(pid):
        for t in ids:
            if pid in roster[t]:
                return t
        return None

    # Infer period starters.
    period_starters = {}
    for p in sorted(by_period):
        if p == 1:
            period_starters[p] = {t: set(starters[t]) for t in ids}
            continue
        found = {t: [] for t in ids}
        subbed_in = set()
        for r in by_period[p]:
            et = r['EVENTMSGTYPE']
            if et == '8':
                out, inn = int(r['PLAYER1_ID'] or 0), int(r['PLAYER2_ID'] or 0)
                if out not in subbed_in and pteam(out) and out not in found[pteam(out)]:
                    found[pteam(out)].append(out)
                subbed_in.add(inn)
                continue
            if et in ('9', '11', '12', '13', '18'):
                continue
            for k in ('PLAYER1_ID', 'PLAYER2_ID', 'PLAYER3_ID'):
                if k != 'PLAYER1_ID' and et not in ('1', '2', '5', '10'):
                    continue  # PLAYER2/3 of fouls/violations are often off-court or referees
                pid = int(r[k] or 0)
                t = pteam(pid)
                if t and pid not in subbed_in and pid not in found[t]:
                    found[t].append(pid)
        period_starters[p] = {t: set(found[t]) for t in ids}

    def run(ps):
        """Walk events; return stints, per-player seconds, final scores, errors."""
        stints, secs, errs = [], defaultdict(float), []
        score = {home: 0, away: 0}
        for p in sorted(by_period):
            on = {t: set(ps[p][t]) for t in ids}
            plen = period_len(p)
            cur = None

            def open_stint(t0):
                return {'period': p, 'start': t0, 'end': t0, 'lineups': [sorted(on[t]) for t in ids],
                        'pts': {home: 0, away: 0}, 'poss': {home: 0, away: 0}}

            cur = open_stint(plen)
            last_miss = None  # (team, live)
            last_off = None
            pending_fg = None  # (team, clock, shooter) made FG awaiting possible and-one
            evs = by_period[p]
            for i, r in enumerate(evs):
                et = r['EVENTMSGTYPE']
                c = clock(r['PCTIMESTRING'])
                t = team_of(r, home, away)
                d = desc(r)
                if pending_fg and not (et == '3' and c == pending_fg[1]) and not (et in ('6', '8', '9', '18') and c == pending_fg[1]):
                    cur['poss'][pending_fg[0]] += 1
                    pending_fg = None
                if et == '8':
                    out, inn = int(r['PLAYER1_ID'] or 0), int(r['PLAYER2_ID'] or 0)
                    tt = pteam(out) or pteam(inn)
                    if tt is None or out not in on[tt]:
                        errs.append(f'P{p} sub out not on court {out}')
                        if tt is None:
                            continue
                    cur['end'] = c
                    stints.append(cur)
                    on[tt].discard(out)
                    on[tt].add(inn)
                    cur = open_stint(c)
                    continue
                if r['SCORE']:
                    a, h = [int(x) for x in r['SCORE'].split(' - ')]
                    dh, da = h - score[home], a - score[away]
                    if dh:
                        cur['pts'][home] += dh
                    if da:
                        cur['pts'][away] += da
                    score[home], score[away] = h, a
                if et == '1':
                    last_off = t
                    pending_fg = (t, c, int(r['PLAYER1_ID'] or 0))
                elif et == '2':
                    last_miss, last_off = (t, True), t
                elif et == '3':
                    last_off = t
                    m = FT_RE.search(d)
                    special = bool(m and m.group(1)) or 'Technical' in d
                    final = bool(m and m.group(2) == m.group(3)) and not special
                    if pending_fg and pending_fg[0] == t and c == pending_fg[1]:
                        pending_fg = None  # and-one: possession ends at the FT
                    if final:
                        if 'MISS' in d:
                            last_miss = (t, True)
                        else:
                            cur['poss'][t] += 1
                            last_miss = None
                    elif 'MISS' in d:
                        last_miss = (t, False)
                elif et == '4':
                    if last_miss and t is not None:
                        if t != last_miss[0] and last_miss[1]:
                            cur['poss'][last_miss[0]] += 1
                        last_off = t if t == last_miss[0] else last_off
                    last_miss = None
                elif et == '5':
                    if 'No Turnover' not in d and t is not None:
                        cur['poss'][t] += 1
                        last_off = None
            if pending_fg:
                cur['poss'][pending_fg[0]] += 1
                pending_fg = None
            elif last_off is not None:
                cur['poss'][last_off] += 1
            cur['end'] = 0
            stints.append(cur)
            for s in stints:
                if s['period'] != p:
                    continue
                for ti, t2 in enumerate(ids):
                    for pid in s['lineups'][ti]:
                        secs[pid] += s['start'] - s['end']
        return stints, secs, score, errs

    ps = period_starters
    filled = 0
    for _ in range(4):
        short = [(p, t) for p in ps for t in ids if len(ps[p][t]) < 5]
        if not short:
            break
        # Seconds using what we have so far (short periods contribute partial lineups).
        _, secs, _, _ = run(ps)
        for p, t in short:
            need = 5 - len(ps[p][t])
            cand = sorted((box_sec[t][x] - secs.get(x, 0), x) for x in roster[t] if x not in ps[p][t])
            for deficit, x in reversed(cand[-need:]):
                ps[p][t].add(x)
                filled += 1
    bad = [(p, t, sorted(ps[p][t])) for p in ps for t in ids if len(ps[p][t]) != 5]
    if bad:
        return None, ['could not infer 5 starters', bad]
    stints, secs, score, errs = run(ps)
    mism = []
    for t in ids:
        for pid in roster[t] | {x for s in stints for x in s['lineups'][ids.index(t)]}:
            e = secs.get(pid, 0) - box_sec[t].get(pid, 0)
            if abs(e) > TOL:
                mism.append({'playerId': pid, 'errorSeconds': round(e, 1)})
    pts = {t: sum(int(r['points'] or 0) for r in box[t].values()) for t in ids}
    if score[home] != pts[home] or score[away] != pts[away]:
        errs.append(f'score {score} vs box {pts}')
    out = []
    for s in stints:
        sec = s['start'] - s['end']
        if sec <= 0 and not any(s['pts'].values()) and not any(s['poss'].values()):
            continue
        out.append({'id': f'{gid:010d}', 'period': s['period'], 'seconds': sec,
                    'teams': [{'teamId': t, 'players': s['lineups'][i],
                               'opponent': {'points': s['pts'][ids[1 - i]]},
                               'defensivePossessions': s['poss'][ids[1 - i]]} for i, t in enumerate(ids)]})
    return {'stints': out, 'errors': errs, 'mismatches': mism, 'filled': filled, 'ids': ids}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pbp', required=True)
    ap.add_argument('--box', required=True)
    ap.add_argument('--season', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    box, box_files = load_box(a.box, a.season)
    events = defaultdict(list)
    for r in csv.DictReader(open(a.pbp, encoding='utf-8')):
        g = int(r['GAME_ID'])
        if str(g)[0] != '2':  # regular season ids are 2YYxxxxx
            continue
        events[g].append(r)
    # Keep the file's row order: it is the order the feed returned, and sorting by EVENTNUM
    # breaks more games (checked on 2016-17: 184 vs 162 valid of the first 200).
    stint_f = open(os.path.join(a.out, 'stints.jsonl'), 'w', encoding='utf-8')
    kept, failures, nst, filled = 0, [], 0, 0
    tot = defaultdict(float)
    for gid in sorted(set(events) | set(box)):
        if gid not in events or gid not in box:
            failures.append({'id': gid, 'error': 'missing pbp' if gid not in events else 'missing box'})
            continue
        res, err = build_game(gid, events[gid], box[gid])
        if err:
            failures.append({'id': gid, 'error': err})
            continue
        filled += res['filled']
        if res['errors'] or res['mismatches']:
            failures.append({'id': gid, 'errors': res['errors'][:5], 'mismatches': res['mismatches'][:10]})
            continue
        kept += 1
        for s in res['stints']:
            nst += 1
            for t in s['teams']:
                tot['points'] += t['opponent']['points']
                tot['possessions'] += t['defensivePossessions']
            stint_f.write(json.dumps(s) + '\n')
    stint_f.close()
    # Official minutes per player-game (box score), all games, for the minutes inputs.
    with open(os.path.join(a.out, 'player-minutes.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['season', 'gameId', 'gameDate', 'teamId', 'playerId', 'name', 'starter', 'seconds'])
        for gid in sorted(box):
            for t in box[gid]:
                for pid, r in box[gid][t].items():
                    w.writerow([a.season, f'{gid:010d}', r['game_date'], t, pid, r['personName'], int(bool(r['position'])), mmss(r['minutes'])])
    summary = {'season': a.season, 'boxGames': len(box), 'pbpGames': len(events), 'validLineupGames': kept,
               'failedGames': len(failures), 'stints': nst, 'filledPeriodStarters': filled,
               'pointsPer100': 100 * tot['points'] / tot['possessions'] if tot['possessions'] else None,
               'possessionsPerTeamGame': tot['possessions'] / (2 * kept) if kept else None,
               'minuteToleranceSeconds': TOL, 'failures': failures,
               'sources': {'pbp': {'file': os.path.basename(a.pbp), 'sha256': sha(a.pbp)},
                           'box': [{'file': os.path.basename(f), 'sha256': sha(f)} for f in box_files]}}
    json.dump(summary, open(os.path.join(a.out, 'preparation.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('failures', 'sources')}))


if __name__ == '__main__':
    main()
