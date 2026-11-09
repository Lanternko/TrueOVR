"""inseason／card 0.2.14：MIX 籃板／兩分干擾加分（E-290、R-183），500 分鐘以下按比例打折（E-292、R-184）。

加分 = λ·sd·P_MIX × min(1, MIN/500)
  P_MIX = (0.5·REBc·s_reb + 0.5·CON·s_con)·s_mix
  REBc  = clip(mean(z rebound, z orebPct, z drebPct), 0, 1.5)；CON = clip(z con2_36, 0, 1.5)；缺值的分量 z 記 0。
凍結（mix-pool-card0214.json，freeze() 產生）：z 的平均／標準差、三個縮放、sd、λ、clip 上下限、500 分鐘，
  全部取自 card 0.2.13a 的 ≥500 分鐘評估人群（E-291 臂 C 的 EP：MIN≥500 且姓名在 stats-2025-26 唯一）。
每天重算（L-117：屬性隨本季更新，不凍結）：
  rebound＝賽中當天的能力值（ranking 的 rebound 欄）；
  orebPct、drebPct、con2_36＝2025-26 與本季依 R-169 box 規則混合，w＝本季分鐘/(本季分鐘+500)（本季分鐘＝box 分鐘）；
    某季沒有值就只用另一季（新秀、復出老將只有本季；2025-26 hustle 不到 200 分鐘的 con 視為沒有，同卡片定義）；
    本季 orebPct／drebPct 讀 tracking/advanced.json，con2_36＝tracking/hustle.json 的 CONTESTED_SHOTS_2PT／MIN×36（本季不設 200 分鐘門檻）。
  打折用的 MIN＝2025-26 卡片分鐘＋本季 box 分鐘。
開季前（本季 0 分鐘、rebound＝卡片值）＝card-0.2.14 的 mixBonus（test/mix_day0_gate.py）。
MIX_BONUS=0 時 run_c4_live 不呼叫本檔（逐位元重現 inseason 0.2.13a）。

inseason／card 0.2.14a（E-294 臂 H-same，role-audit 4/5，使用者裁定採用、字母版）：apply(..., h=True)，凍結檔 mix-pool-card0214a.json。
  z_H = z_L − (1−α)·m_pos（α＝0.5；z_L＝上面的全聯盟 z，m_pos＝該位置在算尺人群的 z_L 平均，5 位置×4 特徵，凍結、不每天重算）；
  缺值的分量 z_H 記 α·m_pos（等於當作位置平均）；
  REBc＝f(mean(z_H rebound, orebPct, drebPct))、CON＝f(z_H con2_36)，f(x)＝1.5·tanh(max(x,0)/1.5)（軟飽和，無平台）；
  P＝(0.5·REBc·s_reb＋0.5·CON·s_con)·s_mix × w(pos)，w：C＝1、PF＝0.68/2.80、其他（含新秀的 G／F）0；λ、sd、500 分鐘打折同 0.2.14。
  位置：卡片＝card 0.2.13a 的 pos（F-033，2025-26 先發最多的位置）；賽中＝ranking 的 pos 欄（老將＝卡片 pos，新秀／復出老將照 ranking）。
  原始特徵每天混本季的規則與 0.2.14 相同（L-117）。h=False（MIX_H=0）走原本 0.2.14 路徑，逐位元不變。

inseason／card 0.2.14b（E-295 臂 W1，role-audit 4/5 reports/audit-0.2.14b/，使用者裁定採用、字母版）：apply(..., h=True, w1=True)，凍結檔 mix-pool-card0214b.json。
  位置改「實際上場位置比例」π（BBRef 2025-26，5 維）而不是標籤：w＝c＝π_C＋0.243·π_PF；m_i,k＝Σ_p π_ip·m_p,k（m_p＝算尺人群以 π 加權的 z_L 平均，凍結）；
  z_H＝z_L−0.5·m_i（缺值記 0.5·m_i）；其餘（1.5·tanh、z 尺、sd、λ、ref、500 分鐘打折、本季混合）同 0.2.14a；三個縮放在 W1 下重算並凍結。
  π 的來源（整季沿用 2025-26，不混本季比例；混入另開實驗）：
    卡片球員＝凍結 players[pid].pi（MP<200 往身高帶收縮，同 E-295；BBRef 對名另加手動別名 reports/card-0.2.14b/bbref-alias.csv）；
    不在卡片但有較早季 BBRef 的老將（復出老將 Lyles、Niang 等）＝凍結 fallback[pid].pi（最近一季，同收縮規則）；
    都沒有（新秀）＝heightPrior[身高]（70–91 吋，超出取端點，身高四捨五入到整數吋）。
  不再有「標籤不在 mpos 就給 0」的分支。w1=False 走 0.2.14a（MIX_W1=0），逐位元不變。

用法：python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze     （重產 0.2.14 凍結檔並核對 cand2 卡）
      python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_h   （產 0.2.14a 凍結檔並核對 card-0.2.15-cand／E-294 bonus_pick）
      python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_w1  （產 0.2.14b 凍結檔；核對 card-0.2.14b-cand：別名 3 人以外差 ≤0.02）
"""
import csv
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FROZEN = HERE / 'mix-pool-card0214.json'
FROZEN_H = HERE / 'mix-pool-card0214a.json'      # 0.2.14a（E-294 H-same）
CAND_H = ROOT / 'reports/card-0.2.15-cand/ranking.csv'
BONUS_PICK = ROOT / 'reports/E294-mix-pos-z-soft/bonus_pick.npz'
CARD14 = ROOT / 'reports/card-0.2.14/ranking.csv'
CARD14A = ROOT / 'reports/card-0.2.14a/ranking.csv'
FROZEN_W1 = HERE / 'mix-pool-card0214b.json'    # 0.2.14b（E-295 W1）
CARD14B = ROOT / 'reports/card-0.2.14b/ranking.csv'
CAND_W1 = ROOT / 'reports/card-0.2.14b-cand/ranking.csv'
ALIAS_W1 = ROOT / 'reports/card-0.2.14b/bbref-alias.csv'
E295 = ROOT / 'reports/E295-mix-pos-continuous/e295_eval.py'
BB_SHARES = ROOT / 'reports/card-0.2.9a+E177-bbref-position-shares'
RV_PRIOR = HERE / 'prior-2025-26-card0213a-rv.json'
POSL = ('PG', 'SG', 'SF', 'PF', 'C')
FEATS = ('rebound', 'orebPct', 'drebPct', 'con2_36')
CARD0213A = ROOT / 'reports/card-0.2.13a/ranking.csv'
CAND2 = ROOT / 'reports/card-0.2.14-cand2/ranking.csv'
STATS25 = ROOT / 'reports/E227-lineup-transformer-r2/data/stats-2025-26.csv'
HUST25 = ROOT / 'data/tracking-cells/2025-26/hustle-2025-26.json'
PRIOR = HERE / 'prior-2025-26-card0213a.json'
DATA26 = ROOT / 'data/defense-seventh/2026-27'


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return ' '.join(s.split())


