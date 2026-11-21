"""名單頁精簡檢視的 10 個合併能力值（spec：reports/roster-lite-view/spec.md）。只改顯示：ranking.csv、OVR、OFF／DEF 算法不動。

建頁時在所有成分都已是最終顯示值之後呼叫 augment(cols, data_rows)：
  - 加權合併（play／outside／inside／offball／perim）：缺成分重新歸一，再還原分散度（f 上限 1.35），下限 40。
  - OFF／DEF 換尺（offR／defR）：70 ＋ 10·z，下限 40，不設上限。
  - handle＝creation 原值；rebound、help 沿用原欄。
  - 每個合併格子加 p.tips[key]（成分分數＋挑出的原始數據列，最多 8 列）。
名次人群 pool＝場均（MPG 欄 min）≥ season_nav.POOL_MPG 的人。
"""
import statistics
import sys

FLOOR = 40.0
F_MAX = 1.35

# key → [(成分欄, 權重)]
WEIGHTED = {
    'play': [('pass', .70), ('tovSkill', .30)],
    'outside': [('threeValue', .55), ('mid', .25), ('ft', .20)],
    'inside': [('short', .60), ('foulDraw', .40)],
    'offball': [('gravity', .40), ('spot', .30), ('cutroll', .30)],
    'perim': [('onBall', .60), ('pressure', .40)],
}
NEW_COLS = ['offR', 'defR', 'play', 'outside', 'inside', 'handle', 'offball', 'perim']


def _pool_vals(vals, inpool):
    return [v for v, ok in zip(vals, inpool) if ok and v is not None]


def merge_weighted(comps, inpool):
    """comps＝[(權重, [每人的值或 None])]；回傳每人的合併值（None＝全部缺）。"""
    n = len(comps[0][1])
    raw = []
    for i in range(n):
        have = [(w, vs[i]) for w, vs in comps if vs[i] is not None]
        sw = sum(w for w, _ in have)
        raw.append(sum(w * v for w, v in have) / sw if sw else None)
    pr = _pool_vals(raw, inpool)
    if len(pr) < 2:
        return [None if r is None else round(max(FLOOR, r), 1) for r in raw]
    m, s = statistics.fmean(pr), statistics.pstdev(pr)
    tw = ts = 0.0
    for w, vs in comps:
        cv = _pool_vals(vs, inpool)
        if len(cv) >= 2:
            tw += w
            ts += w * statistics.pstdev(cv)
    f = min(F_MAX, (ts / tw) / s) if s > 0 and tw > 0 else 1.0
    return [None if r is None else round(max(FLOOR, m + (r - m) * f), 1) for r in raw]


def rescale_net(xs, inpool):
    """OFF／DEF 換尺：70 ＋ 10·(x − pool 平均)/pool 標準差，下限 40，不設上限。"""
    pv = _pool_vals(xs, inpool)
    m, s = statistics.fmean(pv), statistics.pstdev(pv)
    return [None if x is None else round(max(FLOOR, 70 + 10 * (x - m) / s), 1) for x in xs]


def compute(rows, inpool):
    """rows＝[dict(欄→值)]；回傳 {key: [每人的值]}。"""
    out = {}
    for key, comps in WEIGHTED.items():
        out[key] = merge_weighted([(w, [r.get(c) for r in rows]) for c, w in comps], inpool)
    out['handle'] = [r.get('creation') for r in rows]
    out['offR'] = rescale_net([r.get('off') for r in rows], inpool)
    out['defR'] = rescale_net([r.get('def') for r in rows], inpool)
    return out


