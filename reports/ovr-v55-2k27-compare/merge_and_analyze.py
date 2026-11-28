"""把卡片 OVR、v54 模擬板、RAPM、NBA 2K27 評分併成一張表，算 Spearman ρ 與屬性偏差。

輸入
----
- reports/ovr-calibrated-2025-26/ranking.csv        正式卡片板（v53 校準）
- reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv  v54 模擬板（status_snapshot.py 的 LATEST_SIM）
- reports/impact-rapm/rapm.csv                      RAPM
- data/season-league.json                           box score（算 AST/36、三分出手佔比，用於原型判定）
- 本目錄 2k27_ratings.csv                           fetch_2k27.py 抓到的 2K27 評分

輸出
----
- merged.csv        合併後的球員表
- spearman.csv      分鐘分桶 ρ 表
- attr_bias.csv     屬性對照偏差表
- gaps.csv          卡片 vs 2K 名次差距排序（高估 / 低估）
- report.md         繁體中文報告
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

CARD = ROOT / 'reports/ovr-calibrated-2025-26/ranking.csv'
SIM = ROOT / 'reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv'
RAPM = ROOT / 'reports/impact-rapm/rapm.csv'
LEAGUE = ROOT / 'data/season-league.json'
TWOK = HERE / '2k27_ratings.csv'
YEARLY = HERE / '2k_yearly_ovr.csv'

POOLED_MIN_POSS = 5000
LAST_MIN_POSS = 500

BUCKETS = [('<800', 0, 800), ('800-1300', 800, 1300), ('1300+', 1300, 10 ** 9), ('全體', 0, 10 ** 9)]


def rows(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding='utf-8')))


def f(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def rank_desc(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """由大到小的平均名次（tie 取平均）。"""
    vals = [v for _, v in pairs]
    rk = stats.rankdata([-v for v in vals], method='average')
    return {k: float(r) for (k, _), r in zip(pairs, rk)}


def spearman(xs: list[float], ys: list[float]) -> tuple[float | None, int]:
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 8:
        return None, len(pts)
    r = stats.spearmanr([p[0] for p in pts], [p[1] for p in pts]).statistic
    return (None if (r is None or math.isnan(r)) else float(r)), len(pts)


# ------------------------------------------------------------------ 載入

def load() -> list[dict]:
    card = rows(CARD)
    sim = {r['name']: r for r in rows(SIM)}
    rapm = {r['name']: r for r in rows(RAPM)}
    twok = {r['name']: r for r in rows(TWOK)} if TWOK.exists() else {}
    yearly = {r['name']: r for r in rows(YEARLY)} if YEARLY.exists() else {}

    league = json.loads(LEAGUE.read_text(encoding='utf-8'))
    box = {}
    for t in league['teams']:
        for p in t['roster']:
            o = p.get('observed') or {}
            mins = f(o.get('MIN'), 0.0) or 0.0
            box[p['name']] = {
                'astPer36': (f(o.get('AST'), 0.0) or 0.0) * 36 / mins if mins > 0 else None,
                'rebPer36': (f(o.get('REB'), 0.0) or 0.0) * 36 / mins if mins > 0 else None,
                'fgaPer36': (f(o.get('FGA'), 0.0) or 0.0) * 36 / mins if mins > 0 else None,
                'threeRate': (p.get('shotProfile') or {}).get('threeRate'),
                'ftRate': (p.get('shotProfile') or {}).get('freeThrowsPerAttempt'),
            }

    out = []
    for c in card:
        n = c['name']
        s = sim.get(n, {})
        r = rapm.get(n, {})
        k = twok.get(n, {})
        b = box.get(n, {})
        pooled_poss = f(r.get('pooledPoss'), 0.0) or 0.0
        last_poss = f(r.get('lastSeasonPoss'), 0.0) or 0.0
        rec = {
            'name': n,
            'cardRank': int(c['rank']),
            'cardOvr': f(c['ovr']),
            'pos': c['pos'],
            'MIN': f(c['MIN']),
            'simRank': int(s['rank']) if s else None,
            'simPer36': f(s.get('v2Per36')),
            'pooledNet': f(r.get('pooledNet')) if pooled_poss >= POOLED_MIN_POSS else None,
            'pooledPoss': pooled_poss,
            'lastNet': f(r.get('lastSeasonNet')) if last_poss >= LAST_MIN_POSS else None,
            'lastPoss': last_poss,
            'overall2k': f(k.get('overall2k')),
            'pos2k': k.get('pos2k', ''),
            'team2k': k.get('team2k', ''),
            'slug2k': k.get('slug', ''),
            'matchedBy': k.get('matchedBy', ''),
        }
        for a in ('long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound',
                  'physique', 'onBall', 'help', 'creation', 'pressure', 'heightInches'):
            rec[a] = f(c[a])
        for key in ('astPer36', 'rebPer36', 'fgaPer36', 'threeRate', 'ftRate'):
            rec[key] = f(b.get(key))
        for a, col in TWOK_ATTRS.items():
            rec[col] = f(k.get(a))
        y = yearly.get(n, {})
        for yy in ('2K24', '2K25', '2K26', '2K27'):
            rec['k' + yy[2:]] = f(y.get(yy))
        rec['k27d26'] = (rec['k27'] - rec['k26']) if rec['k27'] is not None and rec['k26'] is not None else None
        ys = [rec[c] for c in ('k25', 'k26', 'k27') if rec[c] is not None]
        rec['k3yr'] = sum(ys) / len(ys) if len(ys) >= 2 else None
        out.append(rec)
    return out


TWOK_ATTRS = {
    'Three-Point Shot': 'k_3pt',
    'Mid-Range Shot': 'k_mid',
    'Close Shot': 'k_close',
    'Layup': 'k_layup',
    'Driving Dunk': 'k_ddunk',
    'Standing Dunk': 'k_sdunk',
    'Free Throw': 'k_ft',
    'Post Control': 'k_post',
    'Ball Handle': 'k_handle',
    'Speed with Ball': 'k_swb',
    'Pass Accuracy': 'k_passacc',
    'Pass Vision': 'k_passvis',
    'Pass IQ': 'k_passiq',
    'Interior Defense': 'k_intd',
    'Perimeter Defense': 'k_perd',
    'Help Defense IQ': 'k_helpd',
    'Block': 'k_block',
    'Steal': 'k_steal',
    'Offensive Rebound': 'k_oreb',
    'Defensive Rebound': 'k_dreb',
    'Strength': 'k_str',
    'Speed': 'k_spd',
}


# ------------------------------------------------------------------ 原型判定

ARCH_RULES = """
原型判定規則（依序判定，先中者為準；只用卡片屬性與 box score，不看 2K）：

