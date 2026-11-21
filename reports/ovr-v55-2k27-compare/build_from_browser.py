"""把瀏覽器抓取（2kratings 球員頁，同源 fetch）匯出的分段 JSON 轉成分析用 CSV。

輸入：cache/browser_chunk_*.txt，每行 `i|slug|pos|digits` 或 `i|MISS|status`；
  digits = 41 個兩位數：2K27 overall、2K19..2K27 逐年 OVR（00=缺）、31 屬性（00=缺）。
  i 對應 slug_candidates.json（= ranking.csv 列序）。球隊欄位匯出時捨棄。
輸出：2k27_ratings.csv、2k_yearly_ovr.csv、unmatched.csv
"""
import csv, json
from pathlib import Path

from fetch_2k27 import ATTRS, CARD_CSV

HERE = Path(__file__).resolve().parent
YEARS = [f'2K{y}' for y in range(19, 28)]


def main():
    cands = json.loads((HERE / 'slug_candidates.json').read_text(encoding='utf-8'))
    rows = {}
    for p in sorted((HERE / 'cache').glob('browser_chunk_*.txt')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            i, a, b, *rest = line.split('|')
            if a == 'MISS':
                rows[int(i)] = ['MISS', b.split(',')]
                continue
            d = rest[0]
            nums = [int(d[k:k + 2]) for k in range(0, 82, 2)]
            yr = {y: v for y, v in zip(YEARS, nums[1:10]) if v}
            attrs = [v or '' for v in nums[10:]]
            # 屬性全缺（例：brandon-clarke 頁面解析失敗）時逐年也不可信
            if not any(attrs):
                yr = {}
            rows[int(i)] = [a, '2K27', nums[0], b, '', json.dumps(yr), *attrs]
    card = list(csv.DictReader(open(CARD_CSV, encoding='utf-8')))

    out, yearly, miss = [], [], []
    for i, (name, how, slugs) in enumerate(cands):
        r = rows.get(i)
        if r is None or r[0] == 'MISS':
            c = card[i]
            reason = '尚未抓取' if r is None else '頁面不存在：' + ','.join(map(str, r[1]))
            miss.append([name, c['rank'], c['ovr'], c['MIN'], reason, ','.join(slugs)])
            continue
        slug, game, ovr, pos, team, yj, *attrs = r
        matched = how if slug == slugs[0] else f'{how}-alt'
        out.append([name, slug, matched, ovr, game, pos, team, *attrs])
        y = json.loads(yj) if yj else {}
        yearly.append([name, slug, *[y.get(k, '') for k in YEARS]])

    out.sort(key=lambda x: -float(x[3]))
    with open(HERE / '2k27_ratings.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['name', 'slug', 'matchedBy', 'overall2k', 'gameYear', 'pos2k', 'team2k', *ATTRS])
        w.writerows(out)
    with open(HERE / '2k_yearly_ovr.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['name', 'slug', *YEARS])
        w.writerows(yearly)
    with open(HERE / 'unmatched.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['name', 'cardRank', 'cardOvr', 'MIN', 'reason', 'triedSlugs'])
        w.writerows(miss)
    print(f'matched {len(out)} / {len(cands)}, unmatched {len(miss)}')


if __name__ == '__main__':
    main()