def _f(x):
    return None if x in ('', None) else float(x)


def _mean_std(v):
    v = [x for x in v if x is not None]
    m = sum(v) / len(v)
    return m, math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


# ------------------------------------------------------------------ 凍結
def freeze():
    """照 E-291 臂 C（reports/E291-mix-shrink/e291_eval.py）算 2025-26 原始特徵與尺，存成 playerId 索引。"""
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    card = list(csv.DictReader(open(CARD0213A, encoding='utf-8')))
    pid_of = {p['name']: p['playerId'] for p in json.load(open(PRIOR, encoding='utf-8'))['players']}
    assert all(r['name'] in pid_of for r in card), 'card 0.2.13a 有人不在先驗卡'
    st = {}
    for r in csv.DictReader(open(STATS25, encoding='utf-8')):
        st.setdefault(norm(r['name']), []).append(r)
    js = json.loads(HUST25.read_text(encoding='utf-8'))
    H = {}
    for row in js['rowSet']:
        r = dict(zip(js['headers'], row))
        b = H.setdefault(norm(r['PLAYER_NAME']), {}).setdefault(r['PLAYER_ID'], [0.0, 0.0])
        b[0] += r['MIN'] or 0
        b[1] += r['CONTESTED_SHOTS_2PT'] or 0
    P = []
    for r in card:
        s = st.get(norm(r['name'])) or []
        uniq = len(s) == 1
        ob = _f(s[0]['orebPct']) if uniq else None
        db = _f(s[0]['drebPct']) if uniq else None
        h = H.get(norm(r['name'])) or {}
        con = None
        if len(h) == 1:
            m, c = list(h.values())[0]
            if m >= 200:                       # 卡片定義：2025-26 hustle 不到 200 分鐘＝沒有 con
                con = c / m * 36
        P.append({'name': r['name'], 'playerId': pid_of[r['name']], 'pos': r['pos'], 'MIN': float(r['MIN']),
                  'rebound': float(r['rebound']), 'ovr': float(r['ovr']), 'uniq': uniq, 'orebPct': ob, 'drebPct': db, 'con2_36': con})
    EP = [p for p in P if p['MIN'] >= 500 and p['uniq']]
    ovr = [p['ovr'] for p in EP]
    sd = _mean_std(ovr)[1]
    ref = math.sqrt(sum(p['pos'] == 'C' for p in EP) / len(EP))
    Z = {'rebound': _mean_std([p['rebound'] for p in EP]), 'orebPct': _mean_std([p['orebPct'] for p in EP]),
         'drebPct': _mean_std([p['drebPct'] for p in EP]), 'con2_36': _mean_std([p['con2_36'] for p in EP])}
    cfg = {'lambda': 0.5, 'sd': sd, 'ref': ref, 'clip': [0.0, 1.5], 'rampMin': 500.0, 'blendK': 500.0, 'conMinPrior': 200.0,
           'z': {k: {'mu': v[0], 'sd': v[1]} for k, v in Z.items()}}
    rebc = [_rebc(cfg, p['rebound'], p['orebPct'], p['drebPct']) for p in EP]
    conr = [_conr(cfg, p['con2_36']) for p in EP]
    rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
    s_reb, s_con = ref / rms(rebc), ref / rms(conr)
    s_mix = ref / rms([.5 * a * s_reb + .5 * b * s_con for a, b in zip(rebc, conr)])
    cfg['scales'] = {'reb': s_reb, 'con': s_con, 'mix': s_mix}
    cand = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(CAND2, encoding='utf-8'))}
    players, worst = {}, (0.0, '')
    for p in P:
        b = bonus(cfg, p['rebound'], p['orebPct'], p['drebPct'], p['con2_36'], p['MIN'])['bonus']
        d = abs(b - cand[p['name']])
        worst = max(worst, (d, p['name']))
        players[str(p['playerId'])] = {'name': p['name'], 'MIN': p['MIN'], 'orebPct': p['orebPct'], 'drebPct': p['drebPct'],
                                       'con2_36': p['con2_36'], 'cardRebound': p['rebound'], 'cardBonus': cand[p['name']]}
    doc = {'version': 'card／inseason 0.2.14', 'note': '凍結常數＝E-291 臂 C 的尺（EP＝card 0.2.13a MIN≥500 且姓名在 stats-2025-26 唯一）；'
                                                      'players＝2025-26 原始特徵（姓名對應同 E-291），cardBonus＝card-0.2.14-cand2 的 mixBonus',
           'config': cfg, 'epN': len(EP), 'reproduceCand2MaxAbs': worst[0], 'reproduceCand2Worst': worst[1],
           'sources_sha256': {'card_0213a_ranking': sha(CARD0213A), 'card_0214cand2_ranking': sha(CAND2), 'stats-2025-26.csv': sha(STATS25),
                              'hustle-2025-26.json': sha(HUST25)},
           'players': players}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'EP={len(EP)} sd={sd:.6f} ref={ref:.6f} scales={cfg["scales"]}；重現 cand2 最大差 {worst[0]:.4f}（{worst[1]}）')
    return doc


