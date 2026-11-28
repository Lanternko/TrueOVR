"""稽核：獨立從原始 PBP JSON 重算 2025-26 修正後聯盟 mid/short 命中率，對 shots.json；並算 Kessler 2022-23 修正前後 mid。
不 import 產出者或 V61 的程式。"""
import json, sys, gzip, csv, io
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]

def season_files(season):
    if season == '2025-26':
        m = json.loads((ROOT/'data/defense-a-source/manifest.json').read_text(encoding='utf-8'))
        return [ROOT/s['file'] for s in m['sources']]
    return sorted((ROOT/'data/defense-seventh'/season/'pbp').glob('*.json'))

def tally(season, want_pid=None):
    lg = {'fix': [0,0,0,0], 'raw': [0,0,0,0]}  # midA midM shortA shortM
    pl = defaultdict(lambda: {'fix': [0,0,0,0], 'raw': [0,0,0,0]})
    names = {}
    for f in season_files(season):
        for a in json.loads(f.read_text(encoding='utf-8'))['data']['game']['actions']:
            if a.get('actionType') != '2pt' or a.get('isFieldGoal') != 1:
                continue
            area = a.get('area')
            if area == 'Mid-Range':
                zr = 'mid'
            elif area in ('Restricted Area', 'In The Paint (Non-RA)'):
                zr = 'short'
            else:
                continue
            d = a.get('shotDistance')
            zf = 'short' if (zr == 'mid' and d is not None and d < 8) else zr
            if zr == 'mid' and d is None:
                zf = 'short'  # 產出者把缺值當 0；另計
                lg.setdefault('missing', 0); lg['missing'] = lg.get('missing', 0) + 1
            made = 1 if a.get('shotResult') == 'Made' else 0
            pid = a['personId']; names[pid] = a.get('playerNameI') or a.get('playerName')
            for key, z in (('raw', zr), ('fix', zf)):
                i = 0 if z == 'mid' else 2
                lg[key][i] += 1; lg[key][i+1] += made
                pl[pid][key][i] += 1; pl[pid][key][i+1] += made
    return lg, pl, names

def shots_league():
    d = json.loads((ROOT/'data/benchmark-source/shots.json').read_text(encoding='utf-8'))
    rs = d['data']['resultSets']; rs = rs[0] if isinstance(rs, list) else rs
    t = [0,0,0,0]
    for r in rs['rowSet']:
        t[0] += r[13]; t[1] += r[12]; t[2] += r[7]+r[10]; t[3] += r[6]+r[9]
    return t

out = {}
lg, pl, names = tally('2025-26')
sj = shots_league()
fx = lg['fix']
out['2025-26'] = {
    'pbpFixed': {'midA': fx[0], 'midM': fx[1], 'shortA': fx[2], 'shortM': fx[3], 'mid': fx[1]/fx[0], 'short': fx[3]/fx[2]},
    'pbpRaw': {'mid': lg['raw'][1]/lg['raw'][0], 'short': lg['raw'][3]/lg['raw'][2]},
    'shotsJson': {'midA': sj[0], 'shortA': sj[2], 'mid': sj[1]/sj[0], 'short': sj[3]/sj[2]},
    'missingDist': lg.get('missing', 0),
}
out['2025-26']['diff'] = {z: out['2025-26']['pbpFixed'][z] - out['2025-26']['shotsJson'][z] for z in ('mid', 'short')}
# 比對產出者修正後 history 檔的 2025-26 合計
def gz_tot(p):
    t = [0,0,0,0]
    with gzip.open(p, 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            for i, k in enumerate(('midA','midM','shortA','shortM')): t[i] += int(r[k])
    return t
out['2025-26']['producerHistoryTotals'] = gz_tot(OUT/'history/pbp-zones-2025-26.csv.gz')
lg22, pl22, n22 = tally('2022-23')
kes = [p for p, n in n22.items() if n and 'Kessler' in n]
out['kessler2022-23'] = {str(p): {'name': n22[p], 'raw': pl22[p]['raw'], 'fix': pl22[p]['fix']} for p in kes}
# 產出者 history 2022-23 的 Kessler 合計
def gz_pid(p, pid):
    t = [0,0,0,0]
    with gzip.open(p, 'rt', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if int(r['playerId']) == pid:
                for i, k in enumerate(('midA','midM','shortA','shortM')): t[i] += int(r[k])
    return t
for p in kes:
    out['kessler2022-23'][str(p)]['producerHistory'] = gz_pid(OUT/'history/pbp-zones-2022-23.csv.gz', p)
out['2022-23League'] = {'fix': lg22['fix'], 'raw': lg22['raw'], 'missing': lg22.get('missing', 0),
                       'producerHistoryTotals': gz_tot(OUT/'history/pbp-zones-2022-23.csv.gz')}
(Path(__file__).parent/'a1_zones.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1))
