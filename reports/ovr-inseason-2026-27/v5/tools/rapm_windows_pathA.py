"""Path A：建 Y0–Y2 缺的三個 RAPM 窗，並把 Y0–Y6 用到的八個窗轉成管線格式。

新建（§5.2 截斷窗口，λ 網格與 CV 同 reports/impact-rapm/rapm.py；呼叫 observations / fit_rapm）：
  2014-15、2014-15_2015-16、2014-15_2016-17
  stint 來自 reports/defense-seventh/<季>/stints/stints.jsonl（v5/history 的 gz 原樣解壓）。
已存在的五個窗（v5/history）不重算，只轉欄位：net/O/D/poss → pooledNet/pooledO/pooledD/pooledPoss
（OVRPipeline 讀的欄位；lastSeason* 欄填 0，管線不讀）。
輸出 v5/pathA/rapm/{rapm-<tag>.csv（新建，history 格式）, pipe-<tag>.csv, manifest.json}。
"""
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'reports/impact-rapm'))
import rapm  # noqa: E402

HIST = ROOT / 'reports/ovr-inseason-2026-27/v5/history'
OUT = ROOT / 'reports/ovr-inseason-2026-27/v5/pathA/rapm'
NEW = {'2014-15': ['2014-15'],
       '2014-15_2015-16': ['2014-15', '2015-16'],
       '2014-15_2016-17': ['2014-15', '2015-16', '2016-17']}
EXISTING = ['2014-15_2017-18', '2015-16_2018-19', '2016-17_2019-20',
            '2017-18_2020-21', '2018-19_2021-22']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def names_for(seasons):
    out = {}
    for s in seasons:
        for r in csv.DictReader(open(HIST / f'box-totals-{s}.csv', encoding='utf-8')):
            out[int(r['playerId'])] = r['name']
    return out


def to_pipe(src, dst):
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    with open(dst, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['playerId', 'name', 'pooledNet', 'pooledO', 'pooledD', 'pooledPoss',
                    'lastSeasonNet', 'lastSeasonO', 'lastSeasonD', 'lastSeasonPoss'])
        for r in rows:
            w.writerow([r['playerId'], r['name'], r['net'], r['O'], r['D'], r['poss'], 0, 0, 0, 0])
    return len(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    man = {'new': {}, 'existing': {}}
    names = names_for([f'{y}-{(y + 1) % 100:02d}' for y in range(2014, 2022)])
    reader = lambda s: open(ROOT / f'reports/defense-seventh/{s}/stints/stints.jsonl', encoding='utf-8')
    for tag, seasons in NEW.items():
        t0 = time.time()
        dst = OUT / f'rapm-{tag}.csv'
        obs = list(rapm.observations(seasons, reader))
        players = sorted({p for o in obs for p in o[2] + o[3]})
        fit, info = rapm.fit_rapm(obs, players)
        with open(dst, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['playerId', 'name', 'net', 'O', 'D', 'poss'])
            for p in sorted(fit, key=lambda p: -fit[p]['net']):
                v = fit[p]
                w.writerow([p, names.get(p, ''), round(v['net'], 3), round(v['O'], 3),
                            round(v['D'], 3), round(v['poss'])])
        n = to_pipe(dst, OUT / f'pipe-{tag}.csv')
        man['new'][tag] = {'seasons': seasons, 'observations': len(obs), 'players': len(players),
                           'lambda': info['lambda'], 'cv': info['cvWeightedMSE'],
                           'sha256': sha(dst), 'pipeSha256': sha(OUT / f'pipe-{tag}.csv'),
                           'seconds': round(time.time() - t0, 1)}
        print(tag, len(obs), len(players), info['lambda'], f'{time.time() - t0:.0f}s', flush=True)
    for tag in EXISTING:
        src = HIST / f'rapm-{tag}.csv'
        n = to_pipe(src, OUT / f'pipe-{tag}.csv')
        man['existing'][tag] = {'source': src.relative_to(ROOT).as_posix(), 'sourceSha256': sha(src),
                                'rows': n, 'pipeSha256': sha(OUT / f'pipe-{tag}.csv')}
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