def freeze_h():
    """0.2.14a：照 E-294 臂 H-same（reports/E294-mix-pos-z-soft/e294_eval.py zfeat 'H.5'＋soft＋w）凍結 m_pos 與三個縮放。
    原始特徵、z 尺、算尺人群（379 人）都沿用 mix-pool-card0214.json；位置＝card 0.2.13a 的 pos（F-033）。"""
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    base = load_frozen(False)
    cfg0 = base['config']
    card = list(csv.DictReader(open(CARD0213A, encoding='utf-8')))
    cnt = {}
    for r in csv.DictReader(open(STATS25, encoding='utf-8')):
        cnt[norm(r['name'])] = cnt.get(norm(r['name']), 0) + 1
    pid_of = {v['name']: k for k, v in base['players'].items()}
    P = []
    for r in card:
        v = base['players'][pid_of[r['name']]]
        P.append({'name': r['name'], 'pid': pid_of[r['name']], 'pos': r['pos'], 'MIN': float(r['MIN']),
                  'ep': float(r['MIN']) >= 500 and cnt.get(norm(r['name']), 0) == 1,
                  'f': {'rebound': v['cardRebound'], 'orebPct': v['orebPct'], 'drebPct': v['drebPct'], 'con2_36': v['con2_36']}})
    EP = [p for p in P if p['ep']]
    assert len(EP) == base['epN'], (len(EP), base['epN'])
    mpos = {}
    for pos in POSL:
        mpos[pos] = {}
        for k in FEATS:
            zs = [_z(cfg0, k, p['f'][k]) for p in EP if p['pos'] == pos and p['f'][k] is not None]
            mpos[pos][k] = sum(zs) / len(zs)
    cfg = json.loads(json.dumps(cfg0))
    cfg['h'] = {'alpha': 0.5, 'mpos': mpos, 'posWeight': {'PG': 0.0, 'SG': 0.0, 'SF': 0.0, 'PF': 0.68 / 2.80, 'C': 1.0},
                'sat': 'tanh', 'hi': 1.5, 'mposPool': 'card 0.2.13a MIN>=500 且姓名在 stats-2025-26 唯一（同 epN），z_L 平均，有值的人'}
    cfg.pop('scales')
    zz = [_zh_parts(cfg, p['pos'], p['f']) for p in EP]
    rebc = [_soft(cfg, a) for a, _ in zz]
    conr = [_soft(cfg, b) for _, b in zz]
    rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
    ref = cfg['ref']
    s_reb, s_con = ref / rms(rebc), ref / rms(conr)
    s_mix = ref / rms([.5 * a * s_reb + .5 * b * s_con for a, b in zip(rebc, conr)])
    cfg['scales'] = {'reb': s_reb, 'con': s_con, 'mix': s_mix}
    cand = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(CAND_H, encoding='utf-8'))}
    import numpy as np
    bp = np.load(BONUS_PICK)
    assert str(bp['pick']) == 'H-same'
    npz = dict(zip([str(n) for n in bp['names']], [float(b) for b in bp['bonus']]))
    players, worst, worst_npz = {}, (0.0, ''), 0.0
    for p in P:
        b = bonus_h(cfg, p['pos'], p['f']['rebound'], p['f']['orebPct'], p['f']['drebPct'], p['f']['con2_36'], p['MIN'])['bonus']
        worst = max(worst, (abs(b - cand[p['name']]), p['name']))
        worst_npz = max(worst_npz, abs(b - npz[p['name']]))
        q = dict(base['players'][p['pid']])
        q.update(pos=p['pos'], cardBonus=cand[p['name']])
        players[p['pid']] = q
    assert worst[0] <= 0.0006 and worst_npz <= 1e-9, (worst, worst_npz)
    doc = {'version': 'card／inseason 0.2.14a',
           'note': 'E-294 臂 H-same：z_H＝z_L−(1−α)·m_pos、1.5·tanh 軟飽和、位置權重 C=1／PF=0.243；z 尺／sd／λ／ref／打折／混合規則同 mix-pool-card0214.json；'
                   'm_pos（5 位置×4 特徵）與縮放凍結，不每天重算；players＝0.2.14 凍結檔的 2025-26 原始特徵＋pos（card 0.2.13a，F-033）＋cardBonus（card 0.2.14a mixBonus）',
           'config': cfg, 'epN': len(EP), 'reproduceCandMaxAbs': worst[0], 'reproduceCandWorst': worst[1], 'reproduceBonusPickMaxAbs': worst_npz,
           'sources_sha256': {'mix-pool-card0214.json': sha(FROZEN), 'card_0213a_ranking': sha(CARD0213A), 'card_0215cand_ranking': sha(CAND_H),
                              'E294_bonus_pick': sha(BONUS_PICK), 'stats-2025-26.csv': sha(STATS25)},
           'players': players}
    FROZEN_H.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"EP={len(EP)} scales={cfg['scales']}\nm_pos C={mpos['C']}\n重現 cand 最大差 {worst[0]:.5f}（{worst[1]}）；對 bonus_pick {worst_npz:.2e}")
    return doc


