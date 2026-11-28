"""共用球季能力值計算：S1 先驗、S2 分半信度、S4 回測都走同一套公式。

對應 scripts/build_season_league.js 的 card()（曲線屬性＋百分位屬性）與 v58 的 creation/pressure、
E2-λ0.4 short 折扣（v58 build-card-E 規則）。所有球季只讀
2022-23..2024-25 的 data/defense-seventh/<season>/ 與 2022-25 的四因子；回測視窗的目標季
逐場資料由 S4 自己載入，再用本模組的 `mapping` 常數（2024-25 凍結）轉換（preregistration §1.1）。

單位注意：bio 的 AST_PCT/REB_PCT 是 0-1 比例，NBA 公式 AST%/REB% 是百分數，因此這裡一律乘 100
（百分位映射對單調縮放不變，先驗卡片數值不受影響，但回測視窗可用同一單位計算）。
"""
import csv
import json
import math
from pathlib import Path

from ovr_common import (ATTR_MIDPOINT, CURVES, DATA, ROOT, attr, load_json, percentile,
                        pos_of_height, safe, sha256_file, shooting)

SEASONS = ['2022-23', '2023-24', '2024-25']
RIM_ZONE = 'short'
PSEUDO_ATTEMPTS = 25
MIN_ATTEMPTS_FOR_TAU2 = 40
E2_LAMBDA = 0.4
BOX_KEYS = ['FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'TOV',
            'STL', 'BLK', 'PF', 'PTS', 'MIN']
# 先驗季最低樣本（preregistration §1.1）與季中最低樣本
PRIOR_MIN_SAMPLE = {'long': 200, 'mid': 100, 'short': 100, 'ft': 100, 'drive': 300,
                    'tovSkill': 300, 'pass': 500, 'rebound': 500, 'stamina': 40,
                    'creation': 500, 'pressure': 1000}
SEASON_MIN_SAMPLE = {'long': 20, 'mid': 15, 'short': 15, 'ft': 10, 'drive': 50,
                     'tovSkill': 50, 'pass': 100, 'rebound': 100, 'stamina': 5,
                     'creation': 100, 'pressure': 200}


def season_paths(season):
    base = ROOT / 'data/defense-seventh' / season
    return {
        'box': base / 'player-games.json',
        'bio': base / 'bio.json',
        'pbp': base / 'pbp',
        'team_games': base / 'team-games.json',
        'v3': ROOT / 'reports/defense-seventh' / season / 'calendar-55' / 'v3-league.json',
        'dependence': ROOT / 'reports/player-impact-v30/dependence-audit.json',
        'shot_origin': ROOT / 'reports/ovr-v55-finisher-fix-2025-26/shot-origin.json',
        'four_factors': DATA / 'four-factors-2022-25.csv',
    }


def result_set(path):
    doc = load_json(path)
    sets = doc['data']['resultSets']
    s = sets[0] if isinstance(sets, list) else sets
    return [dict(zip(s['headers'], row)) for row in s['rowSet']]


def read_csv(path):
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _f(v):
    return float(v) if v not in (None, '') else 0.0


