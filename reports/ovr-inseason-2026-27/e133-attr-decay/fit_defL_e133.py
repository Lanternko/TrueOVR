"""E-133（E-111 fit_defL.py 的副本，只改窗口＝Y1、Y2 需要的兩個 RAPM 窗 2014-15_2015-16、2014-15_2016-17；資料自 2014-15 起，窗口只含已有的季）。
E-111 回測用的單季防守 D 檔（def-L）：照 card 0.2.7 的 --defRapm（E-104 phase2_csv.py：e104fit.fit_w(D, 窗口, 'L')，λ=3000、逐場 u 線性權重），
只把窗口換成回測各起點用到的 RAPM 窗（pathA pipe-<窗>.csv 的四季；Y5、Y6 主判定＋Y3 敏感度）。

- 2014-15～2020-21 的 stint 照 E-079／E-104 的 rapm_recency.Data（reports/defense-seventh/<季>/stints/stints.jsonl，經 E079_CACHE 快取）。
- 2021-22 不在 rapm_recency.ALL_SEASONS；Y6 答案窗 2018-19_2021-22 需要它 → 用 v3/data/derived-2021-22/stints/stints.jsonl
  （同 prepare_defense_b1 格式），以 impact-rapm/rapm.py 的 observations() 讀（過濾規則相同）。偏差 D14 揭露。
- 先驗證：同一個 Data 物件擬合 card 窗 2022-23..2025-26，必須重現 def-L-primary.csv（|ΔD| 與 |Δposs| < 1e-6），否則停。
欄位同 def-L-primary.csv：playerId,name,D,poss(=possW),possUnweighted。
用法（repo 根目錄）：E079_CACHE=<快取> python -I -B -X utf8 reports/ovr-inseason-2026-27/e111-card027/fit_defL.py
"""
import csv
import hashlib
import importlib.util
import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E104 = ROOT / 'reports/card-0.2.5+E104-defense-pergame-decay'
_spec = importlib.util.spec_from_file_location('e104fit', E104 / 'e104fit.py')
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
RR = F.RR
S2122 = ROOT / 'reports/ovr-inseason-2026-27/v3/data/derived-2021-22/stints/stints.jsonl'
OUT = HERE / 'defL'
WINDOWS = {'2021-22_2022-23': ['2021-22', '2022-23'],
           '2021-22_2023-24': ['2021-22', '2022-23', '2023-24'],
           '2021-22_2024-25': ['2021-22', '2022-23', '2023-24', '2024-25']}
CARD_WINDOW = ['2022-23', '2023-24', '2024-25', '2025-26']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Data(RR.Data):
    """rapm_recency.Data ＋ 2021-22（其餘照抄 __init__）。"""

    def __init__(self):
        self.obs = pickle.load(open(RR.CACHE, 'rb'))
        assert set(self.obs) == set(RR.ALL_SEASONS), sorted(self.obs)
        self.obs['2021-22'] = list(RR.R.observations(['2021-22'], reader=lambda s: open(S2122, encoding='utf-8')))
        self.players = sorted({p for s in self.obs for o in self.obs[s] for p in o[2] + o[3]})
        self.pidx = {p: i for i, p in enumerate(self.players)}
        self.P = len(self.players)
        self.K = 2 * self.P
        self.s = {s: self._build(obs) for s, obs in self.obs.items()}


def names():
    out = {}
    for s in ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2021-22']:
        for r in csv.DictReader(open(ROOT / f'reports/ovr-inseason-2026-27/v5/history/box-totals-{s}.csv', encoding='utf-8')):
            out[int(r['playerId'])] = r['name']
    for r in csv.DictReader(open(ROOT / 'reports/impact-rapm/rapm.csv', encoding='utf-8')):
        out.setdefault(int(r['playerId']), r['name'])
    return out


def write(out, path, nm):
    with path.open('w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['playerId', 'name', 'D', 'poss', 'possUnweighted'])
        for pid, v in sorted(out.items(), key=lambda kv: -kv[1]['D']):
            wr.writerow([pid, nm.get(pid, ''), repr(v['D']), repr(v['possW']), repr(v['poss'])])


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    D = Data()
    print('data', D.P, {s: len(o) for s, o in D.obs.items()}, f'{time.time() - t0:.0f}s', flush=True)
    rep = {'cache': str(RR.CACHE), 'cacheSha256': sha(RR.CACHE), 'stints2021_22': S2122.relative_to(ROOT).as_posix(),
           'stints2021_22Sha256': sha(S2122), 'obs2021_22': len(D.obs['2021-22']), 'lambda': F.LAM, 'shape': 'L'}
    # 驗證：重現 card 0.2.7 的 def-L-primary.csv
    ref = {int(r['playerId']): r for r in csv.DictReader(open(E104 / 'def-L-primary.csv', encoding='utf-8'))}
    got, _, _ = F.fit_w(D, CARD_WINDOW, 'L')
    dD = max(abs(got[p]['D'] - float(ref[p]['D'])) for p in ref)
    dP = max(abs(got[p]['possW'] - float(ref[p]['poss'])) for p in ref)
    rep['reproduceDefLPrimary'] = {'players': len(ref), 'samePlayers': set(got) == set(ref), 'maxAbsD': dD, 'maxAbsPossW': dP,
                                   'pass': bool(set(got) == set(ref) and dD < 1e-6 and dP < 1e-6)}
    print('reproduce', rep['reproduceDefLPrimary'], f'{time.time() - t0:.0f}s', flush=True)
    if not rep['reproduceDefLPrimary']['pass']:
        (HERE / 'defL-summary-e133.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
        return 3
    nm = names()
    rep['windows'] = {}
    for tag, W in WINDOWS.items():
        _, chk = F.game_u(D, W)
        out, c, share = F.fit_w(D, W, 'L')
        p = OUT / f'def-L-{tag}.csv'
        write(out, p, nm)
        rep['windows'][tag] = {'seasons': W, 'players': len(out), 'intercept': c, 'seasonShare': share, 'uCheck': chk,
                               'sha256': sha(p)}
        print(tag, len(out), chk['pass'], f'{time.time() - t0:.0f}s', flush=True)
    (HERE / 'defL-summary-e133.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