def freeze_w1():
    """0.2.14b：照 E-295 臂 W1（e295_eval.py shares_for＋build）凍結 π、m_p、縮放、身高帶表；BBRef 對名加手動別名（audit-0.2.14b 必修 1）。
    原始特徵、z 尺、sd、λ、ref、算尺人群沿用 mix-pool-card0214a.json（基底）；players 另加 pi、piSrc、cardBonus（W1，未四捨五入）。"""
    import hashlib
    import importlib.util
    import numpy as np
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    spec = importlib.util.spec_from_file_location('e295', E295)
    E = importlib.util.module_from_spec(spec)
    sys.modules['e295'] = E
    spec.loader.exec_module(E)
    base = load_frozen(True)
    alias = {r['bbref_id']: r for r in csv.DictReader(open(ALIAS_W1, encoding='utf-8'))}
    SH = E.load_shares()
    named = {}                               # 季 → norm(BBRef 名) → [(π, MP)]（復出老將名字對照用）
    for s in E.SEASONS:
        named[s] = {}
        for r in csv.DictReader(open(BB_SHARES / f'pos-shares-{s}.csv', encoding='utf-8')):
            v = np.array([float(r[f'p_{p}']) for p in POSL])
            if v.sum() <= 0:
                continue
            v = v / v.sum()
            mp = float(r['MP'] or 0)
            named[s].setdefault(norm(r['name']), []).append((v, mp))
            if not r['playerId'] and r['bbref_id'] in alias:
                a = alias[r['bbref_id']]
                assert norm(r['name']) == norm(a['bbref_name']), (r['name'], a)
                SH[s][a['playerId']] = (v, mp)
    for a in alias.values():
        assert base['players'][a['playerId']]['name'] == a['card_name'], a
        assert a['playerId'] in SH['2025-26'], ('別名沒對到 2025-26', a)
    assert set(E.pids) == set(base['players'])
    PI, SRC, PRI = E.shares_for(E.pids, E.HGT, '2025-26', SH)
    P, _cap, info = E.build(E.FEAT, E.EPZ, PI, PI @ E.POSW)
    BON = E.LAM * E.SD * P * E.ramp
    cand = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(CAND_W1, encoding='utf-8'))}
    anames = {a['card_name'] for a in alias.values()}
    dif = {E.names[i]: float(BON[i] - cand[E.names[i]]) for i in range(E.N)}
    worst_other = max((abs(v), n) for n, v in dif.items() if n not in anames)
    assert worst_other[0] <= 0.02, worst_other
    fmap = {'reb': 'rebound', 'ob': 'orebPct', 'db': 'drebPct', 'con': 'con2_36'}
    cfg = json.loads(json.dumps(base['config']))
    cfg.pop('h')
    cfg['scales'] = {'reb': float(info['scales'][0]), 'con': float(info['scales'][1]), 'mix': float(info['scales'][2])}
    cfg['w1'] = {'alpha': E.ALPHA, 'hi': E.HI, 'posOrder': list(POSL), 'posWeight': [float(x) for x in E.POSW],
                 'mpos': {fmap[k]: [float(x) for x in v] for k, v in info['mpos'].items()},
                 'heightPrior': {str(h): [float(x) for x in PRI(float(h))] for h in range(70, 92)}, 'heightRange': [70, 91],
                 'heightPriorRule': '卡片 2025-26 BBRef MP≥200 的人（含別名），|身高−h|≤1 吋 π 平均（不足 15 人放寬到 ±2、±3…）；'
                                    '賽中身高四捨五入到整數吋、超出 70–91 取端點',
                 'mposPool': 'card 0.2.13a MIN>=500 且姓名在 stats-2025-26 唯一（同 epN），以 π 加權的 z_L 平均',
                 'shrinkMP': E.MPK}
    players = {}
    for i, pid in enumerate(E.pids):
        q = dict(base['players'][pid])
        q.update(pi=[float(x) for x in PI[i]], piSrc=SRC[i], cardBonus=float(BON[i]))
        players[pid] = q
    # 不在卡片的復出老將：最近一季 BBRef（先用 playerId，再用名字且該季唯一），MP<200 往身高帶收縮
    rv = json.load(open(RV_PRIOR, encoding='utf-8'))
    fallback = {}
    for p in rv['players']:
        pid = str(p['playerId'])
        if pid in players or not (p.get('rvMpg') is not None or p.get('returningVet')):
            continue
        for s in E.SEASONS[::-1]:
            hit = SH[s].get(pid)
            if hit is None:
                c = named[s].get(norm(p['name'])) or []
                hit = c[0] if len(c) == 1 else None
            if hit is not None:
                v, mp = hit
                pi = v if mp >= E.MPK else (mp * v + (E.MPK - mp) * PRI(float(p['heightInches']))) / E.MPK
                fallback[pid] = {'name': p['name'], 'pi': [float(x) for x in pi], 'piSrc': s if mp >= E.MPK else s + '+shrink', 'MP': mp}
                break
    worst = 0.0
    for i, pid in enumerate(E.pids):      # 純 Python 賽中公式核對
        q = players[pid]
        b = bonus_w1(cfg, q['pi'], q['cardRebound'], q['orebPct'], q['drebPct'], q['con2_36'], q['MIN'])['bonus']
        worst = max(worst, abs(b - BON[i]))
    assert worst <= 1e-9, worst
    doc = {'version': 'card／inseason 0.2.14b',
           'note': 'E-295 臂 W1：位置權重與位置平均都改 BBRef 2025-26 上場位置比例 π（c＝π_C＋0.243·π_PF；m_i＝π·m_p）；z 尺／sd／λ／ref／打折／混合規則同 0.2.14a 基底；'
                   'm_p、縮放、π、身高帶表凍結，整季不重算；players＝0.2.14a 凍結檔的 2025-26 原始特徵＋pi／piSrc＋cardBonus（card 0.2.14b mixBonus，未四捨五入）；'
                   'fallback＝不在卡片的復出老將最近一季 BBRef π；BBRef 手動別名 reports/card-0.2.14b/bbref-alias.csv',
           'config': cfg, 'epN': base['epN'], 'aliases': list(alias.values()),
           'reproduceCandMaxAbsExceptAlias': worst_other[0], 'reproduceCandWorstExceptAlias': worst_other[1],
           'aliasBonusChange': {n: {'cand': cand[n], 'new': cand[n] + dif[n]} for n in sorted(anames)},
           'reproducePythonMaxAbs': worst, 'shareSourceCounts': {k: SRC.count(k) for k in sorted(set(SRC))},
           'base_sha256': {'mix-pool-card0214a.json': sha(FROZEN_H)},
           'sources_sha256': {'mix-pool-card0214a.json': sha(FROZEN_H), 'card_0213a_ranking': sha(CARD0213A), 'card_0214bcand_ranking': sha(CAND_W1),
                              'E295_eval': sha(E295), 'E295_preregistration': sha(E295.parent / 'preregistration.md'), 'bbref-alias.csv': sha(ALIAS_W1),
                              'prior-2025-26-card0213a-rv.json': sha(RV_PRIOR),
                              **{f'pos-shares-{s}.csv': sha(BB_SHARES / f'pos-shares-{s}.csv') for s in E.SEASONS}},
           'players': players, 'fallback': fallback}
    FROZEN_W1.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"scales={cfg['scales']}\n候選卡差（別名以外）最大 {worst_other[0]:.5f}（{worst_other[1]}）；Python 重現 {worst:.2e}")
    print('別名 3 人', doc['aliasBonusChange'])
    print('fallback', {v['name']: (v['piSrc'], [round(x, 2) for x in v['pi']]) for v in fallback.values()})
    return doc