def shot_origin_fedshare(origin_doc, season):
    """src/source_shot_origin.js shotOriginTables() 的單季移植（EB 收縮 fedShare）。"""
    S = origin_doc['seasons'][season]
    agg = {}
    L = {'fedA': 0, 'fedM': 0, 'selfA': 0, 'selfM': 0, 'putA': 0}
    for pid, zones in S['players'].items():
        r = zones.get(RIM_ZONE)
        if not r:
            continue
        a = agg.setdefault(int(pid), {'fedA': 0, 'fedM': 0, 'selfA': 0, 'selfM': 0, 'putA': 0})
        for k in ('fedA', 'fedM', 'selfA', 'selfM'):
            a[k] += r[k]
            L[k] += r[k]
        a['putA'] += r.get('putA', 0)
        L['putA'] += r.get('putA', 0)
    pf = L['fedM'] / L['fedA'] if L['fedA'] else 0.0
    ps = L['selfM'] / L['selfA'] if L['selfA'] else 0.0
    sbar = L['fedA'] / (L['fedA'] + L['selfA']) if (L['fedA'] + L['selfA']) else 0.5

    def sampling_var(a):
        v = 0.0
        if a['fedA'] > 0:
            v += pf * (1 - pf) / a['fedA']
        if a['selfA'] > 0:
            v += ps * (1 - ps) / a['selfA']
        return v

    eligible = [a for a in agg.values()
                if a['fedA'] + a['selfA'] >= MIN_ATTEMPTS_FOR_TAU2 and a['fedA'] > 0 and a['selfA'] > 0]
    if len(eligible) < 2:
        raise RuntimeError('Not enough players to estimate shot-origin tau^2: ' + season)
    wA = sum(a['fedA'] + a['selfA'] for a in eligible)
    gap_of = lambda a: a['fedM'] / a['fedA'] - a['selfM'] / a['selfA']
    dbar = sum(gap_of(a) * (a['fedA'] + a['selfA']) for a in eligible) / wA
    var_obs = sum((gap_of(a) - dbar) ** 2 for a in eligible) / (len(eligible) - 1)
    mean_sampling = sum(sampling_var(a) for a in eligible) / len(eligible)
    tau2 = max(var_obs - mean_sampling, 1e-6)
    fed = {}
    for pid, a in agg.items():
        A = a['fedA'] + a['selfA']
        fed[pid] = (a['fedA'] + PSEUDO_ATTEMPTS * sbar) / (A + PSEUDO_ATTEMPTS)
    meta = {'leagueFedShare': sbar, 'pctFed': pf, 'pctSelf': ps, 'dBar': dbar, 'tau2': tau2,
            'measuredEligible': len(eligible), 'playersWithRimShots': len(agg)}
    return fed, meta


def zone_of(action):
    """2pt 出手分區（preregistration-v4 §3.2）。

    有官方 area 的季（2022-23 之後）照官方；2021-22 的 payload 沒有 area，
    用座標規則判定（xLegacy/yLegacy 單位 0.1 呎、原點籃框中心；禁區半寬 80、前緣 y=138）。
    哨兵 (0,0) 是 tip/putback 補籃、座標未記，一律判 short。
    """
    area = action.get('area')
    if area:
        return 'mid' if area == 'Mid-Range' else 'short'
    x, y = action.get('xLegacy'), action.get('yLegacy')
    if x is None or y is None:
        return 'short'
    if x == 0 and y == 0:
        return 'short'
    return 'short' if (abs(x) <= 80 and y <= 138) else 'mid'


def load_season(season, with_pbp=True):
    """載入單季資料；box 保留逐場列（供分半與視窗切片）。"""
    P = season_paths(season)
    box = {}
    for r in result_set(P['box']):
        pid = int(r['PLAYER_ID'])
        b = box.setdefault(pid, {'playerId': pid, 'name': r['PLAYER_NAME'], 'rows': []})
        row = {k: _f(r.get(k)) for k in BOX_KEYS}
        row.update({'GAME_ID': r['GAME_ID'], 'GAME_DATE': r['GAME_DATE'], 'TEAM_ID': int(r['TEAM_ID'])})
        b['rows'].append(row)
    bio = {}
    for r in result_set(P['bio']):
        bio[int(r['PLAYER_ID'])] = r
    v3 = {int(p['playerId']): p for t in load_json(P['v3'])['teams'] for p in t['roster']}
    dep = {r['playerId']: r for s in load_json(P['dependence'])['seasons']
           if s['season'] == season for r in s['rows']}
    origin = load_json(P['shot_origin'])
    fed, origin_meta = shot_origin_fedshare(origin, season)
    ff = {}
    if P['four_factors'].exists():
        for r in read_csv(P['four_factors']):
            ff[int(r['playerId'])] = {'value': float(r['tovNonSteal_defense']),
                                      'defensePossessions': float(r['defensePossessions'])}
    shots = {}
    pbp_games = set()
    bad = []
    if with_pbp:
        for path in sorted(P['pbp'].glob('*.json')):
            try:
                actions = load_json(path)['data']['game']['actions']
            except Exception as exc:
                bad.append({'file': path.name, 'error': str(exc)})
                continue
            pbp_games.add(path.stem)
            for a in actions:
                if a.get('isFieldGoal') != 1 or a.get('personId') in (None, 0):
                    continue
                if a.get('shotResult') not in ('Made', 'Missed') or a.get('actionType') != '2pt':
                    continue
                key = (int(a['personId']), path.stem)
                s = shots.setdefault(key, {'midM': 0, 'midA': 0, 'shortM': 0, 'shortA': 0})
                made = 1 if a['shotResult'] == 'Made' else 0
                zone = zone_of(a)
                s[zone + 'M'] += made
                s[zone + 'A'] += 1
    return {'season': season, 'paths': P, 'box': box, 'bio': bio, 'v3': v3, 'dep': dep,
            'fed': fed, 'originMeta': origin_meta, 'ff': ff, 'shots': shots,
            'pbpGames': pbp_games, 'badPbp': bad,
            'allGames': {r['GAME_ID'] for b in box.values() for r in b['rows']}}


