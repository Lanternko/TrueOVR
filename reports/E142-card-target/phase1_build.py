"""E-142 第 1 階段：建 T0/T1/T4/T5/T6 × 四原點的卡片（候選值＝t 季單季值，見 report 的解讀聲明）。
用法：python -I phase1_build.py [候選...]     工作目錄 phase1-work/<候選>/，每個候選獨立（E142_WORK），不碰第 0 階段的 work/。
輸出 phase1-work/cands/<T>-<季>.pkl（{playerId:(net,O,D)}）與 phase1-work/<T>/build-<季>.json。
T6：T4、T5 各分量（O、D）季內 z 分數（兩者都有的球員）平均後再標準化，乘上 T4、T5 該分量標準差的平均回到每百回合單位；net＝O＋D。
"""
import csv, os, pickle, statistics as st, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EI = ROOT / 'data/external-impact'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26']
PW = HERE / 'phase1-work'


def load(kind, s):
    p = {'T1': ('epm_self/epm_%s.csv', 'net', 'O', 'D'), 'T4': ('darko/darko_%s.csv', 'dpm', 'o_dpm', 'd_dpm'),
         'T5': ('bpm/bpm_%s.csv', 'bpm', 'obpm', 'dbpm')}[kind]
    out = {}
    for r in csv.DictReader(open(EI / (p[0] % s), encoding='utf-8-sig')):
        try:
            out[int(r['playerId'])] = (float(r[p[1]]), float(r[p[2]]), float(r[p[3]]))
        except (ValueError, KeyError):
            pass
    return out


def t6(a, b):
    ids = sorted(set(a) & set(b))
    res = {i: [0.0, 0.0] for i in ids}
    for k in (1, 2):
        xa, xb = [a[i][k] for i in ids], [b[i][k] for i in ids]
        ma, sa, mb, sb = st.mean(xa), st.pstdev(xa), st.mean(xb), st.pstdev(xb)
        z = [((x - ma) / sa + (y - mb) / sb) / 2 for x, y in zip(xa, xb)]
        mz, sz = st.mean(z), st.pstdev(z)
        sc = (sa + sb) / 2
        for i, v in zip(ids, z):
            res[i][k - 1] = (v - mz) / sz * sc
    return {i: (v[0] + v[1], v[0], v[1]) for i, v in res.items()}


def cands():
    (PW / 'cands').mkdir(parents=True, exist_ok=True)
    for s in SEASONS:
        d = {'T1': load('T1', s), 'T4': load('T4', s), 'T5': load('T5', s)}
        d['T6'] = t6(d['T4'], d['T5'])
        for k, v in d.items():
            pickle.dump(v, open(PW / 'cands' / f'{k}-{s}.pkl', 'wb'))
            print(k, s, len(v), flush=True)


def build(job):
    k, s = job
    wd = PW / k
    wd.mkdir(parents=True, exist_ok=True)
    pk = 'none' if k == 'T0' else str(PW / 'cands' / f'{k}-{s}.pkl')
    env = dict(os.environ, E142_WORK=str(wd), PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(HERE / 'build_card_t.py'), 'cand', pk, s],
                       env=env, capture_output=True, text=True, encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    print(k, s, 'rc', r.returncode, (r.stdout or '')[-200:], (r.stderr or '')[-300:], flush=True)
    return k, s, r.returncode


if __name__ == '__main__':
    ks = sys.argv[1:] or ['T0', 'T1', 'T4', 'T5', 'T6']
    cands()
    jobs = [(k, s) for k in ks for s in SEASONS]
    with ThreadPoolExecutor(4) as ex:   # 不同候选/原點目錄互不重疊；同一候選的四原點用不同子目錄但共用 W，故每候選序列化見下
        pass
    # 同一候選共用 E142_WORK，build-c0／各季目錄皆不衝突（c0 與 hist 目錄名不同），但 RT.run_calib 的暫存以 tag 區分，故可並行
    with ThreadPoolExecutor(4) as ex:
        rs = list(ex.map(build, jobs))
    sys.exit(1 if any(r[2] for r in rs if r[0] != 'T0') else 0)
