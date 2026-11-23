"""E-307：輸出 T 用的逐季特徵 data/feat-<季>.csv（2021-22～2025-26）與 data/priors.json。
欄：pid, AE, AG, AV（各臂取代 blk36 的值）, rS, paS, gsS（TX 臂新增欄）。只在 blk36 原值非空（≥200 分鐘）時填值。
用法（repo root）：python -I -X utf8 reports/E307-blk-quality/build_feats.py"""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e307_lib as L  # noqa: E402

COLS = ['AE', 'AG', 'AV', 'rS', 'paS', 'gsS']


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pri = L.fit_priors()
    (L.HERE / 'data' / 'priors.json').write_text(json.dumps(pri, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    for s in L.FIT:
        sm = L.season_metrics(s, pri)
        n = 0
        with open(L.HERE / 'data' / f'feat-{s}.csv', 'w', encoding='utf-8', newline='') as fo:
            w = csv.writer(fo); w.writerow(['pid'] + COLS)
            for p, d in sorted(sm.items()):
                if d.get('A0') is None or 'AE' not in d:
                    w.writerow([p] + [''] * len(COLS)); continue
                n += 1
                w.writerow([p] + [round(d[c], 6) for c in COLS])
        print(s, 'players', len(sm), 'filled', n)


if __name__ == '__main__':
    main()