def half_game_sets(sd):
    """逐球員把出賽依 (GAME_DATE, GAME_ID) 排序，奇數場（1,3,…）=A、偶數場=B。"""
    out = {}
    for pid, b in sd['box'].items():
        ordered = sorted(b['rows'], key=lambda r: (r['GAME_DATE'], r['GAME_ID']))
        out[pid] = {'A': {r['GAME_ID'] for r in ordered[0::2]},
                    'B': {r['GAME_ID'] for r in ordered[1::2]}}
    return out


def aggregate(sd, game_map=None):
    """game_map: pid -> set(gids)；None = 全季。"""
    stats = {}
    for pid, b in sd['box'].items():
        keep = game_map.get(pid) if game_map is not None else None
        rows = [r for r in b['rows'] if keep is None or r['GAME_ID'] in keep]
        if not rows:
            continue
        s = {k: 0.0 for k in BOX_KEYS}
        s['GP'] = 0
        for r in rows:
            for k in BOX_KEYS:
                s[k] += r[k]
            s['GP'] += 1
        s['name'] = b['name']
        s['midM'] = s['midA'] = s['shortM'] = s['shortA'] = 0
        for r in rows:
            sh = sd['shots'].get((pid, r['GAME_ID']))
            if sh:
                for k in ('midM', 'midA', 'shortM', 'shortA'):
                    s[k] += sh[k]
        s['MPG'] = safe(s['MIN'], s['GP'])
        s['possDen'] = s['FGA'] + 0.44 * s['FTA'] + s['AST'] + s['TOV']
        stats[pid] = s
    return stats


def raw_values(sd, stats):
    """百分位屬性的原始統計量（單位與 NBA 公式一致）。"""
    out = {k: {} for k in ('drive', 'tovSkill', 'pass', 'rebound', 'stamina', 'physique',
                           'creation', 'pressure')}
    for pid, s in stats.items():
        bio = sd['bio'][pid]
        h = float(bio['PLAYER_HEIGHT_INCHES'])
        w = _f(bio['PLAYER_WEIGHT'])
        out['drive'][pid] = safe(s['FTA'], s['FGA'])
        out['tovSkill'][pid] = -safe(s['TOV'], s['possDen'])
        out['pass'][pid] = _f(bio['AST_PCT']) * 100
        out['rebound'][pid] = (_f(bio['OREB_PCT']) + _f(bio['DREB_PCT'])) * 100
        out['stamina'][pid] = s['MPG']
        out['physique'][pid] = h + w / 10 if w > 0 else None
        received = float(sd['dep'][pid]['sourceReceived']) if pid in sd['dep'] else 0.5
        out['creation'][pid] = (1 - received) * s['FGA'] / max(s['MIN'], 1) * 36
        if pid in sd['ff']:
            out['pressure'][pid] = sd['ff'][pid]['value']
        else:
            out['pressure'][pid] = 0.0
    return out


