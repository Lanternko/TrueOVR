"""由 shots/res.json（shoot.mjs 量測）與暫存頁的 DATA 產生 check.md；斷言失敗就 exit 1。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
res = json.loads((HERE / 'shots/res.json').read_text(encoding='utf-8'))
html = (HERE / 'tmp/w26/roster-viewer.html').read_text(encoding='utf-8')
m = re.search(r'const DATA=(\{.*?\});\nconst COLS', html, re.S)
data = json.loads(m.group(1))
cols = data['cols']
P = [dict(zip(cols, r)) if isinstance(r, list) else r for r in data['rows']]
MERGED = ['offR', 'defR', 'play', 'outside', 'inside', 'handle', 'offball', 'perim']
KEYS = MERGED + ['rebound', 'help']
d = res['data']
fails = []
CK = []


def ck(name, ok, detail=''):
    CK.append(('PASS ' if ok else 'FAIL ') + name + (f'（{detail}）' if detail else ''))
    print(CK[-1])
    if not ok:
        fails.append(name)


ck('console 無錯誤', not res['logs'], str(res['logs'][:3]))
ck('Curry outside 卡有「三分命中率」', '三分命中率' in d['curryOutsideRows'])
ck('Curry outside 卡有「三分出手量」', '三分出手量' in d['curryOutsideRows'])
ck('先發控衛 %s handle 卡有含「擋拆」的列' % d['pg']['name'], any('擋拆' in x for x in d['pg']['rows']), str(d['pg']['rows']))
ck('合併卡每個都有 ATIP', all(ok for _, ok in d['atip']))
over = [(p['name'], k, len(p['tips'][k]['rows'])) for p in P for k in MERGED if p.get('tips') and k in p['tips'] and len(p['tips'][k]['rows']) > 8]
ck('合併卡最多 8 列', not over, str(over[:3]))
dup = [(p['name'], k) for p in P for k in MERGED if p.get('tips') and k in p['tips'] and len({r[0] for r in p['tips'][k]['rows']}) != len(p['tips'][k]['rows'])]
ck('合併卡沒有同名列', not dup, str(dup[:3]))
nofoot = [(p['name'], k) for p in P for k in MERGED if p.get('tips') and k in p['tips'] and len([f for f in ([p['tips'][k].get('foot')] if isinstance(p['tips'][k].get('foot'), str) else (p['tips'][k].get('foot') or [])) if f]) > 1]
ck('合併卡註腳最多一行', not nofoot, str(nofoot[:3]))
mf = res['mob_first']
right = mf['box'][1]
big_ok = all(mf[k][1] <= right + 0.5 for k in ('ovr', 'offR', 'defR', 'play', 'rebound'))
out_vis = max(0, right - mf['outside'][0]) / (mf['outside'][1] - mf['outside'][0])
widths = [round(mf[k][1] - mf[k][0], 1) for k in ('offR', 'defR', 'play', 'rebound')]
ck('手機精簡第一屏：OVR＋四大類完整在可視區內', big_ok, f"可視區右緣 {right}，rebound 右緣 {mf['rebound'][1]}")
ck('手機精簡第一屏：OUT 露出 ≤ 一半', out_vis <= 0.5, f'OUT 露出 {out_vis:.0%}')
ck('手機精簡第一屏：四大類等寬', len(set(widths)) == 1, str(widths))
ck('桌機精簡無橫向捲軸、總寬同詳細', json.loads(res['desk_lite_scrollW'])['sw'] == json.loads(res['desk_lite_scrollW'])['cw'] and abs(json.loads(res['desk_lite_scrollW'])['tbl'] - json.loads(res['desk_full_scrollW'])['tbl']) < 1)
ck('預設：桌機詳細、手機精簡', res['desk_default'] == 'full' and res['mob_default'] == 'lite')
ck('切檢視排序退回 OVR 由高到低', res['desk_sort_after_switch'] == '["lite","ovr",false]' and res['mob_sort_after_switch'] == '["lite","ovr",false]')
ck('年份按鈕字樣', json.loads(res['desk_fseason'])[0][0] == '2026-27' and json.loads(res['desk_fseason'])[1][0] == '2025-26')
ck('齒輪面板賽季列兩連結', len(json.loads(res['desk_gear_season'])) == 2)
ck('詳細欄序 DIQ 接在 RIM 後、無合併值欄', res['desk_full_cols'][22:24] == ['help', 'dbon'] and not set(res['desk_full_cols']) & {'play', 'outside', 'inside', 'handle', 'offball', 'perim'})
ck('合併欄表頭排序（outside 由高到低第一名 Curry）', json.loads(res['desk_sort_outside_top3'])[0] == 'Stephen Curry')
if fails:
    print('FAILED', fails)

L = ['# 名單頁精簡檢視：驗收記錄', '', '建頁：本機暫存目錄 `reports/roster-lite-view/tmp/w26/`（未發布）。量測腳本 `shoot.mjs`、本檔產生器 `make_check.py`。pool＝場均 ≥15 分鐘，共 %d 人。' % d['poolN'], '',
     '## 1. 代表球員的 10 個合併值（顯示值，四捨五入到一位）', '',
     '| 球員 | 位置 | MPG | OVR | OFF | DEF | PLAY | OUT | IN | BALL | OFFB | PER | REB | RIM |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
f = lambda v: '—' if v is None else f'{v:.1f}'
for i, r in enumerate(d['rows']):
    if r.get('missing'):
        L.append(f"| {r['name']}（找不到） |" + ' |' * 12)
        continue
    tag = '' if i < 15 else '（代表）'
    L.append(f"| {r['name']}{tag} | {r['pos']} | {r['min']:.1f} | {r['ovr']:.1f} | " + ' | '.join(f(r[k]) for k in ['offR', 'defR', 'play', 'outside', 'inside', 'handle', 'offball', 'perim', 'rebound', 'help']) + ' |')
L += ['', f"射手型替補＝場均 15–24 分鐘裡 OUT 最高者：{d['bench']}。", '', '## 2. 各合併欄的 pool 分佈（pool 內有值的人）', '',
      '| 欄 | 人數 | 平均 | 標準差 | 最小 | 最大 | ≥99 人數 |', '|---|---|---|---|---|---|---|']
for k in KEYS:
    s = d['stats'][k]
    L.append(f"| {k} | {s['n']} | {s['mean']:.1f} | {s['sd']:.1f} | {s['min']:.1f} | {s['max']:.1f} | {s['ge99']} |")
L += ['', '## 3. 腳本斷言與量測', '']
L += ['- Curry `outside` 卡的列：' + '、'.join(d['curryOutsideRows']),
      f"- 先發控衛 {d['pg']['name']}（{d['pg']['pos']}，{d['pg']['min']:.1f} 分）`handle` 卡的列：" + '、'.join(x.strip() for x in d['pg']['rows']),
      f"- 手機精簡第一屏（390×844）：可視區右緣 {right}px；OVR 右緣 {mf['ovr'][1]}、OFF {mf['offR']}、DEF {mf['defR']}、PLAY {mf['play']}、REB {mf['rebound']}（四大類各寬 {widths[0]}px）；OUT 左緣 {mf['outside'][0]}，露出 {out_vis:.0%}",
      '', '逐項斷言：', ''] + ['- ' + c for c in CK] + ['']
(HERE / 'check.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
sys.exit(1 if fails else 0)
