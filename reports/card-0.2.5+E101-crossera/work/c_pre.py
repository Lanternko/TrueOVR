"""E-101 c-pre（預註冊 §1）：2025-26 修正後 PBP 的聯盟 mid、short 命中率 vs 卡片 shots.json 的聯盟值，兩項差距都要 <= 0.010。
shots.json 的聯盟值 = V61 build_attrs.py:105-106 的 prior（bench_rows('shots') 全體 ΣM／ΣA；分區定義 build_attrs.py:39：
  short = RA + In The Paint (Non-RA)（rowSet 欄 6+9／7+10），mid = Mid-Range（欄 12／13））。
PBP 聯盟值（主要，字面「聯盟」）= 修正後 history/pbp-zones-2025-26.csv.gz 全部列加總。
另報（只報告）：只算卡片 582 人（build_attrs 的 zoneShift 口徑）、未修正版的同一數字。
不過就停（不改規則重試）。輸出 c-pre.json。
用法（repo 根目錄）：python -I -B reports/card-0.2.5+E101-crossera/work/c_pre.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[1]
V61 = ROOT / 'reports/ovr-v61-shrink-history-2025-26'
sys.path.insert(0, str(V61))
import build_attrs as B  # noqa: E402
from lib import read_gz_csv, sha256  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TOL = 0.010
shots = B.bench_rows('shots')
sj = {z: sum(s[z + 'M'] for s in shots) / sum(s[z + 'A'] for s in shots) for z in ('mid', 'short')}
league = json.loads(B.LEAGUE.read_text(encoding='utf-8'))
card_pids = {p['playerId'] for t in league['teams'] for p in t['roster']}
sj_card = {z: sum(s[z + 'M'] for s in shots if s['PLAYER_ID'] in card_pids) / sum(s[z + 'A'] for s in shots if s['PLAYER_ID'] in card_pids)
           for z in ('mid', 'short')}


def pbp(path, only=None):
    t = {'midA': 0, 'midM': 0, 'shortA': 0, 'shortM': 0}
    for r in read_gz_csv(path):
        if only is not None and int(r['playerId']) not in only:
            continue
        for k in t:
            t[k] += int(r[k])
    return {z: t[z + 'M'] / t[z + 'A'] for z in ('mid', 'short')}, t


fixed, tf = pbp(OUT / 'history/pbp-zones-2025-26.csv.gz')
unfixed, tu = pbp(V61 / 'history/pbp-zones-2025-26.csv.gz')
fixed_card, _ = pbp(OUT / 'history/pbp-zones-2025-26.csv.gz', card_pids)
unfixed_card, _ = pbp(V61 / 'history/pbp-zones-2025-26.csv.gz', card_pids)
diff = {z: fixed[z] - sj[z] for z in ('mid', 'short')}
out = {
    'rule': '|PBP 修正後聯盟命中率 − shots.json 聯盟命中率| <= 0.010，mid 與 short 都要',
    'shotsJson': {'league': sj, 'attempts': {z: sum(s[z + 'A'] for s in shots) for z in ('mid', 'short')}},
    'pbpFixed': {'league': fixed, 'totals': tf},
    'diff': diff,
    'pass': all(abs(d) <= TOL for d in diff.values()),
    'reportOnly': {
        'pbpUnfixed': {'league': unfixed, 'totals': tu, 'diffVsShotsJson': {z: unfixed[z] - sj[z] for z in ('mid', 'short')}},
        'cardPlayersOnly': {'shotsJson': sj_card, 'pbpFixed': fixed_card, 'pbpUnfixed': unfixed_card,
                            'diffFixed': {z: fixed_card[z] - sj_card[z] for z in ('mid', 'short')},
                            'diffUnfixed': {z: unfixed_card[z] - sj_card[z] for z in ('mid', 'short')}},
    },
    'inputs_sha256': {'history/pbp-zones-2025-26.csv.gz': sha256(OUT / 'history/pbp-zones-2025-26.csv.gz'),
                      'data/benchmark-source/shots.json': sha256(B.BENCH / 'shots.json')},
}
(OUT / 'c-pre.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('shotsJson', 'pbpFixed', 'diff', 'pass', 'reportOnly')}, ensure_ascii=False))