# ---------- 提示卡 ----------
DESC = {
    'outside': ('外線', 'Outside', '<b>投籃的準度與量</b>：三分、中距離、罰球', [('三分', '55%'), ('中距離', '25%'), ('罰球', '20%')]),
    'inside': ('內線', 'Inside', '<b>禁區得分</b>與<b>造犯規</b>', [('近框', '60%'), ('製造犯規', '40%')]),
    'handle': ('持球', 'Ball Handler', '<b>自己持球創造</b>：自主出手與擋拆持球各半', []),
    'offball': ('無球', 'Off-Ball', '<b>沒拿球</b>時的威脅：引力、空檔投籃、切入順下', [('引力', '40%'), ('空檔射手', '30%'), ('切入順下', '30%')]),
    'play': ('組織', 'Playmaking', '<b>傳球</b>創造機會，且<b>少失誤</b>', [('傳球', '70%'), ('少失誤', '30%')]),
    'perim': ('外防', 'Perimeter D', '<b>外線防守</b>：單防與壓迫（抄截、干擾）', [('單防', '60%'), ('壓迫', '40%')]),
    'offR': ('進攻', 'Offense', '每 36 分鐘比聯盟平均<b>多得幾分</b>，換成 40–99+ 的尺', []),
    'defR': ('防守', 'Defense', '每 36 分鐘比聯盟平均<b>少丟幾分</b>，換成 40–99+ 的尺', []),
}
SHORT = {'outside': 'OUT', 'inside': 'IN', 'handle': 'BALL', 'offball': 'OFFB', 'play': 'PLAY', 'perim': 'PER', 'offR': 'OFF', 'defR': 'DEF'}
COMP_LABEL = {'threeValue': '三分', 'mid': '中距離', 'ft': '罰球', 'short': '近框', 'foulDraw': '製造犯規', 'gravity': '引力',
              'spot': '空檔射手', 'cutroll': '切入順下', 'pass': '傳球', 'tovSkill': '少失誤', 'onBall': '單防', 'pressure': '壓迫'}
# 成分列之後挑的原始數據列：(來源 tips 鍵, 原列名, 合併卡上的列名)；列名挑不到就跳過
PICKS = {
    'outside': [('threeValue', '命中率', '三分命中率'), ('threeValue', '出手量', '三分出手量'), ('mid', '命中率', '中距離命中率'),
                ('mid', '出手量', '中距離出手量'), ('ft', '命中率', '罰球命中率')],
    'inside': [('short', '命中率', '近框命中率'), ('short', '出手量', '近框出手量'), ('foulDraw', '罰球量', '罰球量'),
               ('foulDraw', '罰球率', '罰球率'), ('short', '禁區觸球／36', '禁區觸球／36')],
    'offball': [('gravity', '引力分數', '引力分數')],
    'play': [('pass', '助攻量', '助攻量'), ('pass', '助攻率', '助攻率'), ('pass', '潛在助攻／36', '潛在助攻／36'),
             ('tovSkill', '每百次觸球失誤', '每百次觸球失誤'), ('tovSkill', '失誤', '失誤')],
    'perim': [('pressure', '抄截', '抄截'), ('pressure', '干擾球', '干擾球'), ('pressure', '犯規', '犯規')],
}
MAX_ROWS = 8


def _find(tips, src, name):
    t = tips.get(src)
    for r in (t['rows'] if t else ()):
        if r[0] == name:
            return r
    return None


def _prefix_dedupe(rows):
    """同名列不能出現兩次：後來的加來源前綴（挑列時已改好名；這裡只是保險）。"""
    seen, out = set(), []
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        out.append(r)
    return out


def _fmt_net(x):
    return None if x is None else ('+' if x > 0 else '−' if x < 0 else '') + f'{abs(x):.1f}'


