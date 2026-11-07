"""E-111 §1.3–1.5：凍結合併池 live/pool-027.json（照 e107-card026/build_pool_026.py，只改預註冊列出的三處）。

與 026 的差別：
  1. stamina 不進合併池（E-111 §1.3；賽中照 IC 單季映射）。
  2. 分區（§1.4）：有 area 欄的季（2022-23～2025-26）area 缺值的 2pt 出手跳過（m27_install_zone_filter，載入 PBP 前裝），
     Mid-Range 且 shotDistance<8 → short（m26_zone_of）。
  3. foulDraw 合併池（§1.5）：合成值 0.75·z(FTA/MIN·36)＋0.25·z(FTA/FGA) 的 z 用「該季自己的」池（GP≥30 且 MPG≥20）平均／標準差（母體，ddof=0），
     不用 2025-26 凍結常數。賽中視窗仍用 2025-26 凍結的 z（doc['foulDrawConstants']，同 026）。
其餘（原始值函式、池門檻、尾巴開關、曲線）照 026。另寫 e111-card027/zones-027.json（各季每人 [midA, midM, shortA, shortM]）。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/e111-card027/build_pool_027.py
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
BLOCK = src[src.index('# ==== E-107 026 BEGIN ===='):src.index('# ==== E-111 027 END ====')]
NS = {'SA': SA, 'IC': IC, 'math': math, 'json': json}
exec(compile(BLOCK, 'run_c4_live.py#E107+E111', 'exec'), NS)
m = type('M', (), NS)

OUT = LIVE / 'pool-027.json'
ZONES_OUT = HERE / 'zones-027.json'
PRIOR_CARD = LIVE / 'prior-2025-26-card027.json'
BIO25 = ROOT / 'data/benchmark-source/bio.json'
E090_H1 = ROOT / 'reports/card-0.2.4+E090-onball-tail/h1-results.json'
E101_H1 = ROOT / 'reports/card-0.2.5+E101-crossera/h1-results.json'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
UPD = ['long', 'mid', 'short', 'ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'creation']     # 027：沒有 stamina


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
    if season == '2025-26':      # IC.TARGET_PBP＝data/defense-a-source/pbp（有 area 欄）
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

    m.m27_install_zone_filter()      # 載入 PBP 之前換（027 分區：area 缺值跳過＋m26_zone_of）
    vals = {a: [] for a in UPD}
    per = {a: {} for a in UPD}
    seasons_meta, zones, fz_season = {}, {}, {}
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
        for a in ('tovSkill', 'pass', 'rebound', 'creation'):
            v = [raw[a][p] for p in pool]
            vals[a] += v
            per[a][s] = len(v)
        vol = [stats[p]['FTA'] / stats[p]['MIN'] * 36.0 for p in pool]
        rate = [stats[p]['FTA'] / stats[p]['FGA'] for p in pool]
        mv, mr = sum(vol) / len(vol), sum(rate) / len(rate)
        fzs = {'vol': {'mean': mv, 'std': math.sqrt(sum((x - mv) ** 2 for x in vol) / len(vol))},
               'rate': {'mean': mr, 'std': math.sqrt(sum((x - mr) ** 2 for x in rate) / len(rate))},
               'wVol': fzc['wVol'], 'wRate': fzc['wRate']}
        fz_season[s] = fzs
        v = [m.m26_foul_comp(stats[p]['FTA'], stats[p]['FGA'], stats[p]['MIN'], fzs) for p in pool]
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
        seasons_meta[s]['foulDrawSeasonZ'] = fz_season[s]
        seasons_meta[s]['zoneSkippedAreaMissing2pt'] = {k: v for k, v in m.M27_ZONE_DROPPED.items()}
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
        'doc': 'E-111 凍結合併池（CARD_MODE=027 的賽中映射）。由 e111-card027/build_pool_027.py 產出；run_c4_live.py 的 m26_load_pool() 核對 payloadSha256。',
        'seasons': SEASONS, 'seasonMeta': seasons_meta,
        'poolRules': {'percentile': 'GP>=30 且 MPG>=20（每球員季一筆、不去重）', 'curve': 'MIN>=500；p＝(M+100·該季聯盟命中率)/(A+100)'},
        'zoneRule': "有 area 欄的季（2022-23～2025-26）area 缺值的 2pt 跳過；season_attrs_v4.zone_of ＋ area=='Mid-Range' 且 (shotDistance or 0)<8 → short",
        'zoneSkippedAreaMissing2pt': dict(m.M27_ZONE_DROPPED),
        'foulDrawPoolZ': '合併池 foulDraw 合成值的 z 用各季自己的池（GP>=30 且 MPG>=20）平均／標準差（ddof=0）；見 seasonMeta[s].foulDrawSeasonZ',
        'tailConstants': {'CEIL': m.M26_CEIL, 'K_SD': m.M26_K_SD, 'Z9990': m.M26_Z9990},
        'switchSource': {'e090h1': {'path': E090_H1.relative_to(ROOT).as_posix(), 'sha256': sha256(E090_H1)},
                         'e101h1': {'path': E101_H1.relative_to(ROOT).as_posix(), 'sha256': sha256(E101_H1)}},
        'foulDrawConstants': fzc,     # 賽中視窗用（2025-26 凍結，同 026）
        'foulDrawConstantsSource': {'path': PRIOR_CARD.relative_to(ROOT).as_posix(), 'sha256': sha256(PRIOR_CARD)},
        'curvesSource': {'path': 'src/constants.js', 'sha256': sha256(ROOT / 'src/constants.js')},
        'attrs': attrs,
    }
    doc['payloadSha256'] = m.m26_payload_sha(doc)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    ZONES_OUT.write_text(json.dumps({'note': '每人整季 [midA, midM, shortA, shortM]，027 分區（build_pool_027.py）', 'seasons': zones},
                                    ensure_ascii=False), encoding='utf-8', newline='\n')
    print('payloadSha256', doc['payloadSha256'])
    print('file sha256', sha256(OUT), OUT)
    print(f'done {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
