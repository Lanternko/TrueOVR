"""v57 規劃用診斷腳本（唯讀：只讀既有產物，只寫 reports/ovr-v57-card-2025-26/diagnosis.json）。

量化 v56 留下的兩個問題：
  (1) 側翼/後衛防守專才被低估的幅度（RAPM pooledD 前 30，對照 E2-λ0.4 與 F2-γ0.5 卡片名次、
      2K27 名次、RAPM pooledNet 名次，驗收條件用 rank <= max(2K27, RAPM) 的「不誤傷」口徑）。
  (2) 卡片前十長人過多：前十名各自的 pred 分解（進攻/防守/體格/防守加分），以及 2K27、RAPM 名次。
另附設計候選門檻用的敏感度數字（各名次的 pred 門檻、把一位球員推到門檻名次所需的 bonus、
以 centeredD 反推所需 gamma）與各位置 pooledD / help / onBall 的離散度。

用法：python reports/ovr-v57-card-2025-26/diagnose.py
"""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique',
         'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
POS_INTERACT = ['PG', 'SG', 'SF', 'PF']
INTERACT = ['long', 'short', 'pass', 'rebound', 'help']
OFF = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'creation']
DEF = ['onBall', 'help', 'pressure']
PHYS = ['rebound', 'physique', 'stamina', 'heightInches']
BIG = {'PF', 'C'}
EVAL_POSS = 5000
BLEND_PER36 = 0.75

E2 = 'reports/ovr-v55-card-E-2025-26/card-E2-lam0.4'
F2 = 'reports/ovr-v56-card-defense-2025-26/card-F2-gamma0.5'


def rows(path):
    with open(ROOT / path, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def ranking(path):
    return {r['name']: r for r in rows(path + '/ranking.csv')}


def summary(path):
    return json.loads((ROOT / path / 'summary.json').read_text(encoding='utf-8'))


rapm = {r['name']: r for r in rows('reports/impact-rapm/rapm.csv')}
merged = {r['name']: r for r in rows('reports/ovr-v55-2k27-compare/merged.csv')}
e2, f2 = ranking(E2), ranking(F2)
s_e2, s_f2 = summary(E2), summary(F2)
posMeanD = s_f2['defenseBonusPosMeanD']

pool = [r for r in rapm.values() if float(r['pooledPoss']) >= EVAL_POSS]
net_rank = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda r: -float(r['pooledNet'])))}
d_rank = {r['name']: i + 1 for i, r in enumerate(sorted(pool, key=lambda r: -float(r['pooledD'])))}


def rank2k(name):
    m = merged.get(name)
    return float(m['rank2k']) if m and m['rank2k'] else None


def gate_ref(name):
    """驗收用「不誤傷」上界：max(2K27 名次, RAPM pooledNet 名次)。任一缺值則用另一個。"""
    vals = [v for v in (rank2k(name), net_rank.get(name)) if v]
    return max(vals) if vals else None


def group(pos):
    return 'BIG' if pos in BIG else ('WING' if pos == 'SF' else 'GUARD')


def centeredD(name, pos):
    r = rapm.get(name)
    if not r:
        return None
    return BLEND_PER36 * float(r['pooledD']) - posMeanD[pos]


def decompose(name, card, s):
    """把 pred 分解成 intercept + 各屬性貢獻（含位置交乘）+ defenseBonus。"""
    f = s['formula']
    coef, mean, sd = f['coefficientsOnStandardized'], f['attributeMean'], f['attributeSD']
    pos = card['pos']
    contrib = {}
    for i, a in enumerate(ATTRS):
        z = (float(card[a]) - mean[a]) / sd[a]
        c = coef[i] * z
        if pos in POS_INTERACT and a in INTERACT:
            blk = 15 + POS_INTERACT.index(pos) * 5 + INTERACT.index(a)
            c += coef[blk] * z
        contrib[a] = c
    bonus = float(card.get('defenseBonus') or 0.0)
    return {'intercept': f['intercept'], 'contrib': contrib, 'bonus': bonus,
            'off': sum(contrib[a] for a in OFF), 'def': sum(contrib[a] for a in DEF),
            'phys': sum(contrib[a] for a in PHYS),
            'predCheck': f['intercept'] + sum(contrib.values()) + bonus,
            'predCsv': float(card['predictedPer36'])}


out = {'inputs': {'e2': E2, 'f2': F2, 'evalPoss': EVAL_POSS, 'posMeanD': posMeanD}}