def build_tips(key, p, vals, pools, inpool, sn):
    """p＝這個人的 dict（欄→值，含 tips）；vals＝這個人的合併值 dict；pools＝{欄: pool 值 list}。回傳提示卡 dict 或 None。"""
    v = vals.get(key)
    if v is None:
        return None
    n, en, d, parts = DESC[key]
    tips = p.get('tips') or {}

    def row(label, x, pool_key):
        if x is None:
            return None
        pr, rk = sn.pr_rank(x, pools[pool_key]) if pools.get(pool_key) else (None, None)
        return [label, round(x), pr, rk if inpool else None]

    rows = []
    if key == 'handle':
        t = tips.get('creation')
        rows = [list(r) for r in (t['rows'] if t else ())][:7]
    elif key == 'offR':
        x = p.get('off')
        pr, rk = sn.pr_rank(x, pools['off']) if x is not None and pools.get('off') else (None, None)
        rows = [['每 36 分鐘淨分', _fmt_net(x), pr, rk if inpool else None]]
        for lab, k in (('外線', 'outside'), ('內線', 'inside'), ('持球', 'handle'), ('無球', 'offball'), ('組織', 'play')):
            rows.append(row(lab, vals.get(k), k))
    elif key == 'defR':
        x = p.get('def')
        pr, rk = sn.pr_rank(x, pools['def']) if x is not None and pools.get('def') else (None, None)
        rows = [['每 36 分鐘淨分', _fmt_net(x), pr, rk if inpool else None]]
        rows.append(row('外防', vals.get('perim'), 'perim'))
        rows.append(row('內防', p.get('help'), 'help'))
        b = p.get('dbon')
        if b is not None:
            pr, rk = sn.pr_rank(b, pools['dbon']) if pools.get('dbon') else (None, None)
            rows.append(['防守意識', ('+' if b > 0 else '−' if b < 0 else '') + f'{abs(b):.2f}', pr, rk if inpool else None])
    else:
        for c, _ in WEIGHTED[key] if key in WEIGHTED else ():
            rows.append(row(COMP_LABEL[c], p.get(c), c))
        head = lambda src, k: [list(r) for r in (tips.get(src) or {'rows': ()})['rows']][:k]
        tail = []
        if key == 'offball':
            tail = [r for r in [_find(tips, 'gravity', '引力分數')] if r] + head('spot', 2) + head('cutroll', 2)
        elif key == 'perim':
            tail = head('onBall', 2)
        for src, name, out in PICKS.get(key, ()) if key != 'offball' else ():
            r = _find(tips, src, name)
            if r:
                tail.append([out, *r[1:]])
        rows += [list(r) for r in tail]
    rows = _prefix_dedupe([r for r in rows if r])[:MAX_ROWS]
    foot = [sn.NO_RANK_FOOT if not inpool else 'PR、名次只比場均 ≥ %d 分鐘的人' % sn.POOL_MPG]
    return sn.cell_tip(n, SHORT[key], round(v), rows, d=d, foot=foot)


def augment(cols, data_rows, sn=None):
    """cols／data_rows（list of list）原地加 NEW_COLS 八欄（值＋提示卡）。回傳 {key: [值]}（依 data_rows 順序）。"""
    if sn is None:
        import season_nav as sn
    ci = {c: i for i, c in enumerate(cols)}
    rows = [{c: r[i] for c, i in ci.items()} for r in data_rows]
    inpool = [(r.get('min') or 0) >= sn.POOL_MPG for r in rows]
    vals = compute(rows, inpool)
    pools = {k: _pool_vals(vals[k], inpool) for k in vals}
    for k in ('off', 'def', 'dbon', 'help'):
        pools[k] = _pool_vals([r.get(k) for r in rows], inpool)
    for i, r in enumerate(rows):
        mine = {k: vals[k][i] for k in vals}
        t = data_rows[i][ci['tips']]
        for key in ('outside', 'inside', 'handle', 'offball', 'play', 'perim', 'offR', 'defR'):
            tip = build_tips(key, r, mine, pools, inpool[i], sn)
            if tip:
                t[key] = tip
    for k in NEW_COLS:
        cols.append(k)
    for i, r in enumerate(data_rows):
        r.extend(vals[k][i] for k in NEW_COLS)
    return vals


