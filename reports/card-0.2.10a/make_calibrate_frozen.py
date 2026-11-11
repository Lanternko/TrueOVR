"""由 0.2.9a 的 calibrate_wing_t.py 產生 calibrate_frozen.py：只加 --frozenSummary／--frozenPergame 兩個開關（lead 裁定 B＋全凍結，2026-11-01）。
凍結模式：回歸係數、屬性 mean/SD、PR1/PR50/PR99 錨點、r_repl 與 pergame 錨點全用 0.2.9a 部件卡的值；不帶旗標時與原檔相同。
用法：python -I -X utf8 make_calibrate_frozen.py"""
from pathlib import Path
H = Path(__file__).resolve().parent
SRC = H.parents[0] / 'card-0.2.9+E164-no-stamina' / 'calibrate_wing_t.py'
s = SRC.read_text(encoding='utf-8')

def rep(old, new):
    global s
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)

rep("ROOT = Path(__file__).resolve().parents[2]   # E-134：複本在 reports/<dir>/stage1/",
    "ROOT = Path(__file__).resolve().parents[2]   # E-134：複本在 reports/<dir>/stage1/\nFROZEN = None   # card 0.2.10：{'sum': 0.2.9a 部件卡 summary.json, 'pg': pergame-summary.json}")
# 1) 凍結回歸
rep("""    form, lam = BLEND_FORM, BLEND_LAM
    grid = {f'{form}|{lam}': cv_score(rows, form, lam)}
""", """    global FROZEN
    if '--frozenSummary' in argv:
        FROZEN = {'sum': json.loads(Path(argv[argv.index('--frozenSummary') + 1]).read_text(encoding='utf-8')),
                  'pg': json.loads(Path(argv[argv.index('--frozenPergame') + 1]).read_text(encoding='utf-8'))}
    form, lam = BLEND_FORM, BLEND_LAM
    grid = {} if FROZEN else {f'{form}|{lam}': cv_score(rows, form, lam)}
""")
rep("""    X, mean, sd = design(rows, form)
    s2 = residual_variance(rows, X, y, lam)
    w = weights(rows, s2)
    b = wfit(X, y, w, lam)
    rng = np.random.default_rng(20261017); boots = []
    for _ in range(500):
        i = rng.integers(0, len(y), len(y)); boots.append(wfit(X[i], y[i], w[i], lam))
    boots = np.array(boots)
""", """    if FROZEN:
        fm = FROZEN['sum']['formula']
        assert list(fm['attributeMean'].keys()) == ATTRS and list(fm['attributeSD'].keys()) == ATTRS, '凍結公式的屬性順序與本次 ATTRS 不同'
        mean0 = np.array([fm['attributeMean'][a] for a in ATTRS]); sd0 = np.array([fm['attributeSD'][a] for a in ATTRS])
        X, mean, sd = design(rows, form, mean0, sd0)
        b = np.array([fm['intercept']] + list(fm['coefficientsOnStandardized']))
        assert len(b) == X.shape[1] + 1, '凍結係數長度與設計矩陣不符'
        s2 = None; boots = None
    else:
        X, mean, sd = design(rows, form)
        s2 = residual_variance(rows, X, y, lam)
        w = weights(rows, s2)
        b = wfit(X, y, w, lam)
        rng = np.random.default_rng(20261017); boots = []
        for _ in range(500):
            i = rng.integers(0, len(y), len(y)); boots.append(wfit(X[i], y[i], w[i], lam))
        boots = np.array(boots)
""")
# 2) 錨點
rep("    p1, p50, p99 = q(1), q(50), q(99)\n    ovr = np.where(pred <= p50",
    "    p1, p50, p99 = q(1), q(50), q(99)\n    refit_anchors = (float(p1), float(p50), float(p99))\n    if FROZEN:\n        fa = FROZEN['sum']['scaleAnchorsPer36']; p1, p50, p99 = fa['PR1'], fa['PR50'], fa['PR99']\n    ovr = np.where(pred <= p50")
rep("""'bootstrapSE': float(np.std(boots[:, 1 + i]) / sd[i] * 10)}""", """'bootstrapSE': None if boots is None else float(np.std(boots[:, 1 + i]) / sd[i] * 10)}""")
rep("""        'scaleAnchorsPer36': {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)},""",
    """        'scaleAnchorsPer36': {'PR1': float(p1), 'PR50': float(p50), 'PR99': float(p99)},
        **({'frozen': {'anchorsIfRefitOnThisPred': dict(zip(('PR1', 'PR50', 'PR99'), refit_anchors))}} if FROZEN else {}),""")
# 3) pergame
rep("    r_repl = qf(np.asarray(pred), 10)\n", "    r_repl = FROZEN['pg']['rRepl_PR10_of_pred'] if FROZEN else qf(np.asarray(pred), 10)\n    r_repl_refit = qf(np.asarray(pred), 10)\n")
rep("        p1, p50, p99 = qf(g, 1), qf(g, 50), qf(g, 99)\n        anchors[tag] = {'PR1': p1, 'PR50': p50, 'PR99': p99}\n",
    "        p1, p50, p99 = qf(g, 1), qf(g, 50), qf(g, 99)\n        if FROZEN:\n            fa = FROZEN['pg']['anchors'][tag]; p1, p50, p99 = fa['PR1'], fa['PR50'], fa['PR99']\n        anchors[tag] = {'PR1': p1, 'PR50': p50, 'PR99': p99}\n")
rep("        'rRepl_PR10_of_pred': r_repl, 'anchors': anchors,", "        'rRepl_PR10_of_pred': r_repl, 'rRepl_if_refit_on_this_pred': r_repl_refit, 'frozen': bool(FROZEN), 'anchors': anchors,")
s = '"""card 0.2.10 凍結版 calibrate（make_calibrate_frozen.py 由 0.2.9a calibrate_wing_t.py 產生；不要手改）。"""\n' + s
(H / 'calibrate_frozen.py').write_text(s, encoding='utf-8')
print('ok', len(s))
