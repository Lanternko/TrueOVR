"""E-309 (c)：RIM／DEF 顯示欄加 rimDet（prereg.md 凍結後只跑一次）。只讀不寫線上檔；輸出 results/display.json。
  python -I -X utf8 reports/E309-zone-deterrence/e309_display.py   （cwd＝主 checkout；DATA_ROOT 同 build_rimdet）"""
import csv, json, os, sys, unicodedata
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('DATA_ROOT', 'D:/Projects/CODING/basketball-autochess'))
sys.path.insert(0, str(ROOT / 'scripts'))
import rim_blk_live as RB  # noqa: E402
import season_nav as sn  # noqa: E402

RIM_ARMS = {'R0': 0.0, 'RZ20': 0.20, 'RZ35': 0.35}
DEF_ARMS = {'D0': 0.0, 'DZ10': 0.10, 'DZ20': 0.20}
SHOW = ('Victor Wembanyama', 'Nikola Jokić', 'Neemias Queta', 'Isaiah Stewart', 'Rudy Gobert')


def nm(x):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', x) if not unicodedata.combining(ch)).lower().replace('.', '').replace(' jr', '').replace(' iii', '').replace(' ii', '').strip()


def avg_rank(x):
    x = np.asarray(x, float); o = np.argsort(x, kind='stable'); r = np.empty(len(x)); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[o[j + 1]] == x[o[i]]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2; i = j + 1
    return r


def spearman(a, b):
    return float(np.corrcoef(avg_rank(a), avg_rank(b))[0, 1])


def rimdet(tag):
    return {r['pid']: float(r['rimDet']) for r in csv.DictReader(open(HERE / 'data' / f'rimdet-{tag}.csv', encoding='utf-8'))}


def mix(base, rz, pool, w):
    """(1−w)·z(base)＋w·z(rimDet)，z 在人群內（rimDet 缺＝0），人群內重標準化後套回 base 的人群平均與標準差。"""
    if w == 0:
        return dict(base)
    pp = [p for p in pool if p in base]
    b = np.array([base[p] for p in pp]); mb, sb = b.mean(), b.std()
    zv = np.array([rz[p] for p in pp if p in rz]); mz, sz = zv.mean(), zv.std()
    sc = {p: (1 - w) * (base[p] - mb) / sb + w * ((rz[p] - mz) / sz if p in rz else 0.0) for p in base}
    ps = np.array([sc[p] for p in pp]); m, s = ps.mean(), ps.std()
    return {p: float(mb + sb * (sc[p] - m) / s) for p in base}


def evaluate(disp, pool, pos, name, targets):
    pp = [p for p in pool if p in disp]
    ordr = sorted(pp, key=lambda p: -disp[p]); rank = {p: i + 1 for i, p in enumerate(ordr)}
    pfc = [p for p in ordr if pos[p] in ('PF', 'C')]
    out = {'top10PFC': [(name[p], pos[p], round(disp[p], 1)) for p in pfc[:10]],
           'show': {name[p]: (rank[p], round(disp[p], 1)) for p in pp if name[p] in SHOW}, 'rho': {}}
    for tn, tv in targets.items():
        for g, f in (('all', lambda p: True), ('PFC', lambda p: pos[p] in ('PF', 'C'))):
            sel = [p for p in pp if p in tv and f(p)]
            out['rho'][f'{tn}/{g}'] = (round(spearman([disp[p] for p in sel], [tv[p] for p in sel]), 4), len(sel))
    return out