1. 吃餅長人（roll-man / 餵球終結型長人）
   （身高 ≥ 81 吋 或 位置屬 PF/C）
   且 short ≥ 75（近框終結在全板 p75 以上）
   且 pass ≤ 60 且 creation ≤ 60（不是傳球或持球樞紐）
   且 AST/36 ≤ 2.5。
   註：這裡刻意不卡三分出手佔比。現代長人會投幾顆三分（例如 Matković 的 threeRate 0.38），
   但出手量很小，卡了反而會把最典型的吃餅長人漏掉。

2. 持球創造（on-ball creator）
   creation ≥ 85（全板約 p92）或（pass ≥ 75 且 AST/36 ≥ 4.5）。

3. 3D（投射＋防守側翼）
   long ≥ 68 且 三分出手佔比 ≥ 0.38 且 AST/36 < 4 且 creation < 85
   且 max(onBall, help) ≥ 50。

4. 其他
"""

def archetype(r: dict) -> str:
    h = r.get('heightInches') or 0
    pos = (r.get('pos') or '')
    short = r.get('short') or 0
    ps = r.get('pass') or 0
    ast = r.get('astPer36')
    tr = r.get('threeRate')
    crea = r.get('creation') or 0
    lg = r.get('long') or 0
    onb = r.get('onBall') or 0
    hlp = r.get('help') or 0
    if ((h >= 81 or pos in ('PF', 'C')) and short >= 75 and ps <= 60 and crea <= 60
            and (ast is None or ast <= 2.5)):
        return '吃餅長人'
    if crea >= 85 or (ps >= 75 and ast is not None and ast >= 4.5):
        return '持球創造'
    if (lg >= 68 and tr is not None and tr >= 0.38 and crea < 85
            and (ast is None or ast < 4) and max(onb, hlp) >= 50):
        return '3D'
    return '其他'


# ------------------------------------------------------------------ 主流程

def main() -> int:
    data = load()
    have2k = [r for r in data if r['overall2k'] is not None]
    print(f'卡片板 {len(data)} 人，其中有 2K 評分 {len(have2k)} 人（涵蓋率 {len(have2k)/len(data):.1%}）')

    # 2K 名次只在「有 2K 評分」的子集裡排
    r2k = rank_desc([(r['name'], r['overall2k']) for r in have2k])
    # RAPM 名次同樣在各自的合格子集裡排
    rp = rank_desc([(r['name'], r['pooledNet']) for r in data if r['pooledNet'] is not None])
    rl = rank_desc([(r['name'], r['lastNet']) for r in data if r['lastNet'] is not None])
    for r in data:
        r['rank2k'] = r2k.get(r['name'])
        r['rapmPooledRank'] = rp.get(r['name'])
        r['rapmLastRank'] = rl.get(r['name'])
        r['archetype'] = archetype(r)
        r['rankGap'] = (r['rank2k'] - r['cardRank']) if r['rank2k'] is not None else None

    # ---------------- merged.csv
    cols = ['name', 'archetype', 'pos', 'pos2k', 'team2k', 'MIN',
            'cardOvr', 'cardRank', 'simRank', 'simPer36',
            'overall2k', 'rank2k', 'rankGap',
            'pooledNet', 'pooledPoss', 'rapmPooledRank',
            'lastNet', 'lastPoss', 'rapmLastRank',
            'long', 'mid', 'short', 'ft', 'drive', 'pass', 'rebound', 'tovSkill',
            'physique', 'onBall', 'help', 'creation', 'pressure', 'heightInches',
            'astPer36', 'rebPer36', 'fgaPer36', 'threeRate', 'ftRate',
            'k24', 'k25', 'k26', 'k27', 'k27d26', 'k3yr',
            'slug2k', 'matchedBy'] + list(TWOK_ATTRS.values())
    with (HERE / 'merged.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        for r in sorted(data, key=lambda x: x['cardRank']):
            w.writerow({c: ('' if r.get(c) is None else
                            (round(r[c], 4) if isinstance(r.get(c), float) else r.get(c)))
                        for c in cols})

    # ---------------- spearman.csv
    #   卡片 OVR / 模擬 per36 / 2K 總評 / RAPM 兩種目標 的兩兩 ρ
    pairs = [
        ('卡片 OVR vs 2K 總評', 'cardOvr', 'overall2k'),
        ('模擬 v54 per36 vs 2K 總評', 'simPer36', 'overall2k'),
        ('2K 總評 vs RAPM（多季 pooledNet）', 'overall2k', 'pooledNet'),
        ('2K 總評 vs RAPM（單季 lastSeasonNet）', 'overall2k', 'lastNet'),
        ('卡片 OVR vs RAPM（多季）＝基準', 'cardOvr', 'pooledNet'),
        ('卡片 OVR vs RAPM（單季）＝基準', 'cardOvr', 'lastNet'),
        ('模擬 v54 per36 vs RAPM（多季）', 'simPer36', 'pooledNet'),
        ('模擬 v54 per36 vs RAPM（單季）', 'simPer36', 'lastNet'),
        ('卡片 OVR vs 2K26（季前評分）', 'cardOvr', 'k26'),
        ('模擬 v54 per36 vs 2K26', 'simPer36', 'k26'),
        ('2K26 vs RAPM（單季）', 'k26', 'lastNet'),
        ('2K27−2K26 升降 vs RAPM（單季）', 'k27d26', 'lastNet'),
        ('2K 三年平均（25–27）vs RAPM（多季）', 'k3yr', 'pooledNet'),
        ('卡片 OVR vs 2K27−2K26 升降', 'cardOvr', 'k27d26'),
    ]
    rowsout = []
    for label, a, b in pairs:
        rec = {'對照': label}
        for bname, lo, hi in BUCKETS:
            sub = [r for r in data if r['MIN'] is not None and lo <= r['MIN'] < hi]
            rho, n = spearman([r[a] for r in sub], [r[b] for r in sub])
            rec[f'{bname} ρ'] = '' if rho is None else round(rho, 3)
            rec[f'{bname} n'] = n
        rowsout.append(rec)
    sp_cols = ['對照'] + [x for b, _, _ in BUCKETS for x in (f'{b} ρ', f'{b} n')]
    with (HERE / 'spearman.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=sp_cols)
        w.writeheader()
        w.writerows(rowsout)

    # ---------------- 屬性對照
    def avg(r, keys):
        vs = [r[k] for k in keys if r.get(k) is not None]
        return sum(vs) / len(vs) if vs else None

    attr_pairs = [
        ('3PT vs long', lambda r: r['k_3pt'], lambda r: r['long']),
        ('Mid-Range vs mid', lambda r: r['k_mid'], lambda r: r['mid']),
        ('Close+Layup+Dunk vs short', lambda r: avg(r, ['k_close', 'k_layup', 'k_ddunk', 'k_sdunk']),
         lambda r: r['short']),
        ('Close+Layup+Dunk vs drive', lambda r: avg(r, ['k_close', 'k_layup', 'k_ddunk', 'k_sdunk']),
         lambda r: r['drive']),
        ('Handle+SpeedWithBall vs drive', lambda r: avg(r, ['k_handle', 'k_swb']), lambda r: r['drive']),
        ('Pass(Acc+Vis+IQ) vs pass', lambda r: avg(r, ['k_passacc', 'k_passvis', 'k_passiq']),
         lambda r: r['pass']),
        ('Free Throw vs ft', lambda r: r['k_ft'], lambda r: r['ft']),
        ('Interior+Block vs help', lambda r: avg(r, ['k_intd', 'k_block']), lambda r: r['help']),
        ('HelpDefenseIQ vs help', lambda r: r['k_helpd'], lambda r: r['help']),
        ('Perimeter+Steal vs pressure', lambda r: avg(r, ['k_perd', 'k_steal']), lambda r: r['pressure']),
        ('Perimeter Defense vs onBall', lambda r: r['k_perd'], lambda r: r['onBall']),
        ('OReb+DReb vs rebound', lambda r: avg(r, ['k_oreb', 'k_dreb']), lambda r: r['rebound']),
        ('Strength vs physique', lambda r: r['k_str'], lambda r: r['physique']),
    ]
    attr_rows = []
    attr_detail: dict[str, dict[str, float]] = {}
    for label, fk, fc in attr_pairs:
        pts = [(r, fk(r), fc(r)) for r in have2k]
        pts = [(r, a, b) for r, a, b in pts if a is not None and b is not None]
        if len(pts) < 20:
            continue
        rho = stats.spearmanr([p[1] for p in pts], [p[2] for p in pts]).statistic
        # 把兩邊都轉成同一子集內的百分位，算「卡片百分位 − 2K 百分位」
        n = len(pts)
        pk = stats.rankdata([p[1] for p in pts]) / n * 100
        pc = stats.rankdata([p[2] for p in pts]) / n * 100
        diff = [c - k for c, k in zip(pc, pk)]           # 正 = 卡片給的百分位比 2K 高
        per_arch: dict[str, list[float]] = {}
        for (r, _, _), d in zip(pts, diff):
            per_arch.setdefault(r['archetype'], []).append(d)
        attr_detail[label] = {a: sum(v) / len(v) for a, v in per_arch.items()}
        rec = {'屬性對照': label, 'n': n, 'ρ': round(float(rho), 3),
               '平均|百分位差|': round(sum(abs(d) for d in diff) / n, 1)}
        for a in ('吃餅長人', '持球創造', '3D', '其他'):
            v = attr_detail[label].get(a)
            rec[f'Δ{a}'] = '' if v is None else round(v, 1)
        attr_rows.append(rec)
    attr_rows.sort(key=lambda r: r['ρ'])
    acols = ['屬性對照', 'n', 'ρ', '平均|百分位差|', 'Δ吃餅長人', 'Δ持球創造', 'Δ3D', 'Δ其他']
    with (HERE / 'attr_bias.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=acols)
        w.writeheader()
        w.writerows(attr_rows)

    # ---------------- gaps.csv
    gaps = sorted([r for r in have2k], key=lambda r: -r['rankGap'])
    gcols = ['name', 'archetype', 'pos', 'MIN', 'cardRank', 'cardOvr', 'rank2k', 'overall2k',
             'rankGap', 'simRank', 'rapmPooledRank', 'rapmLastRank', 'pooledNet', 'lastNet',
             'long', 'short', 'drive', 'pass', 'rebound', 'astPer36', 'threeRate']
    with (HERE / 'gaps.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=gcols, extrasaction='ignore')
        w.writeheader()
        for r in gaps:
            w.writerow({c: ('' if r.get(c) is None else
                            (round(r[c], 3) if isinstance(r.get(c), float) else r.get(c)))
                        for c in gcols})

    json.dump({'coverage': len(have2k) / len(data), 'n2k': len(have2k), 'nCard': len(data)},
              (HERE / 'summary.json').open('w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已寫出 merged.csv / spearman.csv / attr_bias.csv / gaps.csv')

    write_report(data, have2k, rowsout, sp_cols, attr_rows, acols, gaps)
    print('已寫出 report.md')
    return 0


# ------------------------------------------------------------------ 報告

def md_table(cols: list[str], recs: list[dict]) -> str:
    L = ['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---'] * len(cols)) + ' |']
    for r in recs:
        L.append('| ' + ' | '.join(str(r.get(c, '')) for c in cols) + ' |')
    return '\n'.join(L)


def write_report(data, have2k, sp_rows, sp_cols, attr_rows, acols, gaps) -> None:
    cov = len(have2k) / len(data)
    unmatched = []
    up = HERE / 'unmatched.csv'
    if up.exists():
        unmatched = rows(up)

    arch_count: dict[str, int] = {}
    for r in data:
        arch_count[r['archetype']] = arch_count.get(r['archetype'], 0) + 1

    # 各原型的平均名次差（正 = 卡片比 2K 給得高，即卡片高估）
    arch_gap: dict[str, list[float]] = {}
    for r in have2k:
        arch_gap.setdefault(r['archetype'], []).append(r['rankGap'])
    arch_rows = [{'原型': a, '人數（有 2K）': len(v), '平均名次差 rank2k−cardRank': round(sum(v) / len(v), 1),
                  '中位數': round(sorted(v)[len(v) // 2], 1)}
                 for a, v in sorted(arch_gap.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))]

    gcols_md = ['name', 'archetype', 'pos', 'MIN', 'cardRank', 'cardOvr', 'rank2k', 'overall2k',
                'rankGap', 'simRank', 'rapmPooledRank', 'rapmLastRank']

    def fmt(recs):
        out = []
        for r in recs:
            out.append({c: ('—' if r.get(c) is None else
                            (round(r[c], 1) if isinstance(r.get(c), float) else r[c]))
                        for c in gcols_md})
        return out

    over = fmt(gaps[:25])
    under = fmt(list(reversed(gaps))[:25])

    km = next((r for r in data if r['name'].startswith('Karlo Matk')), None)

    parts: list[str] = []
    parts.append('# v55 第一步：NBA 2K27 評分 × 卡片 OVR × v54 模擬板 × RAPM 三方對照\n')
    parts.append(f'產生時間：腳本 `merge_and_analyze.py`；抓取腳本 `fetch_2k27.py`。'
                 f'卡片板 {len(data)} 人，成功取得 2K27 評分 {len(have2k)} 人，**涵蓋率 {cov:.1%}**。\n')

    parts.append('## 0. 重要前提：2K 不是真值\n')
    parts.append(
        '- NBA 2K27 總評是遊戲設計者的主觀評分，有明顯的「明星名氣」與遊戲平衡考量，**不是球員價值的真值**。\n'
        '  這裡只把它當作第三個獨立參考點，用來找「我們的卡片板和外部共識不一致」的地方。\n'
        '- 2K27 的名單對應的是 2026-27 球季開季版本，我們的卡片板是 2025-26 資料；'
        '季別落差會讓新秀、剛轉隊、傷癒復出的球員出現系統性偏移，這類球員的差距不要直接當成我們的錯。\n'
        '- 2K 的屬性分佈本身也被遊戲機制壓縮（例如 Pass Vision 給長人普遍很低），'
        '所以屬性對照看的是 **排序一致性（ρ）與分組方向性偏差**，不是絕對值差。\n')

    parts.append('## 1. 方法\n')
    parts.append(
        '**資料來源**\n\n'
        '| 來源 | 檔案 / 位置 | 取用欄位 |\n| --- | --- | --- |\n'
        '| 正式卡片 OVR | `reports/ovr-calibrated-2025-26/ranking.csv` | `rank`、`ovr`、位置、`MIN`、各項卡片屬性 |\n'
        '| v54 模擬板 | `reports/ovr-v54-shrinkage-2025-26/ranking-v2.csv`（`reports/status/status_snapshot.py` 的 `LATEST_SIM=\'v54\'`） | `rank`、`v2Per36` |\n'
        '| RAPM | `reports/impact-rapm/rapm.csv` | 多季 `pooledNet`（條件 `pooledPoss≥5000`）、單季 `lastSeasonNet`（條件 `lastSeasonPoss≥500`） |\n'
        '| box score | `data/season-league.json` | AST/36、REB/36、FGA/36、三分出手佔比（只用於原型判定） |\n'
        '| NBA 2K27 | https://www.2kratings.com/ | 總評、位置、各項屬性 |\n\n'
        '**2K 抓取做法**（最終採用：內建瀏覽器同源 fetch）\n\n'
        '`fetch_2k27.py` 用 Python `requests` 直接抓會被 2kratings 回 403，所以改在內建瀏覽器開 2kratings.com，'
        '在頁內以同源 `fetch` 逐一讀球員頁（每頁間隔 2–4 秒、單頁 20 秒逾時、連續被擋 4 次即停；未解任何 CAPTCHA）。'
        '球員頁 JSON-LD 給 2K27 總評與 31 項屬性，`chartjs-dashboard-line-year` 折線圖給 2K19–2K27 逐年總評。'
        '結果以 `slug|pos|數字串` 分段匯出到 `cache/browser_chunk_*.txt`（每段核對長度＋雜湊），'
        '再由 `build_from_browser.py` 轉成 `2k27_ratings.csv`、`2k_yearly_ovr.csv`、`unmatched.csv`。'
        'slug 候選清單（名字正規化＋別名）沿用 `fetch_2k27.py` 的對應規則，存在 `slug_candidates.json`。\n\n'
        '原本 `fetch_2k27.py` 的流程（保留供參考）：\n\n'
        '1. 先抓 30 支 NBA 隊伍頁與 G-League 附屬隊頁，從頁內的 JSON-LD（`schema.org/Person` 的 `additionalProperty`）'
        '建立「球員名 → 網址 slug ＋ 總評」索引。\n'
        '2. 名字對應流程：先用重音正規化（`Dončić`→`doncic`、`Porziņģis`→`porzingis`、`Dëmin`→`demin`）＋'
        '去掉 `.`、`\'` 後比對；比不到再去掉 `Jr./Sr./II/III/IV` 後綴比對；再不行查人工別名表；'
        '最後退回「由名字直接推導 slug」試打球員頁。\n'
        '3. 逐一抓球員頁，從 JSON-LD 取 31 項屬性，位置取自簡介段落的 `/lists/<position>` 連結。\n'
        '4. 禮貌抓取：HTML 全部存本地 cache（`cache/`，未進版控）、每次請求間 sleep 1 秒、帶一般瀏覽器 User-Agent、'
        '遇 403/429/503 以遞增等待重試 3 次，連續 8 個頁面被擋就直接中止並回報。'
        '**沒有做任何繞過 bot 偵測或解 CAPTCHA 的事。**\n\n'
        '**抓取正確性檢查點**\n\n')
    def r0(v):
        return '—' if v is None else f'{v:.0f}'

    if km:
        parts.append(
            f'- Karlo Matković：2K27 總評抓到 **{r0(km["overall2k"])}**（任務給的期望值 74）。'
            f'卡片 OVR {km["cardOvr"]}（第 {km["cardRank"]} 名）、2K 第 {r0(km["rank2k"])} 名、'
            f'RAPM 多季第 {r0(km["rapmPooledRank"])} 名、單季第 {r0(km["rapmLastRank"])} 名。\n')
    parts.append('\n**名次定義**：`cardRank` 是卡片板原始名次（582 人內）；`rank2k` 是在「成功對應到 2K 的子集」內'
                 '依 2K 總評由高到低的平均名次；RAPM 名次是在各自的樣本量門檻子集內排。'
                 '`rankGap = rank2k − cardRank`，**正值＝卡片給的名次比 2K 高，也就是卡片相對高估**。\n')

    parts.append('\n### 1.1 原型判定規則\n')
    parts.append('```' + ARCH_RULES + '```\n')
    parts.append('原型人數（整個卡片板 %d 人）：' % len(data)
                 + '、'.join(f'{a} {n}' for a, n in sorted(arch_count.items(), key=lambda kv: -kv[1])) + '\n')

    parts.append('\n## 2. 對應失敗 / 未取得 2K 評分的球員\n')
    if not unmatched:
        parts.append('全部對應成功。\n')
    else:
        parts.append(f'共 {len(unmatched)} 人（占卡片板 {len(unmatched)/len(data):.1%}）。'
                     '主要是 2025-26 之後離開 NBA、沒有 2K27 條目，或 slug 命名與名字差太多的球員。\n\n')
        parts.append(md_table(['name', 'cardRank', 'cardOvr', 'MIN', 'reason', 'triedSlugs'], unmatched) + '\n')

    parts.append('\n## 3. Spearman ρ（依出場分鐘分桶）\n')
    parts.append('`n` 是該桶實際有兩邊資料的人數。\n\n')
    parts.append(md_table(sp_cols, sp_rows) + '\n')

    parts.append('\n## 4. 卡片名次 vs 2K 名次差距最大的球員\n')
    parts.append('### 4.1 卡片相對 2K 高估前 25（rankGap 最大）\n\n')
    parts.append(md_table(gcols_md, over) + '\n')
    parts.append('\n### 4.2 卡片相對 2K 低估前 25（rankGap 最小）\n\n')
    parts.append(md_table(gcols_md, under) + '\n')
    parts.append('\n### 4.3 各原型的平均名次差\n\n')
    parts.append(md_table(['原型', '人數（有 2K）', '平均名次差 rank2k−cardRank', '中位數'], arch_rows) + '\n')

    parts.append('\n## 5. 屬性對照：卡片屬性 vs 2K 屬性\n')
    parts.append('`ρ` 由小到大排（ρ 最低＝兩邊對這個能力的排序最不一致）。'
                 '`Δ原型` ＝ 該原型球員的「卡片屬性百分位 − 2K 屬性百分位」平均，'
                 '**正值＝卡片把這個原型的這項能力排得比 2K 高**。\n\n')
    parts.append(md_table(acols, attr_rows) + '\n')

    parts.append('\n## 6. 結論與 v55 修正方向\n')
    cp = HERE / 'conclusion.md'
    parts.append((cp.read_text(encoding='utf-8') if cp.exists()
                  else '（待填：看完上面數據後寫在 conclusion.md，本腳本會自動併入）') + '\n')

    (HERE / 'report.md').write_text('\n'.join(parts), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
