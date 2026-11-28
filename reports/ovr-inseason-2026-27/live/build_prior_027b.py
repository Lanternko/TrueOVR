"""由 card 0.2.7b 的來源產生賽中用的 2025-26 先驗卡（E-111，CARD_MODE=027；預註冊 e111-card027/preregistration.md §1.1）。

照 build_prior_026.py，差別只在 x0 用「未四捨五入」的值：
  直接呼叫 card 0.2.7b 的產生器 reports/card-0.2.6+E107-defense-UL/calibrate-wing.py 的 load()（唯讀匯入、不跑 main），
  參數照 run_cards.py 的 UL6 primary（--attrSource E-070、--defSource E-060、--pressure force、--tailSource E-101 attributes-e101.csv）。
  因此 13 個尾巴屬性＝attributes-e101.csv（未四捨五入）；help＝E-060 new_help；stamina、heightInches＝LEAGUE 名單卡原值
  （= card 0.2.5／0.2.7 的來源，E-101 沒有這三欄）。
檢查（失敗即停）：
  - reports/card-0.2.7/ranking.csv sha256 = summary.json 的 ranking_csv_sha256；
  - card 0.2.7b 與 0.2.6 的屬性欄逐格相同（summary.json columnsDifferentFromCard026 只有 rank、ovr、predictedPer36、defenseBonus、gRepl、ovr36，這裡再實際比對）；
  - 未四捨五入 x0 四捨五入到 0.1 後 = card 0.2.7b ranking.csv 的屬性欄（16 欄、582 人，|差| ≤ 0.05）。
foulDraw 凍結常數同 026（freeze_foul_draw 原樣呼叫，量尺檢查對 card 0.2.7b 的 foulDraw；0.2.7 的 foulDraw 欄＝0.2.6）。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_prior_027.py
"""
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import build_prior_026 as B26  # noqa: E402

OLD = B26.OLD
CARD = ROOT / 'reports/card-0.2.7b/ranking.csv'
CARD_SUMMARY = ROOT / 'reports/card-0.2.7b/summary.json'
CARD026 = ROOT / 'reports/card-0.2.7/ranking.csv'   # 027b 的比對基準改為 card 0.2.7（欄位差異另列）
RB = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work'
E123 = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres'
PF = HERE.parent / 'e128-card027b/passfreeze.json'
TAIL13 = RB / 'tail-e123a.csv'
DEFNEW = E123 / 'work/def-new.csv'
UL = ROOT / 'reports/card-0.2.6+E107-defense-UL'
CW = UL / 'calibrate-wing.py'
SRC = {
    'attrSource': ROOT / 'reports/card-0.2.0+E070-foul-volume/attributes-w075/attributes-new.csv',
    'defSource': ROOT / 'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv',
    'pressureSource': ROOT / 'reports/card-0.2.0+E071-pressure/force-pressure-source.csv',
    'tailSource': ROOT / 'reports/card-0.2.5+E101-crossera/attributes-e101.csv',
}
OUT = HERE / 'prior-2025-26-card027b.json'
ATTRS = B26.ATTRS
DISPLAY = B26.DISPLAY
ATTR_COLS026 = ['pos', 'MIN'] + ATTRS + ['mpg', 'foulDisc', 'presDisplay', 'simulatedPer36', 'align', 'pred0', 'pr']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_cw():
    spec = importlib.util.spec_from_file_location('cw_e107', CW)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.ATTR_SOURCE, m.DEF_SOURCE, m.TAIL_SOURCE = SRC['attrSource'], SRC['defSource'], SRC['tailSource']
    m.PRESSURE_MODE, m.PRESSURE_SOURCE, m.FOULDISC = 'force', SRC['pressureSource'], False
    return m


def unrounded_x0():
    """回傳 {name: {attr: float}}（card 0.2.7b 產生器 load() 的卡片值，未四捨五入）。"""
    m = load_cw()
    rows = m.load(m.TARGET)
    return {r['name']: {a: float(r['card'][a]) for a in ATTRS} for r in rows}, {r['name']: r['MIN'] for r in rows}


