"""球員卡追蹤格子（E-239 後續，使用者 2026-11-05「加格子」）：把 NBA.com 追蹤資料裡穩定的「量」類數字補進既有格子提示卡。
只列量與占比（逐年 Spearman ≥ 0.60），不列效率（PPP、切入失誤率…逐年相關 < 0.30，是雜訊）；不進任何分數、不碰 OVR。
只用單季（NBA 2024-25 起追蹤定義有斷層，不跨季混窗口）。資料：data/tracking-cells/<季>/，由 scripts/fetch_tracking_cells.mjs 手動抓（沒有每日自動更新）。"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import season_nav as sn

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data/tracking-cells'

SYN = ['PRBallHandler', 'PRRollman', 'Handoff', 'Spotup', 'Isolation', 'Cut', 'OffScreen', 'Transition', 'Postup', 'Misc', 'OffRebound']

# 格子 -> [(標籤, 特徵, 格式)]。特徵由 features() 算
CELLS = {
    'drive': [('切入次數／36', 'drv_vol', '{:.1f}')],
    'short': [('禁區觸球／36', 'paint_vol', '{:.1f}'), ('低位觸球／36', 'post_vol', '{:.1f}')],
    'creation': [('拔起出手／36', 'pu_vol', '{:.1f}'), ('孤立占比', 'iso_freq', '{:.0%}'),
                 ('擋拆持球占比', 'prbh_freq', '{:.0%}'), ('交手（handoff）占比', 'hand_freq', '{:.0%}')],
    'pass': [('潛在助攻／36', 'pot_ast', '{:.1f}'), ('擋拆助攻／36', 'scr_ast', '{:.2f}')],
    'threeValue': [('拔起三分出手／36', 'pu3_vol', '{:.1f}'), ('接球三分出手／36', 'cs3_vol', '{:.1f}'),
                   ('快出手占比（觸球 < 2 秒）', 'quick', '{:.0%}')],
}
FOOT = '追蹤欄（NBA.com 追蹤資料）只列出手、觸球與戰術占比的量，不列效率（逐年相關太低，是雜訊）；單季，不進分數'


def _tab(d, name, season):
    f = d / f'{name}-{season}.json'
    if not f.exists():
        return {}
    j = json.loads(f.read_text(encoding='utf-8'))
    h = {k: i for i, k in enumerate(j['headers'])}
    return {int(r[h['PLAYER_ID']]): {k: r[i] for k, i in h.items()} for r in j['rowSet']}


def features(season):
    """{pid: {特徵: 值, 'gp', 'min'}}；缺值不放。每 36＝分子 ÷ Possessions 表 MIN × 36。"""
    d = DATA / season
    pos, drv, pu, cs = (_tab(d, f'pt-{n}', season) for n in ('Possessions', 'Drives', 'PullUpShot', 'CatchShoot'))
    ps, pt, po = (_tab(d, f'pt-{n}', season) for n in ('Passing', 'PaintTouch', 'PostTouch'))
    hu, ta, tl = _tab(d, 'hustle', season), _tab(d, 'shot-touch-all', season), _tab(d, 'shot-touch-lt2', season)
    syn = {t: _tab(d, f'syn-{t}', season) for t in SYN}
    out = {}
    for p, r in pos.items():
        m = r['MIN']
        if not m:
            continue
        f, k = {'gp': r['GP'], 'min': m}, 36 / m
        for key, tab, col in (('drv_vol', drv, 'DRIVES'), ('pu_vol', pu, 'PULL_UP_FGA'), ('pu3_vol', pu, 'PULL_UP_FG3A'),
                              ('cs3_vol', cs, 'CATCH_SHOOT_FG3A'), ('pot_ast', ps, 'POTENTIAL_AST'),
                              ('paint_vol', pt, 'PAINT_TOUCHES'), ('post_vol', po, 'POST_TOUCHES')):
            if p in tab and tab[p][col] is not None:
                f[key] = tab[p][col] * k
        if p in ta and ta[p]['FGA'] >= 20:
            f['quick'] = (tl[p]['FGA'] if p in tl else 0) / ta[p]['FGA']
        if p in hu and hu[p]['MIN']:
            f['scr_ast'] = hu[p]['SCREEN_ASSISTS'] * 36 / hu[p]['MIN']
        tot = sum(t[p]['POSS'] for t in syn.values() if p in t)
        if tot >= 50:
            for key, t in (('iso_freq', 'Isolation'), ('prbh_freq', 'PRBallHandler'), ('hand_freq', 'Handoff')):
                f[key] = (syn[t][p]['POSS'] if p in syn[t] else 0) / tot
        out[p] = f
    return out


def build(season, pool, note=''):
    """{pid: {格子: (rows, foot)}}；pool＝名次人群（pid 集合，同其他提示卡）。rows＝[標籤, 值, PR, 前十名次]。"""
    feats = features(season)
    meta = DATA / season / 'fetched.json'
    when = ''
    if meta.exists():
        m = json.loads(meta.read_text(encoding='utf-8'))
        when = datetime.fromisoformat(m['fetchedAt'].replace('Z', '+00:00')).astimezone().strftime('%m/%d')
    gmax = max((f['gp'] for f in feats.values()), default=0)
    src = f'{season} 追蹤資料' + (f'（{when} 手動抓取，約 {gmax} 場，不自動更新）' if when and note == 'snapshot' else '（整季）')
    out = {}
    for cell, items in CELLS.items():
        dist = {k: [feats[p][k] for p in pool if p in feats and k in feats[p]] for _, k, _ in items}
        for p, f in feats.items():
            rows = []
            for lab, k, fmt in items:
                if k not in f:
                    continue
                pr, rk = sn.pr_rank(f[k], dist[k]) if p in pool and dist[k] else (None, None)
                rows.append((lab, fmt.format(f[k]), pr, rk))
            if rows:
                out.setdefault(p, {})[cell] = (rows, [FOOT, src])
    return out


def add(tips, extra):
    """把追蹤列接在既有提示卡後面（沒有該格提示卡就略過）；extra＝build() 的 {格子: (rows, foot)} 或 None。回傳 tips。"""
    for cell, (rows, foot) in (extra or {}).items():
        t = tips.get(cell)
        if t:
            t['rows'] += [list(r) for r in rows]
            t['foot'] += list(foot)
    return tips
