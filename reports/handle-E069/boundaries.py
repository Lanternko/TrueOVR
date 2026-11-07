"""E-069：每季上/下半季日期邊界。H1 場數規則同 prepare_pergame（前 round(574/1230*N) 場，依 (date,gid)；2025-26 用 trainGames）。
tracking 只能用日期切，所以最終定義 H1 = 日期 <= D1（D1=規則 H1 最後一場的日期）。PBP 同規則。
用法：python reports/handle-E069/boundaries.py"""
import json, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
from lib import H1_FRACTION, SIGNALS, TEST_SEASON, SEVENTH  # noqa
from prepare_pergame import rows_of, sources  # noqa

SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
train = set(json.loads(SIGNALS.read_text(encoding='utf-8'))['trainGames'])
out = {}
games = {}
for s in SEASONS:
    pg, tg, _ = sources(s)
    pl, tm = rows_of(pg), rows_of(tg)
    by = defaultdict(list)
    for r in tm:
        by[r['GAME_ID']].append(r)
    dates = {r['GAME_ID']: r['GAME_DATE'][:10] for r in pl}
    gids = sorted((g for g in by if len(by[g]) == 2), key=lambda g: (dates.get(g, ''), g))
    h1 = set(gids[:round(H1_FRACTION * len(gids))])   # 預註冊 §3.1：依日期前 574/1230 場（2025-26 也用此規則；trainGames 是每隊前 41 場，不是日期前綴）
    d1 = max(dates[g] for g in h1)
    first, last = dates[gids[0]], dates[gids[-1]]
    same = [g for g in gids if dates[g] == d1]
    h1_by_date = [g for g in gids if dates[g] <= d1]
    d2 = (date.fromisoformat(d1) + timedelta(days=1)).isoformat()
    out[s] = {'nGames': len(gids), 'nH1Rule': len(h1), 'seasonFirst': first, 'seasonLast': last, 'D1': d1, 'H2From': d2,
              'nH1ByDate': len(h1_by_date), 'nH2ByDate': len(gids) - len(h1_by_date), 'gamesOnD1': len(same),
              'gamesOnD1InRuleH2': len([g for g in same if g not in h1])}
    games[s] = {g: ('1' if dates[g] <= d1 else '2') + dates[g] for g in gids}
    print(s, out[s])
(HERE / 'boundaries.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
(HERE / 'game-halves.json').write_text(json.dumps(games, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
