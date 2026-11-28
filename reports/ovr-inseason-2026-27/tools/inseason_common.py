"""S3/S4 共用：視窗（前 N 場）能力值、目標季載入、凍結映射套用。

視窗定義：球隊的第 N 場例行賽（team-games 依 GAME_DATE, GAME_ID 排序）；逐場只取
該隊前 N 場。觀測值用先驗季凍結映射（priors/pools）轉成能力值；pass/rebound 用
§1.1 的 box+team-games 公式，short 再套 v58 E2-λ0.4（sTilde 與 creation 凍結先驗季）。
pressure 在本輪不更新（2025-26 沒有可用的 stints），一律沿用先驗。
"""
import json
from collections import defaultdict

from ovr_common import ATTRS, CURVES, DATA, ROOT, attr, load_json, percentile, safe, shooting
import season_attrs as SA

TARGET_BOX = ROOT / 'data/season-source/player-games.json'
TARGET_TEAM = ROOT / 'data/season-source/team-games.json'
TARGET_PBP = ROOT / 'data/defense-a-source/pbp'
DEPENDENCE = ROOT / 'reports/player-impact-v30/dependence-audit.json'
FROZEN_ATTRS = ['physique', 'onBall', 'help', 'heightInches']


def result_set(path):
    return SA.result_set(path)


def load_target_season(with_pbp=True):
    """2025-26 目標季逐場資料（只讀 §5.2 允許的 player-games／team-games／PBP）。"""
    box = {}
    for r in result_set(TARGET_BOX):
        pid = int(r['PLAYER_ID'])
        b = box.setdefault(pid, {'playerId': pid, 'name': r['PLAYER_NAME'], 'rows': []})
        row = {k: SA._f(r.get(k)) for k in SA.BOX_KEYS}
        row.update({'GAME_ID': r['GAME_ID'], 'GAME_DATE': r['GAME_DATE'], 'TEAM_ID': int(r['TEAM_ID'])})
        b['rows'].append(row)
    shots, pbp_games, bad = {}, set(), []
    if with_pbp:
        for path in sorted(TARGET_PBP.glob('*.json')):
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
                zone = 'mid' if a.get('area') == 'Mid-Range' else 'short'
                s[zone + 'M'] += made
                s[zone + 'A'] += 1
    team_rows = result_set(TARGET_TEAM)
    return {'season': '2025-26', 'box': box, 'shots': shots, 'pbpGames': pbp_games,
            'badPbp': bad, 'teamRows': team_rows,
            'allGames': {g for b in box.values() for g in [r['GAME_ID'] for r in b['rows']]},
            'pathBox': TARGET_BOX, 'pathTeam': TARGET_TEAM, 'pathPbp': TARGET_PBP}


def teams_of(sd):
    return sd['teamRows'] if 'teamRows' in sd else result_set(sd['paths']['team_games'])


def team_game_index(sd):
    by_team = defaultdict(list)
    for r in teams_of(sd):
        by_team[int(r['TEAM_ID'])].append((r['GAME_DATE'], r['GAME_ID']))
    idx = {}
    for tid, games in by_team.items():
        for i, (_, gid) in enumerate(sorted(games)):
            idx[(tid, gid)] = i + 1
    return idx


def window_game_map(sd, n):
    idx = team_game_index(sd)
    out = {}
    for pid, b in sd['box'].items():
        out[pid] = {r['GAME_ID'] for r in b['rows']
                    if idx.get((r['TEAM_ID'], r['GAME_ID']), 10 ** 9) <= n}
    return out


def received_prior(season):
    """先驗季的 sourceReceived（dependence-audit）。2025-26 的列一律不讀。"""
    doc = load_json(DEPENDENCE)
    for s in doc['seasons']:
        if s['season'] == season:
            return {int(r['playerId']): float(r['sourceReceived']) for r in s['rows']}
    return {}


def _e2_short(base, prior_card, creation_prior):
    e2 = prior_card.get('e2') if prior_card else None
    if not e2:
        return base
    s_tilde = float(e2['sTilde'])
    pos = prior_card.get('pos')
    exempt = 0.0
    if pos in ('PF', 'C') and creation_prior is not None:
        exempt = max(0.0, min(1.0, (creation_prior - 55.0) / 10.0))
    eff = SA.E2_LAMBDA + (1 - SA.E2_LAMBDA) * exempt
    factor = s_tilde + eff * (1 - s_tilde)
    return max(40.0, min(99.0, 70.0 + (base - 70.0) * factor))