def team_totals(sd):
    """{gameId: {teamId: {'FGM':…, 'REB':…}}}，供 §1.1 的 AST%／REB% 公式。"""
    out = {}
    rows = sd['teamRows'] if 'teamRows' in sd else result_set(sd['paths']['team_games'])
    for r in rows:
        out.setdefault(r['GAME_ID'], {})[int(r['TEAM_ID'])] = {
            'FGM': _f(r['FGM']), 'REB': _f(r['REB']),
            'FGA': _f(r['FGA']), 'FTA': _f(r['FTA']), 'OREB': _f(r['OREB']), 'TOV': _f(r['TOV'])}
    return out


def team_possessions(t):
    """球隊回合估計：FGA + 0.44·FTA − OREB + TOV（與 u_proxy 的官方尺度換算用）。"""
    return t['FGA'] + 0.44 * t['FTA'] - t['OREB'] + t['TOV']


def pass_rebound_raw(sd, game_map=None):
    """§1.1 的 AST%／REB% 公式（box+team-games 重建），支援分半與視窗切片。

    AST% = 100·AST/((MIN/48)·團隊FGM − FGM)
    REB% = 100·REB·48/(MIN·(團隊REB+對手REB))
    注意：S1 先驗用 bio 官方 AST_PCT／(OREB_PCT+DREB_PCT)（等效於 on-floor 定義）；
    這兩條公式在同一季的排序相關係數 AST 0.93、REB 0.99，但 REB 水平約為一半，因此
    S2/S4 的分半／視窗一律用本函式重算 pool 與觀測值，確保兩端同尺度。
    """
    totals = team_totals(sd)
    ast_out, reb_out = {}, {}
    for pid, b in sd['box'].items():
        keep = game_map.get(pid) if game_map is not None else None
        num_ast = den_ast = num_reb = den_reb = 0.0
        for r in b['rows']:
            if keep is not None and r['GAME_ID'] not in keep:
                continue
            teams = totals.get(r['GAME_ID'], {})
            if len(teams) != 2 or r['TEAM_ID'] not in teams:
                continue
            t = teams[r['TEAM_ID']]
            opp_id = [k for k in teams if k != r['TEAM_ID']][0]
            o = teams[opp_id]
            den_ast += (r['MIN'] / 48.0) * t['FGM'] - r['FGM']
            num_ast += r['AST']
            den_reb += r['MIN'] * (t['REB'] + o['REB'])
            num_reb += r['REB']
        ast_out[pid] = 100.0 * num_ast / den_ast if den_ast > 0 else 0.0
        reb_out[pid] = 100.0 * num_reb * 48.0 / den_reb if den_reb > 0 else 0.0
    return {'pass': ast_out, 'rebound': reb_out}


def build_mapping(sd, stats, raw=None):
    """全季凍結映射：pool（GP>=30 & MPG>=20）、聯盟命中率先驗、各屬性 pool 原始值。"""
    players = list(stats)
    pool = [p for p in players if stats[p]['GP'] >= 30 and stats[p]['MPG'] >= 20]
    if raw is None:
        raw = raw_values(sd, stats)
    size_pool = [p for p in pool if raw['physique'][p] is not None]

    def total(key):
        return sum(stats[p][key] for p in players)

    priors = {'long': safe(total('FG3M'), total('FG3A')),
              'ft': safe(total('FTM'), total('FTA')),
              'mid': safe(sum(s['midM'] for s in stats.values()), sum(s['midA'] for s in stats.values())),
              'short': safe(sum(s['shortM'] for s in stats.values()), sum(s['shortA'] for s in stats.values()))}
    pools = {a: [raw[a][p] for p in pool] for a in raw if a != 'physique'}
    pools['physique'] = [raw['physique'][p] for p in size_pool]
    return {'season': sd['season'], 'pool': pool, 'priors': priors, 'raw': raw, 'pools': pools,
            'sizePool': size_pool}


