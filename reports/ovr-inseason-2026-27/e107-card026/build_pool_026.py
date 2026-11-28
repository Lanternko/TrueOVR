"""E-107 §2.3：凍結合併池 live/pool-026.json（新賽季管線自己的原始值函式，2022-23～2025-26 四個整季）。

- 原始值：season_attrs_v4 的 aggregate／raw_with_box（pass、rebound 用 box＋team-games 重建，同賽中視窗）；
  tovSkill＝−TOV/possDen、stamina＝MPG、creation＝(1−received)·FGA/MIN·36；foulDraw＝E-070 合成值（z 常數凍結自 2025-26，
  live/prior-2025-26-card026.json 的 foulDrawFreeze）。
- 分區：zone_of 換成 026 版（E-101 規則：Mid-Range 且 shotDistance<8 → short），在載入 PBP 之前換。
- 2022-23～2024-25：SA.load_season(s)（data/defense-seventh/<s>）；2025-26：IC.load_target_season()＋bio（data/benchmark-source/bio.json）
  ＋dependence-audit 2025-26，與 run_c4_live.setup() 同一份 2025-26 資料。box 只留有 bio 的球員（同 setup）。
- 池門檻（E-101）：百分位型 GP≥30 且 MPG≥20；命中率型 MIN≥500（p＝收縮命中率 (M+100·聯盟該季命中率)/(A+100)）。每個球員季一筆、不去重。
- 尾巴開關：build_e101.passed() on {**E-090 h1, **E-101 h1}（照抄，不重判）；stamina 不在 E-101 → top/bot 都關。
- 命中率型：a99 = inverse_open(99, 反轉曲線, −1e9, 1e9)；s = 1.96·S_p；lo = 0（bot 開）或 40。
另寫 e107-card026/zones-026.json（各季每人 mid/short 出手數，供 (z) 核對）。
"""
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
LIVE = REPORT / 'live'
ROOT = HERE.parents[2]
sys.path.insert(0, str(REPORT / 'v5' / 'tools'))
sys.path.insert(0, str(REPORT / 'v4' / 'tools'))
sys.path.insert(0, str(REPORT / 'tools'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import season_attrs_v4 as SA  # noqa: E402
import inseason_common_v4 as IC  # noqa: E402
from ovr_common import CURVES  # noqa: E402

RUN_LIVE = LIVE / 'run_c4_live.py'
src = RUN_LIVE.read_text(encoding='utf-8')
BLOCK = src[src.index('# ==== E-107 026 BEGIN ===='):src.index('# ==== E-107 026 END ====')]
NS = {'SA': SA, 'IC': IC, 'math': math, 'json': json}
exec(compile(BLOCK, 'run_c4_live.py#E107', 'exec'), NS)
m = type('M', (), NS)

OUT = LIVE / 'pool-026.json'
ZONES_OUT = HERE / 'zones-026.json'
PRIOR_CARD = LIVE / 'prior-2025-26-card026.json'
BIO25 = ROOT / 'data/benchmark-source/bio.json'
E090_H1 = ROOT / 'reports/card-0.2.4+E090-onball-tail/h1-results.json'
E101_H1 = ROOT / 'reports/card-0.2.5+E101-crossera/h1-results.json'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
UPD = ['long', 'mid', 'short', 'ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'creation', 'stamina']


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def passed(h, a, end):      # 同 build_e101.passed
    return bool(h.get(a, {}).get(end, {}).get('pass', False))


def parse_curves():
    txt = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
    out = {}
    for name in ('CURVE_3PT', 'CURVE_MID', 'CURVE_SHORT', 'CURVE_FT'):
        body = re.search(rf'export const {name} = \[(.*?)\];', txt, re.S).group(1)
        out[name] = [(float(a), float(b)) for a, b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', body)]
    return out


def load(season):
    """回傳 sdm（box 只留有 bio 者）與丟掉人數。"""
    if season == '2025-26':
        sd = IC.load_target_season()
        bio = {int(r['PLAYER_ID']): r for r in SA.result_set(BIO25)}
        dep = {int(r['playerId']): r for s in json.loads(IC.DEPENDENCE.read_text(encoding='utf-8'))['seasons']
               if s['season'] == season for r in s['rows']}
        box = {p: b for p, b in sd['box'].items() if p in bio}
        sdm = {'season': season, 'box': box, 'bio': bio, 'dep': dep, 'ff': {}, 'v3': {}, 'fed': {},
               'shots': sd['shots'], 'teamRows': sd['teamRows']}
        src_files = {'box': IC.TARGET_BOX, 'team': IC.TARGET_TEAM, 'bio': BIO25, 'dependence': IC.DEPENDENCE}
        npbp = len(sd['pbpGames'])
        dropped = len(sd['box']) - len(box)
        return sdm, src_files, npbp, dropped, len(sd['badPbp'])
    sd = SA.load_season(season)
    box = {p: b for p, b in sd['box'].items() if p in sd['bio']}
    dropped = len(sd['box']) - len(box)
    sd = {**sd, 'box': box}
    P = sd['paths']
    src_files = {'box': P['box'], 'team': P['team_games'], 'bio': P['bio'], 'dependence': P['dependence']}
    return sd, src_files, len(sd['pbpGames']), dropped, len(sd['badPbp'])


def main():
    t0 = time.time()
    assert {k: [tuple(map(float, xy)) for xy in v] for k, v in CURVES.items() if k in m.M26_CURVE.values()} \
        == {k: v for k, v in parse_curves().items()}, 'ovr_common CURVES 與 src/constants.js 不同'
    fz = json.loads(PRIOR_CARD.read_text(encoding='utf-8'))['foulDrawFreeze']
    fzc = {'vol': fz['vol'], 'rate': fz['rate'], 'wVol': fz['wVol'], 'wRate': fz['wRate']}
    H1 = {**json.loads(E090_H1.read_text(encoding='utf-8'))['h1'], **json.loads(E101_H1.read_text(encoding='utf-8'))['h1']}

    SA.zone_of = m.m26_zone_of      # 載入 PBP 之前換（026 分區）
    vals = {a: [] for a in UPD}
    per = {a: {} for a in UPD}
    seasons_meta, zones = {}, {}
    for s in SEASONS:
        sd, src_files, npbp, dropped, bad = load(s)
        stats = SA.aggregate(sd)
        raw = SA.raw_with_box(sd, stats)
        players = list(stats)
        tot = lambda k: sum(stats[p][k] for p in players)  # noqa: E731
        priors = {'long': SA.safe(tot('FG3M'), tot('FG3A')), 'ft': SA.safe(tot('FTM'), tot('FTA')),
                  'mid': SA.safe(tot('midM'), tot('midA')), 'short': SA.safe(tot('shortM'), tot('shortA'))}
        pool = [p for p in players if stats[p]['GP'] >= 30 and stats[p]['MPG'] >= 20]
        min500 = [p for p in players if stats[p]['MIN'] >= 500]
        for a in ('tovSkill', 'pass', 'rebound', 'creation', 'stamina'):
            v = [raw[a][p] for p in pool]
            vals[a] += v
            per[a][s] = len(v)
        v = [m.m26_foul_comp(stats[p]['FTA'], stats[p]['FGA'], stats[p]['MIN'], fzc) for p in pool]
        vals['foulDraw'] += v
        per['foulDraw'][s] = len(v)
        for a, (mk, ak) in {'long': ('FG3M', 'FG3A'), 'mid': ('midM', 'midA'), 'short': ('shortM', 'shortA'),
                            'ft': ('FTM', 'FTA')}.items():
            v = [m.m26_shrunk(stats[p][mk], stats[p][ak], priors[a]) for p in min500]
            vals[a] += v
            per[a][s] = len(v)
        zones[s] = {str(p): [stats[p]['midA'], stats[p]['midM'], stats[p]['shortA'], stats[p]['shortM']] for p in players}
        seasons_meta[s] = {'players': len(players), 'pool': len(pool), 'min500': len(min500), 'leaguePriors': priors,
                           'boxPlayersDroppedNoBio': dropped, 'pbpGames': npbp, 'badPbp': bad,
                           'sources': {k: {'path': Path(v).resolve().relative_to(ROOT).as_posix(), 'sha256': sha256(v)}
                                       for k, v in src_files.items()}}
        print(f'{s}: players {len(players)} pool {len(pool)} min500 {len(min500)} dropped {dropped} pbp {npbp} bad {bad} '
              f'({time.time() - t0:.0f}s)', flush=True)

    attrs = {}
    for a in UPD:
        top, bot = passed(H1, a, 'top'), passed(H1, a, 'bot')
        an = m.m26_anchors(vals[a])
        ent = {'type': 'curve' if a in m.M26_CURVE else 'percentile', 'top': top, 'bot': bot,
               'anchors': an, 'poolPerSeason': per[a], 'sorted': sorted(float(x) for x in vals[a])}
        if a in m.M26_CURVE:
            curve = CURVES[m.M26_CURVE[a]]
            a99 = m.m26_inverse_open(99, [(y, x) for x, y in curve], -1e9, 1e9)
            ent.update({'curve': m.M26_CURVE[a], 'a99': a99, 's': m.M26_K_SD * an['S'],
                        'lo': 0.0 if bot else 40.0, 'hi': m.M26_CEIL if top else 99.0})
        attrs[a] = ent
        print(f"{a:9s} top={top!s:5} bot={bot!s:5} N={an['poolN']} r90={an['r90']:.5f} r99={an['r99']:.5f} "
              f"r1={an['r1']:.5f} SD={an['SD_pool']:.5f} S={an['S']:.5f}" + (f" a99={ent['a99']:.5f} s={ent['s']:.5f}"
                                                                           if a in m.M26_CURVE else ''), flush=True)

    doc = {
        'doc': 'E-107 §2.3 凍結合併池（CARD_MODE=026 的賽中映射）。由 e107-card026/build_pool_026.py 產出；run_c4_live.py 的 m26_load_pool() 核對 payloadSha256。',
        'seasons': SEASONS, 'seasonMeta': seasons_meta,
        'poolRules': {'percentile': 'GP>=30 且 MPG>=20（每球員季一筆、不去重）', 'curve': 'MIN>=500；p＝(M+100·該季聯盟命中率)/(A+100)'},
        'zoneRule': "season_attrs_v4.zone_of ＋ area=='Mid-Range' 且 (shotDistance or 0)<8 → short",
        'tailConstants': {'CEIL': m.M26_CEIL, 'K_SD': m.M26_K_SD, 'Z9990': m.M26_Z9990},
        'switchSource': {'e090h1': {'path': E090_H1.relative_to(ROOT).as_posix(), 'sha256': sha256(E090_H1)},
                         'e101h1': {'path': E101_H1.relative_to(ROOT).as_posix(), 'sha256': sha256(E101_H1)}},
        'foulDrawConstants': fzc,
        'foulDrawConstantsSource': {'path': PRIOR_CARD.relative_to(ROOT).as_posix(), 'sha256': sha256(PRIOR_CARD)},
        'curvesSource': {'path': 'src/constants.js', 'sha256': sha256(ROOT / 'src/constants.js')},
        'attrs': attrs,
    }
    doc['payloadSha256'] = m.m26_payload_sha(doc)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    ZONES_OUT.write_text(json.dumps({'note': '每人整季 [midA, midM, shortA, shortM]，026 分區（build_pool_026.py）', 'seasons': zones},
                                    ensure_ascii=False), encoding='utf-8', newline='\n')
    print('payloadSha256', doc['payloadSha256'])
    print('file sha256', sha256(OUT), OUT)
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
