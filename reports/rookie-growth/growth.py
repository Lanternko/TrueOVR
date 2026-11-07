"""新秀 OVR 隨已打場數的變化（只報告、不調參；使用者 2026-10-30「新秀有沒有隨著好表現提升 OVR，做成長曲線」）。
兩群：
  2025 屆：E-116 回測同一批 37 人（2025-26 MIN>=500、有 card 0.2.7 卡），用球隊前 N 場（他沒上場的場次不算）算新秀版 OVR，對照季末 card 0.2.7。
  2026 屆：現行 live（inseason 0.2.7＋E-116 新秀先驗），用 2026-27 前 N 場（N=0..已打場數）。
兩條線：e116＝上線的算法（起點＋自己數據加權）；own＝只看自己的數據（w=1）。
用法：python -I -X utf8 growth.py  → growth.csv
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E116 = HERE.parent / 'E116-rookie-prior'
LIVE = HERE.parent / 'ovr-inseason-2026-27' / 'live'
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(E116))
import build_rookie_prior as BR            # noqa: E402
import run_c4_live_rookie as RW            # noqa: E402

NS25 = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 70, 82)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    fit = json.load(open(E116 / 'fit.json', encoding='utf-8'))
    ns = RW.load_ns()
    C, F, IC, SA, V2 = ns['C'], ns['F'], ns['IC'], ns['SA'], ns['V2']
    sd26, mp = ns['setup']()
    PRIOR = ns['PRIOR']
    rel = V2.load_reliability()
    pw = ns['PW'].for_start(C, 'S*')
    anc, r_repl = ns['e064_anchors']()
    out = []

    # ---- 2025 屆（同 E-116 backtest.py 的人群與資料組法）
    sd25 = IC.load_target_season()
    bio25 = {int(r['PLAYER_ID']): r for r in SA.result_set(ns['BIO25'])}
    dep25 = {int(r['playerId']): r for s in ns['load_json'](IC.DEPENDENCE)['seasons']
             if s['season'] == PRIOR for r in s['rows']}
    box = {p: b for p, b in sd25['box'].items() if p in bio25}
    sdm = {'season': PRIOR, 'box': box, 'bio': bio25, 'dep': dep25, 'ff': {}, 'v3': {}, 'fed': {},
           'shots': sd25['shots'], 'teamRows': sd25['teamRows']}
    try:
        mapping = C.mapping_for('2024-25')
        assert mapping['priors']
    except Exception:
        mapping = mp['mapping']
    key = {}
    for r in C.load_csv(ns['FORMAL_RANKING']):
        key.setdefault(r['name'], r)
    prior_ids = set(F.load_prior(PRIOR)[0])
    LO, HI = fit['clip']
    pop = []
    for pid, b in sorted(bio25.items()):
        if str(b.get('DRAFT_YEAR')) != '2025' or pid not in prior_ids:
            continue
        bx = box.get(pid)
        mins = sum(r['MIN'] for r in bx['rows']) if bx else 0.0
        if mins < 500 or b['PLAYER_NAME'] not in key:
            continue
        pick = BR.pick_of(b)
        h = float(b['PLAYER_HEIGHT_INCHES'])
        pos = BR.height_pos(h)
        x = BR.design(pick, pos)
        x0, k = {}, {}
        for a in BR.ABIL:
            f = fit['abilities'][a]
            v = f['b0'] + f['b1_lnPick'] * x[1] + f['gF'] * x[2] + f['gC'] * x[3]
            x0[a] = min(max(v, LO), HI)
            if f['k'] is not None:
                k[a] = f['k']
        pop.append({'playerId': pid, 'name': b['PLAYER_NAME'], 'pick': pick, 'pos': pos, 'heightInches': h,
                    'mpg0': fit['medians']['mpg0'], 'usg0': 0.0, 'x0': x0, 'k': k,
                    'gp': len(bx['rows']), 'ans': float(key[b['PLAYER_NAME']]['ovr'])})
    for p in pop:
        ev = RW.eval_rookie(ns, pw, anc, r_repl, p, None, 'e116', rel)
        out.append({'class': 2025, 'name': p['name'], 'pick': p['pick'], 'pos': p['pos'], 'N': 0, 'games': 0,
                    'ovr_e116': round(ev['ovr'], 2), 'ovr_own': '', 'seasonEnd': round(p['ans'], 1)})
    for n in NS25:
        wins = RW.rookie_windows(ns, sdm, mapping, pop, n)
        for p in pop:
            rec = wins.get(p['playerId'])
            if rec is None:
                continue
            row = {'class': 2025, 'name': p['name'], 'pick': p['pick'], 'pos': p['pos'], 'N': n, 'games': rec['GP'],
                   'seasonEnd': round(p['ans'], 1)}
            for arm in ('e116', 'own'):
                row['ovr_' + arm] = round(RW.eval_rookie(ns, pw, anc, r_repl, p, rec, arm, rel)['ovr'], 2)
            out.append(row)
        print('2025 N', n, flush=True)

    # ---- 2026 屆（live）
    rookies = json.load(open(LIVE / 'rookie-prior-2026.json', encoding='utf-8'))['players']
    rookies = [r for r in rookies if r['playerId'] not in prior_ids]
    gp = {r['playerId']: len(sd26['box'][r['playerId']]['rows']) if sd26['box'].get(r['playerId']) else 0 for r in rookies}
    for r in rookies:
        ev = RW.eval_rookie(ns, pw, anc, r_repl, r, None, 'e116', rel)
        out.append({'class': 2026, 'name': r['name'], 'pick': r['pick'], 'pos': r['pos'], 'N': 0, 'games': 0,
                    'ovr_e116': round(ev['ovr'], 2), 'ovr_own': '', 'seasonEnd': ''})
    m26 = C.mapping_for(PRIOR)
    for n in range(1, max(gp.values()) + 1):
        wins = RW.rookie_windows(ns, sd26, m26, rookies, n)
        for r in rookies:
            rec = wins.get(r['playerId'])
            if rec is None:
                continue
            row = {'class': 2026, 'name': r['name'], 'pick': r['pick'], 'pos': r['pos'], 'N': n, 'games': rec['GP'],
                   'seasonEnd': ''}
            for arm in ('e116', 'own'):
                row['ovr_' + arm] = round(RW.eval_rookie(ns, pw, anc, r_repl, r, rec, arm, rel)['ovr'], 2)
            out.append(row)
    cols = ['class', 'name', 'pick', 'pos', 'N', 'games', 'ovr_e116', 'ovr_own', 'seasonEnd']
    with open(HERE / 'growth.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(out)
    print('rows', len(out), '2025 人數', len(pop), '2026 人數', len(rookies))


if __name__ == '__main__':
    main()
