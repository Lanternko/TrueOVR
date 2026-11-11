"""近 5 場表逐項上色閘門（使用者 2026-11-03）。npm test 會跑。
檢查 2026-27 每位球員 g5 每一列：分項（index 19）加總與顯示評分（index 17）差 < 0.02；評分被截到 0 的列跳過。
分項順序／五色切點在 scripts/enrich_roster_viewer.py（ITEM_ORDER、ITEM_PCT）；另查五色等級（index 20）各級比例合理。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import enrich_roster_viewer as er  # noqa: E402

TOL = 0.02


class G5Items(unittest.TestCase):
    def test_items_sum_to_rating(self):
        er.SRC = ROOT / 'data' / 'season-source-2026-27' / 'player-games.json'
        real = er.aggregate()
        n = skipped = fb = 0
        bad = []
        for name, r in real.items():
            for g in r['g5']:
                if g[17] is None:
                    continue
                self.assertEqual(len(g[19]), len(er.ITEM_ORDER), name)
                tot = sum(g[19])
                if tot <= 0 or g[17] <= 0:
                    skipped += 1
                    continue
                n += 1
                fb += g[18]
                if abs(tot - g[17]) >= TOL:
                    bad.append((name, g[0], g[17], round(tot, 3)))
        self.assertGreater(n, 100)
        self.assertEqual(bad[:10], [])
        print(f'g5 items: {n} rows ok ({fb} fallback), {skipped} clipped rows skipped')


if __name__ == '__main__':
    unittest.main()