def main():
    want = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))['ranking_csv_sha256']
    if sha(CARD) != want:
        raise SystemExit(f'card 0.2.7b ranking.csv sha256 不符：{sha(CARD)} vs summary {want}')
    ranking = list(csv.DictReader(CARD.open(encoding='utf-8')))
    rows = {r['name']: r for r in ranking}
    r26 = {r['name']: r for r in csv.DictReader(CARD026.open(encoding='utf-8'))}
    assert set(rows) == set(r26) and len(rows) == 582
    diffcols = sorted({c for n in rows for c in rows[n] if rows[n][c] != r26[n].get(c)})
    allowed = {'rank', 'ovr', 'predictedPer36', 'defenseBonus', 'gRepl', 'ovr36', 'pass', 'help', 'pressure', 'presDisplay', 'simulatedPer36', 'align', 'pred0', 'pr'}
    if not set(diffcols) <= allowed:
        raise SystemExit(f'card 0.2.7b 與 0.2.6 有能力值欄不同：{diffcols}')
    x0, mins = unrounded_x0()
    tail = {r['name']: r for r in csv.DictReader(TAIL13.open(encoding='utf-8'))}
    dnew = {r['name']: r for r in csv.DictReader(DEFNEW.open(encoding='utf-8'))}
    OVER = ['long', 'mid', 'short', 'ft', 'drive', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'physique', 'onBall', 'creation', 'pressure']
    for n in x0:
        for a in OVER:
            x0[n][a] = float(tail[n][a])
        if n in dnew:
            x0[n]['help'] = float(dnew[n]['new_help'])
    assert set(x0) == set(rows), '產生器名單與 card 0.2.7b 不同'
    worst, nbad = 0.0, 0
    for n, r in rows.items():
        for a in ATTRS:
            d = abs(x0[n][a] - float(r[a]))
            worst = max(worst, d)
            nbad += d > 0.05 + 1e-9
    print(f'未四捨五入 x0 vs card 0.2.7b ranking.csv：最大差 {worst:.5f}，>0.05 的格 {nbad}')
    if nbad:
        raise SystemExit('未四捨五入 x0 四捨五入後不等於 card 0.2.7')
    doc = json.loads(OLD.read_text(encoding='utf-8'))
    assert len(doc['players']) == 582
    dmin = 0.0
    for p in doc['players']:
        r = rows[p['name']]
        assert r['pos'] == p['pos'], p['name']
        for a in ATTRS:
            p[a] = x0[p['name']][a]
        for a in DISPLAY:
            p[a] = float(r[a]) if r[a] != '' else None
        dmin = max(dmin, abs(float(p['observed']['MIN']) - mins[p['name']]))
    print(f'先驗卡 observed.MIN vs 產生器 MIN 最大差 {dmin:.3e}')
    doc['foulDrawFreeze'] = B26.freeze_foul_draw(ranking)
    pf = json.loads(PF.read_text(encoding='utf-8'))
    assert pf['reproducesA0PassP50BitIdentical']
    doc['passFreeze'] = {'wVol': pf['wVol'], 'wRate': pf['wRate'], 'vol': pf['vol'], 'rate': pf['rate'], 'pool': pf['pool'], 'poolSize': pf['poolSize'], 'rateUnit': 'fraction (AST/astCh); live AST% is x100'}
    doc['note'] = ('E-128 CARD_MODE=027b 的 x0：先取 card 0.2.7 產生器 load() 的未四捨五入值，再以 rebase-027a/work/tail-e123a.csv 覆蓋 13 個尾巴屬性（含 E-125 pass、E-123 pressure），help＝E-123 def-new.csv new_help（0.1 位）；'
                   'stamina／heightInches＝LEAGUE 名單卡。'
                   '其餘欄位沿用 prior-2025-26-v5.json。presDisplay、foulDisc 只供顯示（card 0.2.7b ranking.csv）。')
    doc['x0Check'] = {'vsCard027RankingMaxAbs': worst, 'cellsOver005': nbad, 'card027VsCard026DiffCols': diffcols,
                      'observedMinVsGeneratorMinMaxAbs': dmin}
    doc['sources'] = {
        'formalCard': {'file': CARD.relative_to(ROOT).as_posix(), 'sha256': sha(CARD)},
        'formalCardSummary': {'file': CARD_SUMMARY.relative_to(ROOT).as_posix(), 'sha256': sha(CARD_SUMMARY)},
        'card026Ranking': {'file': CARD026.relative_to(ROOT).as_posix(), 'sha256': sha(CARD026)},
        'generator': {'file': CW.relative_to(ROOT).as_posix(), 'sha256': sha(CW)},
        **{k: {'file': v.relative_to(ROOT).as_posix(), 'sha256': sha(v)} for k, v in SRC.items()},
        'tail13': {'file': TAIL13.relative_to(ROOT).as_posix(), 'sha256': sha(TAIL13)},
        'helpNew': {'file': DEFNEW.relative_to(ROOT).as_posix(), 'sha256': sha(DEFNEW)},
        'passFreeze': {'file': PF.relative_to(ROOT).as_posix(), 'sha256': sha(PF)},
        'baseV5Prior': {'file': OLD.relative_to(ROOT).as_posix(), 'sha256': sha(OLD)},
        'foulDrawPool': {'file': B26.E070.relative_to(ROOT).as_posix(), 'sha256': sha(B26.E070)},
        'e101TailSummary': {'file': (B26.E101 / 'tail-summary.json').relative_to(ROOT).as_posix(),
                            'sha256': sha(B26.E101 / 'tail-summary.json')},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    n99 = {a: sum(1 for p in doc['players'] if p[a] > 99) for a in ATTRS}
    print('x0 > 99 人數：', {a: n for a, n in n99.items() if n})
    print('wrote', OUT, len(doc['players']), 'sha256', sha(OUT))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
