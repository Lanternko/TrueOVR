"""inseason 0.2.10g（E-192）自檢：賽中端的窗口用人特徵在 c=82（2025-26 季末）要等於卡片端 usage-2025-26-card0210g.json 的 L、a、has、y、v。
y、v 在 c=82 用 2025-26 bio 年齡（卡的算法）；賽中用當下年齡（age_flags）。
用法（repo root）：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/check_inseason_0210g.py"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import window11 as W  # noqa: E402


def main():
    Wn = W.Win11()
    cur, G = Wn.season_cur(W.PRIOR)
    f = Wn.usage_at(G, cur, W.PRIOR, G)
    doc = json.loads((HERE / 'usage-2025-26-card0210g.json').read_text(encoding='utf-8'))
    bad = {'L': 0, 'a': 0, 'has': 0, 'y': 0, 'v': 0, 'missing': 0}
    for k, u in doc['players'].items():
        p = int(k)
        if p not in Wn.D.pidx:
            bad['missing'] += 1
            continue
        i = Wn.D.pidx[p]
        age = Wn.age25.get(p)
        y, v = float(age is not None and age <= W.AGE_Y), float(age is not None and age >= W.AGE_V)
        bad['L'] += float(f['L'][i]) != u['L']
        bad['a'] += float(f['a'][i]) != u['a']
        bad['has'] += bool(f['has'][i]) != u['has']
        bad['y'] += y != u['y']
        bad['v'] += v != u['v']
    print('players', len(doc['players']), 'mismatch', bad)
    assert not any(bad.values()), bad
    print('OK：c=82 窗口特徵與卡片端逐位相同')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
