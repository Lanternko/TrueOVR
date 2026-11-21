"""E-202 共用：載入、bootstrap、2K27 Ball Handle、F-143。"""
import csv, hashlib, json, unicodedata
from pathlib import Path
import numpy as np
from scipy.stats import rankdata, spearmanr
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
TAIL = ROOT / 'reports/card-0.2.10i/tail-U.csv'
TWOK = ROOT / 'reports/ovr-v55-2k27-compare/2k27_ratings.csv'
HANDLE = ROOT / 'reports/handle-E069/handle.csv'
SEED, B = 20261102, 2000
RAPM_FILES = {'full': E126 / 'rapm-2025-26.json', 'odd': HERE / 'work/rapm-2025-26-odd.json', 'even': HERE / 'work/rapm-2025-26-even.json'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    for t in ('.', ',', "'", '-'):
        s = s.replace(t, ' ')
    return ' '.join(x for x in s.split() if x not in ('jr', 'sr', 'ii', 'iii', 'iv'))


def rank_path(arm):
    return HERE / f'work/{arm}/final/out/ranking.csv'


def load_arm(arm):
    pid = {r['name']: int(r['playerId']) for r in csv.DictReader(open(TAIL, encoding='utf-8'))}
    return {pid[r['name']]: r for r in csv.DictReader(open(rank_path(arm), encoding='utf-8'))}


def twok_bh():
    out = {}
    for r in csv.DictReader(open(TWOK, encoding='utf-8')):
        if (r.get('Ball Handle') or '').strip():
            out[norm(r['name'])] = float(r['Ball Handle'])
    return out


def poss36(cards):
    """持球分鐘/36＝handle.csv 2025-26 TIME_OF_POSS ÷ 卡片 MIN × 36。"""
    h = {int(r['playerId']): float(r['TIME_OF_POSS']) for r in csv.DictReader(open(HANDLE, encoding='utf-8')) if r['season'] == '2025-26'}
    return {p: h[p] / float(c['MIN']) * 36 for p, c in cards.items() if p in h and float(c['MIN']) > 0}


def f143(cards):
    ids = [p for p, c in cards.items() if float(c['MIN']) >= 500]
    v = poss36(cards)
    med = float(np.median([v[p] for p in ids if p in v]))
    top = sorted(ids, key=lambda p: -float(cards[p]['tovSkill']))[:30]
    return {'median': med, 'n_below': sum(1 for p in top if p in v and v[p] < med), 'n_nodata': sum(1 for p in top if p not in v),
            'top30_mean_poss36': float(np.mean([v[p] for p in top if p in v])),
            'top5': [cards[p]['name'] for p in top[:5]]}


def hw(x):
    return float((np.percentile(x, 95) - np.percentile(x, 5)) / 2)


def ci(x):
    return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]