def window_cards(sd, n, mapping, prior_cards, received, season_min_sample=None):
    """回傳 {pid: {attr, sample n,MIN,GP,u, raw…}}（只含視窗內有出賽的球員）。"""
    gm = window_game_map(sd, n)
    stats = SA.aggregate(sd, gm)
    totals = SA.team_totals(sd)
    pb = SA.pass_rebound_raw(sd, gm)
    raw = {'drive': {}, 'tovSkill': {}, 'pass': pb['pass'], 'rebound': pb['rebound'],
           'stamina': {}, 'creation': {}}
    for pid, s in stats.items():
        raw['drive'][pid] = SA.safe(s['FTA'], s['FGA'])
        raw['tovSkill'][pid] = -SA.safe(s['TOV'], s['possDen'])
        raw['stamina'][pid] = s['MPG']
    out = {}
    for pid, s in stats.items():
        pc = prior_cards.get(pid)
        if pc is None:
            continue
        rec = received.get(pid, 0.5)
        creation_raw = (1.0 - rec) * s['FGA'] / max(s['MIN'], 1.0) * 36.0
        raw['creation'][pid] = creation_raw
        creation = attr(percentile(creation_raw, mapping['pools']['creation']))
        base_short = shooting(s['shortM'], s['shortA'], mapping['priors']['short'], CURVES['CURVE_SHORT'])
        onfloor = 0.0
        for r in sd['box'][pid]['rows']:
            if r['GAME_ID'] not in gm[pid]:
                continue
            t = totals.get(r['GAME_ID'], {}).get(r['TEAM_ID'])
            if t:
                onfloor += SA.team_possessions(t) * r['MIN'] / 48.0
        events = s['FGA'] + 0.44 * s['FTA'] + s['TOV']
        card = {
            'playerId': pid,
            'long': shooting(s['FG3M'], s['FG3A'], mapping['priors']['long'], CURVES['CURVE_3PT']),
            'mid': shooting(s['midM'], s['midA'], mapping['priors']['mid'], CURVES['CURVE_MID']),
            'shortBase': base_short,
            'short': _e2_short(base_short, pc, pc.get('creation')),
            'ft': shooting(s['FTM'], s['FTA'], mapping['priors']['ft'], CURVES['CURVE_FT']),
            'drive': attr(percentile(raw['drive'][pid], mapping['pools']['drive'])),
            'tovSkill': attr(percentile(raw['tovSkill'][pid], mapping['pools']['tovSkill'])),
            'pass': attr(percentile(raw['pass'][pid], mapping['pools']['pass'])),
            'rebound': attr(percentile(raw['rebound'][pid], mapping['pools']['rebound'])),
            'stamina': attr(percentile(raw['stamina'][pid], mapping['pools']['stamina'])),
            'creation': creation,
            'sample': {'fg3a': s['FG3A'], 'midA': s['midA'], 'shortA': s['shortA'], 'fta': s['FTA'],
                       'fga': s['FGA'], 'possDen': s['possDen'], 'min': s['MIN'], 'gp': s['GP'],
                       'defensePossessions': 0.0},
            'MIN': s['MIN'], 'GP': s['GP'],
            # 官方尺度 proxy（100·使用回合／在場球隊回合）；per-36 版本一併記錄
            'u_proxy': 100.0 * events / onfloor if onfloor > 0 else 0.0,
            'u_proxy_per36': events / max(s['MIN'], 1.0) * 36.0,
        }
        out[pid] = card
    return out


def sample_of(card, attr_name):
    key = {'long': 'fg3a', 'mid': 'midA', 'short': 'shortA', 'ft': 'fta', 'drive': 'fga',
           'tovSkill': 'possDen', 'pass': 'min', 'rebound': 'min', 'stamina': 'gp',
           'creation': 'min', 'pressure': 'defensePossessions'}[attr_name]
    return float(card['sample'].get(key, 0.0))
