"""E-280／E-281 共用：按名字查 stats-<季>.csv 的 per-36 欄；window=True 時取 t-3..t（最早 2021-22）分鐘加權平均。
對不到或空值填全體平均，回傳 (values{key: np.array}, missing{key: n})。"""
import csv, unicodedata
from pathlib import Path
import numpy as np
DATA = Path(__file__).resolve().parents[1] / 'E227-lineup-transformer-r2' / 'data'
SEASONS = ['2021-22', '2022-23', '2023-24', '2024-25', '2025-26']


def nm(x):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', x) if not unicodedata.combining(ch)).lower().replace('.', '').replace(' jr', '').replace(' iii', '').replace(' ii', '').strip()


def _table(s):
    by = {}
    for r in csv.DictReader(open(DATA / f'stats-{s}.csv', encoding='utf-8')):
        by.setdefault(r['name'], r); by.setdefault(nm(r['name']), r)
    return by


def lookup(names, season, keys, window=False):
    i = SEASONS.index(season)
    ss = SEASONS[max(0, i - 3):i + 1] if window else [season]
    tabs = [_table(s) for s in ss]
    out, miss = {}, {}
    for k in keys:
        v = []
        for n in names:
            num = den = 0.0
            for tb in tabs:
                r = tb.get(n) or tb.get(nm(n))
                if r and r.get(k, '') not in ('', None):
                    m = float(r.get('minutes') or 0) if window else 1.0
                    if m > 0:
                        num += m * float(r[k]); den += m
            v.append(num / den if den > 0 else np.nan)
        v = np.array(v, float)
        miss[k] = int(np.isnan(v).sum())
        v[np.isnan(v)] = np.nanmean(v)
        out[k] = v
    return out, miss
