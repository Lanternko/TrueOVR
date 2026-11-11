"""E-116 §3 回測（seed 20261116；結果只報告，不回頭調參，L-026）。
對象：bio DRAFT_YEAR=='2025'、card 0.2.7 有卡（prior-2025-26-card027.json）、2025-26 MIN>=500。
N=5/10/20：用每人 2025-26 前 N 場當視窗；三臂：E-116（k=σ²/τ²）、frozen（k=50·nRef）、own（w=1）。
答案：card 0.2.7 季末 OVR（D6，預註冊 §3 末條的退路）。用法：python -I -X utf8 backtest.py
"""
import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent / 'ovr-inseason-2026-27' / 'live'
sys.path.insert(0, str(LIVE))
import build_rookie_prior as BR            # noqa: E402
import run_c4_live_rookie as RW            # noqa: E402

SEED = 20261116
NS = (5, 10, 20)
ARMS = ('e116', 'frozen', 'own')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    fit = json.load(open(HERE / 'fit.json', encoding='utf-8'))
    ns = RW.load_ns()
    C, F, IC, SA, V2 = ns['C'], ns['F'], ns['IC'], ns['SA'], ns['V2']
    sd26, mp = ns['setup']()
    PRIOR = ns['PRIOR']
    # 2025-26 資料（同 setup() 的 sdm 組法）
    sd25 = IC.load_target_season()
    bio25 = {int(r['PLAYER_ID']): r for r in SA.result_set(ns['BIO25'])}
    dep25 = {int(r['playerId']): r for s in ns['load_json'](IC.DEPENDENCE)['seasons']
             if s['season'] == PRIOR for r in s['rows']}
    box = {p: b for p, b in sd25['box'].items() if p in bio25}
    sdm = {'season': PRIOR, 'box': box, 'bio': bio25, 'dep': dep25, 'ff': {}, 'v3': {}, 'fed': {},
           'shots': sd25['shots'], 'teamRows': sd25['teamRows']}
    mapping_note = '2024-25'
    try:
        mapping = C.mapping_for('2024-25')
        assert mapping['priors']
    except Exception as e:                                    # D8：退路
        mapping = mp['mapping']
        mapping_note = f'2025-26（退路 D8：{type(e).__name__}）'
    # 答案
    key = {}
    cards_rows = C.load_csv(ns['FORMAL_RANKING'])
    for r in cards_rows:
        key.setdefault(r['name'], r)
    prior_cards, _ = F.load_prior(PRIOR)
    prior_ids = set(prior_cards)
    rel = V2.load_reliability()
    pw = ns['PW'].for_start(C, 'S*')
    anc, r_repl = ns['e064_anchors']()
    LO, HI = fit['clip']
    meds = fit['medians']
    pop = []
    for pid, b in sorted(bio25.items()):
        if str(b.get('DRAFT_YEAR')) != '2025' or pid not in prior_ids:
            continue
        bx = box.get(pid)
        mins = sum(r['MIN'] for r in bx['rows']) if bx else 0.0
        if mins < 500:
            continue
        name = b['PLAYER_NAME']
        if name not in key:
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
        pop.append({'playerId': pid, 'name': name, 'team': b['TEAM_ABBREVIATION'], 'pick': pick, 'pos': pos,
                    'heightInches': h, 'mpg0': meds['mpg0'], 'usg0': 0.0, 'x0': x0, 'k': k,
                    'min': mins, 'gp': len(bx['rows']), 'ans': float(key[name]['ovr']), 'card': key[name]})
    # 尺度核對
    scale = {}
    for a in BR.ABIL:
        d = [float(p['card'][a]) - p['x0'][a] for p in pop if p['card'].get(a) not in (None, '')]
        scale[a] = {'n': len(d), 'mean': statistics.fmean(d), 'median': statistics.median(d)} if d else None
    # 回測
    base = {p['playerId']: RW.eval_rookie(ns, pw, anc, r_repl, p, None, 'e116', rel) for p in pop}
    detail = []
    err = {(n, a): [] for n in NS for a in ARMS}
    err0 = []
    for p in pop:
        err0.append(abs(base[p['playerId']]['ovr'] - p['ans']))
    for n in NS:
        wins = RW.rookie_windows(ns, sdm, mapping, pop, n)
        for p in pop:
            rec = wins.get(p['playerId'])
            row = {'name': p['name'], 'pick': p['pick'], 'pos': p['pos'], 'N': n,
                   'gamesInWindow': rec['GP'] if rec else 0, 'ans': round(p['ans'], 1),
                   'ovr_x0': round(base[p['playerId']]['ovr'], 2)}
            for a in ARMS:
                ev = RW.eval_rookie(ns, pw, anc, r_repl, p, rec, a, rel)
                row['ovr_' + a] = round(ev['ovr'], 2)
                err[(n, a)].append(abs(ev['ovr'] - p['ans']))
            detail.append(row)
    mae = {f'N{n}': {a: statistics.fmean(err[(n, a)]) for a in ARMS} for n in NS}
    med = {f'N{n}': {a: statistics.median(err[(n, a)]) for a in ARMS} for n in NS}
    res = {'seed': SEED, 'nPlayers': len(pop), 'mappingForWindows': mapping_note,
           'mae': mae, 'medianAbsErr': med, 'maeStartOnly(x0,no data)': statistics.fmean(err0),
           'answerKey': 'card 0.2.7 季末 OVR（D6）', 'scaleCheck': scale,
           'e116_vs_own_N10': mae['N10']['e116'] - mae['N10']['own'],
           'flag_e116_worse_than_own_by_gt1_at_N10': (mae['N10']['e116'] - mae['N10']['own']) > 1.0}
    json.dump(res, open(HERE / 'backtest-results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cols = list(detail[0])
    with open(HERE / 'backtest-detail.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(detail)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
