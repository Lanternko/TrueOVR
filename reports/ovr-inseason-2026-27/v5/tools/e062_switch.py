"""E-062 開關：把視窗卡 long/mid/shortBase/ft 的 shooting() 換成「球員自己為中心」版本。

mode: 'off'（不動，現行 C4）、'C4s'（中心 = forward(x0_i, curve)，m0=100）、'C4r'（m0=0，原始命中率）。
做法：包住 inseason_common_v4.window_cards，先呼叫原函式，再只覆寫四個投籃類欄位與依賴 shortBase 的 short。
其他欄位完全沿用原函式。install('off') 不做任何事。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4' / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import inseason_common_v4 as IC  # noqa: E402
from ovr_common import CURVES, inverse  # noqa: E402

_ORIG = IC.window_cards
# (視窗卡欄位, 先驗卡欄位, 曲線, 聯盟先驗 key, 命中/出手欄位)
SPECS = [('long', 'long', 'CURVE_3PT', 'long', 'FG3M', 'FG3A'),
         ('mid', 'mid', 'CURVE_MID', 'mid', 'midM', 'midA'),
         ('shortBase', 'shortBase', 'CURVE_SHORT', 'short', 'shortM', 'shortA'),
         ('ft', 'ft', 'CURVE_FT', 'ft', 'FTM', 'FTA')]


def forward(x, curve):
    """inverse() 的反函式：能力值 → 命中率（分段線性；超出範圍取端點命中率）。"""
    if x <= curve[0][0]:
        return curve[0][1]
    if x >= curve[-1][0]:
        return curve[-1][1]
    for i in range(1, len(curve)):
        x0, y0 = curve[i - 1]
        x1, y1 = curve[i]
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    raise AssertionError


def install(mode):
    if mode == 'off':
        IC.window_cards = _ORIG
        return
    assert mode in ('C4s', 'C4r'), mode

    def window_cards(sd, n, mapping, prior_cards, received, season_min_sample=None):
        out = _ORIG(sd, n, mapping, prior_cards, received, season_min_sample)
        gm = IC.window_game_map(sd, n)
        stats = IC.SA.aggregate(sd, gm)
        for pid, card in out.items():
            s = stats[pid]
            pc = prior_cards[pid]
            for key, pkey, cname, lkey, mk, ak in SPECS:
                curve = CURVES[cname]
                m, a = s[mk], s[ak]
                if mode == 'C4r':
                    if a <= 0:
                        continue            # 出手 0：不更新（樣本門檻會擋掉；保留原值）
                    val = inverse(m / a, curve)
                else:
                    x0 = pc.get(pkey)
                    mu = forward(float(x0), curve) if x0 is not None else mapping['priors'][lkey]
                    val = inverse((m + 100 * mu) / (a + 100), curve)
                card[key] = val
            card['short'] = IC._e2_short(card['shortBase'], pc, pc.get('creation'))
        return out

    IC.window_cards = window_cards
