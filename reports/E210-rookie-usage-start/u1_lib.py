"""E-210 U1（新秀 usage 層起點先驗）共用函式。不改任何 live/ 檔、build_2k_start.py、CURRENT.json、src/。
載入方式沿用 E-208 的 e208_lib（live 程式以 git HEAD 取原始碼）；U1 只替換 chain_rookie 的 usage 層權重。
U1：pn = p + (1−w)·(full(L0) − p) + w·(full(L̂) − p)，w = min(N/10, 1)；L0 = log1p(mpg0)（E-116 凍結的 mpg0 中位數）、
L̂ = log1p(MPGhat)（現行管線的視窗收縮值）；p 是同一時刻的 pred0＋防守加成。N=0 時 MPGhat=mpg0 → pn = full(L0)，N≥10 → 與 B0 完全相同。
子程序：無（e208_lib 內的 git 呼叫都帶 CREATE_NO_WINDOW）。"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'E208-rookie-start-recheck'))
import e208_lib as L  # noqa: E402

RW = L.RW
B2 = L.B2
_CHAIN0 = RW.chain_rookie           # B0（現行）
BIG = 10 ** 6


def chain_u1(ns, pw, anc, r_repl, cur, pos, n_games, dl, coef, d):
    """cur 需帶 mpg0。借用現行 chain_rookie 算 p（n=0）與 full(L)（n 很大 → 權重 1），只重組權重，不複製公式。"""
    m0, mh = cur['mpg0'], cur['mpgHat']
    c0 = _CHAIN0(ns, pw, anc, r_repl, cur, pos, 0, dl, coef, d)
    p = c0['pred']
    f_hat = _CHAIN0(ns, pw, anc, r_repl, cur, pos, BIG, dl, coef, d)['predNew']
    f_pri = _CHAIN0(ns, pw, anc, r_repl, dict(cur, mpgHat=m0), pos, BIG, dl, coef, d)['predNew']
    w = min(n_games / RW.USAGE_N, 1.0)
    pn = p + (1 - w) * (f_pri - p) + w * (f_hat - p)
    g = (pn - r_repl) * ns['sat_w'](mh)
    return dict(c0, predNew=pn, g=g, ovr=ns['e064_map'](g, anc), full_prior=f_pri, full_hat=f_hat)


def patch_live(mpg0_by_pid):
    """live 主流程用：把 RW.chain_rookie 換成 U1（write_outputs 呼叫時 cur 沒有 mpg0 → 用 pid 查表）。"""
    def wrapper(ns, pw, anc, r_repl, cur, pos, n_games, dl, coef, d):
        return chain_u1(ns, pw, anc, r_repl, dict(cur, mpg0=mpg0_by_pid[cur['pid']]), pos, n_games, dl, coef, d)
    RW.chain_rookie = wrapper


def n0_ovr(en, rk, chain):
    """沒有數據（N=0）時，經 chain 的 OVR（B0 的 chain 在 n=0 權重 0＝eval_rookie 的 ovr）。"""
    e = RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, rk, None, 'e116', en.rel)
    cur = {'pid': rk['playerId'], 'pred0': e['pred0'], 'mpgHat': e['mpgHat'], 'mpg0': rk['mpg0']}
    return chain(en.ns, en.pw, en.anc, en.r_repl, cur, rk['pos'], 0, {}, en.coef, 0.0)['ovr']


def solve_u1(en, rk, target):
    """build_2k_start.solve 的同法（60 次二分），N=0 的目標改成「含 full_prior 的 OVR」。"""
    def ovr(d):
        return n0_ovr(en, dict(rk, x0=B2.shifted(rk['x0'], d)), chain_u1)
    lo, hi = -80.0, 80.0
    assert ovr(lo) < target < ovr(hi), (rk['name'], target, ovr(lo), ovr(hi))
    for _ in range(60):
        mid = (lo + hi) / 2
        if ovr(mid) < target:
            lo = mid
        else:
            hi = mid
    d = (lo + hi) / 2
    return d, ovr(d)


def make_rk_u1(en, pid, name, pick, pos, kind, season):
    b = en.bio[pid]
    h = float(b['PLAYER_HEIGHT_INCHES'])
    x0, k = L.x0_shape(en, pick, pos)
    rk = {'playerId': pid, 'name': name, 'pick': pick, 'pos': pos, 'heightInches': h, 'mpg0': en.mpg0, 'x0': x0, 'k': k}
    T = L.curve(pick)
    d, ov = solve_u1(en, rk, T)
    rk['x0'] = B2.shifted(x0, d)
    rk.update(T=T, delta=d, start=ov, season=season, kind=kind)
    return rk


def window_ovr2(en, rk, rec, arm, chain):
    """回傳 dict(raw=只資料, ovr=經 chain 的線上算法)；chain＝_CHAIN0（B0）或 chain_u1。"""
    e = RW.eval_rookie(en.ns, en.pw, en.anc, en.r_repl, rk, rec, arm, en.rel)
    cur = {'pid': rk['playerId'], 'pred0': e['pred0'], 'mpgHat': e['mpgHat'], 'mpg0': rk['mpg0']}
    n = rec['GP'] if rec else 0
    ch = chain(en.ns, en.pw, en.anc, en.r_repl, cur, rk['pos'], n, {}, en.coef, 0.0)
    return {'raw': e['ovr'], 'ovr': ch['ovr'], 'mpgHat': e['mpgHat'], 'n': n}
