"""E-227 探索臂 R2-stats-nost（事後對照，測試集已讀過，不改 E-227 判定）。
R2-stats 的特徵張量把 stamina 的值欄與它的遮罩欄拿掉（其餘 40 項特徵完全相同；z 分數逐欄獨立，所以直接從 stats 張量刪欄＝重新建一份沒有 stamina 的特徵）。
超參數沿用 tuning.json 的 R2-stats（lr 0.001、wd 0.1），不重調。凍結檔不動：E227_SRC 環境變數指向凍結程式碼所在目錄（預設＝上一層）。"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('E227_SRC', os.path.dirname(HERE))
sys.path.insert(0, SRC)
from e227_common import ATTRS, SEASONS  # noqa: E402

ARM = 'R2-stats-nost'
KIND = 'stats'
F_FULL = 41
ST = ATTRS.index('stamina')


def drop_stamina_cols(F=F_FULL):
    """張量最後一維 [值 F 欄 | 遮罩 F 欄] 中要保留的欄索引。"""
    return [i for i in range(2 * F) if i not in (ST, F + ST)]


def strip(T, F=F_FULL):
    """T＝tensors() 輸出 [attr, pos, side, y]；回傳 stamina 欄被拿掉的版本。"""
    keep = drop_stamina_cols(F)
    return [T[0][..., keep].contiguous(), T[1], T[2], T[3]]


def strip_np(vec, F=F_FULL):
    """vec[..., 2F] numpy／list 陣列 → 去 stamina。"""
    import numpy as np
    return np.asarray(vec, np.float32)[..., drop_stamina_cols(F)]
