"""card 0.2.15 底卡（不含 MIX 加分）：把 card_route_0212c.py（CRTPNR=1）的輸出整理成 reports/card-0.2.15-base/。
改自 reports/card-0.2.13-fit/make_card_0213.py：係數／RAPM／三值／引力檔改從 card-0.2.15-w246 取；pnr 不再是獨立欄，
改寫 crt-attr.csv（持球進攻＝creation 欄的兩個成分：自主創造 crt、擋拆持球 pnr，各自值與百分位）。
用法（repo root）：
  WIN_LEN=246 PNR_CARD=1 MIX_BONUS=0 DEF_AXIS=calendar RETURNING_VETS=0 RV_USAGE=0 CRTPNR=1 CRTPNR_BOOT=1 \
    python -I -X utf8 reports/card-0.2.12b-touch/card_route_0212c.py reports/card-0.2.15-fit/route-crt
  python -I -X utf8 reports/card-0.2.15-fit/make_card_0215.py reports/card-0.2.15-fit/route-crt reports/card-0.2.15-base
（CRTPNR=0 同指令＝card 0.2.13a 逐位元重現，route-base0 已驗 582 人 ovr 全同）
"""
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import crtpnr_live as CPL  # noqa: E402

SRC = ROOT / 'reports/card-0.2.12b'
FIT = ROOT / 'reports/card-0.2.15-w246'
PREV = ROOT / 'reports/card-0.2.13a'
src_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
hdr = list(csv.DictReader(open(SRC / 'ranking.csv', encoding='utf-8')).fieldnames)
rt = list(csv.DictReader(open(src_dir / 'ranking.csv', encoding='utf-8')))
ALIAS = {'mpg': 'MPGhat', 'ovr36': 'ovrPer36', 'gRepl': 'g', 'MIN': 'MINprior'}   # 線上管線後來把 MIN 改名 MINprior（值同）


def fmt(c, v):
    if c == 'gRepl':
        return repr(round(float(v), 4))
    if c == 'heightInches':
        return str(int(float(v)))
    if c == 'simulatedPer36':
        return '0.0'
    return v


order = {r['name']: i for i, r in enumerate(csv.DictReader(open(PREV / 'ranking.csv', encoding='utf-8')))}
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
F = CPL.frozen()
bad = [r['name'] for r in rt if abs(float(r['creation']) - round(F['card'][int(r['playerId'])]['crtpnr'], 1)) > 0.051]
assert not bad, bad[:5]
with open(out / 'crt-attr.csv', 'w', encoding='utf-8', newline='') as fh:
    wr = csv.writer(fh, lineterminator='\n')
    wr.writerow(['playerId', 'name', 'crtpnr', 'crt', 'crtPct', 'pnr', 'pnrPct', 'pnrRaw', 'z'])
    for p, v in F['card'].items():
        wr.writerow([p, v['name'], repr(v['crtpnr']), repr(v['creation']), round(CPL.pct('crtPool', v['creation']), 1),
                     repr(v['pnr']), round(CPL.pct('pnrPool', v['pnr']), 1), repr(v['pnrRaw']), repr(v['z'])])
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
for k in ('change_0213a', 'pnr', 'pnr_attr_csv_sha256'):
    summ.pop(k, None)
summ.update({'version': 'card 0.2.15-base', 'base': 'card 0.2.13a 的管線（W246）；係數 reports/card-0.2.15-w246/', 'players': len(rows),
             'change': 'E-303 MRG5（使用者 2026-11-10「合併做進卡片」）：creation 欄＝持球進攻＝(z_crt＋z_pnr)/√(2+2r) → 0–99（live/crtpnr_live.py，凍結 crtpnr-pool-card0215.json）；pnr 不再是獨立特徵；全部係數在 W246 重擬合（card-0.2.15-w246）。不含 MIX 加分（由 reports/card-0.2.15/build_card_0215.py 疊）。',
             'win_len': 246, 'ranking_csv_sha256': sha(out / 'ranking.csv'), 'three_value_csv_sha256': sha(out / 'three-value.csv'),
             'crt_attr_csv_sha256': sha(out / 'crt-attr.csv'), 'crtpnr': fs.get('crtpnr'),
             'build_command': 'WIN_LEN=246 PNR_CARD=1 MIX_BONUS=0 DEF_AXIS=calendar RETURNING_VETS=0 RV_USAGE=0 CRTPNR=1 CRTPNR_BOOT=1 card_route_0212c.py <work> → reports/card-0.2.15-fit/make_card_0215.py <work> reports/card-0.2.15-base（CRTPNR=0 逐位元重現 card 0.2.13a）'})
for k in ('anchors', 'anchor_source', 'ovr_map', 'pool_90_99', 'pool_ge99'):
    if k in fs:
        summ[k] = fs[k]
summ['ovr_changed'] = None
(out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(summ['ranking_csv_sha256'])