# ---- (1) RAPM pooledD 前 30 ----
top30 = sorted(pool, key=lambda r: -float(r['pooledD']))[:30]
tbl = []
for i, r in enumerate(top30):
    n = r['name']
    ce, cf = e2.get(n), f2.get(n)
    pos = (cf or ce or {}).get('pos')
    ref = gate_ref(n)
    row = {'pooledDRank': i + 1, 'name': n, 'pos': pos, 'group': group(pos) if pos else None,
           'pooledD': round(float(r['pooledD']), 3), 'pooledNet': round(float(r['pooledNet']), 3),
           'centeredD': round(centeredD(n, pos), 3) if pos else None,
           'rank2k': rank2k(n), 'rapmNetRank': net_rank.get(n),
           'e2Rank': int(ce['rank']) if ce else None, 'f2Rank': int(cf['rank']) if cf else None,
           'gateRef': ref,
           'e2Violation': (int(ce['rank']) - ref) if (ce and ref) else None,
           'f2Violation': (int(cf['rank']) - ref) if (cf and ref) else None,
           'f2Bonus': round(float(cf['defenseBonus']), 3) if cf else None,
           'predF2': float(cf['predictedPer36']) if cf else None,
           'help': float(cf['help']) if cf else None, 'onBall': float(cf['onBall']) if cf else None,
           'creation': float(cf['creation']) if cf else None}
    tbl.append(row)
out['pooledDTop30'] = tbl

grp = {}
for g in ('BIG', 'WING', 'GUARD'):
    sel = [r for r in tbl if r['group'] == g and r['f2Violation'] is not None]
    if not sel:
        continue
    fails_e2 = [r for r in sel if r['e2Violation'] > 0]
    fails_f2 = [r for r in sel if r['f2Violation'] > 0]
    grp[g] = {'n': len(sel), 'failGateE2': len(fails_e2), 'failGateF2': len(fails_f2),
              'medianViolationE2': statistics.median([r['e2Violation'] for r in sel]),
              'medianViolationF2': statistics.median([r['f2Violation'] for r in sel]),
              'maxViolationF2': max(r['f2Violation'] for r in sel),
              'worstF2': sorted(sel, key=lambda r: -r['f2Violation'])[0]['name'],
              'meanBonusF2': round(statistics.mean([r['f2Bonus'] for r in sel]), 3)}
out['byGroup'] = grp


# ---- (2) 前十名分解 ----
def top_n(card_map, s, n=12):
    sel = sorted(card_map.values(), key=lambda r: int(r['rank']))[:n]
    res = []
    for r in sel:
        d = decompose(r['name'], r, s)
        res.append({'rank': int(r['rank']), 'name': r['name'], 'pos': r['pos'], 'ovr': float(r['ovr']),
                    'isBig': r['pos'] in BIG, 'pred': d['predCsv'], 'bonus': round(d['bonus'], 3),
                    'off': round(d['off'], 3), 'def': round(d['def'], 3), 'phys': round(d['phys'], 3),
                    'intercept': round(d['intercept'], 3),
                    'predRecomputeErr': round(d['predCheck'] - d['predCsv'], 6),
                    'topAttrs': sorted(((a, round(c, 3)) for a, c in d['contrib'].items()),
                                       key=lambda kv: -kv[1])[:4],
                    'rank2k': rank2k(r['name']), 'rapmNetRank': net_rank.get(r['name']),
                    'pooledDRank': d_rank.get(r['name']), 'gateRef': gate_ref(r['name']),
                    'centeredD': round(centeredD(r['name'], r['pos']), 3) if rapm.get(r['name']) else None})
    return res


out['top12E2'] = top_n(e2, s_e2)
out['top12F2'] = top_n(f2, s_f2)
out['bigCount'] = {
    lab: {'top%d' % k: sum(1 for r in m.values() if int(r['rank']) <= k and r['pos'] in BIG) for k in (10, 15, 20)}
    for lab, m in (('E2', e2), ('F2', f2))}
ALLOWED = {'Victor Wembanyama', 'Giannis Antetokounmpo', 'Nikola Jokić', 'Chet Holmgren'}
out['allowedBigs'] = sorted(ALLOWED)
out['extraBigsTop10'] = {
    lab: [r['name'] for r in sorted(m.values(), key=lambda r: int(r['rank']))[:10]
          if r['pos'] in BIG and r['name'] not in ALLOWED]
    for lab, m in (('E2', e2), ('F2', f2))}

