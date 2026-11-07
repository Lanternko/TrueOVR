"""賽中即時 OVR（2026-27）共同工具：凍結常數、百分位映射、命中率反查曲線。

所有函式逐行對應 scripts/build_season_league.js 與 v58 的 build-card-E 規則，
曲線本身直接從 src/constants.js 讀取（不複製數值，避免漂移）。本檔只讀取，不修改 src/。
"""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTDIR = Path(__file__).resolve().parents[1]  # reports/ovr-inseason-2026-27
DATA = OUTDIR / 'data'
FIT = OUTDIR / 'fit'
BACKTEST = OUTDIR / 'backtest'

ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'physique',
         'onBall', 'help', 'stamina', 'heightInches', 'creation', 'pressure']
UPDATABLE = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'stamina',
             'creation', 'pressure']
MAIN_ATTRS = ['long', 'mid', 'short', 'ft', 'drive', 'tovSkill', 'pass', 'rebound', 'stamina']
FROZEN = ['physique', 'onBall', 'help', 'heightInches']

_CURVE_NAMES = ['CURVE_3PT', 'CURVE_MID', 'CURVE_SHORT', 'CURVE_FT', 'CURVE_DEF_3PT', 'CURVE_DEF_RIM']


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _curve_body(text, name):
    """曲線本體文字。支援 `NAME = [...]` 與實驗旗標 `NAME = FLAG ? [...] : [...]`；
    後者照 JS 同樣規則判斷：環境變數 FLAG === '1' 取前一組，否則取後一組。"""
    m = re.search(r'export const ' + name + r'\s*=\s*\[(.*?)\];', text, re.S)
    if m:
        return m.group(1)
    m = re.search(r'export const ' + name + r'\s*=\s*(\w+)\s*\?\s*\[(.*?)\]\s*:\s*\[(.*?)\];', text, re.S)
    if not m:
        raise RuntimeError('Missing curve in src/constants.js: ' + name)
    flag = m.group(1)
    if not re.search(r'export const ' + flag + r"\s*=\s*globalThis\.process\?\.env\?\." + flag + r"\s*===\s*'1';", text):
        raise RuntimeError('Unrecognized flag for ' + name + ' in src/constants.js: ' + flag)
    return m.group(2) if os.environ.get(flag) == '1' else m.group(3)


def load_constants():
    text = (ROOT / 'src/constants.js').read_text(encoding='utf-8')
    out = {}
    for name in _CURVE_NAMES:
        out[name] = [tuple(float(v) for v in pair.split(','))
                     for pair in re.findall(r'\[\s*([^\[\]]+?)\s*\]', _curve_body(text, name))]
    m = re.search(r'export const ATTR_MIDPOINT\s*=\s*(-?[\d.]+)', text)
    if not m:
        raise RuntimeError('Missing ATTR_MIDPOINT in src/constants.js')
    out['ATTR_MIDPOINT'] = float(m.group(1))
    return out


CONST = load_constants()
CURVES = {k: v for k, v in CONST.items() if k != 'ATTR_MIDPOINT'}
ATTR_MIDPOINT = CONST['ATTR_MIDPOINT']


def safe(a, b):
    return a / b if b > 0 else 0.0


def percentile(x, values):
    """build_season_league.js percentile()：0-100，含相等值算半個。"""
    n = len(values)
    return 100.0 * (sum(1 for v in values if v < x) + 0.5 * sum(1 for v in values if v == x)) / n


def attr(p):
    """build_season_league.js attr()：PR1=40、PR50=70、PR99=99 的分段線性映射。"""
    return max(40.0, min(99.0, 40 + (p - 1) * 30 / 49 if p < 50 else 70 + (p - 50) * 29 / 49))


def inverse(p, curve):
    """build_season_league.js inverse()：把命中率（或防守分差）反查成能力值。"""
    import math
    if not math.isfinite(p):
        raise ValueError('Nonfinite probability passed to inverse curve')
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if min(y0, y1) <= p <= max(y0, y1):
            return max(40.0, min(99.0, x0 + (p - y0) / (y1 - y0) * (x1 - x0)))
    return 40.0 if abs(p - curve[0][1]) < abs(p - curve[-1][1]) else 99.0


def shooting(makes, attempts, mean, curve):
    """固定 100 次出手偽計數的聯盟先驗收縮，再反查曲線。"""
    return inverse((makes + 100 * mean) / (attempts + 100), curve)


def pos_of_height(h):
    return 'PG' if h <= 75 else 'SG' if h <= 78 else 'SF' if h <= 80 else 'PF' if h <= 82 else 'C'


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
