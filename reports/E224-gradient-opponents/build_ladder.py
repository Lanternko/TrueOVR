"""E-224 §3 的 Ladder_k 與候選球員表（機械規則，無可調參數）。
球隊歸屬：OVR 來源卡的賽季（2425→2023-24，2526→2024-25）常規賽 box score（gameId 前綴 002），
球員歸到該季出賽分鐘最多的球隊（交易球員的決定規則；卡上沒有球隊欄位）。
Ladder_k＝30 隊「MIN_season 排名第 k 的球員 OVR」之平均（每隊取 MIN_season 前 9，MIN_season 取自卡）。
輸出 work/ladder-<key>.json：ladder[9]、flat、candidates（各位置 MIN_season≥500 的球員：pid, ovr, min, pos）。
用法：python -I reports/E224-gradient-opponents/build_ladder.py"""
import csv, glob, gzip, json, re, collections, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
MINS = [36, 36, 34, 32, 30, 26, 22, 14, 10]
CFG = {'2425': dict(card='2023-24-v5-min.csv', raw='dnp-2023-24-raw', prefix='00223'),
       '2526': dict(card='2024-25-v5-min.csv', raw='dnp-2024-25-raw', prefix='00224')}

def mins(s):
    m = re.match(r'PT(\d+)M([\d.]+)S', s or '')
    return int(m.group(1)) + float(m.group(2)) / 60 if m else 0.0

out_all = {}
for key, c in CFG.items():
    card = {}
    for r in csv.DictReader(open(ROOT / 'reports/ovr-inseason-2026-27/v5/cards' / c['card'], encoding='utf-8')):
        card[int(r['playerId'])] = dict(pid=int(r['playerId']), name=r['name'], pos=r['pos'], ovr=float(r['ovr']), min=float(r['MIN_season']))
    tm = collections.defaultdict(lambda: collections.defaultdict(float)); ng = 0
    for f in sorted(glob.glob(str(ROOT / 'data/season-source' / c['raw'] / 'boxscore_*.json.gz'))):
        if not pathlib.Path(f).name.startswith('boxscore_' + c['prefix']): continue
        bx = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']; ng += 1
        for side in ('homeTeam', 'awayTeam'):
            t = bx[side]
            for p in t['players']:
                tm[p['personId']][t['teamId']] += mins(p['statistics']['minutes'])
    team_of = {pid: max(d.items(), key=lambda kv: (kv[1], -kv[0]))[0] for pid, d in tm.items()}   # 分鐘最多；同分取較小 teamId
    byteam = collections.defaultdict(list); nobox = []
    for pid, p in card.items():
        if pid in team_of: byteam[team_of[pid]].append(p)
        else: nobox.append(pid)
    ladder_rows = []
    for t, ps in sorted(byteam.items()):
        top = sorted(ps, key=lambda p: (-p['min'], p['pid']))[:9]
        assert len(top) == 9, (key, t, len(top))
        ladder_rows.append([p['ovr'] for p in top])
    nt = len(ladder_rows)
    ladder = [sum(r[k] for r in ladder_rows) / nt for k in range(9)]
    flat = sum(m * l for m, l in zip(MINS, ladder)) / 240
    cands = sorted([p for p in card.values() if p['min'] >= 500], key=lambda p: p['pid'])
    out = dict(key=key, card=c['card'], games=ng, teams=nt, ladder=ladder, flat=flat, mins=MINS, candidates=cands, no_box_players=nobox)
    json.dump(out, open(HERE / 'work' / f'ladder-{key}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(key, 'games', ng, 'teams', nt, 'ladder', [round(x, 2) for x in ladder], 'flat', round(flat, 2), 'cands', len(cands), 'no_box', len(nobox))