# ---- (3) 敏感度：名次 -> pred 門檻 ----
pred_sorted = sorted((float(r['predictedPer36']) for r in f2.values()), reverse=True)
out['predAtRankF2'] = {str(k): round(pred_sorted[k - 1], 3) for k in
                       (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 20, 25, 30, 40, 60, 100, 150, 200)}

# 把未過門檻者推到 gateRef 名次所需的 pred 增量（單調估計，忽略其他人同時移動）
need = []
for r in tbl:
    if r['f2Violation'] is None or r['f2Violation'] <= 0:
        continue
    target = min(int(r['gateRef']), len(pred_sorted))
    need_pred = pred_sorted[target - 1]
    delta = need_pred - r['predF2']
    cd = r['centeredD']
    need.append({'name': r['name'], 'pos': r['pos'], 'group': r['group'], 'f2Rank': r['f2Rank'],
                 'gateRef': r['gateRef'], 'f2Violation': r['f2Violation'],
                 'predF2': round(r['predF2'], 3), 'predNeeded': round(need_pred, 3),
                 'deltaPredNeeded': round(delta, 3), 'centeredD': cd,
                 'impliedGamma': round(delta / cd, 2) if cd and cd > 0 else None})
out['gammaNeededF2Failures'] = sorted(need, key=lambda r: -r['deltaPredNeeded'])

# ---- (4) 各位置離散度（支持「跨位置標準化」候選）----
disp = {}
for pos in ('PG', 'SG', 'SF', 'PF', 'C'):
    sel = [r for r in f2.values() if r['pos'] == pos]
    ds = [float(rapm[r['name']]['pooledD']) for r in sel
          if r['name'] in rapm and float(rapm[r['name']]['pooledPoss']) >= EVAL_POSS]
    cds = [BLEND_PER36 * d - posMeanD[pos] for d in ds]
    disp[pos] = {'nCard': len(sel), 'nPool': len(ds),
                 'sdPooledD': round(statistics.pstdev(ds), 3),
                 'sdCenteredD': round(statistics.pstdev(cds), 3),
                 'maxCenteredD': round(max(cds), 3),
                 'p90CenteredD': round(sorted(cds)[int(0.9 * (len(cds) - 1))], 3),
                 'sdHelp': round(statistics.pstdev([float(r['help']) for r in sel]), 2),
                 'sdOnBall': round(statistics.pstdev([float(r['onBall']) for r in sel]), 2),
                 'sdCreation': round(statistics.pstdev([float(r['creation']) for r in sel]), 2)}
out['dispersionByPos'] = disp

# ---- (5) v56 七人門檻現況（給 v57 沿用時對照）----
v53 = ranking('reports/ovr-calibrated-2025-26')
SEVEN = ['Karlo Matković', 'John Collins', 'Isaiah Stewart', 'Luka Garza',
         'Neemias Queta', 'Rudy Gobert', 'Jalen Smith']
out['sevenPlayer'] = [{'name': n, 'v53': int(v53[n]['rank']), 'e2': int(e2[n]['rank']),
                       'f2': int(f2[n]['rank']), 'rank2k': rank2k(n), 'rapmNetRank': net_rank.get(n),
                       'gateRef': gate_ref(n), 'f2Bonus': round(float(f2[n]['defenseBonus']), 3),
                       'centeredD': round(centeredD(n, f2[n]['pos']), 3)} for n in SEVEN]

# ---- (6) 外部基準自己的前十長人組成（判斷「前十只能 4 位長人」是否與外部證據相容）----
card_pos = {n: r['pos'] for n, r in f2.items()}
two_k = sorted(((rank2k(n), n) for n in f2 if rank2k(n)), key=lambda kv: kv[0])[:12]
rapm_top = sorted(((net_rank[n], n) for n in f2 if n in net_rank), key=lambda kv: kv[0])[:12]
out['externalTop12'] = {
    '2k27': [{'rank': k, 'name': n, 'pos': card_pos.get(n), 'isBig': card_pos.get(n) in BIG} for k, n in two_k],
    'rapmNet': [{'rank': k, 'name': n, 'pos': card_pos.get(n), 'isBig': card_pos.get(n) in BIG} for k, n in rapm_top],
}
out['externalBigsTop10'] = {
    '2k27': [n for k, n in two_k if k <= 10 and card_pos.get(n) in BIG],
    'rapmNet': [n for k, n in rapm_top if k <= 10 and card_pos.get(n) in BIG],
}

