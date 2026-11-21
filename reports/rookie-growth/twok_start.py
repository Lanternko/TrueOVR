"""2K 給新秀的起點：每屆新秀在「新秀那一版 2K」的 OVR（draft 年 Y → 2K(Y+1)），對順位整理。
資料：reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv（2kratings，2K19–2K27 逐年 OVR；只含 2025-26 還在聯盟的人 → 早屆有倖存者偏差）
      data/benchmark-source/bio.json（2025-26 bio：DRAFT_YEAR／DRAFT_NUMBER）。只報告、不調參。
用法：python -I -X utf8 twok_start.py → twok-start.csv、twok-by-pick.json
"""
import csv
import json
import math
import statistics
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv'
BIO = ROOT / 'data/benchmark-source/bio.json'
BANDS = [(1, 3), (4, 10), (11, 20), (21, 30), (31, 45), (46, 60), (61, 99)]   # 61＝落選


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in s if c.isalnum())


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    doc = json.load(open(BIO, encoding='utf-8'))
    rs = doc['data']['resultSets'][0]
    hdr, rows = rs['headers'], rs['rowSet']
    bio = {norm(r[hdr.index('PLAYER_NAME')]): dict(zip(hdr, r)) for r in rows}
    out = []
    for r in csv.DictReader(open(TWOK, encoding='utf-8')):
        b = bio.get(norm(r['name']))
        if not b or str(b['DRAFT_YEAR']) in ('', 'Undrafted', 'None'):
            continue
        y = int(b['DRAFT_YEAR'])
        ed = f'2K{y - 2000 + 1}'
        if ed not in r or not r[ed]:
            continue
        dn = b['DRAFT_NUMBER']
        pick = int(dn) if str(dn).isdigit() else 61
        out.append({'name': r['name'], 'draftYear': y, 'pick': pick, 'edition': ed, 'rookie2K': int(r[ed]),
                    'now2K27': int(r['2K27']) if r['2K27'] else ''})
    out.sort(key=lambda r: (r['draftYear'], r['pick']))
    with open(HERE / 'twok-start.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    # 順位段 × 屆別（近三屆 2023–2025 倖存偏差小，另列）
    summ = {}
    for lo, hi in BANDS:
        for tag, ys in (('all', range(2018, 2026)), ('recent3', range(2023, 2026))):
            v = [r['rookie2K'] for r in out if lo <= r['pick'] <= hi and r['draftYear'] in ys]
            summ.setdefault(f'{lo}-{hi}', {})[tag] = {
                'n': len(v), 'mean': round(statistics.fmean(v), 1) if v else None,
                'median': statistics.median(v) if v else None, 'min': min(v, default=None), 'max': max(v, default=None)}
    # 對數順位直線（近三屆，落選不納入）：rookie2K = a + b·ln(pick)
    pts = [(math.log(r['pick']), r['rookie2K']) for r in out if r['pick'] <= 60 and r['draftYear'] >= 2023]
    mx, my = statistics.fmean(p[0] for p in pts), statistics.fmean(p[1] for p in pts)
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    a = my - b * mx
    fitline = {'a': round(a, 2), 'b_lnPick': round(b, 2), 'n': len(pts),
               'pred': {p: round(a + b * math.log(p), 1) for p in (1, 2, 3, 5, 10, 15, 20, 30, 45, 60)}}
    json.dump({'bands': summ, 'fitRecent3': fitline, 'byYear': {y: sum(1 for r in out if r['draftYear'] == y)
                                                               for y in range(2018, 2026)}},
              open(HERE / 'twok-by-pick.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({'bands': summ, 'fit': fitline}, ensure_ascii=False, indent=1))
    print('人數', len(out))


if __name__ == '__main__':
    main()
