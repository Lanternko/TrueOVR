"""inseason／card 0.2.14b MIX 加分閘門（E-295 W1；0.2.14a＝E-294 H-same；0.2.14＝R-183／R-184）。npm test 會跑。
(1) day0 一致性：開季前（本季沒有資料、本季 0 分鐘、rebound＝卡片值、pos＝卡片 pos）賽中公式算出的加分＝card-0.2.14b 的 mixBonus（差 ≤0.001）。
    走 mix_live.apply(h=True, w1=True)（賽中寫 ranking 前同一條路徑），本季資料夾指到空資料夾＝開季前。
    回退路徑 apply(h=True)（MIX_W1=0）仍要＝card-0.2.14a，apply(h=False)（MIX_H=0）仍要＝card-0.2.14。
(1b) card-0.2.14b：別名 3 人以外加分與 card-0.2.14b-cand 差 ≤0.02；凍結檔記 0214a 基底 sha；π／m_p／縮放／身高帶表齊全；
    卡外：復出老將用最近一季 BBRef，新秀用身高帶（超出 70–91 取端點），沒有「標籤不在 mpos 給 0」。
(2) card-0.2.14a：ranking.csv sha＝summary.json；ovr＝round(ovr_0213a＋mixBonus, 1)；與 card-0.2.15-cand 逐位元相同。card-0.2.14 同理（對 cand2）。
(3) 凍結常數：m_pos 5×4、s_reb／s_con／s_mix（不每天重算）；位置權重 C=1、PF=0.243、其他 0。
(4) 本季混合規則：w＝m/(m+500)、缺一季只用另一季、打折分鐘＝2025-26＋本季。
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
CARD14A = ROOT / 'reports' / 'card-0.2.14a'
CARD14B = ROOT / 'reports' / 'card-0.2.14b'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def r1(v):
    return round(v + 0.0, 1)


class MixDay0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = {r['name']: r for r in csv.DictReader(open(ROOT / 'reports/card-0.2.13a/ranking.csv', encoding='utf-8'))}
        cls.cards = {False: list(csv.DictReader(open(CARD14 / 'ranking.csv', encoding='utf-8'))),
                     True: list(csv.DictReader(open(CARD14A / 'ranking.csv', encoding='utf-8'))),
                     'w1': list(csv.DictReader(open(CARD14B / 'ranking.csv', encoding='utf-8')))}
        cls.frozens = {h: MX.load_frozen(h) for h in (False, True)}
        cls.frozens['w1'] = MX.load_frozen(True, True)
        cls.pid = {v['name']: int(p) for p, v in cls.frozens[True]['players'].items()}

    def _day0(self, h):
        card, label = self.cards[h], {'w1': 'card-0.2.14b', True: 'card-0.2.14a', False: 'card-0.2.14'}[h]
        rows = []
        for r in card:
            o0 = float(self.base[r['name']]['ovr'])
            rows.append({'playerId': self.pid[r['name']], 'name': r['name'], 'pos': self.base[r['name']]['pos'], 'rebound': self.base[r['name']]['rebound'],
                         'heightInches': self.base[r['name']]['heightInches'],
                         'MIN26': 0.0, '_ovr': o0, 'ovr': o0, 'lastOVR': o0, 'dOVR': 0.0, 'formalOVR': o0})
        with tempfile.TemporaryDirectory() as empty:
            if h == 'w1':
                MX.apply(rows, r1, Path(empty), h=True, w1=True)
            else:
                MX.apply(rows, r1, Path(empty), h=h)
        want = {r['name']: (float(r['mixBonus']), float(r['ovr'])) for r in card}
        bad = [(r['name'], r['mixBonus'], want[r['name']][0]) for r in rows if abs(r['mixBonus'] - want[r['name']][0]) > 0.05]
        self.assertEqual(bad, [], f'day0 加分和 {label} 對不上：{bad[:5]}')
        self.assertLessEqual(max(abs(r['mixBonus'] - want[r['name']][0]) for r in rows), 0.001)
        # 加分重算差 ≤0.0005，碰到四捨五入邊界時 OVR 可差 0.1
        badovr = [r['name'] for r in rows if abs(r['ovr'] - want[r['name']][1]) > 0.1001]
        self.assertEqual(badovr, [], f'day0 OVR 和 {label} 對不上：{badovr[:5]}')
        self.assertTrue(all(abs(r['dOVR']) <= 0.1001 for r in rows), 'day0 dOVR 應為 0（lastOVR 也加了卡片加分）')
        self.assertTrue(all(r['formalOVR'] == want[r['name']][1] for r in rows), f'formalOVR 應換成 {label}')

    def test_day0_equals_card_0214b(self):
        self._day0('w1')

    def test_day0_rollback_equals_card_0214a(self):
        self._day0(True)

    def test_day0_rollback_equals_card_0214(self):
        self._day0(False)

    def _card(self, d, ver, src):
        s = json.loads((d / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['version'], ver)
        self.assertEqual(sha(d / 'ranking.csv'), s['ranking_csv_sha256'])
        self.assertEqual(sha(d / 'ranking.csv'), sha(src))
        for r in csv.DictReader(open(d / 'ranking.csv', encoding='utf-8')):
            # 卡片用未四捨五入的加分算 OVR，mixBonus 欄只到三位小數：容許 0.05＋0.0005（例 Grant Nelson 64.9／65.0 邊界）
            self.assertLessEqual(abs(float(r['ovr']) - (float(self.base[r['name']]['ovr']) + float(r['mixBonus']))), 0.0505 + 1e-9, msg=r['name'])

    def test_card_0214b(self):
        d = CARD14B
        s = json.loads((d / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['version'], 'card 0.2.14b')
        self.assertEqual(sha(d / 'ranking.csv'), s['ranking_csv_sha256'])
        alias = {r['card_name'] for r in csv.DictReader(open(d / 'bbref-alias.csv', encoding='utf-8'))}
        self.assertEqual(alias, {'Ronald Holland II', 'Trevon Scott', 'Adama Bal'})
        cand = {r['name']: float(r['mixBonus']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.14b-cand/ranking.csv', encoding='utf-8'))}
        fz = self.frozens['w1']
        for r in self.cards['w1']:
            self.assertLessEqual(abs(float(r['ovr']) - (float(self.base[r['name']]['ovr']) + float(r['mixBonus']))), 0.0505 + 1e-9, msg=r['name'])
            if r['name'] not in alias:
                self.assertLessEqual(abs(float(r['mixBonus']) - cand[r['name']]), 0.02 + 1e-9, msg=r['name'])
        for v in fz['players'].values():
            if v['name'] in alias:
                self.assertTrue(v['piSrc'].startswith('2025-26'), v)   # 別名後有 BBRef 2025-26
        self.assertEqual(fz['base_sha256']['mix-pool-card0214a.json'], sha(MX.FROZEN_H))

    def test_frozen_w1(self):
        fz = self.frozens['w1']
        cfg, w = fz['config'], fz['config']['w1']
        c0 = self.frozens[True]['config']
        self.assertEqual((cfg['z'], cfg['sd'], cfg['lambda'], cfg['ref'], cfg['rampMin'], cfg['blendK']),
                         (c0['z'], c0['sd'], c0['lambda'], c0['ref'], c0['rampMin'], c0['blendK']))
        self.assertEqual(w['posWeight'], [0.0, 0.0, 0.0, 0.68 / 2.80, 1.0])
        self.assertEqual(sorted(w['mpos']), sorted(MX.FEATS))
        self.assertEqual(sorted(int(h) for h in w['heightPrior']), list(range(70, 92)))
        self.assertTrue(all('pi' in v and abs(sum(v['pi']) - 1) < 1e-9 for v in fz['players'].values()))
        self.assertEqual(len(fz['players']), len(self.cards['w1']))
        names = {v['name'] for v in fz['fallback'].values()}
        self.assertTrue({'Trey Lyles', 'Georges Niang'} <= names, names)
        # 新秀：身高帶、超出取端點；標籤不影響（G／F 也可能有加分）
        cur = {1: {'orebPct': 0.15, 'drebPct': 0.30, 'con2_36': 12.0}}
        self.assertEqual(MX.pi_for(fz, 1, 95.0), (w['heightPrior']['91'], 'height:91'))
        self.assertEqual(MX.pi_for(fz, 1, 66.0), (w['heightPrior']['70'], 'height:70'))
        self.assertGreater(MX.live_bonus(fz, 1, 95.0, 900.0, cur, 'G', height=84.0)['bonus'], 0.0)
        self.assertEqual(MX.live_bonus(fz, 1, 95.0, 900.0, cur, 'C', height=84.0)['bonus'],
                         MX.live_bonus(fz, 1, 95.0, 900.0, cur, 'PG', height=84.0)['bonus'])
        lyles = next(p for p, v in fz['fallback'].items() if v['name'] == 'Trey Lyles')
        self.assertTrue(MX.pi_for(fz, lyles, 81.0)[1].startswith('fallback:'))

    def test_card_0214a(self):
        self._card(CARD14A, 'card 0.2.14a', ROOT / 'reports/card-0.2.15-cand/ranking.csv')

    def test_card_0214(self):
        self._card(CARD14, 'card 0.2.14', ROOT / 'reports/card-0.2.14-cand2/ranking.csv')

    def test_frozen_h(self):
        cfg = self.frozens[True]['config']
        h = cfg['h']
        self.assertEqual(h['alpha'], 0.5)
        self.assertEqual(h['posWeight'], {'PG': 0.0, 'SG': 0.0, 'SF': 0.0, 'PF': 0.68 / 2.80, 'C': 1.0})
        self.assertEqual(sorted(h['mpos']), sorted(MX.POSL))
        self.assertTrue(all(sorted(v) == sorted(MX.FEATS) for v in h['mpos'].values()))
        self.assertAlmostEqual(h['mpos']['C']['rebound'], 1.230, places=3)
        self.assertAlmostEqual(h['mpos']['C']['con2_36'], 1.472, places=3)
        self.assertEqual({k: round(v, 5) for k, v in cfg['scales'].items()}, {'reb': 1.05237, 'con': 1.02558, 'mix': 1.12377})
        c0 = self.frozens[False]['config']
        self.assertEqual((cfg['z'], cfg['sd'], cfg['lambda'], cfg['rampMin'], cfg['blendK']), (c0['z'], c0['sd'], c0['lambda'], c0['rampMin'], c0['blendK']))
        # 非 PF／C（含新秀 G／F）加分 0
        cur = {1: {'orebPct': 0.30, 'drebPct': 0.40, 'con2_36': 15.0}}
        for pos in ('PG', 'SG', 'SF', 'G', 'F', None):
            self.assertEqual(MX.live_bonus(self.frozens[True], 1, 99.0, 900.0, cur, pos)['bonus'], 0.0)
        self.assertGreater(MX.live_bonus(self.frozens[True], 1, 99.0, 900.0, cur, 'C')['bonus'], 0.0)

    def test_blend_rules(self):
        for h in (False, True):
            fz = self.frozens[h]
            cfg = fz['config']
            self.assertEqual((cfg['lambda'], cfg['rampMin'], cfg['blendK'], cfg['clip']), (0.5, 500.0, 500.0, [0.0, 1.5]))
            self.assertAlmostEqual(cfg['sd'], 13.41, places=2)
            # 新秀（凍結檔沒有）：只用本季值，打折分鐘＝本季分鐘
            cur = {1: {'orebPct': 0.15, 'drebPct': 0.30, 'con2_36': 12.0}}
            d = MX.live_bonus(fz, 1, 90.0, 250.0, cur, 'C')
            self.assertEqual((d['orebPct'], d['con2_36'], d['MIN'], d['ramp']), (0.15, 12.0, 250.0, 0.5))
            self.assertAlmostEqual(d['bonus'], d['full'] * 0.5)
            # 老將：打折分鐘＝2025-26 卡片分鐘＋本季分鐘
            p, v = next((int(p), v) for p, v in fz['players'].items() if 100 < v['MIN'] < 300)
            d = MX.live_bonus(fz, p, v['cardRebound'], 100.0, {}, 'C')
            self.assertAlmostEqual(d['MIN'], v['MIN'] + 100.0)
        self.assertAlmostEqual(MX.blend(0.10, 0.20, 500, 500), 0.15)
        self.assertEqual(MX.blend(None, 0.20, 10, 500), 0.20)
        self.assertEqual(MX.blend(0.10, None, 300, 500), 0.10)
        self.assertEqual(MX.blend(0.10, 0.20, 0, 500), 0.10)


if __name__ == '__main__':
    unittest.main()