# ---- (7) 「過譽」檢查：卡片名次比兩個外部基準都好多少（正數=卡片比兩者都高估）----
over = []
for r in sorted(f2.values(), key=lambda r: int(r['rank']))[:25]:
    n = r['name']
    refs = [v for v in (rank2k(n), net_rank.get(n)) if v]
    if not refs:
        continue
    over.append({'name': n, 'pos': r['pos'], 'isBig': r['pos'] in BIG, 'f2Rank': int(r['rank']),
                 'rank2k': rank2k(n), 'rapmNetRank': net_rank.get(n),
                 'bestRef': min(refs), 'overRating': round(min(refs) - int(r['rank']), 1),
                 'bonus': round(float(r['defenseBonus']), 3)})
out['overRatingF2Top25'] = sorted(over, key=lambda r: -r['overRating'])

# ---- (8) taper 用錨點：E2 pred 在縮放參考池（MIN>=500）的百分位 ----
ref_pool = sorted((float(r['predictedPer36']) for r in e2.values() if float(r['MIN']) >= 500))


def pct_of(x):
    below = sum(1 for v in ref_pool if v < x)
    return round(100.0 * below / (len(ref_pool) - 1), 2)


out['e2PredPercentiles'] = {'nRefPool': len(ref_pool),
                            'predAtPR': {str(p): round(ref_pool[int(round(p / 100 * (len(ref_pool) - 1)))], 3)
                                         for p in (50, 70, 80, 85, 90, 92, 95, 97, 98, 99)}}
watch = ['Evan Mobley', 'Joel Embiid', 'Aaron Gordon', 'Victor Wembanyama', 'Chet Holmgren',
         'Nikola Jokić', 'Giannis Antetokounmpo', 'Rudy Gobert', 'Neemias Queta', 'Karlo Matković',
         'Isaiah Stewart', 'Jalen Smith', 'Herbert Jones', 'Alex Caruso', 'Marcus Smart',
         'Ausar Thompson', 'Dillon Brooks', 'Matisse Thybulle', 'Ajay Mitchell', 'Ronald Holland II',
         'Franz Wagner', 'Anthony Davis', 'Jaren Jackson Jr.', 'OG Anunoby', 'Draymond Green', 'Dean Wade']
out['watchlist'] = [{'name': n, 'pos': e2[n]['pos'], 'e2Rank': int(e2[n]['rank']),
                     'e2Pred': float(e2[n]['predictedPer36']), 'e2PredPR': pct_of(float(e2[n]['predictedPer36'])),
                     'f2Rank': int(f2[n]['rank']), 'centeredD': round(centeredD(n, e2[n]['pos']), 3) if rapm.get(n) else None,
                     'rank2k': rank2k(n), 'rapmNetRank': net_rank.get(n), 'gateRef': gate_ref(n)}
                    for n in watch if n in e2]

# ---- (9) 位置置中後的 RAPM 目標值 r（= calibrate.py::attach_rapm 的 r，beta=0），
#          用來量化「把 pred 往 r 收縮」這個雙向對齊候選的方向與幅度。
BLEND_POSS = 1000
r_val = {}
for pos in ('PG', 'SG', 'SF', 'PF', 'C'):
    sel = [r for r in e2.values() if r['pos'] == pos]
    pool_pos = [r for r in sel if r['name'] in rapm and float(rapm[r['name']]['pooledPoss']) >= BLEND_POSS]
    num = sum(float(r['MIN']) * BLEND_PER36 * float(rapm[r['name']]['pooledNet']) for r in pool_pos)
    den = sum(float(r['MIN']) for r in pool_pos)
    mu = num / den
    for r in sel:
        x = rapm.get(r['name'])
        if x and float(x['pooledPoss']) >= BLEND_POSS:
            r_val[r['name']] = BLEND_PER36 * float(x['pooledNet']) - mu
out['rTargetMuNote'] = 'r = 0.75*pooledNet - MIN 加權位置均值（池 pooledPoss>=1000），同 calibrate.py::attach_rapm'
for w in out['watchlist']:
    w['rTarget'] = round(r_val[w['name']], 3) if w['name'] in r_val else None
    w['rMinusE2Pred'] = round(r_val[w['name']] - w['e2Pred'], 3) if w['name'] in r_val else None