# ------------------------------------------------------------------ 公式
def _z(cfg, key, x):
    if x is None:
        return 0.0
    z = cfg['z'][key]
    return (x - z['mu']) / z['sd']


def _clip(cfg, x):
    lo, hi = cfg['clip']
    return min(max(x, lo), hi)


def _rebc(cfg, reb, ob, db):
    return _clip(cfg, (_z(cfg, 'rebound', reb) + _z(cfg, 'orebPct', ob) + _z(cfg, 'drebPct', db)) / 3)


def _conr(cfg, con):
    return _clip(cfg, _z(cfg, 'con2_36', con))


def bonus(cfg, reb, ob, db, con, minutes):
    rebc, conr = _rebc(cfg, reb, ob, db), _conr(cfg, con)
    s = cfg['scales']
    full = cfg['lambda'] * cfg['sd'] * (.5 * rebc * s['reb'] + .5 * conr * s['con']) * s['mix']
    ramp = min(1.0, minutes / cfg['rampMin'])
    return {'bonus': full * ramp, 'full': full, 'ramp': ramp, 'rebc': rebc, 'con': conr}


def _zh(cfg, pos, key, x):
    """0.2.14a：z_H＝z_L−(1−α)·m_pos；缺值記 α·m_pos。"""
    h = cfg['h']
    mp = h['mpos'][pos][key]
    if x is None:
        return h['alpha'] * mp
    return _z(cfg, key, x) - (1 - h['alpha']) * mp


