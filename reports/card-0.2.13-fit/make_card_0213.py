"""card 0.2.13（E-258 pnr）：把 card_route_0212c.py 的輸出（線上管線格式，PNR=1）整理成正式卡片資料夾 reports/card-0.2.13/。
改自 reports/card-0.2.12b-touch/make_card_0212c.py：係數／RAPM／三值／引力檔改從 card-0.2.13-w246 取；另寫 pnr-attr.csv（檢視器 PNR 欄與 tooltip）。
用法（repo root）：
  WIN_LEN=246 python -I -X utf8 reports/card-0.2.12b-touch/card_route_0212c.py <work>
  python -I -X utf8 reports/card-0.2.13-fit/make_card_0213.py <work> reports/card-0.2.13 0.2.13
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'reports/card-0.2.12b'          # 欄位順序、同分排序、summary 範本
FIT = ROOT / 'reports/card-0.2.13-w246'      # 係數／RAPM／三值／引力檔（W246 底，加 pnr 重擬合）
PREV = ROOT / 'reports/card-0.2.12c'         # 上一版正式卡（R-109 對照）
FROZEN = ROOT / 'reports/ovr-inseason-2026-27/live/pnr-pool-card0213.json'
src_dir, out, ver = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
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
assert len(rows) == 582, len(rows)
out.mkdir(parents=True, exist_ok=True)
with open(out / 'ranking.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, lineterminator='\n')
    w.writerow(hdr)
    for i, r in enumerate(rows, 1):
        w.writerow([i if c == 'rank' else fmt(c, r[ALIAS.get(c, c)]) for c in hdr])
for n in ('three-value.csv', 'rapm-T6.csv', 'gravity-attr.csv', 'gravity-raw.csv'):
    shutil.copyfile(FIT / n, out / n)
# pnr：卡片值＝凍結池（pnr_live.freeze，c=0 四季窗口、不含本季）；card_route 的 pnr 欄必須與它逐值相同
F = json.loads(FROZEN.read_text(encoding='utf-8'))
pid_of = {r['name']: int(r['playerId']) for r in rt}
bad = [r['name'] for r in rt if abs(float(r['pnr']) - round(F['card'][str(r['playerId'])]['pnr'], 1)) > 0.051] if 'pnr' in rt[0] else ['（card_route 沒有 pnr 欄）']
assert not bad, bad[:5]
with open(out / 'pnr-attr.csv', 'w', encoding='utf-8', newline='') as fh:
    wr = csv.writer(fh, lineterminator='\n')
    wr.writerow(['playerId', 'name', 'pnr', 'poss', 'vol', 'rate'])
    for p, v in F['card'].items():
        wr.writerow([p, v['name'], repr(v['pnr']), round(v['poss'], 1), round(v['vol'], 4), round(v['rate'], 4)])
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay/def-L-primary.csv'
nm = {int(r['playerId']): r['name'] for r in csv.DictReader(open(E104, encoding='utf-8'))}
nm.update({int(r['playerId']): r['name'] for r in rt})
with open(out / 'def-L-primary.csv', 'w', encoding='utf-8', newline='') as fh:
    wr = csv.writer(fh)
    wr.writerow(['playerId', 'name', 'D', 'poss', 'possUnweighted'])
    for r in csv.DictReader(open(src_dir / 'def-L-live.csv', encoding='utf-8')):
        wr.writerow([r['playerId'], nm[int(r['playerId'])], r['D'], r['poss'], r['possUnweighted']])
summ = json.loads((PREV / 'summary.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fs = json.loads((FIT / 'summary.json').read_text(encoding='utf-8'))
summ.update({'version': f'card {ver}', 'base': 'reports/card-0.2.12c（card 0.2.12c，W246）', 'players': len(rows),
             'change': 'E-258：加能力值 pnr（擋拆持球）＝Synergy PRBallHandler 每 36 分鐘回合（量）與每回合得分（率，經驗貝氏收縮，只在 ≥50 回合的人裡排）各半，四季滑動窗口；0–99 映射凍結於 live/pnr-pool-card0213.json；全部係數與 OVR 錨點在 W246 窗口重擬合（card-0.2.13-w246）。',
             'win_len': 246, 'ranking_csv_sha256': sha(out / 'ranking.csv'), 'three_value_csv_sha256': sha(out / 'three-value.csv'),
             'pnr_attr_csv_sha256': sha(out / 'pnr-attr.csv'), 'pnr': fs.get('pnr'),
             'build_command': 'WIN_LEN=246 reports/card-0.2.12b-touch/card_route_0212c.py <work> → reports/card-0.2.13-fit/make_card_0213.py <work> reports/card-0.2.13 0.2.13（PNR=0 逐位元重現 card 0.2.12c）'})
for k in ('anchors', 'anchor_source', 'ovr_map', 'pool_90_99', 'pool_ge99'):
    if k in fs:
        summ[k] = fs[k]
summ['ovr_changed'] = None
(out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(summ['ranking_csv_sha256'])