(ROOT / 'reports/ovr-v57-card-2025-26/diagnosis.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# ---- 控制台摘要 ----
print('== pooledD top30：驗收口徑 rank <= max(2K27, RAPM) 的違反量（正數=低估）==')
print('rank pos  name                        pooledD centeredD 2K27  RAPM  E2    F2    gateRef vioE2 vioF2 bonus')
for r in tbl:
    print('%4s %-4s %-26s %7s %9s %5s %5s %5s %5s %7s %5s %5s %6s' % (
        r['pooledDRank'], r['pos'] or '--', r['name'][:26], r['pooledD'], r['centeredD'],
        r['rank2k'], r['rapmNetRank'], r['e2Rank'], r['f2Rank'], r['gateRef'],
        r['e2Violation'], r['f2Violation'], r['f2Bonus']))
print()
print('== 分組彙總 ==')
for g, v in grp.items():
    print(g, json.dumps(v, ensure_ascii=False))
print()
print('== F2-y0.5 前 12（pred 分解）==')
for r in out['top12F2']:
    print('%3s %-3s %-24s ovr=%-6s pred=%-7s off=%-7s def=%-7s phys=%-7s bonus=%-6s 2K=%s RAPM=%s dRank=%s big=%s' % (
        r['rank'], r['pos'], r['name'][:24], r['ovr'], r['pred'], r['off'], r['def'], r['phys'],
        r['bonus'], r['rank2k'], r['rapmNetRank'], r['pooledDRank'], r['isBig']))
print()
print('== E2-lam0.4 前 12（pred 分解）==')
for r in out['top12E2']:
    print('%3s %-3s %-24s ovr=%-6s pred=%-7s off=%-7s def=%-7s phys=%-7s 2K=%s RAPM=%s big=%s' % (
        r['rank'], r['pos'], r['name'][:24], r['ovr'], r['pred'], r['off'], r['def'], r['phys'],
        r['rank2k'], r['rapmNetRank'], r['isBig']))
print()
print('bigCount', json.dumps(out['bigCount']))
print('extraBigsTop10', json.dumps(out['extraBigsTop10'], ensure_ascii=False))
print('predAtRankF2', json.dumps(out['predAtRankF2']))
print()
print('== 未過門檻者所需 pred 增量 / 反推 gamma（單調估計）==')
for r in out['gammaNeededF2Failures']:
    print('%-24s %-3s %-5s f2=%-4s ref=%-6s vio=%-5s pred=%-7s need=%-7s delta=%-7s centeredD=%s gamma=%s' % (
        r['name'][:24], r['pos'], r['group'], r['f2Rank'], r['gateRef'], r['f2Violation'],
        r['predF2'], r['predNeeded'], r['deltaPredNeeded'], r['centeredD'], r['impliedGamma']))
print()
print('== 各位置離散度 ==')
for p, v in disp.items():
    print(p, json.dumps(v))
print()
print('== 七人門檻 ==')
for r in out['sevenPlayer']:
    print(json.dumps(r, ensure_ascii=False))
print()
print('== 外部基準前 12（長人標記）==')
for k, v in out['externalTop12'].items():
    print(k, json.dumps([('%s(%s)%s' % (r['name'], r['pos'], '*BIG' if r['isBig'] else '')) for r in v], ensure_ascii=False))
print('externalBigsTop10', json.dumps(out['externalBigsTop10'], ensure_ascii=False))
print()
print('== F2 前 25「過譽」排序（overRating = min(2K27,RAPM) - 卡片名次）==')
for r in out['overRatingF2Top25']:
    print('%-24s %-3s big=%-5s f2=%-4s 2K=%-7s RAPM=%-5s bestRef=%-6s over=%-6s bonus=%s' % (
        r['name'][:24], r['pos'], r['isBig'], r['f2Rank'], r['rank2k'], r['rapmNetRank'],
        r['bestRef'], r['overRating'], r['bonus']))
print()
print('== E2 pred 百分位錨點（參考池 MIN>=500, n=%d）==' % out['e2PredPercentiles']['nRefPool'])
print(json.dumps(out['e2PredPercentiles']['predAtPR']))
print('name                     pos e2Rank e2Pred  e2PR   f2Rank centeredD 2K      RAPM  gateRef')
for r in out['watchlist']:
    print('%-24s %-3s %-6s %-7s %-6s %-6s %-9s %-7s %-5s %s' % (
        r['name'][:24], r['pos'], r['e2Rank'], r['e2Pred'], r['e2PredPR'], r['f2Rank'],
        r['centeredD'], r['rank2k'], r['rapmNetRank'], r['gateRef']))
print('-- rTarget（位置置中 RAPM 目標）與 r - e2Pred（負=卡片高於 RAPM 目標）--')
for r in out['watchlist']:
    print('%-24s %-3s e2Pred=%-7s r=%-7s r-pred=%-7s' % (r['name'][:24], r['pos'], r['e2Pred'], r['rTarget'], r['rMinusE2Pred']))
