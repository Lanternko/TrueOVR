"""E-141 只報告項：2026 屆新秀在各候選下的開季 OVR、目前 OVR 與名次。
目前資料用 live 設定（ns['setup']）＋全部已賽場次視窗；老將名次取自最新已發布的 ranking.csv（不重跑 live main，不寫 live 檔）。
近似處：未重擬合 live 防守加成（vet_defense／live_bonus 在 main 內），所以 B0r 的目前 OVR 與已發布值會有小差，下面一併列出。"""
import sys
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E141-rookie-start-shift')
import json, math, csv
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE)); sys.path.insert(0, str(ROOT / 'reports/E121-rookie-scale'))
import run_c4_live_rookie as RW
import build_2k_start as B2
import rookie_defense as RD

CANDS = {'B0r': -5.0, 'S25': -2.5, 'S0': 0.0, 'S+25': 2.5}
fit2k = json.load(open(ROOT / 'reports/rookie-growth/twok-by-pick.json', encoding='utf-8'))['fitRecent3']
q, _ = B2.make_q()
base = json.load(open(LIVE / 'rookie-prior-2026-e116.json', encoding='utf-8'))['players']
ns = RW.load_ns(); ns['setup']()
rel = ns['V2'].load_reliability(); pw = ns['PW'].for_start(ns['C'], 'S*')
anc, r_repl = ns['e064_anchors']()
IC, C = ns['IC'], ns['C']
sd26 = IC.load_target_season()
wins = RW.rookie_windows(ns, sd26, C.mapping_for(ns['PRIOR']), base, ns['ALL_N'])
dfns = RD.inseason('2026-27', {r['playerId']: r['pos'] for r in base})
pubs = sorted(p for p in LIVE.glob('2026-*') if p.is_dir() and (p / 'ranking.csv').exists() and (p / 'rookies-detail.json').exists())
pub = pubs[-1]
rank_rows = list(csv.DictReader(open(pub / 'ranking.csv', encoding='utf-8')))
pub_rk = {r['playerId']: r for r in json.load(open(pub / 'rookies-detail.json', encoding='utf-8'))}
rk_ids = {str(r['playerId']) for r in base}
vets = [r for r in rank_rows if r['playerId'] not in rk_ids]
vet_cur = [float(r['ovr']) for r in vets]
vet_last = [float(r['lastOVR']) for r in vets if r.get('lastOVR') not in ('', None)]
out = []
for rk in base:
    pid = rk['playerId']
    gp = len(sd26['box'][pid]['rows']) if pid in sd26['box'] else 0
    rec = wins.get(pid)
    row = {'playerId': pid, 'name': rk['name'], 'pick': rk['pick'], 'N': gp, 'cand': {}}
    for c, sh in CANDS.items():
        T = q(fit2k['a'] + fit2k['b_lnPick'] * math.log(rk['pick'])) + sh
        d, _ = B2.solve(ns, pw, anc, r_repl, rel, rk, T)
        r2 = dict(rk, x0=B2.shifted(rk['x0'], d))
        op = RW.eval_rookie(ns, pw, anc, r_repl, r2, None, 'e116', rel)['ovr']
        cu = RW.eval_rookie(ns, pw, anc, r_repl, r2, rec, 'e116', rel, dfns.get(pid) if gp > 0 else None)['ovr']
        row['cand'][c] = {'T': T, 'delta': d, 'open': op, 'cur': cu,
                          'openRank': 1 + sum(v > op for v in vet_last), 'curRank': (1 + sum(v > cu for v in vet_cur)) if gp > 0 else None}
    p = pub_rk.get(pid) or pub_rk.get(str(pid))
    row['published'] = {'ovr': p['ovr'], 'lastOVR': p['lastOVR'], 'rank': p['rank'], 'N': p['N']} if p else None
    out.append(row)
res = {'publishedDir': pub.name, 'nRookies': len(out), 'players': out,
       'approx': 'live 防守加成未重擬合；老將名次取已發布 ranking.csv；開季名次對老將 lastOVR（先驗卡）'}
dif = [abs(r['cand']['B0r']['cur'] - r['published']['ovr']) for r in out if r['published'] and r['N'] > 0]
res['B0rCurrentVsPublished_maxAbsDiff'] = max(dif) if dif else None
res['B0rOpenVsPublishedLast_maxAbsDiff'] = max(abs(r['cand']['B0r']['open'] - r['published']['lastOVR']) for r in out if r['published'])
json.dump(res, open(HERE / 'class2026.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(pub.name, len(out), res['B0rCurrentVsPublished_maxAbsDiff'], res['B0rOpenVsPublishedLast_maxAbsDiff'])
for r in sorted(out, key=lambda r: r['pick'])[:8]:
    print(r['name'], r['pick'], r['N'], {c: (round(v['open'], 1), round(v['cur'], 1), v['curRank']) for c, v in r['cand'].items()}, r['published'])
