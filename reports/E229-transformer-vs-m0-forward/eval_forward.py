"""E-229 前向評估：T vs M0（2026-27）。凍結前拒絕執行（缺 FREEZE.txt）；已完賽且凍結後記錄的場次不足 --min-games 也拒絕。
  python -I -X utf8 eval_forward.py [--min-games 400] [--log-dir log] [--results ../../data/defense-seventh/2026-27/league.json] [--out eval-forward.json]
FREEZE.txt 第一行＝凍結時間（ISO，含時區）。只用 generated >= 凍結時間、非 -smoke 的記錄；每場取開賽前最後一筆（generated < tipoff）。
p＝Φ((邊際±H)/σ)（H=2.5、σ=12，記錄裡已算好 pT／pM0）。Brier 逐場；成對場次 bootstrap 2000 次、rng 20261102、5／95 百分位＝90% 區間。
只做顯式 import，不用 star import（E-228 的 HERE 被覆寫事故）。"""
import argparse, glob, json, math, os, sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MDE_B = 0.013        # 凍結 2026-11-04（preregistration.md J1）
CAL_MAX = 0.15       # 凍結 2026-11-04（preregistration.md J2）


def parse_t(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def load_records(log_dir, freeze_t):
    best = {}
    for f in sorted(glob.glob(os.path.join(log_dir, '????-??-??.json'))):      # 不含 -smoke
        for r in json.load(open(f, encoding='utf-8'))['records']:
            if r.get('smoke'):
                continue
            g = parse_t(r['generated']); tip = parse_t(r['tipoff'])
            if g < freeze_t or g >= tip:
                continue
            if r['game_id'] not in best or g > parse_t(best[r['game_id']]['generated']):
                best[r['game_id']] = r
    return best


def load_results(path):
    out = {}
    for g in json.load(open(path, encoding='utf-8'))['schedule']:
        o = g.get('observed')
        if o and o.get('homeScore') is not None and o.get('awayScore') is not None and o['homeScore'] != o['awayScore']:
            out[g['id']] = 1.0 if o['homeScore'] > o['awayScore'] else 0.0
    return out


def calibration(p, y, bins=5):
    o = np.argsort(p, kind='stable'); res = []
    for ix in np.array_split(o, bins):
        res.append(dict(n=int(len(ix)), meanP=float(p[ix].mean()), freq=float(y[ix].mean()), dev=float(abs(p[ix].mean() - y[ix].mean()))))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-games', type=int, default=400)
    ap.add_argument('--log-dir', default=os.path.join(HERE, 'log'))
    ap.add_argument('--results', default=os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data', 'defense-seventh', '2026-27', 'league.json'))
    ap.add_argument('--freeze', default=os.path.join(HERE, 'FREEZE.txt'))
    ap.add_argument('--out', default=os.path.join(HERE, 'eval-forward.json'))
    a = ap.parse_args()
    if not os.path.exists(a.freeze):
        sys.exit('拒絕：預註冊尚未凍結（缺 FREEZE.txt），不得以真實結果評估')
    freeze_t = parse_t(open(a.freeze, encoding='utf-8').readline().strip())
    recs = load_records(a.log_dir, freeze_t); res = load_results(a.results)
    ids = sorted(g for g in recs if g in res)
    n = len(ids)
    if n < a.min_games:
        sys.exit(f'拒絕：凍結後記錄且已完賽的場次 {n} < {a.min_games}')
    y = np.array([res[g] for g in ids]); pT = np.array([recs[g]['pT'] for g in ids]); pM = np.array([recs[g]['pM0'] for g in ids])
    pX = 0.5 * pT + 0.5 * pM
    eps = 1e-6
    def brier(p): return (p - y) ** 2
    def ll(p): q = np.clip(p, eps, 1 - eps); return -(y * np.log(q) + (1 - y) * np.log(1 - q))
    out = dict(n=n, freeze=freeze_t.isoformat(), firstDate=min(recs[g]['date'] for g in ids), lastDate=max(recs[g]['date'] for g in ids),
               brier=dict(T=float(brier(pT).mean()), M0=float(brier(pM).mean()), MIX=float(brier(pX).mean())),
               logloss=dict(T=float(ll(pT).mean()), M0=float(ll(pM).mean()), MIX=float(ll(pX).mean())),
               calibration=dict(T=calibration(pT, y), M0=calibration(pM, y), MIX=calibration(pX, y)))
    rng = np.random.default_rng(20261102); boots = [rng.integers(0, n, n) for _ in range(2000)]
    def pair(u, v):
        d = np.array([(u[ix] - v[ix]).mean() for ix in boots])
        return dict(diff=float((u - v).mean()), lo=float(np.percentile(d, 5)), hi=float(np.percentile(d, 95)))
    out['pairs'] = {'brier T-M0': pair(brier(pT), brier(pM)), 'brier MIX-M0': pair(brier(pX), brier(pM)),
                    'logloss T-M0': pair(ll(pT), ll(pM)), 'logloss MIX-M0': pair(ll(pX), ll(pM))}
    out['maxCalDev'] = {k: max(b['dev'] for b in v) for k, v in out['calibration'].items()}
    if MDE_B is not None and CAL_MAX is not None:
        out['judgment'] = {'J1 不更差': bool(out['pairs']['brier T-M0']['hi'] < MDE_B), 'J2 校準不壞': bool(out['maxCalDev']['T'] <= CAL_MAX),
                           'report: T 優於 M0 (上界<0)': bool(out['pairs']['brier T-M0']['hi'] < 0)}
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
