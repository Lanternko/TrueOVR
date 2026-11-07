"""E-204：把 card_route.py 的輸出（線上管線格式）整理成卡片資料夾格式（欄位與 reports/card-0.2.12-tov/ranking.csv 相同）。
用法（repo root）：python -I -X utf8 reports/E204-window-246/make_card.py <card_route 輸出夾> <輸出夾> [版號]
WIN_LEN=328 的輸出必須與 card-0.2.12-tov/ranking.csv 數值相同（版號參數填 check）。
其餘檔案（three-value、gravity-attr／raw、rapm-T6）窗口不影響，原樣複製；def-L-primary.csv 取 card_route 的 def-L-live.csv 補姓名；錨點凍結（summary.json anchors 同 card 0.2.12）。"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'reports/card-0.2.12b'          # 欄位順序、同分排序、summary 範本（0.2.12b，W246）
W328 = ROOT / 'reports/card-0.2.12c-w246'     # 係數／RAPM／三值／引力檔所在（觸球版 W246 底，2026-11-02 重擬合）
src_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
ver = sys.argv[3] if len(sys.argv) > 3 else 'check'
hdr = list(csv.DictReader(open(SRC / 'ranking.csv', encoding='utf-8')).fieldnames)
rt = list(csv.DictReader(open(src_dir / 'ranking.csv', encoding='utf-8')))
ALIAS = {'mpg': 'MPGhat', 'ovr36': 'ovrPer36', 'gRepl': 'g'}


def fmt(c, v):
    if c == 'gRepl':
        return repr(round(float(v), 4))
    if c == 'heightInches':
        return str(int(float(v)))
    if c == 'simulatedPer36':
        return '0.0'
    return v


order = {r['name']: i for i, r in enumerate(csv.DictReader(open(SRC / 'ranking.csv', encoding='utf-8')))}
rows = sorted(rt, key=lambda r: (-float(r['ovr']), order.get(r['name'], 9999)))
out.mkdir(parents=True, exist_ok=True)
with open(out / 'ranking.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(hdr)
    for i, r in enumerate(rows, 1):
        w.writerow([i if c == 'rank' else fmt(c, r[ALIAS.get(c, c)]) for c in hdr])
if ver == 'check':     # 數值核對（字串格式不同：mpg 33.0／33.00、gRepl 線上管線只留 3 位）
    A = list(csv.DictReader(open(out / 'ranking.csv', encoding='utf-8')))
    B = list(csv.DictReader(open(SRC / 'ranking.csv', encoding='utf-8')))
    bad = {}
    for x, y in zip(A, B):
        for c in hdr:
            try:
                same = abs(float(x[c]) - float(y[c])) <= (6e-4 if c == 'gRepl' else 1e-9)
            except ValueError:
                same = x[c] == y[c]
            if not same:
                bad[c] = bad.get(c, 0) + 1
    print('card-0.2.12-tov 逐欄數值差異（空＝全同）：', bad)
    sys.exit(1 if bad else 0)
for n in ('three-value.csv', 'rapm-T6.csv', 'gravity-attr.csv', 'gravity-raw.csv'):
    shutil.copyfile(W328 / n, out / n)
# 防守加成 D 的重擬合（window 246）→ 名單頁 DIQ 負分顯示用（build_card_viewer.defense_centered 要 name 欄）；card 0.2.12 用的是 card-0.2.5+E104 的 def-L-primary.csv（WIN_LEN=328 的 card_route def-L-live.csv 與它逐位相同）
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay/def-L-primary.csv'
nm = {int(r['playerId']): r['name'] for r in csv.DictReader(open(E104, encoding='utf-8'))}
nm.update({int(r['playerId']): r['name'] for r in rt})
with open(out / 'def-L-primary.csv', 'w', encoding='utf-8', newline='') as fh:
    wr = csv.writer(fh)
    wr.writerow(['playerId', 'name', 'D', 'poss', 'possUnweighted'])
    for r in csv.DictReader(open(src_dir / 'def-L-live.csv', encoding='utf-8')):
        wr.writerow([r['playerId'], nm[int(r['playerId'])], r['D'], r['poss'], r['possUnweighted']])
summ = json.loads((SRC / 'summary.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
summ.update({'version': f'card {ver}', 'base': 'reports/card-0.2.12b（card 0.2.12b，W246）', 'players': len(rows),
             'change': 'E-207／R-144：tovSkill 的失誤率 r 分母由持球分鐘改觸球次數（k、kh 乘 ρ＝15.593；v 仍用持球分鐘）；池 mu/sd／先驗／0-99 映射／全部係數與 OVR 錨點皆在 W246 窗口重擬合（card-0.2.12c-w246，2026-11-02；其餘 7 項屬性池仍照 win_len 慣例以 328 建）。',
             'win_len': 246, 'ranking_csv_sha256': sha(out / 'ranking.csv'), 'three_value_csv_sha256': sha(out / 'three-value.csv'),
             'build_command': 'WIN_LEN=246 reports/card-0.2.12b-touch/card_route_0212c.py <work> → make_card_0212c.py <work> reports/card-0.2.12c "0.2.12c"（TOV_TOUCH=0 逐位元重現 card 0.2.12b；WIN_LEN=328 的重現見 card-0.2.12c-fit246 V328 臂＝E-206 KC final）'})
w3 = json.loads((W328 / 'summary.json').read_text(encoding='utf-8'))
for k in ('anchors', 'anchor_source', 'ovr_map', 'pool_90_99', 'pool_ge99'):   # 錨點＝觸球版 328 底重取的（與賽中端讀的 summary 一致）
    if k in w3:
        summ[k] = w3[k]
for k in ('pre_ranking_sha256', 'equals_E202_KT_final', 'c0', 'sources_sha256', 'tov'):
    summ.pop(k, None)
summ['ovr_changed'] = None
(out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
summ['win_len'] = 246
print(summ['ranking_csv_sha256'])
