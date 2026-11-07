"""team_badness 原樣複製自 E-153 e153_build.py（連續 d，E-147 公式）。"""
def team_badness(M, tg_path):
    tg = M.jload(tg_path)['data']['resultSets'][0]
    h = tg['headers']
    it, iw, ipm = h.index('TEAM_ID'), h.index('WL'), h.index('PLUS_MINUS')
    acc = {}
    for r in tg['rowSet']:
        a = acc.setdefault(r[it], [0, 0, 0.0])
        a[0] += 1; a[1] += r[iw] == 'W'; a[2] += float(r[ipm])
    out = {}
    for t, (gp, w, pm) in acc.items():
        nr, wp = pm / (gp + 10), (w + 5) / (gp + 10)
        s = 0.7 * (0.5 + 0.033 * nr) + 0.3 * wp
        out[t] = {'d': min(1.0, max(0.0, (0.40 - s) / 0.10)), 'gp': gp}
    return out