def judge(res, arms, base):
    v = {}
    for a in arms:
        if a == base:
            continue
        d = {f'{s}:{k}': round(r[0] - res[s][base]['rho'][k][0], 4) for s in res for k, r in res[s][a]['rho'].items()}
        pfc = d.get('2026-27:EPM_D/PFC')
        v[a] = {'delta': d, 'noWorse': all(x >= -0.02 for x in d.values()), 'failItems': [k for k, x in d.items() if x < -0.02],
                'pfcEpmGain': pfc, 'pass': all(x >= -0.02 for x in d.values()) and pfc >= 0.01,
                'pfcEpm': res['2026-27'][a]['rho']['EPM_D/PFC'][0]}
    ok = {a: x for a, x in v.items() if x['pass']}
    chosen = None
    if ok:
        best = max(x['pfcEpm'] for x in ok.values())
        chosen = min((a for a, x in ok.items() if best - x['pfcEpm'] <= 0.003), key=lambda a: arms[a])
    v['_chosen'] = chosen
    return v


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    live = ROOT / 'reports/ovr-inseason-2026-27/live'
    day = os.environ.get('E309_DAY') or max(p.parent.name for p in live.glob('2026-*/t-swap.json')); ld = live / day
    meta = json.loads((ld / 'meta.json').read_text(encoding='utf-8'))
    rows = list(csv.DictReader((ld / 'ranking.csv').open(encoding='utf-8')))
    ts = json.loads((ld / 't-swap.json').read_text(encoding='utf-8'))
    pool = set(ts['pool'])
    pos = {r['playerId']: r['pos'] for r in rows}; name = {r['playerId']: r['name'] for r in rows}
    epm = {r['playerId']: float(r['D']) for r in csv.DictReader(open(ROOT / 'reports/impact-epm-2026-27/epm-live.csv', encoding='utf-8'))}
    tdef = {k: -v for k, v in ts['oppPts100'].items()}
    tg = {'EPM_D': epm, 'T_DEF': tdef}
    rz = rimdet('live')
    # ---- RIM 2026-27：現行 D30（和網站同一個函式） ----
    help_ = {int(r['playerId']): float(r['help']) for r in rows if r['help'] != ''}
    rb = RB.compute(help_, {int(p) for p in pool}, meta['window8']['gamesDone'], meta['dataCutoff'], ROOT / 'data/season-source-2026-27/player-games.json')
    assert rb, 'RB.compute 失敗'
    rim0 = {str(p): v for p, v in rb.items()}
    rim = {'2026-27': {a: evaluate(mix(rim0, rz, pool, w), pool, pos, name, tg) for a, w in RIM_ARMS.items()}}
    # ---- RIM 2025-26 卡片頁 ----
    card = list(csv.DictReader(open(ROOT / 'reports/card-0.2.15/ranking.csv', encoding='utf-8')))
    rs = json.loads((ROOT / 'data/season-source/player-games.json').read_text(encoding='utf-8'))['data']['resultSets']
    t = rs[0] if isinstance(rs, list) else rs; h = {k: i for i, k in enumerate(t['headers'])}
    pid_of = {nm(r[h['PLAYER_NAME']]): str(r[h['PLAYER_ID']]) for r in t['rowSet']}
    c_rows = [dict(r, _pid=pid_of.get(nm(r['name']))) for r in card if r['help'] != '']
    c_rows = [r for r in c_rows if r['_pid']]
    pool2 = {r['_pid'] for r in c_rows if float(r['mpg'] or 0) >= sn.POOL_MPG}
    rb2 = RB.compute({int(r['_pid']): float(r['help']) for r in c_rows}, {int(p) for p in pool2})
    assert rb2, 'RB.compute 2025-26 失敗'
    rim0b = {str(p): v for p, v in rb2.items()}
    pos2 = {r['_pid']: r['pos'] for r in c_rows}; name2 = {r['_pid']: r['name'] for r in c_rows}
    e2 = {nm(r['name']): float(r['D']) for r in csv.DictReader(open(ROOT / 'data/external-impact/epm_self/epm_2025-26.csv', encoding='utf-8'))}
    epm2 = {r['_pid']: e2[nm(r['name'])] for r in c_rows if nm(r['name']) in e2}
    rz2 = rimdet('card-2025-26')
    rim['2025-26'] = {a: evaluate(mix(rim0b, rz2, pool2, w), pool2, pos2, name2, {'EPM_D': epm2}) for a, w in RIM_ARMS.items()}
    # ---- DEF 2026-27：現行 off_def＋blend_t ----
    od, bad = sn.off_def(rows, 'playerId'); od, n_t = sn.blend_t(od, ts)
    def0 = {p: v[1] for p, v in od.items() if v[1] is not None}
    dfn = {'2026-27': {a: evaluate(mix(def0, rz, pool, w), pool, pos, name, tg) for a, w in DEF_ARMS.items()}}
    out = {'day': day, 'pool': len(pool), 'pool2025_26': len(pool2), 'offDefBad': bad, 'blendT': n_t,
           'rimDetCoverage': {'2026-27': sum(p in rz for p in pool), '2025-26': sum(p in rz2 for p in pool2)},
           'RIM': rim, 'DEF': dfn, 'verdict': {'RIM': judge(rim, RIM_ARMS, 'R0'), 'DEF': judge(dfn, DEF_ARMS, 'D0')}}
    (HERE / 'results').mkdir(exist_ok=True)
    (HERE / 'results' / os.environ.get('E309_OUT', 'display.json')).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('day', 'pool', 'pool2025_26', 'offDefBad', 'blendT', 'rimDetCoverage')}, ensure_ascii=False))
    for col in ('RIM', 'DEF'):
        for s, arms in out[col].items():
            for a, r in arms.items():
                print(col, s, a, r['rho'], r['show'])
        print(col, 'verdict', json.dumps(out['verdict'][col], ensure_ascii=False))
    for col in ('RIM', 'DEF'):
        for a, r in out[col]['2026-27'].items():
            print(col, a, 'PF/C top10', [x[0] for x in r['top10PFC']])


if __name__ == '__main__':
    main()
