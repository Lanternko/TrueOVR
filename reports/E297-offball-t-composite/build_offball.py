"""E-297：無球細項（逐季，E-227 stats 同口徑）→ data/offball-<季>.csv。定義見 prereg.md。
用法（repo root）：python -I -B -X utf8 reports/E297-offball-t-composite/build_offball.py"""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
RAW = ROOT / 'reports/E239-tracking-full/data'
E227D = ROOT / 'reports/E227-lineup-transformer-r2/data'
SEAS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
SYN = {'cut36': 'Cut', 'offScr36': 'OffScreen', 'handoff36': 'Handoff', 'spotup36': 'Spotup', 'roll36': 'PRRollman',
       'putback36': 'OffRebound', 'trans36': 'Transition'}
COLS = ['cut36', 'cutPPP', 'offScr36', 'handoff36', 'spotup36', 'roll36', 'putback36', 'trans36', 'distOff36', 'speedOff', 'cs3a36', 'cs3pct']
MIN_MIN, K_CUT, K_CS = 200.0, 30.0, 50.0


def table(name):
    d = json.loads((RAW / f'{name}.json').read_text(encoding='utf-8'))
    out = {}
    for r in d['rowSet']:
        r = dict(zip(d['headers'], r)); p = str(r['PLAYER_ID'])
        if p in out:   # 保險：同人多列就加總量欄
            for k in ('POSS', 'PTS'):
                if k in r:
                    out[p][k] = (out[p][k] or 0) + (r[k] or 0)
        else:
            out[p] = r
    return out


def main():
    (HERE / 'data').mkdir(exist_ok=True); info = {}
    for s in SEAS:
        mins = {r['pid']: float(r['minutes'] or 0) for r in csv.DictReader(open(E227D / f'stats-{s}.csv', encoding='utf-8'))}
        syn = {c: table(f'syn-{p}-{s}') for c, p in SYN.items()}
        sd, cs = table(f'pt-SpeedDistance-{s}'), table(f'pt-CatchShoot-{s}')
        cut = syn['cut36']; lg_cut = sum(r['PTS'] for r in cut.values()) / sum(r['POSS'] for r in cut.values())
        lg_cs = sum(r['CATCH_SHOOT_FG3M'] or 0 for r in cs.values()) / sum(r['CATCH_SHOOT_FG3A'] or 0 for r in cs.values())
        rows, miss = [], {c: 0 for c in COLS}
        for p, m in mins.items():
            o = {'pid': p, 'minutes': m}
            if m < MIN_MIN:
                rows.append({**o, **{c: '' for c in COLS}}); continue
            for c in SYN:
                r = syn[c].get(p); o[c] = round(36 * (r['POSS'] if r else 0) / m, 5)
                miss[c] += r is None
            r = cut.get(p); o['cutPPP'] = round(((r['PTS'] if r else 0) + K_CUT * lg_cut) / ((r['POSS'] if r else 0) + K_CUT), 5)
            r = sd.get(p)
            if r and r['MIN'] and r['DIST_MILES_OFF'] is not None:
                o['distOff36'] = round(36 * r['DIST_MILES_OFF'] / r['MIN'], 5); o['speedOff'] = r['AVG_SPEED_OFF']
            else:
                o['distOff36'] = o['speedOff'] = ''; miss['distOff36'] += 1; miss['speedOff'] += 1
            r = cs.get(p)
            if r and r['MIN'] and r['CATCH_SHOOT_FG3A'] is not None:
                o['cs3a36'] = round(36 * r['CATCH_SHOOT_FG3A'] / r['MIN'], 5)
                o['cs3pct'] = round((r['CATCH_SHOOT_FG3M'] + K_CS * lg_cs) / (r['CATCH_SHOOT_FG3A'] + K_CS), 5)
            else:
                o['cs3a36'] = o['cs3pct'] = ''; miss['cs3a36'] += 1; miss['cs3pct'] += 1
            rows.append(o)
        with open(HERE / 'data' / f'offball-{s}.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, ['pid', 'minutes'] + COLS); w.writeheader(); w.writerows(rows)
        info[s] = {'players': len(rows), 'ge200': sum(m >= MIN_MIN for m in mins.values()), 'missingAmongGe200': miss,
                   'lgCutPPP': round(lg_cut, 4), 'lgCs3': round(lg_cs, 4)}
    (HERE / 'data' / 'offball-info.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
