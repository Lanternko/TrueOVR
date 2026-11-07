"""raw/<gameId>_<pid>.json → player_game.csv（playerId, gameId, half, FGA, FGM, sumXFG, FG3A, FG3M, sumXFG3）。
FGA/FGM/sumXFG 一律由 shotList 逐球加總（shotType 含 '3PT' 者算三分）。half：int(gameId)%2==0 → A，否則 B（同 E-081）。
另寫 build_check.json：error 檔數、shots 欄位與 shotList 筆數不符的場次數。"""
import csv, glob, json, os
here = os.path.dirname(os.path.abspath(__file__))
rows, errs, mism, tot = [], 0, 0, 0
for f in sorted(glob.glob(os.path.join(here, 'raw', '*.json'))):
    o = json.load(open(f, encoding='utf-8'))
    if 'error' in o:
        errs += 1; continue
    sl = o['shotList']; tot += 1
    if o.get('shots') is not None and o['shots'] != len(sl): mism += 1
    t3 = [s for s in sl if '3PT' in (s['shotType'] or '')]
    rows.append([o['playerId'], o['gameId'], 'A' if int(o['gameId']) % 2 == 0 else 'B',
                 len(sl), sum(s['success'] for s in sl), round(sum(s['shotQuality'] for s in sl), 4),
                 len(t3), sum(s['success'] for s in t3), round(sum(s['shotQuality'] for s in t3), 4)])
with open(os.path.join(here, 'player_game.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh); w.writerow('playerId,gameId,half,FGA,FGM,sumXFG,FG3A,FG3M,sumXFG3'.split(',')); w.writerows(rows)
json.dump({'files': tot + errs, 'ok': tot, 'error_files': errs, 'shots_vs_shotList_mismatch': mism}, open(os.path.join(here, 'build_check.json'), 'w'))
print(tot, errs, mism)
