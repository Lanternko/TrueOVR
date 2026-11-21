import sys, json
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E208-rookie-start-recheck')
sys.stdout.reconfigure(encoding='utf-8')
import e208_lib as L
R = L.ROOT
live = R / 'reports/ovr-inseason-2026-27/live'
files = {
 'E141 rookie-players.csv': R / 'reports/E141-rookie-start-shift/rookie-players.csv',
 'E116 fit.json': R / 'reports/E116-rookie-prior/fit.json',
 'rookie-prior-2026.json (live, HEAD 內容)': live / 'rookie-prior-2026.json',
 'CURRENT.json': live / 'CURRENT.json',
 'card-0.2.12b ranking.csv': R / 'reports/card-0.2.12b/ranking.csv',
 'live 2026-10-31 rookies-detail.json': live / '2026-10-31/rookies-detail.json',
 'live 2026-10-31 ranking.csv': live / '2026-10-31/ranking.csv',
 'live 2026-10-31 meta.json': live / '2026-10-31/meta.json',
 '2026-27 player-games.json': R / 'data/defense-seventh/2026-27/player-games.json',
 'benchmark-source bio.json': R / 'data/benchmark-source/bio.json',
 'usage-2025-26-card0212-tov.json (已搬 _retired)': live / '_retired/usage-2025-26-card0212-tov.json',
 'prior-2025-26-card0212-tov.json (已搬 _retired)': live / '_retired/prior-2025-26-card0212-tov.json',
}
for s in L.CRJ_SEASONS:
    files[f'crJ-{s}.csv.gz'] = L.SD.I10 / 'work/history' / f'crJ-{s}.csv.gz'
out = {k: (L.sha256(v) if v.exists() else 'MISSING ' + str(v)) for k, v in files.items()}
out['gitHead'] = L.HEAD_SHA
out['pinnedFromHead'] = ['run_c4_live.py', 'run_c4_live_rookie.py', 'tov_live.py', 'window8.py']
json.dump(out, open(L.HERE / 'G2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in out.items(): print(k, v if isinstance(v, str) else v)