def raw_with_box(sd, stats, game_map=None):
    """raw_values ＋ 用 box/team-games 重建的 §1.1 AST%／REB%（S2/S4 一律用這版）。"""
    raw = raw_values(sd, stats)
    raw.update(pass_rebound_raw(sd, game_map))
    return raw


def compute_attrs(sd, stats, mapping, pressure_raw=None):
    """把統計量轉成 15 項能力值。pressure_raw 可覆寫（分半四因子）。"""
    raw = {k: dict(v) for k, v in mapping['raw'].items()}
    if pressure_raw is not None:
        raw['pressure'] = pressure_raw
    out = {}
    for pid, s in stats.items():
        if pid not in sd['bio']:
            continue
        bio = sd['bio'][pid]
        h = float(bio['PLAYER_HEIGHT_INCHES'])
        w = _f(bio['PLAYER_WEIGHT'])
        pos = pos_of_height(h)
        creation = attr(percentile(raw['creation'][pid], mapping['pools']['creation']))
        card = {
            'playerId': pid, 'name': s['name'], 'pos': pos, 'heightInches': h,
            'age': _f(bio['AGE']) if bio['AGE'] not in (None, '') else None,
            'long': shooting(s['FG3M'], s['FG3A'], mapping['priors']['long'], CURVES['CURVE_3PT']),
            'mid': shooting(s['midM'], s['midA'], mapping['priors']['mid'], CURVES['CURVE_MID']),
            'shortBase': shooting(s['shortM'], s['shortA'], mapping['priors']['short'], CURVES['CURVE_SHORT']),
            'ft': shooting(s['FTM'], s['FTA'], mapping['priors']['ft'], CURVES['CURVE_FT']),
            'drive': attr(percentile(raw['drive'][pid], mapping['pools']['drive'])),
            'tovSkill': attr(percentile(raw['tovSkill'][pid], mapping['pools']['tovSkill'])),
            'pass': attr(percentile(raw['pass'][pid], mapping['pools']['pass'])),
            'rebound': attr(percentile(raw['rebound'][pid], mapping['pools']['rebound'])),
            'stamina': attr(percentile(raw['stamina'][pid], mapping['pools']['stamina'])),
            'physique': attr(percentile(raw['physique'][pid], mapping['pools']['physique'])) if w > 0 else 70.0,
            'onBall': float(sd['v3'][pid]['onBall']) if pid in sd['v3'] else 70.0,
            'help': float(sd['v3'][pid]['help']) if pid in sd['v3'] else 70.0,
            'creation': creation,
            'pressure': attr(percentile(raw['pressure'][pid], mapping['pools']['pressure'])),
        }
        s_tilde = sd['fed'].get(pid)
        if s_tilde is None:
            card['short'] = card['shortBase']
            card['e2'] = None
        else:
            exempt = 0.0
            if pos in ('PF', 'C') and math.isfinite(creation):
                exempt = max(0.0, min(1.0, (creation - 55) / (65 - 55)))
            eff = E2_LAMBDA + (1 - E2_LAMBDA) * exempt
            factor = s_tilde + eff * (1 - s_tilde)
            card['short'] = max(40.0, min(99.0, ATTR_MIDPOINT + (card['shortBase'] - ATTR_MIDPOINT) * factor))
            card['e2'] = {'sTilde': round(s_tilde, 6), 'exempt': round(exempt, 6),
                          'effectiveLambda': round(eff, 6), 'discountFactor': round(factor, 6)}
        # 樣本數（§1.1 的 n 定義）
        card['sample'] = {'fg3a': s['FG3A'], 'midA': s['midA'], 'shortA': s['shortA'], 'fta': s['FTA'],
                          'fga': s['FGA'], 'possDen': s['possDen'], 'min': s['MIN'], 'gp': s['GP'],
                          'defensePossessions': sd['ff'][pid]['defensePossessions'] if pid in sd['ff'] else 0.0}
        card['observed'] = {k: s[k] for k in BOX_KEYS} | {'GP': s['GP'], 'midM': s['midM'],
                                                          'midA': s['midA'], 'shortM': s['shortM'],
                                                          'shortA': s['shortA']}
        out[pid] = card
    return out
