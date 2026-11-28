"""E-101 改動一（預註冊 §1）：mid、short 的 2025-26 收縮後命中率 p，用修正後 PBP 分區＋聯盟先驗（fit['prior']='league'），k／kh／lam 不改。
複製自 ../card-0.2.5+E097-topscale/work/a0_league.py；改動：V61 引擎經 e101_zones（monkeypatch engine.read_gz_csv）改讀本資料夾 history/。
跑三次：
  1. V61 分區＋位置先驗 → 必須逐人重現 E-090 work/a0-raw.json（對照）
  2. V61 分區＋聯盟先驗 → 必須逐人重現 E-097 a0-league.json league（對照）
  3. E-101 分區＋聯盟先驗 → 本實驗的 p
每次另存 attrs-validation.json 的 zoneShift。
輸出：a0-e101.json。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/a0_e101.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
E090 = ROOT / 'reports/card-0.2.4+E090-onball-tail'
E097 = ROOT / 'reports/card-0.2.5+E097-topscale'
TMP = HERE / 'tmp'
TMP.mkdir(exist_ok=True)
sys.path.insert(0, str(V61))
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import build_attrs as B  # noqa: E402
import engine as E  # noqa: E402
import e101_zones as Z  # noqa: E402

B.D = TMP
src = (V61 / 'build_attrs.py').read_text(encoding='utf-8').splitlines()
LINE_INV_NEW = next(i + 1 for i, s in enumerate(src) if 'vals = {p: inverse(float(rn[i]), curve)' in s)
_inv = B.inverse
cap = {}


def inv_hook(p, curve):
    f = sys._getframe(1)
    if f.f_code.co_name == 'main' and f.f_lineno == LINE_INV_NEW:
        cap.setdefault(f.f_locals['a'], {})[str(f.f_locals['p'])] = p
    return _inv(p, curve)


bt = json.loads((V61 / 'backtest.json').read_text(encoding='utf-8'))
out = {'runs': {}, 'zoneShift': {}}
for name, zones, prior in (('v61_position', False, 'position'), ('v61_league', False, 'league'), ('e101_league', True, 'league')):
    b2 = json.loads(json.dumps(bt))
    for a in ('mid', 'short'):
        assert b2['production'][a]['selected'] == 'c' and b2['production'][a]['fit']['prior'] == 'position'
        b2['production'][a]['fit']['prior'] = prior
    (TMP / 'backtest.json').write_text(json.dumps(b2, ensure_ascii=False), encoding='utf-8')
    Z.use(zones, E)
    n0 = len(Z.reads())
    cap.clear()
    B.inverse = inv_hook
    B.main()
    B.inverse = _inv
    Z.use(False, E)
    out['runs'][name] = {a: dict(cap[a]) for a in ('mid', 'short')}
    out['zoneShift'][name] = json.loads((TMP / 'attrs-validation.json').read_text(encoding='utf-8'))['zoneShift']
    out.setdefault('e101ZoneReads', {})[name] = Z.reads()[n0:]
    print(name, 'zone files redirected:', len(Z.reads()) - n0, flush=True)

raw = json.load(open(E090 / 'work/a0-raw.json', encoding='utf-8'))
lg = json.load(open(E097 / 'a0-league.json', encoding='utf-8'))
ctl = {}
for a in ('mid', 'short'):
    d1 = max(abs(out['runs']['v61_position'][a][k] - raw[a]['p'][k]) for k in raw[a]['p'])
    d2 = max(abs(out['runs']['v61_league'][a][k] - lg['league'][a][k]) for k in lg['league'][a])
    assert set(out['runs']['v61_position'][a]) == set(raw[a]['p']) and d1 < 1e-12, (a, d1)
    assert set(out['runs']['v61_league'][a]) == set(lg['league'][a]) and d2 < 1e-12, (a, d2)
    ctl[a] = {'vsE090a0raw': d1, 'vsE097league': d2}
assert len(out['e101ZoneReads']['e101_league']) > 0 and len(out['e101ZoneReads']['v61_league']) == 0
out['controlMaxAbsDiff'] = ctl
out['p'] = out['runs']['e101_league']
json.dump(out, open(OUT / 'a0-e101.json', 'w', encoding='utf-8'), indent=1)
for a in ('mid', 'short'):
    d = [out['p'][a][k] - lg['league'][a][k] for k in out['p'][a]]
    print(a, 'control', ctl[a], 'e101-E097league: min %.4f max %.4f' % (min(d), max(d)), 'zoneShift', out['zoneShift']['e101_league'][a])
