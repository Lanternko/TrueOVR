"""E-187 改疊 0.2.10a：E-186 e186_cands.py 原樣複本，讀修正後（L-102，17:20 重產）的 T6 候選。
E-186 目標 T6R：T6R = mean(T6) + sd(T6) * (0.5*z(T6) + 0.5*z(T0))，O、D 分別算，net = O + D（預註冊 §1）。
z 在每季、卡片擬合人群內算＝(T6 候選) ∩ (該原點 T0 rapm 檔的列)，也就是 swap_rapm 會留下的那批人；平均與標準差用母體標準差（同 phase1_build.t6）。
T0＝該原點的四季合併 RAPM 檔（歷史原點 stage1/work/<季>/rapm-R.csv；2025-26 reports/impact-rapm/rapm.csv）的 pooledO／pooledD。
輸出 work/cands/T6R-<季>.pkl（{playerId:(net,O,D)}）與 work/cands/summary.json。用法（repo root）：python -I -B -X utf8 <本檔>"""
import csv, hashlib, json, pickle, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
S1W = ROOT / 'reports/card-0.2.7c+E134-rolling-prior/stage1/work'
T6D = ROOT / 'reports/E142-card-target/phase1-work/cands'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
W = 0.5


def t0_path(t):
    return ROOT / 'reports/impact-rapm/rapm.csv' if t == '2025-26' else S1W / t / 'rapm-R.csv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    out = {}
    for t in SEASONS:
        t6 = pickle.load(open(T6D / f'T6-{t}.pkl', 'rb'))
        t0 = {int(r['playerId']): (float(r['pooledO']), float(r['pooledD'])) for r in csv.DictReader(open(t0_path(t), encoding='utf-8-sig'))}
        ids = sorted(set(t6) & set(t0))
        res = {i: [0.0, 0.0] for i in ids}
        for k in (0, 1):
            a = [t6[i][k + 1] for i in ids]
            b = [t0[i][k] for i in ids]
            ma, sa, mb, sb = st.mean(a), st.pstdev(a), st.mean(b), st.pstdev(b)
            for i, x, y in zip(ids, a, b):
                res[i][k] = ma + sa * (W * (x - ma) / sa + (1 - W) * (y - mb) / sb)
        cand = {i: (v[0] + v[1], v[0], v[1]) for i, v in res.items()}
        pickle.dump(cand, open(HERE / 'work/cands' / f'T6R-{t}.pkl', 'wb'))
        cor = [st.correlation([t6[i][k + 1] for i in ids], [t0[i][k] for i in ids]) for k in (0, 1)]
        out[t] = {'n_T6': len(t6), 'n_T0': len(t0), 'n_pop': len(ids), 'T0_file': t0_path(t).relative_to(ROOT).as_posix(), 'T0_sha256': sha(t0_path(t)),
                  'corr_T6_T0_O_D': cor, 'sd_T6R_over_sd_T6_net': st.pstdev([cand[i][0] for i in ids]) / st.pstdev([t6[i][0] for i in ids])}
        print(t, out[t])
    (HERE / 'work/cands/summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
