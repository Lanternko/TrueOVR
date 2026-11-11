"""R-162 / E-230：2026 新秀起點加季前賽（PS）位移。使用者 2026-11-04 核可「現在就套用到線上」。
做法：從未位移的 rookie-prior-2026-e116.json 讀 x0，目標 = T(順位) + 1.51·D_PS，用 E-121 同一個二分法重解整體平移 δ（L-109：不是事後加在 OVR 上）。
D_PS = Σm·(gs36 − μ)/(Σm + 100)，只用 2026-27 季前賽（E-230 data/PS_2026-27.json.gz）；沒有 PS 記錄的人 D=0（照順位曲線）。
先用「位移 0」重解一遍，必須重現現行檔的 e121.delta（max |Δδ| ≤ 0.01），才寫檔。
舊檔先備份成 _retired/rookie-prior-2026-pre-ps.json（run_c4_live_rookie.PS_START=0 讀它）。
用法：python -I -X utf8 apply_ps_start.py
"""
import gzip
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import run_c4_live_rookie as RW  # noqa: E402

CURVE_A, CURVE_B = 73.0, 5.9
B_PS = 1.51                       # E-230 全樣本擬合 b（使用者 2026-11-04 核可用這個尺度）
SHRINK = 100.0
LO, HI = 0.0, 150.0
LIVE_JSON = HERE / 'rookie-prior-2026.json'
BASE_JSON = HERE / 'rookie-prior-2026-e116.json'
BACKUP = HERE / '_retired' / 'rookie-prior-2026-pre-ps.json'
PS_DATA = ROOT / 'reports/E230-sl-preseason-rookie-start/data/PS_2026-27.json.gz'


def ps_signal():
    j = json.load(gzip.open(PS_DATA, 'rt', encoding='utf-8'))
    h = {c: i for i, c in enumerate(j['headers'])}

    def gmsc(r):
        g = lambda c: (r[h[c]] or 0)
        return (g('PTS') + 0.4 * g('FGM') - 0.7 * g('FGA') - 0.4 * (g('FTA') - g('FTM')) + 0.7 * g('OREB')
                + 0.3 * g('DREB') + g('STL') + 0.7 * g('AST') + 0.7 * g('BLK') - 0.4 * g('PF') - g('TOV'))
    mins, gs, gp = {}, {}, {}
    for r in j['rows']:
        m = float(r[h['MIN']] or 0)
        if m <= 0:
            continue
        p = str(r[h['PLAYER_ID']])
        mins[p] = mins.get(p, 0.0) + m
        gs[p] = gs.get(p, 0.0) + gmsc(r)
        gp[p] = gp.get(p, 0) + 1
    mu = 36 * sum(gs.values()) / sum(mins.values())
    return {p: dict(D=mins[p] * (36 * gs[p] / mins[p] - mu) / (mins[p] + SHRINK), min=round(mins[p], 1), gp=gp[p]) for p in mins}, mu


def shifted(x0, d):
    return {a: min(max(v + d, LO), HI) for a, v in x0.items()}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ns = RW.load_ns()
    C, V2 = ns['C'], ns['V2']
    ns['setup']()
    rel = V2.load_reliability()
    pw = ns['PW'].for_start(C, 'S*')
    anc, r_repl = ns['e064_anchors']()

    def solve(rk, target):
        def ovr(d):
            return RW.eval_rookie(ns, pw, anc, r_repl, dict(rk, x0=shifted(rk['x0'], d)), None, 'e116', rel)['ovr']
        lo, hi = -80.0, 80.0
        assert ovr(lo) < target < ovr(hi), (rk['name'], target)
        for _ in range(60):
            mid = (lo + hi) / 2
            if ovr(mid) < target:
                lo = mid
            else:
                hi = mid
        d = (lo + hi) / 2
        return d, ovr(d)

    cur = json.load(open(LIVE_JSON, encoding='utf-8'))
    applied = 'ps' in cur['players'][0]      # 已套過：換版後重解，跳過重現檢查、不覆蓋備份
    live_delta = {rk['playerId']: rk['e121']['delta'] for rk in cur['players']}
    doc = json.load(open(BASE_JSON, encoding='utf-8'))
    sig, mu = ps_signal()

    # 1) 重現檢查：位移 0 → 必須重現現行 δ
    if not applied:
        worst = 0.0
        for rk in doc['players']:
            t0 = CURVE_A - CURVE_B * math.log(rk['pick'])
            d0, _ = solve(rk, t0)
            worst = max(worst, abs(d0 - live_delta[rk['playerId']]))
        print(f'重現檢查 max|Δδ| = {worst:.4f}')
        if worst > 0.01:
            raise SystemExit('位移 0 重解沒重現現行 δ，停止（不寫檔）')

    # 2) 套用位移
    if not applied:
        BACKUP.write_text(LIVE_JSON.read_text(encoding='utf-8'), encoding='utf-8')
    rows = []
    for rk in doc['players']:
        t0 = CURVE_A - CURVE_B * math.log(rk['pick'])
        s = sig.get(str(rk['playerId']))
        D = s['D'] if s else 0.0
        shift = B_PS * D
        base = RW.eval_rookie(ns, pw, anc, r_repl, rk, None, 'e116', rel)['ovr']
        d, got = solve(rk, t0 + shift)
        rk['x0'] = shifted(rk['x0'], d)
        rk['e121'] = {'twoK': None, 'target': round(t0 + shift, 2), 'delta': round(d, 3), 'ovrE116': round(base, 2)}
        rk['ps'] = {'D': round(D, 3), 'shift': round(shift, 2), 'minutes': s['min'] if s else 0, 'games': s['gp'] if s else 0,
                    'curve': round(t0, 2)}
        rows.append((rk['name'], rk['pick'], round(t0, 1), round(shift, 1), round(got, 1)))
    doc.update({'experiment': 'E-121+E-230', 'shift': None,
                'targetCurve': {'a': CURVE_A, 'b_lnPick': -CURVE_B, 'ruling': 'R-096', 'psShift': {'b': B_PS, 'shrink': SHRINK, 'mu': round(mu, 3), 'ruling': 'R-162'}},
                'note': doc.get('note', '') + '；R-096：x0 齊頭平移到 73 − 5.9·ln 順位；R-162：目標再加 1.51·D_PS（2026 季前賽，E-230），沒有 PS 記錄者 D=0'})
    json.dump(doc, open(LIVE_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'已寫 {LIVE_JSON.name}；舊檔備份 {BACKUP.name}；μ_PS={mu:.2f}')
    for r in sorted(rows, key=lambda r: -r[3]):
        print(f'{r[0]:24s} pick{r[1]:>3} 曲線{r[2]:5.1f} 位移{r[3]:+5.1f} 起點{r[4]:5.1f}')


if __name__ == '__main__':
    main()
