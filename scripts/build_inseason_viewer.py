"""賽中 OVR 名單頁：以正式卡名單頁為版型，換成 inseason 0.2.4（原名 0.2.2，R-050 起跟先驗正式卡同號；C4，先驗 card 0.2.4＝用人回歸＋當季 RAPM 目標；OVR 為每場，R-028；舊版 0.2.1 為 card 0.2.2 先驗）的 OVR、現任球隊與 2026-27 場均真實數據。

輸入：reports/ovr-inseason-2026-27/live/<日期>/{ranking.csv,meta.json}、data/season-source-2026-27/player-games.json。
版型：reports/ovr-v58-card-2025-26/roster-viewer.html（只讀）。
注入隊色／隊徽／頭像／真實數據沿用 scripts/enrich_roster_viewer.py 的函式與樣式（不改該檔，在記憶體裡換資料來源與年份文字）。
輸出：live/<日期>/roster-viewer.html

用法：python -I scripts/build_inseason_viewer.py [日期，預設 2026-10-27]
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enrich_roster_viewer as er  # noqa: E402
from season_nav import add_season_nav, apply_common, regroup_attrs  # noqa: E402
import season_nav as sn  # noqa: E402
from site_header import add_masthead  # noqa: E402
import attr_cell_tips as AT  # noqa: E402
import blend_display as BD  # noqa: E402
import tracking_cells as TC  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reports/impact-epm-2026-27'))
import epm_live  # noqa: E402
from build_card_viewer import (onball_rows, onball_tip, pres_tip, pres_tips, tov_tip,  # noqa: E402
                               PRES_SUB, PRES_LOW_GOOD)

ROOT = er.ROOT
PD_NOTE = '（老將近三季加權含本季；新秀只看本季）'


def pres_tips_live(path, ids):
    """壓迫／切入賽中解凍（2026-11-01）：live/<日>/pres-drive.json 的窗口分量 → ({playerId: 細項列}, pool 人數)。
    格式同 build_card_viewer.pres_tips；PR／名次人群＝ids（本季場均 ≥ sn.POOL_MPG 分鐘，老將新秀都算；使用者 2026-11-01）。"""
    side = json.loads(path.read_text(encoding='utf-8'))['players']
    pool = [v for pid, v in side.items() if pid in ids]
    tips = {}
    for pid, v in side.items():
        lines, inpool = [], pid in ids
        for k, label, unit, fmt in PRES_SUB:
            c = k.replace('_shr', '')
            x = float(v['shr'][c])
            pr, rk = sn.pr_rank(x, [float(q['shr'][c]) for q in pool], low_good=k in PRES_LOW_GOOD)
            s = fmt.format(x)
            if k in PRES_LOW_GOOD:
                s += '（多）' if pr <= 33 else '（少）' if pr >= 67 else '（普通）'
            lines.append((label, s + unit, pr, rk if inpool else None))
        tips[pid] = (lines, v['force'])
    return tips, len(pool)
BASE = ROOT / 'reports/ovr-v58-card-2025-26/roster-viewer.html'
SRC26 = ROOT / 'data/season-source-2026-27/player-games.json'


# OVR 折線圖（使用者 2026-10-31：近 5 場表右邊空著）：開季先驗＋逐場重算的 OVR（ovr_history.py 產 ovr-history.json），
# 放在近 5 場表右邊，窄螢幕換行到表下面；沒有這個檔就不畫
OVR_CSS = """
.card .g5.hc{display:flex;flex-wrap:wrap;gap:12px;align-items:stretch;justify-self:stretch;overflow:visible;border:0;background:none}
.card .g5.hc[hidden]{display:none}
.g5.hc>.g5in{flex:0 1 auto;min-width:0;max-width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:3px;background:var(--panel-2);scrollbar-width:thin;scrollbar-color:#38424f transparent}
.g5.hc>.ovc{flex:1 1 240px;min-width:0;display:flex;flex-direction:column;border:1px solid var(--line);border-radius:3px;background:var(--panel-2);padding:6px 10px 4px}
.ovc .ovh{display:flex;justify-content:space-between;align-items:baseline;color:var(--muted);font:600 .7rem var(--f-disp);letter-spacing:.04em;padding-bottom:2px}
.ovc .ovh b{color:var(--fg);font:700 .86rem var(--f-disp);font-variant-numeric:tabular-nums}
.ovc svg{width:100%;height:auto;display:block;overflow:visible;margin:auto 0}
.ovc .ax{font:500 10px var(--f-disp);fill:var(--muted);font-variant-numeric:tabular-nums}
.ovc .gd{stroke:var(--line);stroke-width:1}
.ovc .ref{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 4;opacity:.6}
.ovc .ln{fill:none;stroke:var(--g-a);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.ovc .ar{fill:var(--g-a);opacity:.08}
.ovc .pt{fill:var(--panel-2);stroke:var(--g-a);stroke-width:2}
.ovc .pt.st{stroke:var(--muted)}
.ovc .hit{fill:transparent;cursor:default}
.ovc .tip rect{fill:#0d1117;stroke:var(--line)}
.ovc .tip text{font:600 11px var(--f-disp);fill:var(--fg);font-variant-numeric:tabular-nums}
"""
OVR_JS = r"""
// OVR 折線（使用者 2026-10-31）：開季先驗（新秀＝順位起點）→ 每打一場重算一次；虛線＝開季
function ovrChart(p) {
  const h = OVRH[p.name];
  if (!h || !h.pts.length) return '';
  const md = d => +d.slice(5, 7) + '/' + +d.slice(8);
  const pts = [['開季', h.start], ...h.pts.map(([d, v]) => [md(d), v])];
  const W = 340, H = 170, L = 30, R = 12, T = 12, B = 22;
  const vs = pts.map(q => q[1]);
  let lo = Math.min(...vs), hi = Math.max(...vs);
  const pad = Math.max(1, (6 - (hi - lo)) / 2);
  lo = Math.floor(lo - pad); hi = Math.ceil(hi + pad);
  const x = i => L + (pts.length > 1 ? i * (W - L - R) / (pts.length - 1) : (W - L - R) / 2);
  const y = v => T + (hi - v) * (H - T - B) / (hi - lo);
  const step = Math.max(1, Math.ceil((hi - lo) / 4));
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
  const xl = Math.max(1, Math.ceil(pts.length / 8));          // x 標籤太密就隔幾場標一次（最後一場一定標）
  const path = pts.map((q, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(q[1]).toFixed(1)).join('');
  const area = path + `L${x(pts.length - 1).toFixed(1)} ${H - B}L${x(0).toFixed(1)} ${H - B}Z`;
  const last = vs[vs.length - 1], d = typeof p.dovr === 'number' ? p.dovr : last - h.start;   // 差值和圓環同源（折線點只存到 0.1，相減會差 0.1）
  const tip = (q, i) => `${i ? q[0] : '開季起點'}　OVR ${q[1].toFixed(1)}`;
  return `<div class="ovc"><div class="ovh"><span>OVR 走勢 · 每場重算</span><span>開季 <b>${h.start.toFixed(1)}</b> → 現在 <b>${last.toFixed(1)}</b>` +
    ` <b class="${d >= 0.05 ? 'up' : d <= -0.05 ? 'dn' : ''}">${d > 0 ? '+' : ''}${d.toFixed(1)}</b></span></div>` +
    `<svg viewBox="0 0 ${W} ${H}" onmouseleave="ovTip(this)">` +
    ticks.map(v => `<line class="gd" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="ax" x="${L - 5}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`).join('') +
    `<line class="ref" x1="${L}" x2="${W - R}" y1="${y(h.start)}" y2="${y(h.start)}"/>` +
    `<path class="ar" d="${area}"/><path class="ln" d="${path}"/>` +
    pts.map((q, i) => `<circle class="pt${i ? '' : ' st'}" cx="${x(i)}" cy="${y(q[1])}" r="${i === pts.length - 1 ? 4 : 3}"/>` +
      ((i % xl === 0 && pts.length - 1 - i >= xl) || i === pts.length - 1 ? `<text class="ax" x="${x(i)}" y="${H - 6}" text-anchor="middle">${q[0]}</text>` : '') +
      `<circle class="hit" cx="${x(i)}" cy="${y(q[1])}" r="11" data-t="${tip(q, i)}" onmouseenter="ovTip(this.ownerSVGElement,this)"/>`).join('') +
    `<g class="tip" visibility="hidden"><rect rx="3" height="20"/><text y="14"></text></g></svg></div>`;
}
function ovTip(svg, c) {
  const g = svg.querySelector('.tip');
  if (!c) { g.setAttribute('visibility', 'hidden'); return; }
  const t = g.querySelector('text'), r = g.querySelector('rect');
  t.textContent = c.dataset.t;
  const w = t.getComputedTextLength() + 14, vb = svg.viewBox.baseVal;
  const cx = +c.getAttribute('cx'), cy = +c.getAttribute('cy');
  const gx = Math.min(Math.max(cx - w / 2, 0), vb.width - w), gy = cy > 34 ? cy - 30 : cy + 10;
  r.setAttribute('width', w); t.setAttribute('x', 7);
  g.setAttribute('transform', `translate(${gx},${gy})`);
  g.setAttribute('visibility', 'visible');
}
"""


def add_ovr_chart(live):
    """近 5 場表右邊加 OVR 折線（記憶體裡改 er.JS／er.CSS，不改 enrich_roster_viewer.py）。"""
    f = live / 'ovr-history.json'
    if not f.exists():
        print('OVR 折線：沒有 ovr-history.json，不畫', file=sys.stderr)
        return
    h = json.loads(f.read_text(encoding='utf-8'))
    data = {v['name']: {'start': v['start'], 'pts': v['pts']} for v in h['players'].values() if v['pts']}  # N=0（傷兵等）不畫
    old = """<div class="g5${sv ? ' sd' : ''}"${G5_OPEN ? '' : ' hidden'}>${sv ? seasonLog(r) : gameLog(r, p)}</div>"""
    new = ("""<div class="g5${sv ? ' sd' : ''}${!sv && OVRH[p.name] ? ' hc' : ''}"${G5_OPEN ? '' : ' hidden'}>"""
           """${sv ? seasonLog(r) : OVRH[p.name] ? `<div class="g5in">${gameLog(r, p)}</div>${ovrChart(p)}` : gameLog(r, p)}</div>""")
    assert er.JS.count(old) == 1, old
    er.JS = er.JS.replace(old, new) + '\nconst OVRH=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';' + OVR_JS
    er.CSS += OVR_CSS


def onball_live(rows, pool):
    """PER D 提示卡（E-060 三分量）：和頁面 onBall 同一份累計量——老將＝四季窗口加權含本季（rookie_defense.veteran），
    新秀＝本季（rookie_defense.inseason）。分量換回 onBall 和頁面差 ≥ 0.05 的人不給卡。PR 人群＝pool（int playerId 集合，同 TO）。"""
    sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
    import rookie_defense as RD
    rs = json.loads(SRC26.read_text(encoding='utf-8'))['data']['resultSets'][0]
    c = len({r[rs['headers'].index('GAME_ID')] for r in rs['rowSet']}) / 1230 * 82   # 同 run_c4_live_rookie.vet_defense
    prior = {p['playerId']: p for p in json.load(open(RD.PRIOR_CARD, encoding='utf-8'))['players']}
    pf = {p: {'PG': 'G', 'SG': 'G', 'SF': 'F', 'PF': 'F', 'C': 'C'}.get(q.get('pos')) for p, q in prior.items()}
    vet, _ = RD.veteran(c, '2026-27', pf, comps=True)
    new = RD.inseason_comps('2026-27', pf)
    st, scale = RD.frozen_stats(), RD.OnBallScale()
    comps, note, off = {}, {}, 0
    for r in rows:
        pid = int(r['playerId'])
        x = vet.get(pid) if pid in prior else new.get(pid)
        if not x or r['onBall'] == '':
            continue
        g = x[3]
        z = (x[0] - st['zC3'][g][0]) / st['zC3'][g][1] + (x[1] - st['zB'][0]) / st['zB'][1] - (x[2] - st['zT'][0]) / st['zT'][1]
        if abs(scale(z) - float(r['onBall'])) >= 0.05:
            off += 1
            continue
        comps[pid] = x[:3]
        note[pid] = '（近三季加權，含本季）' if pid in prior else '（新秀：只看本季）'
    if off:
        print(f'PER D 提示卡：{off} 人分量換回 onBall 對不上頁面，不給卡', file=sys.stderr)
    return onball_rows(comps, pool), note


GRAV_NOTE = {'2025-26': '（本季還沒有資料，看 2025-26）', '2026-27': '（只看本季）', '2025-26+2026-27': '（2025-26 與本季依出場畫面加權）'}


def main():
    sys.stdout.reconfigure(encoding='utf-8')    # -I 不吃 PYTHONIOENCODING；名字有 ņ 等字時 cp950 印不出來
    day = sys.argv[1] if len(sys.argv) > 1 else '2026-10-27'
    live = ROOT / 'reports/ovr-inseason-2026-27/live' / day
    meta = json.loads((live / 'meta.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader((live / 'ranking.csv').open(encoding='utf-8')))
    nopr = len(list(csv.DictReader((live / 'no-prior.csv').open(encoding='utf-8'))))
    cols = ['rank', 'ovr', 'name', 'pos', 'team', 'ht', 'min', 'gp', 'imp', 'dbon', 'threeValue', 'mid', 'short', 'ft',
            'drive', 'foulDraw', 'pass', 'tovSkill', 'creation', 'rebound', 'physique', 'stamina', 'onBall', 'help', 'pressure',
            'last', 'dovr', 'tips']
    # card 0.2.2 先驗（E-074）：ranking.csv 帶 presDisplay／foulDisc → PRES 欄顯示 presDisplay，提示卡列逼失誤與五分量（同 build_card_viewer.py）
    has_pd = 'presDisplay' in rows[0]
    # 提示卡名次人群：本季場均（頁面 MPG 欄）≥ sn.POOL_MPG 分鐘
    pool = sn.mpg_pool({r['playerId']: float(r['MIN26'] or 0) / int(r['N']) for r in rows if int(r['N'])})
    ipool = {int(k) for k in pool}
    if has_pd:
        cols += ['force', 'foulDisc']
        pd_live = (live / 'pres-drive.json').exists()     # 2026-11-01 壓迫／切入解凍：有側檔就用窗口分量
        ptips, n_pres = pres_tips_live(live / 'pres-drive.json', pool) if pd_live else pres_tips({r['name'] for r in rows if r['playerId'] in pool})   # 否則：2025-26 五分量（凍結）
    # TO 提示卡：2026-27 至今的失誤、持球分鐘、每持球分鐘失誤（0.2.12）
    trows, n_tov = sn.tov_rows(SRC26, 'PLAYER_ID', ipool, ROOT / 'data/defense-seventh/2026-27/possessions.json')
    hrows = sn.three_rows(SRC26, 'PLAYER_ID', ipool)   # 3PT 提示卡：本季至今三分命中率、出手量
    wstat = AT.window_stats(False, meta['window8']['gamesDone'])
    bdisp = BD.build(wstat, False)   # 3PT／FT 顯示欄量準混合（R-168）：只改顯示，OVR／名次不動
    atips = AT.build(wstat, ipool, AT.season_near_rim())   # MID／INS／FT／DRV／FD／PASS／CRT／REB／RIM 提示卡：四季窗口含本季
    trk = TC.build('2026-27', ipool, 'snapshot')   # 追蹤量格子（E-239 後續）：手動快照，接在 DRV／INS／CRT／PASS／3PT 提示卡後面，不進分數
    orows, ob_note = onball_live(rows, ipool)
    base = BASE.read_text(encoding='utf-8')
    old = json.loads(re.search(r'const DATA=(\{.*?\});\nconst COLS', base, re.S).group(1))
    ht = {r[old['cols'].index('name')]: r[old['cols'].index('ht')] for r in old['rows']}
    # DIQ 顯示負分：先試今天的 def-L-live.csv／meta 記的 def-L 檔配 meta 的 posMeanD（老將 live 加成就是前者），
    # 再試 def-L-live.csv 反推 posMeanD；都對不上就只顯示正值。新秀走卡鏈，加成 × min(1, possW/2500)（taper）
    ul = next((v['ulBonus'] for v in meta.values() if isinstance(v, dict) and 'ulBonus' in v), None)
    live_d = ROOT / 'data/_inseason_build/def-L-live.csv'
    rk = live / 'rookies-detail.json'
    taper = {str(x['playerId']) for x in json.loads(rk.read_text(encoding='utf-8'))} if rk.exists() else ()
    dcen = sn.defense_centered(rows, 'playerId', ([(live_d, ul['posMeanD']), (ROOT / ul['defL'], ul['posMeanD'])] if ul else [])
                               + [(live_d, None)], taper)
    if dcen is None:
        print('DIQ 負分：找不到對得上的 D 檔，只顯示正值', file=sys.stderr)
    # 0.2.10j：GRV 提示卡讀 live/<日>/gravity.json（run_c4_live_rookie 寫：原始引力、來源）；PR／名次對有 NBA.com 資料、場均夠的人
    gj = live / 'gravity.json'
    grav = json.loads(gj.read_text(encoding='utf-8'))['players'] if gj.exists() else {}
    g_pool = [v['raw'] for p, v in grav.items() if p in pool and v['raw'] is not None and v['src'] not in sn.GRAVITY_IMPUTED]
    od, od_bad = sn.off_def(rows, 'playerId')
    if od_bad:
        print(f'進攻／防守分：{od_bad} 人 pred0 用卡片係數算不回來，顯示「—」', file=sys.stderr)
    data_rows = []
    def tips(r):
        t = {}
        if has_pd:
            if pd_live:
                sub = ptips.get(r['playerId'])
                t['pressure'] = (sn.cell_tip('壓迫', 'PRES', round(float(r['pressure'])), [], d='新秀：本季還沒有壓迫分量')
                                 if r['presDisplay'] == '' or sub is None else
                                 pres_tip(float(r['presDisplay']), float(r['pressure']), sub[0], n_pres, PD_NOTE, r['playerId'] in pool))
            else:
                t['pressure'] = (sn.cell_tip('壓迫', 'PRES', round(float(r['pressure'])), [], d='新秀：沒有 2025-26 的壓迫分量')
                                 if r['presDisplay'] == '' or r['name'] not in ptips else
                                 pres_tip(float(r['presDisplay']), float(r['pressure']), ptips[r['name']], n_pres, '（只看 2025-26 賽季數據）', r['playerId'] in pool))
        hr = hrows.get(int(r['playerId']))
        if hr:
            t['threeValue'] = sn.three_tip(float(r['threeValue'] or r['long']), hr, '2026-27 至今', r['playerId'] in pool)
        for a, sub in atips.get(int(r['playerId']), {}).items():
            if r.get(a, '') != '':
                t[a] = AT.tip(a, float(r[a]), sub, '（近三季加權，含本季）')
        TC.add(t, trk.get(int(r['playerId'])))
        tr = trows.get(int(r['playerId']))
        if tr:
            t['tovSkill'] = tov_tip(float(r['tovSkill']), tr, n_tov, '2026-27 至今', r['playerId'] in pool)
        ob = orows.get(int(r['playerId']))
        if ob:
            t['onBall'] = onball_tip(float(r['onBall']), ob, ob_note[int(r['playerId'])], r['playerId'] in pool)
        gv = grav.get(r['playerId'])
        if gv and r.get('gravity', '') != '':
            t['gravity'] = sn.gravity_tip(float(r['gravity']), gv['raw'], gv['src'], g_pool, r['playerId'] in pool, GRAV_NOTE.get(gv['src'], ''))
        return t
    rows = sn.display_rows(rows)   # 能力值顯示尺（2026-11-02 方案 B）：off/def、名次人群已用原值算完
    for r in rows:   # R-168：有窗口資料的人 3PT／FT 換量準混合（已含顯示尺）；新秀沒資料維持原值
        b = bdisp.get(int(r['playerId']), {})
        if 'ft' in b:
            r['ft'] = repr(round(sn.display_scale(b['ft']), 1))
        if 'threeValue' in b:
            r['threeValue'] = repr(round(sn.display_scale(b['threeValue']), 1))
    for r in rows:
        num = lambda k: float(r[k])
        # E-116 新秀先驗列沒有 threeValue／presDisplay／foulDisc（無上季卡）：3PT 退回 long、PRES 退回 pressure、犯規紀律留空
        alt = {'threeValue': 'long', 'presDisplay': 'pressure'}
        opt = lambda k: num(k) if r[k] != '' else (num(alt[k]) if k in alt else None)
        # 舊版型沒有的人（E-116 新秀）身高改取 ranking.csv 的 heightInches（bio）
        h = ht.get(r['name']) or (round(num('heightInches')) if r.get('heightInches') else 0)
        data_rows.append([int(r['rank']), num('ovr'), r['name'], r['pos'], r['team'], h,
                          round(num('MIN26') / int(r['N']), 1) if int(r['N']) else 0.0, int(r['N']), num('predictedPer36'),
                          dcen[r['playerId']] if dcen else (num('defenseBonus') or None),
                          *[opt('presDisplay') if (a == 'pressure' and has_pd) else opt(a) for a in cols[10:25]],
                          num('lastOVR'), num('dOVR'), tips(r), *([num('pressure'), opt('foulDisc')] if has_pd else []),
                          *od[r['playerId']], opt('gravity') if r.get('gravity', '') != '' else None])
    cols += ['off', 'def', 'gravity']   # 0.2.10j：引力（舊版夾沒有 gravity 欄 → null）
    # ΔOVR 五色：≥+4 深綠、+1～+4 淺綠、±1 內灰、−1～−4 橘、≤−4 紅（沿用等第色）
    dcol = ("(v => v >= 4 ? 'var(--g-a)' : v >= 1 ? 'var(--g-b)' : v > -1 ? 'var(--muted)'"
            " : v > -4 ? 'var(--g-d)' : 'var(--g-f)')(p.dovr)")
    s = base
    s = s.replace('<title>OVR 名單檢視</title>', '<title>球員能力值 · TrueOVR</title>', 1)
    s = s.replace('<h1>2025-26 <span>OVR</span> 名單</h1>', '<h1>2026-27 <span>OVR</span> 名單</h1>', 1)
    s = re.sub(r'<div class="src">.*?</div>',
               f'<div class="src">OVR：賽中 C4（{meta["version"]}），開季起點 {meta["priorCard"]}{"（用人回歸＋當季 RAPM 目標）" if "predNew" in rows[0] else ""}；數據截至 {meta["dataCutoff"]}；'
               f'{("PRES＝逼失誤扣犯規（老將近三季加權含本季、新秀只看本季）· " if pd_live else "PRES＝逼失誤扣犯規（沿用 2025-26 數據）· ") if has_pd else ""}{"GRV＝引力：沒拿球時防守人也不敢離開他的程度（NBA.com 無球外線引力，2025-26 與本季加權；沒有資料的人用三分出手、命中率、用球率與位置推估）· " if 'gravity' in rows[0] else ""}N=已打場數 · {len(rows)} 人（另 {nopr} 人沒有上季卡，未列入）· 樣本很小，只看趨勢</div>', s, count=1, flags=re.S)
    new_data = json.dumps({'cols': cols, 'rows': data_rows}, ensure_ascii=False, separators=(',', ':'))
    s = re.sub(r'const DATA=\{.*?\};\nconst COLS', lambda m: f'const DATA={new_data};\nconst COLS', s, count=1, flags=re.S)
    for a, b in [
        ("['long', '3PT', '三分']", "['threeValue', '3PT', '三分']"),
        ("['drive', 'DRV', '切入']", "['drive', 'DRV', '切入'], ['foulDraw', 'FD', '製造犯規']"),
        ('<th class="g" colspan="2">出場</th>', '<th class="g" colspan="3">出場</th>'),
        ('colspan="22"', 'colspan="25"'),
        ("th('min', 'MIN', '分鐘', 'gl') + th('gp', 'GP', '場數')",
         "th('min', 'MPG', '分鐘', 'gl') + th('gp', 'N', '場數') + th('dovr', 'ΔOVR', '較開季')"),
        ("[[0, '全部'], [500, '≥500'], [1000, '≥1000'], [1500, '≥1500']]",
         "[[0, '全部'], [10, '≥10'], [20, '≥20'], [30, '≥30']]"),
        ('<td class="sub${sc(\'gp\')}">${p.gp}</td>',
         '<td class="sub${sc(\'gp\')}">${p.gp}</td>\n'
         '      <td class="sub${sc(\'dovr\')}" style="color:${' + dcol + '}">'
         '${(v => (v > 0 ? \'+\' : \'\') + v.toFixed(1))(Math.abs(p.dovr) < 0.05 ? 0 : p.dovr)}</td>'),
        ('<td class="sub gl${sc(\'min\')}">${p.min.toLocaleString()}</td>',
         '<td class="sub gl${sc(\'min\')}">${p.min.toFixed(1)}</td>'),
        ('<span>上場 <b>${p.min.toLocaleString()}</b> 分鐘</span><span>出賽 <b>${p.gp}</b> 場</span>',
         '<span>場均 <b>${p.min.toFixed(1)}</b> 分鐘</span><span>已打 N=<b>${p.gp}</b> 場</span>'
         "<span>開季卡 OVR <b>${p.last.toFixed(1)}</b>（<b>${(p.dovr > 0 ? '+' : '') + p.dovr.toFixed(2)}</b>）</span>"),
        ('模擬每 36 分鐘淨值', '新賽季預測每 36 分鐘淨值'),
    ]:
        assert s.count(a) >= 1, a
        s = s.replace(a, b)
    s = apply_common(s)
    if has_pd:
        a, b = "['pressure', 'PRES', '壓命中率']", "['pressure', 'PRES', '壓迫']"
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    s = sn.apply_cell_tips(s)   # PRES／TO 格子帶浮動提示卡
    s = regroup_attrs(s)  # 和 2025-26 頁同分組；要在上面 PRES 改名之後
    s = add_season_nav(s, 'inseason')
    s = add_masthead(s, 'inseason')   # 眉頭（2026-11-02，參考 arammeta）
    out = live / 'roster-viewer.html'
    out.write_text(s, encoding='utf-8')
    # 注入隊色／頭像／2026-27 場均（換資料來源與年份文字）
    er.SRC = SRC26
    er.JS = er.JS.replace('2025-26 例行賽紀錄', '2026-27 賽季紀錄')
    # 影響力四格改用 2026-27 自製 EPM 式（當季 box 先驗＋生涯 RAPM 先驗＋當季 RAPM；只顯示，不進 OVR）
    epm_rows, _ = epm_live.run()
    # 第四格：原在場減不在場雜訊太大（Wembanyama +53.5，使用者 2026-10-30 換成 box 估計），2026-11-03 再換成場均評分（見下方 JS 替換）
    epm_imp = {r['playerId']: {k: v for k, v in (('o', r['O']), ('d', r['D'])) if v is not None}
               for r in epm_rows}
    # 場均評分格沿用近 5 場表的五色（原本只掛在 .g5 底下）
    er.CSS += '.chip .gv{display:flex;align-items:baseline;gap:4px}.strong .chip .gv i{margin:0}.strong .chip:not(.dim) .gv{margin-top:2px}.chip small.rk5{font:600 .72rem var(--f-disp);color:var(--muted)}.chip i.c5a{color:var(--g-a)}.chip i.c5b{color:var(--g-b)}.chip i.c5c{color:#a3abb5}.chip i.c5d{color:#f09a8c}.chip i.c5f{color:var(--g-f)}\n'
    er.IMPACT_LOADER = lambda: {pid: {k: round(v, 2) for k, v in d.items()} for pid, d in epm_imp.items()}
    add_ovr_chart(live)
    for a, b in [
        ('title="無 2025-26 RAPM"', 'title="本季未上場"'),
        ('2025-26 RAPM 進攻：', '2026-27 自製 EPM 式（本季數據表＋生涯 RAPM 打底＋本季 RAPM）進攻：'),
        ('2025-26 RAPM 防守：', '2026-27 自製 EPM 式（本季數據表＋生涯 RAPM 打底＋本季 RAPM）防守：'),
        ('2025-26 RAPM 淨值＝進攻＋防守', '2026-27 自製 EPM 式淨值＝進攻＋防守（本季數據表＋生涯 RAPM 打底＋本季 RAPM）'),
        # 第四格再改成本季場均評分（Z1 0–10，整季每場平均；使用者 2026-11-03）：box 估計開季被收縮約八成，
        # Ty Jerome 場均 25.8 分只排 #53、藍領中鋒反而前 15；評分抓得到開季爆發。
        # 顏色改看全聯盟名次五等分（高綠、中灰、低紅；使用者 2026-11-03），名次人群＝場均 ≥15 分鐘（同能力值，sn.POOL_MPG），旁邊標 #名次
        ("    chip('在場增益', m.onoff, '2025-26 他在場減不在場的球隊每 100 回合淨效率（扣掉球隊本身強弱；會受替補好壞影響）' + (m.on == null ? '' : '；在場時球隊淨效率 ' + sg(m.on)))}",
         "    (() => { const v = r.sd ? r.sd.gc : null;\n"
         "      if (v == null) return `<span class=\"chip\" title=\"本季尚未出賽\">場均評分<i class=\"flat\">—</i></span>`;\n"
         "      if (!window.GC_POOL) window.GC_POOL = Object.values(REAL).filter(x => x.gp > 0 && x.mpg >= %d && x.sd && x.sd.gc != null).map(x => x.sd.gc);\n"
         "      const pool = window.GC_POOL, rk = pool.filter(x => x > v).length + 1, inPool = r.mpg >= %d, f = (rk - 1) / pool.length;\n"
         "      const cl = f < 0.2 ? 'c5a' : f < 0.4 ? 'c5b' : f < 0.6 ? 'c5c' : f < 0.8 ? 'c5d' : 'c5f';\n"
         "      const tip = GC_DEF + '。本季每場評分平均；顏色＝全聯盟名次五等分（綠高、灰中、紅低），名次人群＝場均 ≥%d 分鐘共 ' + pool.length + ' 人' + (inPool ? '' : '；他場均不到 %d 分鐘，不列名次') + (r.gc && r.gc.b != null ? '。上季 ' + gcS(r.gc.b) : '');\n"
         "      return `<span class=\"chip\" title=\"${tip}\">場均評分<span class=\"gv\"><i class=\"${cl}\">${gcS(v)}</i>${inPool ? `<small class=\"rk5\">#${rk}</small>` : ''}</span></span>`; })()}" % (sn.POOL_MPG, sn.POOL_MPG, sn.POOL_MPG, sn.POOL_MPG)),
        ("'在場增益'", "'場均評分'"),
    ]:
        assert er.JS.count(a) >= 1, a
        er.JS = er.JS.replace(a, b)
    real = er.aggregate()
    # 在名單上還沒出賽的人（N=0）：沒有逐場紀錄，補 id 讓卡片有頭像，gp 0 讓 realBox 顯示「尚未出賽」
    for r in rows:
        if int(r['N']) == 0:
            real.setdefault(r['name'], {'id': int(r['playerId']), 'gp': 0, 'teams': [r['team']]})
    er.inject(out, real)
    print('wrote', out, len(rows), 'players')


if __name__ == '__main__':
    main()
