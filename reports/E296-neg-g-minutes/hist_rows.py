"""E-296：用 ovr_history 同一流程逐日重算（同一把尺），但每天另存 predNew／MPGhat／g／mixBonus／N／MIN26。
用法：python -I -X utf8 reports/E296-neg-g-minutes/hist_rows.py → reports/E296-neg-g-minutes/today/ovr-history.json（pts 為 dict）"""
import csv, sys
from pathlib import Path
EXP = Path(__file__).resolve().parent
LIVE = EXP.parents[1] / 'reports/ovr-inseason-2026-27/live'
sys.path.insert(0, str(LIVE))
import ovr_history as OH
OH.CACHE = EXP / 'hist-cache.json'
KEEP = ('ovr', 'predNew', 'MPGhat', 'g', 'mixBonus', 'N', 'MIN26', 'pred0', 'defenseBonus')
def read_rows(path):
    out = {}
    for r in csv.DictReader(Path(path).open(encoding='utf-8')):
        out[r['playerId']] = {k: (float(r[k]) if r.get(k) not in (None, '') else None) for k in KEEP}
    return out
OH.read_ovr = read_rows
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    OH.build(EXP / 'today')