def _zh_parts(cfg, pos, f):
    zr = (_zh(cfg, pos, 'rebound', f['rebound']) + _zh(cfg, pos, 'orebPct', f['orebPct']) + _zh(cfg, pos, 'drebPct', f['drebPct'])) / 3
    return zr, _zh(cfg, pos, 'con2_36', f['con2_36'])


def _soft(cfg, x):
    hi = cfg['h']['hi']
    return hi * math.tanh(max(x, 0.0) / hi)


def bonus_h(cfg, pos, reb, ob, db, con, minutes):
    w = cfg['h']['posWeight'].get(pos, 0.0)
    ramp = min(1.0, minutes / cfg['rampMin'])
    if w == 0.0 or pos not in cfg['h']['mpos']:
        return {'bonus': 0.0, 'full': 0.0, 'ramp': ramp, 'rebc': 0.0, 'con': 0.0, 'pos': pos, 'posW': 0.0}
    zr, zc = _zh_parts(cfg, pos, {'rebound': reb, 'orebPct': ob, 'drebPct': db, 'con2_36': con})
    rebc, conr = _soft(cfg, zr), _soft(cfg, zc)
    s = cfg['scales']
    full = cfg['lambda'] * cfg['sd'] * (.5 * rebc * s['reb'] + .5 * conr * s['con']) * s['mix'] * w
    return {'bonus': full * ramp, 'full': full, 'ramp': ramp, 'rebc': rebc, 'con': conr, 'pos': pos, 'posW': w}


