"""v58 規劃用診斷腳本（唯讀既有產物；只寫 reports/ovr-v58-card-2025-26/diagnosis.json）。

目的（對應本次派工流程第 2 步）：
  1. 拆解 v57 最佳候選 G3-delta0.25 的 pred = pred0 + defenseBonus + align，說明
     Draymond Green 為何被推到第 10、Giannis Antetokounmpo 差多少分才能進前十。
  2. 列出所有「被向上修正（bonus+align>0）」且卡片名次已優於 RAPM pooledNet 名次的球員，
     量化「過譽幅度 = RAPM 名次 − 卡片名次」，作為 v58 上限機制的診斷依據。
  3. 對每個候選上限機制做**靜態敏感度**（直接對 v57 G3-delta0.25 的既有 pred 做後處理，
     不重跑回歸、不重算 OVR、不產生任何 ranking.csv；真正候選會在 preregistration.md
     鎖定後才由 calibrate-wing.py 重新產生）。敏感度只用來確認候選值不會明顯自相矛盾。
  4. 檢查保護組（側翼/後衛 14 人、長人 16 人、七人名單）在上限機制下誰會被碰到。

用法：python reports/ovr-v58-card-2025-26/diagnose.py
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/ovr-v58-card-2025-26'
V57 = ROOT / 'reports/ovr-v57-card-2025-26'
G3DIR = V57 / 'card-G3-delta0.25'
E2DIR = ROOT / 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4'
V53DIR = ROOT / 'reports/ovr-calibrated-2025-26'
RAPM = ROOT / 'reports/impact-rapm/rapm.csv'
MERGED = ROOT / 'reports/ovr-v55-2k27-compare/merged.csv'

EVAL_POSS = 5000
BIG = {'PF', 'C'}
WING = {'SF'}
GUARD = {'PG', 'SG'}
ALLOWED = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren'}
SEVEN = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza',
         'Neemias Queta', 'Rudy Gobert', 'Jalen Smith']
NAMED_WING = ['Herbert Jones', 'Alex Caruso', 'Marcus Smart']


def rows(path):
    with open(path, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def by_name(path):
    return {r['name']: r for r in rows(path)}


# rapm.csv 有大量空 name 列；比照 evaluate.mjs / diagnose.py：Python dict 同名最後一列覆蓋。
rapm = {r['name']: r for r in rows(RAPM)}
merged = {r['name']: r for r in rows(MERGED)}
g3 = by_name(G3DIR / 'ranking.csv')
e2 = by_name(E2DIR / 'ranking.csv')
v53 = by_name(V53DIR / 'ranking.csv')
summary = json.loads((G3DIR / 'summary.json').read_text(encoding='utf-8'))

pool = [r for r in rapm.values() if float(r['pooledPoss']) >= EVAL_POSS]
net_rank = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda r: -float(r['pooledNet'])))}
d_rank = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda r: -float(r['pooledD'])))}


def rank2k(name):
    m = merged.get(name)
    return float(m['rank2k']) if m and m['rank2k'] else None


def gate_ref(name):
    vals = [v for v in (rank2k(name), net_rank.get(name)) if v is not None]
    return max(vals) if vals else None


def is_big(name):
    return g3.get(name, {}).get('pos') in BIG


# ---- 1. G3 前 20 分解 ----
def pack(name):
    r = g3[name]
    return {
        'name': name, 'rank': int(r['rank']), 'pos': r['pos'], 'pred': float(r['predictedPer36']),
        'pred0': float(r['pred0']), 'bonus': float(r['defenseBonus']), 'align': float(r['align']),
        'lift': float(r['defenseBonus']) + float(r['align']), 'pr': float(r['pr']),
        'e2Rank': int(e2[name]['rank']) if name in e2 else None,
        'rank2k': rank2k(name), 'rapmNetRank': net_rank.get(name),
        'rapmDRank': d_rank.get(name),
        'minRef': min([v for v in (rank2k(name), net_rank.get(name)) if v is not None], default=None),
        'maxRef': gate_ref(name),
        'isBig': is_big(name),
    }


top20 = [pack(r['name']) for r in sorted(g3.values(), key=lambda r: int(r['rank']))[:20]]
out = {'inputs': {
    'g3': str(G3DIR.relative_to(ROOT)), 'e2': str(E2DIR.relative_to(ROOT)),
    'v53': str(V53DIR.relative_to(ROOT)), 'rapm': str(RAPM.relative_to(ROOT)),
    'merged': str(MERGED.relative_to(ROOT)), 'evalPoss': EVAL_POSS,
    'note': 'G3-delta0.25 = v57 最佳候選（γ=1.0, δ=0.25, taper PR 90/96）。'},
    'top20G3': top20}

# ---- 2. Draymond 與 Giannis ----
d = pack('Draymond Green')
g = pack('Giannis Antetokounmpo')
rank10_pred = d['pred']
# 以同一份 G3 球員池重排，觀察抽掉 bonus / align 的影響
names = list(g3.keys())


def rerank(score):
    return {n: i + 1 for i, n in enumerate(sorted(names, key=lambda n: (-score(n), n)))}


pred0_only = rerank(lambda n: float(g3[n]['pred0']))
no_bonus = rerank(lambda n: float(g3[n]['pred0']) + float(g3[n]['align']))
no_align = rerank(lambda n: float(g3[n]['pred0']) + float(g3[n]['defenseBonus']))
full = rerank(lambda n: float(g3[n]['predictedPer36']))

out['draymond'] = {
    **d,
    'pred0Rank': pred0_only['Draymond Green'],
    'pred0PlusAlignRank': no_bonus['Draymond Green'],
    'pred0PlusBonusRank': no_align['Draymond Green'],
    'shareOfLiftFromBonus': d['bonus'] / d['lift'] if d['lift'] else None,
    'bonusTaperWeight': None,
    'note': 'pred0 第 %d；只加 align 第 %d；只加 bonus 第 %d；兩者相加第 %d。' % (
        pred0_only['Draymond Green'], no_bonus['Draymond Green'],
        no_align['Draymond Green'], full['Draymond Green']),
}
pr_pool = sorted(float(r['pred0']) for r in g3.values() if float(r['MIN']) >= 500)
pr_d = 100.0 * sum(1 for v in pr_pool if v < d['pred0']) / (len(pr_pool) - 1)
out['draymond']['prFromPred0'] = round(pr_d, 2)
out['draymond']['bonusTaperWeight'] = round(
    min(1.0, max(0.0, (96.0 - pr_d) / (96.0 - 90.0))), 3)

out['giannis'] = {
    **g,
    'gapToRank10': round(rank10_pred - g['pred'], 3),
    'neededAlignDelta': round(rank10_pred - g['pred'], 3),
    'impliedDeltaIfOnlyAlign': round((rank10_pred - g['pred']) / (g['align'] / 0.25), 4) if g['align'] else None,
    'note': '與第 10 名差 %.3f 分；align=δ(r−pred0)，r−pred0=%.3f，故只調 δ 需再加 %.4f（δ≈%.4f）。' % (
        rank10_pred - g['pred'], g['align'] / 0.25,
        (rank10_pred - g['pred']) / (g['align'] / 0.25), 0.25 + (rank10_pred - g['pred']) / (g['align'] / 0.25)),
}

# 目前排在 Giannis 前面的 13 人
above = [pack(n) for n in sorted(names, key=lambda n: -float(g3[n]['predictedPer36']))
         if float(g3[n]['predictedPer36']) > g['pred']]
out['aboveGiannis'] = above

# ---- 3. 被向上修正且卡片已優於 RAPM 的球員 ----
lifted = []
for n, r in g3.items():
    bonus, align = float(r['defenseBonus']), float(r['align'])
    lift = bonus + align
    rr = net_rank.get(n)
    if lift <= 0 or rr is None or float(rapm[n]['pooledPoss']) < EVAL_POSS:
        continue
    rank = int(r['rank'])
    lifted.append({
        'name': n, 'pos': r['pos'], 'rank': rank, 'pred': float(r['predictedPer36']),
        'pred0': float(r['pred0']), 'bonus': round(bonus, 3), 'align': round(align, 3),
        'lift': round(lift, 3), 'rapmNetRank': rr, 'rank2k': rank2k(n),
        'overRatingVsRapm': rr - rank,
        'liftsIntoTop10': rank <= 10 and rr > 10,
    })
lifted.sort(key=lambda x: -x['overRatingVsRapm'])
out['liftedOverRated'] = lifted

# ---- 4. 保護組是否被上限機制碰到 ----
def cap_bind(name, margin, ref='rapm'):
    r = g3.get(name)
    if not r:
        return None
    rr = net_rank.get(name)
    kk = rank2k(name)
    if rr is None and kk is None:
        return None
    ref_rank = rr if ref == 'rapm' else min([v for v in (kk, rr) if v is not None])
    rank = int(r['rank'])
    return {'rank': rank, 'refRank': ref_rank, 'allowedRank': max(1, math.ceil(ref_rank - margin)),
            'bind': rank < max(1, math.ceil(ref_rank - margin))}


protect = {}
wg = [n for n in g3 if g3[n]['pos'] in WING | GUARD and n in d_rank and d_rank[n] <= 30]
bg = [n for n in g3 if g3[n]['pos'] in BIG and n in d_rank and d_rank[n] <= 30]
protect['wingGuard14'] = [ {'name': n, **{f'm{m}': cap_bind(n, m) for m in (0, 5, 10)}}
                          for n in sorted(wg, key=lambda n: int(g3[n]['rank']))]
protect['big16'] = [ {'name': n, **{f'm{m}': cap_bind(n, m) for m in (0, 5, 10)}}
                     for n in sorted(bg, key=lambda n: int(g3[n]['rank']))]
protect['seven'] = [ {'name': n, 'v53Rank': int(v53[n]['rank']), 'g3Rank': int(g3[n]['rank']),
                      **{f'm{m}': cap_bind(n, m) for m in (0, 5, 10)}} for n in SEVEN]
protect['namedWing'] = [ {'name': n, **{f'm{m}': cap_bind(n, m) for m in (0, 5, 10)}} for n in NAMED_WING]
out['protection'] = protect

# ---- 5. 靜態敏感度：RAPM / consensus 上限（固定點），不重跑回歸 ----
def static_cap(margin, ref='rapm'):
    """對 v57 G3 的既有 pred 做固定點上限；只為診斷，不是候選輸出。"""
    base = {n: float(g3[n]['predictedPer36']) for n in names}
    pred0 = {n: float(g3[n]['pred0']) for n in names}
    lift = {n: float(g3[n]['defenseBonus']) + float(g3[n]['align']) for n in names}
    allowed = {}
    for n in names:
        rr, kk = net_rank.get(n), rank2k(n)
        if rr is None and kk is None:
            allowed[n] = None
        elif ref == 'rapm':
            allowed[n] = max(1, math.ceil((rr if rr is not None else kk) - margin))
        else:
            vals = [v for v in (rr, kk) if v is not None]
            allowed[n] = max(1, math.ceil(min(vals) - margin))
    pred = dict(base)
    for it in range(100):
        sorted_pred = sorted(pred.values(), reverse=True)
        def T(a):
            return sorted_pred[min(max(a, 1), len(sorted_pred)) - 1] - 1e-9
        changed = 0.0
        for n in names:
            a = allowed[n]
            if a is None or lift[n] <= 0:
                continue
            new = min(pred[n], max(pred0[n], T(a)))
            changed = max(changed, pred[n] - new)
            pred[n] = new
        if changed < 1e-10:
            break
    order = sorted(names, key=lambda n: (-pred[n], -pred0[n], n))
    rank = {n: i + 1 for i, n in enumerate(order)}
    changed_players = [n for n in names if pred[n] < base[n] - 1e-9]
    return {
        'margin': margin, 'ref': ref, 'iterations': it + 1,
        'top10': [{'rank': rank[n], 'name': n, 'pos': g3[n]['pos'], 'pred': round(pred[n], 3),
                   'basePred': round(base[n], 3), 'pred0': round(pred0[n], 3),
                   'rapmNetRank': net_rank.get(n), 'rank2k': rank2k(n),
                   'isBig': g3[n]['pos'] in BIG, 'capped': pred[n] < base[n] - 1e-9}
                  for n in order[:10]],
        'keyRanks': {n: rank[n] for n in
                     ['Draymond Green', 'Giannis Antetokounmpo', 'Victor Wembanyama',
                      'Nikola Jokić', 'Chet Holmgren', 'Evan Mobley', 'Joel Embiid',
                      'Aaron Gordon', 'Rudy Gobert', 'Neemias Queta', 'Karlo Matković',
                      'Herbert Jones', 'Alex Caruso', 'Marcus Smart', 'Jalen Smith']},
        'cappedCount': len(changed_players),
        'cappedTop30': [{'name': n, 'baseRank': int(g3[n]['rank']), 'newRank': rank[n],
                         'basePred': round(base[n], 3), 'newPred': round(pred[n], 3)}
                        for n in sorted(changed_players, key=lambda n: int(g3[n]['rank']))[:20]],
        'wingGuardPass': sum(1 for n in wg if rank[n] <= gate_ref(n)),
        'bigPass': sum(1 for n in bg if rank[n] <= gate_ref(n)),
        'top10Bigs': [n for n in order[:10] if g3[n]['pos'] in BIG],
        'allFourTop10': all(rank[n] <= 10 for n in ALLOWED),
    }


sens = {'rapm': [static_cap(m, 'rapm') for m in (0, 5, 10)],
        'consensus': [static_cap(m, 'consensus') for m in (0, 5, 10)]}
out['staticCapSensitivity'] = {
    'note': '直接對 v57 G3-delta0.25 既有 pred 做固定點上限的靜態敏感度；未重跑回歸/OVR，'
            '不是候選輸出，只用於確認上限值不會明顯破壞保護組。真正候選由 calibrate-wing.py 重算。',
    'results': sens}

# ---- 6. 資料 SHA256 ----
sha = hashlib.sha256((ROOT / 'data/season-league.json').read_bytes()).hexdigest()
out['dataSeasonLeagueSha256'] = sha
out['expectedSha256'] = '497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6'

(OUT / 'diagnosis.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# ---- 主控台摘要 ----
print('== Draymond ==')
print(json.dumps(out['draymond'], ensure_ascii=False))
print('== Giannis ==')
print(json.dumps(out['giannis'], ensure_ascii=False))
print('== 排在 Giannis 前的 13 人 ==')
for r in above:
    print('%2d %-3s %-24s pred=%-6s pred0=%-6s bonus=%-6s align=%-6s lift=%-6s RAPM=%-4s 2K=%s' % (
        r['rank'], r['pos'], r['name'][:24], r['pred'], r['pred0'], r['bonus'], r['align'],
        round(r['lift'], 3), r['rapmNetRank'], r['rank2k']))
print('== 向上修正且卡片優於 RAPM（前 25）==')
for r in lifted[:25]:
    print('%-24s %-3s rank=%-4s RAPM=%-4s 2K=%-6s over=%-5s lift=%-6s bonus=%-6s align=%-6s' % (
        r['name'][:24], r['pos'], r['rank'], r['rapmNetRank'], r['rank2k'],
        r['overRatingVsRapm'], r['lift'], r['bonus'], r['align']))
print('== 靜態上限敏感度 ==')
for ref, arr in sens.items():
    for s in arr:
        print(ref, 'm=%d' % s['margin'], 'top10:', ' '.join(
            '%d.%s' % (x['rank'], x['name']) for x in s['top10']),
            '| bigs', len(s['top10Bigs']), '| allFour', s['allFourTop10'],
            '| wg', s['wingGuardPass'], '| big', s['bigPass'], '| capped', s['cappedCount'])
print('sha256', sha)
