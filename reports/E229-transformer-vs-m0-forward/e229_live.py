"""E-229：T 的每日 live 特徵（2026-27）。不讀任何 2026-27 比賽結果（只用 player-games 的 box 累計，與 M0 同源）。
每位球員的 41 欄向量（15 能力值＋26 統計，各 z 分數＋遮罩）：
  能力值：與 M0 同源——今日 live ranking.csv（publish_state 最後發布日）；live 沒有的人退回 M0 的底卡（BASE_CARDS 24-25 卡→23-24 卡，同 baseProfiles）；兩者皆無＝全缺（mask 0）。
          z 分數的 mu／sd 用 live ranking 全體（E-227 訓練時就是「季內表」z 分數）。
  統計：K=500 預先固定（不調）。w_cur = min_cur/(min_cur+500)，min_cur = 2026-27 賽季至昨日（美東日期 < today）累計分鐘。
        box 五欄（stl36 blk36 pf36 oreb36 dreb36）：值 = w_cur*本季每36 + (1-w_cur)*2025-26 每36；2025-26 沒值（<200 分鐘）者，以聯盟均值代 2025-26（等於向均值收縮）；
        本季沒出賽者 = 只用 2025-26。hustle／rimthree／matchup／adv 四類：R-169（E-246）起同規則混本季（見 season_tracking）；BLEND_DEFAULT=() 時只用 2025-26，沒有就缺值（mask 0）。
        統計 z 分數的 mu／sd 取 2025-26 表中有值球員的（混合後）值。
  身高（位置規則）與 pass／creation 同能力值來源；缺身高用 live 身高中位數。"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'reports', 'E228-transformer-team-rating'))
import numpy as np
from t_lib import Ctx, F, KIND                       # 只取需要的名字，不 star import
from e227_common import ATTRS, STATS, STAT_CLASSES, load_player_table

K_PRIOR_MIN = 500.0                                  # 預先固定，不調
BOX = STAT_CLASSES['box']
SD = os.path.join(ROOT, 'data', 'season-source-2026-27')
LIVE_ROOT = os.path.join(ROOT, 'reports', 'ovr-inseason-2026-27', 'live')


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def live_dir():
    st = json.load(open(os.path.join(LIVE_ROOT, 'publish_state.json'), encoding='utf-8'))
    return os.path.join(LIVE_ROOT, st['dataCutoff'])


def card_csv(ldir):
    meta = json.load(open(os.path.join(ldir, 'meta.json'), encoding='utf-8'))
    name = (meta.get('priorCard') or 'card 0.2.12b').replace('card ', 'card-')
    p = os.path.join(ROOT, 'reports', name, 'ranking.csv')
    return p if os.path.exists(p) else os.path.join(ROOT, 'reports', 'card-0.2.12b', 'ranking.csv')


def season_box(today_et):
    """2026-27 至昨日（GAME_DATE < today_et）每人累計 {pid: Counter-like dict}。"""
    d = json.load(open(os.path.join(SD, 'player-games.json'), encoding='utf-8'))['data']['resultSets']
    t = d[0] if isinstance(d, list) else d
    H = t['headers']; ix = {h: H.index(h) for h in ('PLAYER_ID', 'GAME_DATE', 'MIN', 'STL', 'BLK', 'PF', 'OREB', 'DREB')}
    acc = {}
    for r in t['rowSet']:
        if str(r[ix['GAME_DATE']]) >= today_et:
            continue
        m = r[ix['MIN']]
        if m is None or (isinstance(m, str) and ':' not in m and not m.replace('.', '').isdigit()):
            continue
        m = (int(m.split(':')[0]) + int(m.split(':')[1]) / 60) if isinstance(m, str) and ':' in m else float(m)
        if m <= 0:
            continue
        a = acc.setdefault(str(r[ix['PLAYER_ID']]), dict(MIN=0.0, STL=0.0, BLK=0.0, PF=0.0, OREB=0.0, DREB=0.0))
        a['MIN'] += m
        for k in ('STL', 'BLK', 'PF', 'OREB', 'DREB'):
            a[k] += r[ix[k]] or 0
    return acc


# E-246：21 欄追蹤統計混本季（規則同 box：w=min/(min+500)，本季值不設 200 分鐘門檻）。
# BLEND_DEFAULT＝線上預設混哪幾類；空＝舊 T0（全用 2025-26）。2026-11-05 使用者採用 T1（E-246）→ 四類全混。
TRACK_CLASSES = ('hustle', 'rimthree', 'matchup', 'adv')
BLEND_DEFAULT = TRACK_CLASSES
TRACK_DIR = os.path.join(ROOT, 'data', 'defense-seventh', '2026-27', 'tracking')   # 每日整季累計（截至前一晚）
MATCHUP_DIR = os.path.join(ROOT, 'data', 'matchup-source', '2026-27')             # 每日逐場 boxscorematchupsv3


def _rows(path):
    d = json.load(open(path, encoding='utf-8'))
    d = d.get('data', d)
    s = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return [dict(zip(s['headers'], r)) for r in s['rowSet']]


def season_tracking(today_et, cur, classes, snap_dir=None):
    """本季 21 欄原值 {pid: {col: v}}（只算 classes 內的類別）。cur＝season_box(today_et)。
    snap_dir：含 hustle/rim/three/advanced.json 的夾（回測＝DateTo 前一天快照；線上＝TRACK_DIR）。matchup 一律逐場加總 GAME_DATE < today_et。"""
    snap_dir = snap_dir or TRACK_DIR
    out = {}
    mn = lambda p: cur[p]['MIN'] if p in cur else 0.0
    def put(p, **kv):
        out.setdefault(p, {}).update({k: v for k, v in kv.items() if v is not None})
    if 'hustle' in classes and os.path.exists(os.path.join(snap_dir, 'hustle.json')):
        for r in _rows(os.path.join(snap_dir, 'hustle.json')):
            p = str(r['PLAYER_ID']); m = mn(p)
            if m > 0:
                f = 36 / m
                put(p, deflections36=r['DEFLECTIONS'] * f, cont2pt36=r['CONTESTED_SHOTS_2PT'] * f, cont3pt36=r['CONTESTED_SHOTS_3PT'] * f,
                    charges36=r['CHARGES_DRAWN'] * f, looseO36=r['OFF_LOOSE_BALLS_RECOVERED'] * f, looseD36=r['DEF_LOOSE_BALLS_RECOVERED'] * f,
                    boxoutO36=r['OFF_BOXOUTS'] * f, boxoutD36=r['DEF_BOXOUTS'] * f, screenAst36=r['SCREEN_ASSISTS'] * f)
    if 'rimthree' in classes:
        for kind, pct, ns, fga, cd, cf in (('rim', 'LT_06_PCT', 'NS_LT_06_PCT', 'FGA_LT_06', 'rimDiff', 'rimFGA36'),
                                           ('three', 'FG3_PCT', 'NS_FG3_PCT', 'FG3A', 'threeDiff', 'threeFGA36')):
            fp = os.path.join(snap_dir, f'{kind}.json')
            if not os.path.exists(fp):
                continue
            for r in _rows(fp):
                p = str(r['CLOSE_DEF_PERSON_ID']); m = mn(p)
                if m > 0 and (r[fga] or 0) > 0 and r[pct] is not None and r[ns] is not None:
                    put(p, **{cd: r[pct] - r[ns], cf: r[fga] * 36 / m})
    if 'matchup' in classes:
        d = json.load(open(os.path.join(SD, 'player-games.json'), encoding='utf-8'))['data']['resultSets']
        t = d[0] if isinstance(d, list) else d
        gi, di = t['headers'].index('GAME_ID'), t['headers'].index('GAME_DATE')
        gdate = {r[gi]: str(r[di]) for r in t['rowSet']}
        acc = {}
        for fn in os.listdir(MATCHUP_DIR):
            gid = fn[:-5]
            if not fn.endswith('.json') or gid not in gdate or gdate[gid] >= today_et:
                continue
            for r in json.load(open(os.path.join(MATCHUP_DIR, fn), encoding='utf-8'))['matchups']:
                a = acc.setdefault(str(r['def']), [0.0, 0.0, 0.0, 0.0])
                a[0] += r['playerPoints'] or 0; a[1] += r['partialPossessions'] or 0
                a[2] += r['matchupFieldGoalsMade'] or 0; a[3] += r['matchupFieldGoalsAttempted'] or 0
        for p, a in acc.items():
            if mn(p) > 0 and a[1] > 0 and a[3] > 0:
                put(p, oppPtsPerPoss=a[0] / a[1], oppFGpct=a[2] / a[3])
    if 'adv' in classes and os.path.exists(os.path.join(snap_dir, 'advanced.json')):
        for r in _rows(os.path.join(snap_dir, 'advanced.json')):
            p = str(r['PLAYER_ID'])
            if mn(p) > 0:
                put(p, usg=r['USG_PCT'], astPct=r['AST_PCT'], ts=r['TS_PCT'], orebPct=r['OREB_PCT'], drebPct=r['DREB_PCT'], tovPct=r['TM_TOV_PCT'])
    return out


def nn(name):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', name or '') if not unicodedata.combining(c)).lower().replace('.', '').replace("'", '').replace('-', ' ').strip()


def build(today_et, ldir=None, names=None, blend=None, snap_dir=None):
    """回傳 (B, tab, info)：B[pid]=(vals[F], mask[F])，tab[pid]={heightInches,pass,creation}（供位置規則）。"""
    ldir = ldir or live_dir()
    live = {r['playerId']: r for r in read_csv(os.path.join(ldir, 'ranking.csv'))}
    card = {}                                         # live 沒有的人：M0 同一份底卡（BASE_CARDS：24-25 卡、23-24 卡，由近到遠，用 playerId）
    need = {str(p) for p in (names or {})} - set(live)
    for rel in ('reports/ovr-inseason-2026-27/v5/cards/2024-25-v5-min.csv', 'reports/ovr-inseason-2026-27/v5/cards/2023-24-v5-min.csv'):
        f = os.path.join(ROOT, rel)
        if not os.path.exists(f):
            continue
        for r in read_csv(f):
            if r['playerId'] in need and r['playerId'] not in card:
                card[r['playerId']] = r
    # 能力值
    A = {p: {a: float(r[a]) for a in ATTRS if r.get(a) not in (None, '')} for p, r in live.items()}
    abil_src = {p: 'live' for p in A}
    for p, r in card.items():
        if p not in A:
            A[p] = {a: float(r[a]) for a in ATTRS if r.get(a) not in (None, '')}; abil_src[p] = 'card'
    mu, sd = {}, {}
    for a in ATTRS:
        v = [A[p][a] for p in live if a in A[p]]
        if len(v) >= 10 and np.std(v) > 1e-9:
            mu[a], sd[a] = float(np.mean(v)), float(np.std(v))
    # 統計
    prior = load_player_table('2025-26')
    cur = season_box(today_et)
    mean_box = {c: float(np.mean([d[c] for d in prior.values() if d.get(c) is not None])) for c in BOX}
    S = {}
    for p, d in prior.items():
        S[p] = {c: d[c] for c in STATS if d.get(c) is not None}
    for p, a in cur.items():
        S.setdefault(p, {})
    mixed = {}
    for p in S:
        mixed[p] = dict(S[p]); a = cur.get(p); mc = a['MIN'] if a else 0.0
        if mc > 0:
            w = mc / (mc + K_PRIOR_MIN)
            for c, k in zip(BOX, ('STL', 'BLK', 'PF', 'OREB', 'DREB')):
                cv = a[k] * 36.0 / mc; pv = S[p].get(c)
                mixed[p][c] = w * cv + (1 - w) * (mean_box[c] if pv is None else pv)
    blend = tuple(BLEND_DEFAULT if blend is None else blend)
    n_track = 0
    if blend:                                         # E-246：21 欄同規則混本季
        mean_st = {c: float(np.mean([d[c] for d in prior.values() if d.get(c) is not None])) for c in STATS}
        for p, vals in season_tracking(today_et, cur, blend, snap_dir).items():
            mc = cur[p]['MIN'] if p in cur else 0.0
            if mc <= 0 or p not in mixed:
                continue
            w = mc / (mc + K_PRIOR_MIN); n_track += 1
            for c, cv in vals.items():
                pv = S[p].get(c)
                mixed[p][c] = w * cv + (1 - w) * (mean_st[c] if pv is None else pv)
    smu, ssd = {}, {}
    for c in STATS:
        v = [mixed[p][c] for p in prior if c in mixed[p]]
        if len(v) >= 10 and np.std(v) > 1e-9:
            smu[c], ssd[c] = float(np.mean(v)), float(np.std(v))
    pids = set(A) | set(mixed)
    B = {}; tab = {}
    for p in pids:
        vals = np.zeros(F, np.float32); mask = np.zeros(F, np.float32)
        for j, a in enumerate(ATTRS):
            if p in A and a in A[p] and a in mu:
                vals[j] = (A[p][a] - mu[a]) / sd[a]; mask[j] = 1.0
        for j, c in enumerate(STATS):
            if p in mixed and c in mixed[p] and c in smu:
                vals[len(ATTRS) + j] = (mixed[p][c] - smu[c]) / ssd[c]; mask[len(ATTRS) + j] = 1.0
        B[p] = (vals, mask)
        if p in A:
            tab[p] = {'heightInches': A[p].get('heightInches'), 'pass': A[p].get('pass'), 'creation': A[p].get('creation')}
    info = dict(liveDir=os.path.basename(ldir), nLive=len(live), nCardOnly=sum(1 for s in abil_src.values() if s == 'card'),
                nStatsPrior=len(prior), nCurPlayers=len(cur), nBlendedBox=sum(1 for p in cur if p in mixed), K=K_PRIOR_MIN, todayEt=today_et,
                blendTrack=list(blend), nBlendedTrack=n_track)
    return B, tab, info


def make_ctx(today_et, ldir=None, names=None, blend=None, snap_dir=None):
    """E-228 的 Ctx（E-227 R2-stats 五個 seed、prior 2025-26 的每場回合數），特徵表換成 live 混合表。"""
    C = Ctx('E227-R2-stats', '2025-26')
    B, tab, info = build(today_et, ldir, names, blend, snap_dir)
    C.B = B; C.tab = tab
    hs = [d['heightInches'] for d in tab.values() if d.get('heightInches') is not None]
    C.med_h = float(np.median(hs))
    return C, info