def _zw1(cfg, mi, key, x):
    """0.2.14b：z_H＝z_L−(1−α)·m_i；缺值記 α·m_i（m_i＝π·m_p）。"""
    a = cfg['w1']['alpha']
    if x is None:
        return a * mi
    return _z(cfg, key, x) - (1 - a) * mi


def pi_for(frozen, pid, height):
    """π 與來源：卡片 players → 復出老將 fallback → 身高帶表（整數吋，超出取端點）。"""
    q = frozen['players'].get(str(pid))
    if q is not None and 'pi' in q:
        return q['pi'], q['piSrc']
    q = frozen.get('fallback', {}).get(str(pid))
    if q is not None:
        return q['pi'], 'fallback:' + q['piSrc']
    w = frozen['config']['w1']
    lo, hi = w['heightRange']
    h = min(max(int(round(float(height))), lo), hi)
    return w['heightPrior'][str(h)], f'height:{h}'


def bonus_w1(cfg, pi, reb, ob, db, con, minutes):
    w1 = cfg['w1']
    w = sum(p * q for p, q in zip(pi, w1['posWeight']))
    ramp = min(1.0, minutes / cfg['rampMin'])
    m = {k: sum(p * q for p, q in zip(pi, w1['mpos'][k])) for k in FEATS}
    zr = (_zw1(cfg, m['rebound'], 'rebound', reb) + _zw1(cfg, m['orebPct'], 'orebPct', ob) + _zw1(cfg, m['drebPct'], 'drebPct', db)) / 3
    zc = _zw1(cfg, m['con2_36'], 'con2_36', con)
    hi = w1['hi']
    rebc, conr = hi * math.tanh(max(zr, 0.0) / hi), hi * math.tanh(max(zc, 0.0) / hi)
    s = cfg['scales']
    full = cfg['lambda'] * cfg['sd'] * (.5 * rebc * s['reb'] + .5 * conr * s['con']) * s['mix'] * w
    return {'bonus': full * ramp, 'full': full, 'ramp': ramp, 'rebc': rebc, 'con': conr, 'posW': w}


def blend(past, cur, m, k):
    """R-169 box 規則：w＝m/(m+k)；某一邊沒有值就只用另一邊。"""
    if cur is None or m <= 0:
        return past
    if past is None:
        return cur
    w = m / (m + k)
    return w * cur + (1 - w) * past


# ------------------------------------------------------------------ 賽中
def frozen_path(h=False, w1=False):
    return FROZEN_W1 if (h and w1) else (FROZEN_H if h else FROZEN)


def load_frozen(h=False, w1=False):
    return json.load(open(frozen_path(h, w1), encoding='utf-8'))


def _rows(path):
    d = json.load(open(path, encoding='utf-8'))
    d = d.get('data', d)
    s = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return [dict(zip(s['headers'], r)) for r in s['rowSet']]


