"""inseason／card 0.2.14 MIX 加分閘門（R-183／R-184）。npm test 會跑。
(1) day0 一致性：開季前（本季沒有資料、本季 0 分鐘、rebound＝卡片值）賽中公式算出的加分＝card-0.2.14 的 mixBonus（差 ≤0.05）。
    走 mix_live.apply()（賽中寫 ranking 前同一條路徑），本季資料夾指到空資料夾＝開季前。
(2) card-0.2.14：ranking.csv sha＝summary.json；ovr＝round(ovr_0213a＋mixBonus, 1)；與 cand2 逐位元相同。
(3) 本季混合規則：w＝m/(m+500)、缺一季只用另一季、打折分鐘＝2025-26＋本季。
"""
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'reports' / 'ovr-inseason-2026-27' / 'live'
sys.path.insert(0, str(LIVE))
import mix_live as MX  # noqa: E402

CARD14 = ROOT / 'reports' / 'card-0.2.14'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def r1(v):
    return round(v + 0.0, 1)


class MixDay0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card = list(csv.DictReader(open(CARD14 / 'ranking.csv', encoding='utf-8')))
        cls.base = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.13a/ranking.csv', encoding='utf-8'))}
        cls.frozen = MX.load_frozen()
        cls.pid = {v['name']: int(p) for p, v in cls.frozen['players'].items()}

    def test_day0_equals_card(self):
        rows = []
        for r in self.card:
            o0 = float(self.base[r['name']]['ovr'])
            rows.append({'playerId': self.pid[r['name']], 'name': r['name'], 'rebound': self.base[r['name']]['rebound'],
                         'MIN26': 0.0, '_ovr': o0, 'ovr': o0, 'lastOVR': o0, 'dOVR': 0.0, 'formalOVR': o0})
        with tempfile.TemporaryDirectory() as empty:
            MX.apply(rows, r1, Path(empty))
        want = {r['name']: (float(r['mixBonus']), float(r['ovr'])) for r in self.card}
        bad = [(r['name'], r['mixBonus'], want[r['name']][0]) for r in rows if abs(r['mixBonus'] - want[r['name']][0]) > 0.05]
        self.assertEqual(bad, [], f'day0 加分和 card-0.2.14 對不上：{bad[:5]}')
        self.assertLessEqual(max(abs(r['mixBonus'] - want[r['name']][0]) for r in rows), 0.05)
        # 加分重算差 ≤0.0005，碰到四捨五入邊界時 OVR 可差 0.1（Peyton Watson、Johnny Furphy）
        badovr = [r['name'] for r in rows if abs(r['ovr'] - want[r['name']][1]) > 0.1001]
        self.assertEqual(badovr, [], f'day0 OVR 和 card-0.2.14 對不上：{badovr[:5]}')
        self.assertTrue(all(abs(r['dOVR']) <= 0.1001 for r in rows), 'day0 dOVR 應為 0（lastOVR 也加了卡片加分）')
        self.assertTrue(all(r['formalOVR'] == want[r['name']][1] for r in rows), 'formalOVR 應換成 card 0.2.14')

    def test_card_0214(self):
        s = json.loads((CARD14 / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['version'], 'card 0.2.14')
        self.assertEqual(sha(CARD14 / 'ranking.csv'), s['ranking_csv_sha256'])
        self.assertEqual(sha(CARD14 / 'ranking.csv'), sha(ROOT / 'reports/card-0.2.14-cand2/ranking.csv'))
        for r in self.card:
            self.assertAlmostEqual(float(r['ovr']), round(float(self.base[r['name']]['ovr']) + float(r['mixBonus']), 1), places=6, msg=r['name'])

    def test_blend_rules(self):
        cfg = self.frozen['config']
        self.assertEqual((cfg['lambda'], cfg['rampMin'], cfg['blendK'], cfg['clip']), (0.5, 500.0, 500.0, [0.0, 1.5]))
        self.assertAlmostEqual(cfg['sd'], 13.41, places=2)
        self.assertAlmostEqual(MX.blend(0.10, 0.20, 500, 500), 0.15)
        self.assertEqual(MX.blend(None, 0.20, 10, 500), 0.20)
        self.assertEqual(MX.blend(0.10, None, 300, 500), 0.10)
        self.assertEqual(MX.blend(0.10, 0.20, 0, 500), 0.10)
        # 新秀（凍結檔沒有）：只用本季值，打折分鐘＝本季分鐘
        cur = {1: {'orebPct': 0.15, 'drebPct': 0.30, 'con2_36': 12.0}}
        d = MX.live_bonus(self.frozen, 1, 90.0, 250.0, cur)
        self.assertEqual((d['orebPct'], d['con2_36'], d['MIN'], d['ramp']), (0.15, 12.0, 250.0, 0.5))
        self.assertAlmostEqual(d['bonus'], d['full'] * 0.5)
        # 老將：打折分鐘＝2025-26 卡片分鐘＋本季分鐘
        p, v = next((int(p), v) for p, v in self.frozen['players'].items() if 100 < v['MIN'] < 300)
        d = MX.live_bonus(self.frozen, p, v['cardRebound'], 100.0, {})
        self.assertAlmostEqual(d['MIN'], v['MIN'] + 100.0)


if __name__ == '__main__':
    unittest.main()
