# -*- coding: utf-8 -*-
"""BACKFILL COPY：載入同資料夾的 calibrate.py（加了 --rapm/--possScale 的複本），origin-attr.json 仍讀原資料夾；
其餘與 reports/ovr-v55-card-origin-attr-2025-26/calibrate_c1.py 相同。

C1：在 reports/ovr-calibrated-2025-26/calibrate.py 的 15 個屬性之外，加第 16 個主效應屬性
originShare（= build-origin-attr.mjs 算出的 1 − s̃，40–99 量表），其餘管線（目標、權重、CV
選模、ridge、bootstrap、輸出格式）完全不動——直接載入原始模組、monkeypatch `load()` 掛上新
屬性、把 'originShare' 併進 ATTRS，再呼叫原本的 main()。這樣除了新屬性以外不會有任何演算法
或超參數分歧，C1 vs B12 的差異可以單純歸因於這一個屬性。

originShare 沒有放進 INTERACT（position-interactions 的位置交乘項清單）：任務要求只新增一個
主效應屬性，不擴大模型自由度去額外調交乘項。

  python reports/ovr-v55-card-origin-attr-2025-26/calibrate_c1.py \
      --target reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv \
      --alpha 0.5 --league data/season-league.json \
      --out reports/ovr-v55-card-origin-attr-2025-26/card-C1
"""
import importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent

spec = importlib.util.spec_from_file_location('calibrate_base', Path(__file__).parent / 'calibrate.py')
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)

ORIGIN = json.loads((ROOT / 'reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json').read_text(encoding='utf-8'))
ORIGIN_PLAYERS = ORIGIN['players']

calibrate.ATTRS = calibrate.ATTRS + ['originShare']

_base_load = calibrate.load


def load_with_origin(target_path):
    rows = _base_load(target_path)
    missing = []
    for r in rows:
        rec = ORIGIN_PLAYERS.get(str(r['card']['playerId']))
        if rec is None:
            missing.append(r['name'])
            continue
        r['card']['originShare'] = rec['originShareAttr']
    if missing:
        raise SystemExit(f'origin-attr.json missing playerId for: {missing}')
    return rows


calibrate.load = load_with_origin

if __name__ == '__main__':
    calibrate.main()
    summary_path = None
    if '--out' in sys.argv:
        summary_path = Path(sys.argv[sys.argv.index('--out') + 1])
    else:
        summary_path = HERE
    p = summary_path / 'summary.json'
    s = json.loads(p.read_text(encoding='utf-8'))
    s['baseCalibrateScript'] = 'reports/ovr-calibrated-2025-26/calibrate.py'
    s['newAttribute'] = {
        'name': 'originShare', 'definition': '1 - fedShare (s-tilde), EB-shrunk, 2025-26 shot-origin',
        'source': 'reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json',
        'addedToInteract': False,
    }
    p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')