def current(data26=DATA26):
    """本季整季累計：{pid: {'orebPct','drebPct','con2_36'}}（缺檔＝沒有本季值）。路徑在 DATA26 底下，ovr_history 單日重算會導到截斷資料夾。"""
    out = {}
    ap, hp = Path(data26) / 'tracking' / 'advanced.json', Path(data26) / 'tracking' / 'hustle.json'
    if ap.exists():
        for r in _rows(ap):
            if (r.get('MIN') or 0) > 0:
                out.setdefault(int(r['PLAYER_ID']), {}).update(orebPct=r['OREB_PCT'], drebPct=r['DREB_PCT'])
    if hp.exists():
        acc = {}
        for r in _rows(hp):
            a = acc.setdefault(int(r['PLAYER_ID']), [0.0, 0.0])
            a[0] += r['MIN'] or 0
            a[1] += r['CONTESTED_SHOTS_2PT'] or 0
        for pid, (m, c) in acc.items():
            if m > 0:
                out.setdefault(pid, {})['con2_36'] = c / m * 36
    return out


def live_bonus(frozen, pid, rebound, cur_min, cur, pos=None, height=None):
    """pos 只在 0.2.14a 凍結檔（config 有 'h'）用到；height 只在 0.2.14b（config 有 'w1'、π 查不到時查身高帶）用到。"""
    cfg = frozen['config']
    past = frozen['players'].get(str(pid)) or {}
    c = cur.get(int(pid)) or {}
    k = cfg['blendK']
    ob = blend(past.get('orebPct'), c.get('orebPct'), cur_min, k)
    db = blend(past.get('drebPct'), c.get('drebPct'), cur_min, k)
    con = blend(past.get('con2_36'), c.get('con2_36'), cur_min, k)
    mins = (past.get('MIN') or 0.0) + cur_min
    if 'w1' in cfg:
        pi, src = pi_for(frozen, pid, height)
        out = bonus_w1(cfg, pi, rebound, ob, db, con, mins)
        out.update(pi=[round(x, 4) for x in pi], piSrc=src)
    else:
        out = bonus_h(cfg, pos, rebound, ob, db, con, mins) if 'h' in cfg else bonus(cfg, rebound, ob, db, con, mins)
    out.update(orebPct=ob, drebPct=db, con2_36=con, MIN=mins, w=(cur_min / (cur_min + k) if cur_min > 0 else 0.0),
               cardBonus=past.get('cardBonus', 0.0))
    return out


def apply(rows, r1, data26=DATA26, h=False, w1=False):
    """rows＝寫 ranking.csv 前的合併列（老將＋新秀）。原地改 ovr／_ovr／lastOVR／dOVR／formalOVR，加 mixBonus；回傳 {pid: 明細}。
    lastOVR 基準（本季 0 場）加正式卡（h：card 0.2.14a；否則 card 0.2.14）的 mixBonus（卡外的人 0），dOVR 只反映本季造成的變化。
    h＝True（0.2.14a）時位置取 rows 的 pos 欄；h＝w1＝True（0.2.14b）時位置取凍結 π，查不到用 rows 的 heightInches 查身高帶。"""
    w1 = bool(h and w1)
    frozen = load_frozen(h, w1)
    cur = current(data26)
    card14 = {}
    for r in csv.DictReader(open(CARD14B if w1 else (CARD14A if h else CARD14), encoding='utf-8')):
        card14.setdefault(r['name'], float(r['ovr']))
    detail = {}
    for r in rows:
        pid = int(r['playerId'])
        m = float(r['MIN26'] or 0)
        if w1:
            d = live_bonus(frozen, pid, float(r['rebound']), m, cur, height=r.get('heightInches'))
        else:
            d = live_bonus(frozen, pid, float(r['rebound']), m, cur, r.get('pos')) if h else live_bonus(frozen, pid, float(r['rebound']), m, cur)
        b, b0 = d['bonus'], d['cardBonus']
        r['_ovr'] = r['_ovr'] + b
        r['ovr'] = r1(r['_ovr'])
        if r.get('lastOVR') not in ('', None):
            r['lastOVR'] = r1(float(r['lastOVR']) + b0)
        if r.get('dOVR') not in ('', None):
            r['dOVR'] = round(float(r['dOVR']) + b - b0, 2)
        if r.get('formalOVR') not in ('', None):
            r['formalOVR'] = card14.get(r['name'], r['formalOVR'])
        r['mixBonus'] = round(b, 3)
        detail[str(pid)] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
    return detail


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['freeze']:
        freeze()
    elif sys.argv[1:] == ['freeze_h']:
        freeze_h()
    elif sys.argv[1:] == ['freeze_w1']:
        freeze_w1()
    else:
        raise SystemExit(__doc__)
