"""球隊評分的梯度對手（R-158，E-224 B5）所需的 Ladder_k 與候選球員表。規則照 E-224 §3 的機械版本，沒有可調參數。
來源：上一季正式卡 reports/<card>/ranking.csv（ovr、pos、MIN；沒有 playerId，靠球員名正規化 nn() 對到 box score 的 personId）
＋ 上一季常規賽 box score（gameId 前綴 002）。球員歸到出賽分鐘最多的球隊（同分取較小 teamId）。
Ladder_k＝30 隊「MIN 排名第 k 的球員 OVR」之平均（每隊取前 9）。候選＝MIN≥500 的球員。
卡名對不到 box score 球員、或同一個正規化名對到多個 personId 的人不進候選也不進 Ladder，列在 unmatched／ambiguous。
輸出 data/team-ratings-gradient-ladder.json（git add -f）。換季或換卡時重跑：
  python -I -X utf8 scripts/build_gradient_ladder.py [--card card-0.2.12c] [--box-dir data/season-source/dnp-2025-26-raw] [--prefix 00225]"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/team-ratings-gradient-ladder.json'
MINS = [36, 36, 34, 32, 30, 26, 22, 14, 10]
MIN_CAND = 500


def nn(s: str) -> str:
    """球員名正規化；與 team_ratings_daily.nn 同規則（NFKD 去重音、拿掉 Jr/Sr/II/III/IV/V、只留 a-z）。"""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', s)
    return re.sub(r'[^a-z]', '', s)


def minutes(s: str) -> float:
    m = re.match(r'PT(\d+)M([\d.]+)S', s or '')
    return int(m.group(1)) + float(m.group(2)) / 60 if m else 0.0


def read_boxes(box_dir: Path, prefix: str) -> tuple:
    """回傳 (games, team_minutes{pid:{teamId:min}}, names{pid:name})。"""
    tm = collections.defaultdict(lambda: collections.defaultdict(float)); names = {}; ng = 0
    for f in sorted(box_dir.glob(f'boxscore_{prefix}*.json.gz')):
        if not f.name.endswith('.json.gz'):
            continue
        bx = json.loads(gzip.open(f, 'rt', encoding='utf-8').read())['game']; ng += 1
        for side in ('homeTeam', 'awayTeam'):
            t = bx[side]
            for p in t['players']:
                tm[p['personId']][t['teamId']] += minutes(p['statistics']['minutes'])
                names.setdefault(p['personId'], p.get('name') or '')
    return ng, tm, names


def build(card_rows: list, tm: dict, names: dict) -> dict:
    by_name = collections.defaultdict(set)
    for pid, nm in names.items():
        by_name[nn(nm)].add(pid)
    team_of = {pid: max(d.items(), key=lambda kv: (kv[1], -kv[0]))[0] for pid, d in tm.items()}
    card, unmatched, ambiguous = [], [], []
    for r in card_rows:
        pids = by_name.get(nn(r['name']), set())
        if not pids:
            unmatched.append(r['name']); continue
        if len(pids) > 1:
            ambiguous.append(r['name']); continue
        pid = next(iter(pids))
        card.append(dict(pid=int(pid), name=r['name'], pos=r['pos'], ovr=float(r['ovr']), min=float(r['MIN'])))
    seen = set()
    for p in card:   # 卡上同名（正規化後）重複的人也算 ambiguous
        if p['pid'] in seen:
            ambiguous.append(p['name'])
        seen.add(p['pid'])
    card = [p for p in card if p['name'] not in ambiguous]
    byteam = collections.defaultdict(list)
    for p in card:
        byteam[team_of[p['pid']]].append(p)
    rows = []
    for t, ps in sorted(byteam.items()):
        top = sorted(ps, key=lambda p: (-p['min'], p['pid']))[:9]
        if len(top) < 9:
            raise SystemExit(f'team {t} 只有 {len(top)} 人對到卡，無法建梯度')
        rows.append([p['ovr'] for p in top])
    ladder = [sum(r[k] for r in rows) / len(rows) for k in range(9)]
    cands = sorted([p for p in card if p['min'] >= MIN_CAND], key=lambda p: p['pid'])
    return dict(ladder=ladder, flat=sum(m * l for m, l in zip(MINS, ladder)) / 240, mins=MINS, teams=len(rows),
                candidates=cands, unmatched=sorted(unmatched), ambiguous=sorted(set(ambiguous)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--card', default='card-0.2.12c')
    ap.add_argument('--box-dir', default='data/season-source/dnp-2025-26-raw')
    ap.add_argument('--prefix', default='00225')
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args(argv)
    rows = list(csv.DictReader(open(ROOT / 'reports' / a.card / 'ranking.csv', encoding='utf-8')))
    ng, tm, names = read_boxes(ROOT / a.box_dir, a.prefix)
    out = build(rows, tm, names)
    out.update(card=a.card, boxDir=a.box_dir, prefix=a.prefix, games=ng)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('games', ng, 'teams', out['teams'], 'ladder', [round(x, 2) for x in out['ladder']], 'flat', round(out['flat'], 2),
          'cands', len(out['candidates']), 'unmatched', len(out['unmatched']), 'ambiguous', len(out['ambiguous']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
