"""E-077：選秀體測臂展在身高體重之外，能不能多解釋籃板與蓋帽（照 preregistration.md）。"""
import json, os, re, hashlib, unicodedata, collections
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
SEED, NBOOT = 20261029, 2000


# ---------- 體測 ----------
def build_combine():
    raw = os.path.join(HERE, 'combine-anthro.raw.txt')
    out = os.path.join(HERE, 'combine-anthro.json')
    if os.path.exists(raw):
        rows = []
        for ln in open(raw, encoding='utf-8').read().splitlines():
            n, y, h, r, w = ln.split('|')
            rows.append([n, int(y), float(h), float(r) if r else None, float(w)])
        body = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
        json.dump({'source': 'https://www.nba.com/stats/draft/combine-anthro?SeasonYear=<YYYY-YY>（2000-01..2025-26，網頁表格）',
                   'fetchedAt': '2026-10-29',
                   'columns': ['name', 'combine_year', 'height_wo_shoes_in', 'standing_reach_in', 'wingspan_in'],
                   'note': '只收臂展與赤腳身高都有值的列',
                   'sha256_rows': hashlib.sha256(body.encode('utf-8')).hexdigest(),
                   'rows': rows}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
        os.remove(raw)
    return json.load(open(out, encoding='utf-8'))


ALIAS = {'edriceadebayo': 'bamadebayo', 'alexandresarr': 'alexsarr', 'carltoncarrington': 'bubcarrington',
         'nicolasclaxton': 'nicclaxton', 'herbertjones': 'herbjones'}
ALIAS.update({v: k for k, v in list(ALIAS.items())})


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', ' ', s)
    return re.sub(r'[^a-z]', '', s)


# ---------- 表現 ----------
def rs(path, i=0):
    d = json.load(open(path, encoding='utf-8'))['data']['resultSets']
    s = d[i] if isinstance(d, list) else d
    return [dict(zip(s['headers'], r)) for r in s['rowSet']]


def mins(v):
    if isinstance(v, str) and ':' in v:
        a, b = v.split(':')
        return int(a) + int(b) / 60
    return float(v or 0)


def season_rows():
    obs, skipped = [], []
    d7 = os.path.join(ROOT, 'data', 'defense-seventh')
    for s in [f'{y}-{str(y + 1)[2:]}' for y in range(2014, 2025)]:
        b, g = os.path.join(d7, s, 'bio.json'), os.path.join(d7, s, 'player-games.json')
        if not (os.path.exists(b) and os.path.exists(g)):
            skipped.append(s)
            continue
        agg = collections.defaultdict(lambda: [0, 0.0, 0])
        for r in rs(g):
            m = mins(r['MIN'])
            if m <= 0:
                continue
            a = agg[r['PLAYER_ID']]
            a[0] += 1; a[1] += m; a[2] += r['BLK'] or 0
        seen = set()
        for r in rs(b):
            i = r['PLAYER_ID']
            if i in seen or i not in agg:
                continue
            seen.add(i)
            gp, mn, blk = agg[i]
            obs.append(dict(season=s, pid=i, name=r['PLAYER_NAME'], gp=gp, mpg=mn / gp,
                            h=r['PLAYER_HEIGHT_INCHES'], w=r['PLAYER_WEIGHT'],
                            oreb=r['OREB_PCT'], dreb=r['DREB_PCT'], blk36=blk / mn * 36))
    bdir = os.path.join(ROOT, 'data', 'benchmark-source')
    base = {r['PLAYER_ID']: r for r in rs(os.path.join(bdir, 'base.json'))}
    rim = {r['CLOSE_DEF_PERSON_ID']: r for r in rs(os.path.join(bdir, 'defense-rim.json'))}
    sh = {}
    d = json.load(open(os.path.join(bdir, 'shots.json'), encoding='utf-8'))['data']['resultSets']
    for r in (d[0] if isinstance(d, list) else d)['rowSet']:
        sh[r[0]] = r
    for r in rs(os.path.join(bdir, 'bio.json')):
        i = r['PLAYER_ID']
        if i not in base:
            continue
        x = base[i]
        o = dict(season='2025-26', pid=i, name=r['PLAYER_NAME'], gp=x['GP'], mpg=x['MIN'] / x['GP'] if x['GP'] else 0,
                 h=r['PLAYER_HEIGHT_INCHES'], w=r['PLAYER_WEIGHT'], oreb=r['OREB_PCT'], dreb=r['DREB_PCT'],
                 blk36=x['BLK'] / x['MIN'] * 36 if x['MIN'] else np.nan)
        o['rimd'] = rim[i]['PLUSMINUS'] if i in rim and rim[i]['FGA_LT_06'] >= 100 else np.nan
        o['rafg'] = sh[i][6] / sh[i][7] if i in sh and sh[i][7] and sh[i][7] >= 50 else np.nan
        obs.append(o)
    obs = [o for o in obs if o['gp'] >= 30 and o['mpg'] >= 20 and o['h'] and o['w']]
    for o in obs:
        o['h'] = float(o['h']); o['w'] = float(o['w'])
        for k in ('oreb', 'dreb'):
            o[k] = np.nan if o[k] is None else float(o[k])
    return obs, skipped


# ---------- 模型 ----------
def fit(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def heldout_r2(y, Xb, Xt, half):
    """A 擬合→B 評估、B→A；合併算 held-out R²。回傳 (基準, 測試)。"""
    pb, pt = np.empty_like(y), np.empty_like(y)
    for k in (0, 1):
        tr, te = half != k, half == k
        pb[te] = Xb[te] @ fit(Xb[tr], y[tr])
        pt[te] = Xt[te] @ fit(Xt[tr], y[tr])
    sst = ((y - y.mean()) ** 2).sum()
    return 1 - ((y - pb) ** 2).sum() / sst, 1 - ((y - pt) ** 2).sum() / sst


def run(obs, ykey, expo='ape', measured_only=False):
    o = [r for r in obs if np.isfinite(r[ykey])]
    y = np.array([r[ykey] for r in o], float)
    h = np.array([r['h'] for r in o]); w = np.array([r['w'] for r in o])
    e = np.array([r[expo] for r in o], float)
    miss = np.isnan(e).astype(float)
    ec = np.where(miss == 1, 0.0, e - np.nanmean(e))
    pid = np.array([r['pid'] for r in o]); half = pid % 2
    one = np.ones_like(h)
    Xb = np.column_stack([one, h, w] if measured_only else [one, h, w, miss])
    Xt = np.column_stack([Xb, ec])
    r2b, r2t = heldout_r2(y, Xb, Xt, half)
    res = dict(n_obs=len(y), n_players=len(set(pid.tolist())), n_measured_obs=int((miss == 0).sum()),
               n_measured_players=len(set(pid[miss == 0].tolist())),
               r2_base=r2b, r2_test=r2t, dr2=r2t - r2b, beta_per_inch=fit(Xt, y)[-1], y_sd=float(y.std()))
    rng = np.random.default_rng(SEED)
    up = np.unique(pid)
    idx = {p: np.where(pid == p)[0] for p in up}
    d, bs = [], []
    for _ in range(NBOOT):
        pick = np.concatenate([idx[p] for p in rng.choice(up, len(up), replace=True)])
        a, b = heldout_r2(y[pick], Xb[pick], Xt[pick], half[pick])
        d.append(b - a)
        bs.append(fit(Xt[pick], y[pick])[-1])
    res['dr2_ci'] = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    res['beta_ci'] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    return res


def main():
    comb = build_combine()
    by = {}
    for n, yr, hh, rr, ww in comb['rows']:
        k = norm(n)
        if k not in by or yr >= by[k][0]:
            by[k] = (yr, hh, rr, ww)
    dup = sum(1 for c in collections.Counter(norm(r[0]) for r in comb['rows']).values() if c > 1)
    obs, skipped = season_rows()
    for o in obs:
        k = norm(o['name'])
        m = by.get(k) or by.get(ALIAS.get(k, ''))
        o['ape'] = m[3] - m[1] if m else np.nan
        o['reach'] = (m[2] - m[1]) if m and m[2] else np.nan
    out = dict(seasons_skipped_missing_files=skipped, combine_rows=len(comb['rows']), combine_dup_names=dup,
               combine_sha256=comb['sha256_rows'], seed=SEED, nboot=NBOOT,
               seasons_used=sorted(set(o['season'] for o in obs)),
               measured_share_obs=float(np.mean([np.isfinite(o['ape']) for o in obs])),
               primary={}, reach={}, sens_measured={}, sens_2526={}, secondary_2526={})
    prim = ['oreb', 'dreb', 'blk36']
    for y in prim:
        out['primary'][y] = run(obs, y)
        out['reach'][y] = run(obs, y, expo='reach')
        out['sens_measured'][y] = run([o for o in obs if np.isfinite(o['ape'])], y, measured_only=True)
    o26 = [o for o in obs if o['season'] == '2025-26']
    for y in prim:
        out['sens_2526'][y] = run(o26, y)
    for y in ['rimd', 'rafg']:
        out['secondary_2526'][y] = run(o26, y)
    out['passed'] = [y for y in prim if out['primary'][y]['dr2_ci'][0] > 0]
    out['verdict_add_to_phys'] = len(out['passed']) >= 2
    json.dump(out, open(os.path.join(HERE, 'results.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, default=float)


if __name__ == '__main__':
    main()
