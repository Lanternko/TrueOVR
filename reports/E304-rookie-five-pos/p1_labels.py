"""E-304 P1：新秀前 N 場的位置份額 vs 整季老將規則標籤（TV 距離）。純 box＋bio，無子程序。
用法：python -I -X utf8 p1_labels.py  -> p1.json
"""
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
POS = ['PG', 'SG', 'SF', 'PF', 'C']
SEASONS = ['2022-23', '2023-24', '2024-25', '2026-27']   # 2026-27 只輸出標籤給 G-live，不進 P1
P1_SEASONS = SEASONS[:3]
KAPPA = 5


def h5(h):
    return 'PG' if h <= 75 else 'SG' if h <= 78 else 'SF' if h <= 80 else 'PF' if h <= 82 else 'C'


def secs(m):
    x = re.match(r'PT(\d+)M([\d.]+)S', m or '')
    return int(x.group(1)) * 60 + float(x.group(2)) if x else 0.0


def load(season):
    base = ROOT / 'data/defense-seventh' / season
    rs = json.load(open(base / 'bio.json', encoding='utf-8'))['data']['resultSets'][0]
    bio = {r[0]: dict(zip(rs['headers'], r)) for r in rs['rowSet']}
    games = []
    for f in glob.glob(str(base / 'boxes' / '*.json')):
        g = json.load(open(f, encoding='utf-8'))['data']['game']
        games.append(g)
    games.sort(key=lambda g: (g.get('gameTimeUTC') or g.get('gameEt') or '', g['gameId']))
    log = {}      # pid -> [(starterSlot or None, seconds)] 依日期
    for g in games:
        for t in ('homeTeam', 'awayTeam'):
            for p in g[t]['players']:
                s = secs(p['statistics'].get('minutes'))
                if s <= 0:
                    continue
                slot = p.get('position') if p.get('starter') == '1' and p.get('position') in POS else None
                log.setdefault(p['personId'], []).append((slot, s))
    return bio, log, games


def shares(rows, hpos, sbar, kind):
    sec = {p: 0.0 for p in POS}
    starts = 0
    for slot, s in rows:
        if slot:
            sec[slot] += s
            starts += 1
    if kind == 'H5':
        return onehot(hpos)
    if kind == 'S5':
        return onehot(max(POS, key=lambda p: (sec[p], -POS.index(p))) if starts >= 5 else hpos)
    if kind == 'W5':
        tot = sum(sec.values()) + KAPPA * sbar
        return {p: (sec[p] + KAPPA * sbar * (p == hpos)) / tot for p in POS}
    raise ValueError(kind)


def onehot(p):
    return {q: float(q == p) for q in POS}


def b0(h):
    # 現行新秀：build_rookie_prior.height_pos（≤76 G、≥82 C、其他 F）→ run_c4_live_rookie.DPOS（SG／SF／C）
    return onehot('SG' if h <= 76 else 'C' if h >= 82 else 'SF')


def tv(a, b):
    return 0.5 * sum(abs(a[p] - b[p]) for p in POS)


def main():
    out = {'kappa': KAPPA, 'seasons': {}, 'live2026': {}}
    for season in SEASONS:
        bio, log, games = load(season)
        st = [s for g in games for t in ('homeTeam', 'awayTeam') for p in g[t]['players']
              if p.get('starter') == '1' for s in [secs(p['statistics'].get('minutes'))] if s > 0]
        sbar = sum(st) / len(st)
        y0 = season[:4]
        rk = [pid for pid, b in bio.items() if str(b.get('DRAFT_YEAR')) == y0 and pid in log]
        rows = []
        for pid in rk:
            b = bio[pid]
            h = float(b['PLAYER_HEIGHT_INCHES'])
            hp = h5(h)
            full = log[pid]
            r = {'pid': pid, 'name': b['PLAYER_NAME'], 'h': h, 'G': len(full), 'h5': hp,
                 'startsFull': sum(1 for s, _ in full if s)}
            if season in P1_SEASONS:
                ans = shares(full, hp, sbar, 'S5')
                ans_soft = shares(full, hp, sbar, 'W5')
                r['ans'] = max(POS, key=lambda p: ans[p])
                for n in (5, 10, 20):
                    if len(full) < n:
                        continue
                    part = full[:n]
                    arms = {'B0': b0(h), 'H5': shares(part, hp, sbar, 'H5'),
                            'S5': shares(part, hp, sbar, 'S5'), 'W5': shares(part, hp, sbar, 'W5')}
                    r[f'tv{n}'] = {a: round(tv(v, ans), 4) for a, v in arms.items()}
                    r[f'tvSoft{n}'] = {a: round(tv(v, ans_soft), 4) for a, v in arms.items()}
            else:
                r['S5'] = max(POS, key=lambda p: shares(full, hp, sbar, 'S5')[p])
                r['W5'] = {p: round(v, 4) for p, v in shares(full, hp, sbar, 'W5').items()}
            rows.append(r)
        if season in P1_SEASONS:
            summ = {}
            for n in (5, 10, 20):
                use = [r for r in rows if f'tv{n}' in r]
                summ[n] = {'n': len(use), **{a: round(sum(r[f'tv{n}'][a] for r in use) / len(use), 4) for a in ('B0', 'H5', 'S5', 'W5')},
                           'soft': {a: round(sum(r[f'tvSoft{n}'][a] for r in use) / len(use), 4) for a in ('B0', 'H5', 'S5', 'W5')}}
            out['seasons'][season] = {'sbar': sbar, 'summary': summ, 'rows': rows}
        else:
            out['live2026'] = {'sbar': sbar, 'rows': rows}
    pooled = {}
    for n in (5, 10, 20):
        use = [r for s in P1_SEASONS for r in out['seasons'][s]['rows'] if f'tv{n}' in r]
        pooled[n] = {'n': len(use), **{a: round(sum(r[f'tv{n}'][a] for r in use) / len(use), 4) for a in ('B0', 'H5', 'S5', 'W5')},
                     'soft': {a: round(sum(r[f'tvSoft{n}'][a] for r in use) / len(use), 4) for a in ('B0', 'H5', 'S5', 'W5')}}
    out['pooled'] = pooled
    json.dump(out, open(HERE / 'p1.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'pooled': pooled, 'perSeason10': {s: out['seasons'][s]['summary'][10] for s in P1_SEASONS}}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