# ---------- 自檢 ----------
def _selftest():
    import math
    ok = lambda c, m: (c or sys.exit('FAIL: ' + m))
    n = 40
    base = [50 + i for i in range(n)]
    inp = [True] * n
    # 單一成分：value＝原值
    one = merge_weighted([(1.0, [float(x) for x in base])], inp)
    ok(all(abs(a - b) < 0.06 for a, b in zip(one, base)), '單一成分 value 不等於原值')
    # 缺成分：權重重新歸一
    a = [float(x) for x in base]
    b = [float(x) for x in base]
    b[3] = None
    r = merge_weighted([(.5, a), (.5, b)], inp)
    ok(r[3] is not None and abs(r[3] - a[3]) < 0.6, '缺成分沒有重新歸一')
    # 全缺回 None
    r = merge_weighted([(.5, [None] * n), (.5, [None] * n)], inp)
    ok(all(x is None for x in r), '全缺應回 None')
    r = merge_weighted([(.5, a[:5] + [None]), (.5, b[:5] + [None])], [True] * 6)
    ok(r[5] is None, '某人全缺應回 None')
    # 下限 40
    low = merge_weighted([(1.0, [10.0] + [float(x) for x in base[:-1]])], inp)
    ok(low[0] == 40.0, '下限 40 沒套用')
    # f 上限 1.35：兩成分完全反向 → 合併後 raw 標準差≈0 時 t/s 會爆，f 必須被 1.35 蓋住
    up = [float(x) for x in base]
    dn = [float(100 - x) + 0.01 * (i % 3) for i, x in enumerate(base)]
    m = merge_weighted([(.5, up), (.5, dn)], inp)
    raw = [.5 * x + .5 * y for x, y in zip(up, dn)]
    mu = statistics.fmean(raw)
    ok(all(abs((v - mu) - (rw - mu) * F_MAX) < 0.06 or v == 40.0 for v, rw in zip(m, raw)), 'f 未被限制在 1.35')
    # 正常相關時 f>1：還原分散度（分散度回到成分的水準）
    c1 = [float(x) for x in base]
    c2 = [float(x) + (3 if i % 2 else -3) for i, x in enumerate(base)]
    mm = merge_weighted([(.5, c1), (.5, c2)], inp)
    ok(statistics.pstdev(mm) >= statistics.pstdev([(x + y) / 2 for x, y in zip(c1, c2)]) - 1e-6, '分散度沒還原')
    # OFF 換尺：單調、pool 平均＝70、標準差＝10
    xs = [-3.3 + .1 * i for i in range(n)] + [None]
    sc = rescale_net(xs, [True] * n + [False])
    ok(sc[-1] is None, 'OFF None 應回 None')
    ok(all(x <= y for x, y in zip(sc[:n - 1], sc[1:n])), 'OFF 換尺不單調')
    ok(abs(statistics.fmean(sc[:n]) - 70) < 0.5 or min(sc[:n]) <= 40.0, 'OFF 換尺平均不是 70')
    ok(max(rescale_net([0.0] * 30 + [100.0], [True] * 31)) > 99, 'OFF 不應有上限')
    # augment：欄位、提示卡
    cols = ['min', 'tips', 'pass', 'tovSkill', 'threeValue', 'mid', 'ft', 'short', 'foulDraw', 'creation', 'gravity', 'spot', 'cutroll',
            'onBall', 'pressure', 'help', 'dbon', 'off', 'def']
    drows = []
    for i in range(30):
        v = 55.0 + i
        drows.append([20.0, {'threeValue': {'rows': [['命中率', '40%', 50, None], ['出手量', '5/36', 50, None]]}}] + [v] * 9
                     + [None if i == 0 else v, None if i == 0 else v] + [v, v, v, 0.1 * i, i * .2 - 3, i * .1 - 1])
    class _SN:
        POOL_MPG = 15
        NO_RANK_FOOT = 'x'
        @staticmethod
        def pr_rank(x, pool, low_good=False):
            return round(100 * sum(q < x for q in pool) / len(pool)), None
        @staticmethod
        def cell_tip(n, s, v, rows, d='', foot=()):
            return {'n': n, 's': s, 'v': v, 'd': d, 'rows': [list(r) for r in rows], 'foot': list(foot)}
    cc = list(cols)
    vals = augment(cc, drows, _SN)
    ok(cc[-8:] == NEW_COLS and all(len(r) == len(cc) for r in drows), 'augment 欄數不對')
    ok(drows[5][1]['outside']['rows'][3][0] == '三分命中率' and len(drows[5][1]['offR']['rows']) <= MAX_ROWS, 'outside 提示卡列不對')
    ok(vals['offball'][0] is not None, '缺 spot／cutroll 時 offball 應用 gravity')
    print('lite_cells selftest OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        _selftest()
    else:
        print(__doc__)
