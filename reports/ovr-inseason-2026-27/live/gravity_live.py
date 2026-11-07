"""inseason 0.2.10j（R-134／R-135，E-200）：賽中端能力值 gravity（無球外線引力）。
  原始值：NBA.com gravityleaders 的 AVGOFFBALLPERIMETERGRAVITYSCORE；2025-26（凍結，E-198 用的同一份）與 2026-27（每天抓，scripts/fetch_gravity.mjs
          → data/defense-seventh/2026-27/gravity.json）依 FRAMES 加權混合，再乘現行四季窗口的季權重（rookie_defense.window_weights(c)，
          只用他有資料的季、權重重新正規化）：raw = Σ_s ww[s]·FRAMES_s·g_s ／ Σ_s ww[s]·FRAMES_s。
  補值：兩季都缺的人（含新秀）＝E-198 同一套 OLS（raw ~ 1 + 3PA/36 + 3P% + USG% + 位置啞變數，PG 為基準），用本季可得資料擬合：
        樣本＝今天有混合值且本季有上場、bio 有 USG% 的人；特徵＝2026-27 player-games 加總（3PA、3PM、MIN）與 bio USG_PCT；位置＝先驗卡 pos（新秀 G/F/C → SG/SF/C）。
        本季還沒上場的人：老將沿用卡片值（card 0.2.10j gravity-raw.csv，含卡片的補值）；新秀用 ROOKIE_G0（見 freeze()）。
        GRAVITY_EPM=1（inseason 0.2.12a，2026-11-02 使用者「現在就上 0.2.11a」，因 0.2.12 同時上線改疊在 0.2.12 上；GRAVITY_EPM=0 重現 0.2.12，TOV_POSS=0 時預設關＝重現 0.2.11）：OLS 補值依本季分鐘往進攻 EPM 推估收縮，
          raw = w·OLS + (1−w)·(a + b·O)，w = MIN／(MIN + EPM_K)；O＝epm_live.run() 的本季進攻（先驗打底，幾分鐘也穩），
          a、b＝2025-26 有 API 值的人 raw ~ epm_self 2025-26 O 的單變量 OLS。沒有本季 O 的人照舊用 OLS。（Joshua Jefferson 4 分鐘 OLS 109.6）
  0–99：照 creation（E-175 PctMapper，池＝卡片 2025-26 GP≥30 且 MPG≥20 的原始／補值，凍結；兩端尾巴開），與卡片端同一把尺：
        本季 0 場、只有 2025-26 值的人＝卡片 gravity 逐位元相同。
  基準（lastOVR、本季 0 場）：老將＝卡片值；新秀＝ROOKIE_G0（x0 不含 gravity，build_2k_start 的 δ 平移不動它）。
凍結檔：gravity-pool-card0210j.json（python -I -B -X utf8 gravity_live.py freeze 產生；會核對對卡片 gravity-attr.csv 逐位元重現）。
抓檔失敗：沿用上次成功的 gravity.json（daily 只記警告）；檔不存在＝只用 2025-26（＋OLS 補值）。
開關：GRAVITY=0 時 run_c4_live 完全不 import 本檔（重現 0.2.10i）。"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
sys.path.insert(0, str(ROOT / 'reports/ovr-v61-shrink-history-2025-26'))
import e175_lib as L  # noqa: E402

FROZEN = HERE / 'gravity-pool-card0210j.json'
CARD = ROOT / 'reports/card-0.2.10j'
G25 = ROOT / 'reports/F126-shot-difficulty/gravity-split/gravity-2025-26.json'
CUR_FILE = ROOT / 'data/defense-seventh/2026-27/gravity.json'
BASE25 = ROOT / 'data/benchmark-source/base.json'
BIO25 = ROOT / 'data/benchmark-source/bio.json'
EPM25 = ROOT / 'data/external-impact/epm_self/epm_2025-26.csv'
_ENV = __import__('os').environ
EPM_ON = _ENV.get('GRAVITY_EPM', '0' if _ENV.get('TOV_POSS', '1') == '0' else '1') == '1'
EPM_K = 200.0   # 分鐘；w = MIN／(MIN + EPM_K)
KEY, FR = 'AVGOFFBALLPERIMETERGRAVITYSCORE', 'FRAMES'
POS = ['SG', 'SF', 'PF', 'C']
DPOS = {'G': 'SG', 'F': 'SF', 'C': 'C'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
_CACHE = {}


def _rs(p):
    d = json.load(open(p, encoding='utf-8'))
    d = d.get('data', d)
    s = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
    return [dict(zip(s['headers'], r)) for r in s['rowSet']]


def _leaders(rows):
    out = {}
    for r in rows:
        if r.get(KEY) is not None and r.get(FR):
            out[int(r['PLAYERID'])] = (float(r[KEY]), float(r[FR]))
    return out


# ------------------------------------------------------------------ 凍結
def freeze():
    raw = list(csv.DictReader(open(CARD / 'gravity-raw.csv', encoding='utf-8')))
    attr = {int(r['playerId']): r for r in csv.DictReader(open(CARD / 'gravity-attr.csv', encoding='utf-8'))}
    b = {int(r['PLAYER_ID']): r for r in _rs(BASE25)}
    pool = []
    for r in raw:
        p = int(r['playerId'])
        gp, mn = float(b[p]['GP']), float(b[p]['MIN'])
        if gp >= L.POOL_GP and gp > 0 and mn / max(gp, 1) >= L.POOL_MPG:
            pool.append(float(r['raw']))
    mp = L.PctMapper(pool, True, True)
    got = mp(np.array([float(r['raw']) for r in raw]))
    bad = [r['name'] for r, v in zip(raw, got) if repr(float(v)) != attr[int(r['playerId'])]['gravity']]
    assert not bad, f'凍結池重現不了卡片 gravity：{bad[:5]}'
    # 新秀基準：卡片裡 2025 屆新秀（2025-26 bio DRAFT_YEAR=2025）的 gravity 中位數（固定常數，不隨本季資料變）
    bio = {int(r['PLAYER_ID']): r for r in _rs(BIO25)}
    rk = sorted(float(attr[p]['gravity']) for p in attr if str(bio.get(p, {}).get('DRAFT_YEAR')) == '2025')
    g0 = float(np.median(rk))
    doc = {'doc': 'inseason 0.2.10j gravity 凍結池（gravity_live.py freeze）：pool＝card 0.2.10j 2025-26 GP≥30 且 MPG≥20 的 raw（含補值），PctMapper 兩端尾巴開；'
                  'card＝每個卡片球員的 raw／imputed／gravity；g25＝2025-26 API 的 (score, FRAMES)；rookieG0＝卡片 2025 屆新秀 gravity 中位數（新秀本季 0 場時的值）',
           'pool': pool, 'tails': {'top': True, 'bot': True}, 'anchors': mp.an,
           'card': {r['playerId']: {'raw': float(r['raw']), 'imputed': int(r['imputed']), 'gravity': float(attr[int(r['playerId'])]['gravity'])} for r in raw},
           'g25': {str(k): v for k, v in _leaders(json.load(open(G25, encoding='utf-8'))).items()},
           'rookieG0': g0, 'rookieG0N': len(rk),
           'sourcesSha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in (CARD / 'gravity-raw.csv', CARD / 'gravity-attr.csv', G25, BASE25, BIO25)}}
    FROZEN.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'pool': len(pool), 'card': len(raw), 'g25': len(doc['g25']), 'rookieG0': g0, 'rookieG0N': len(rk)}, ensure_ascii=False))


def frozen():
    if 'f' not in _CACHE:
        d = json.loads(FROZEN.read_text(encoding='utf-8'))
        d['mapper'] = L.PctMapper(d['pool'], d['tails']['top'], d['tails']['bot'])
        d['card'] = {int(k): v for k, v in d['card'].items()}
        d['g25'] = {int(k): tuple(v) for k, v in d['g25'].items()}
        _CACHE['f'] = d
    return _CACHE['f']


def to_attr(raw):
    return float(frozen()['mapper'](np.array([raw]))[0])


def rookie_g0():
    return float(frozen()['rookieG0'])


# ------------------------------------------------------------------ 賽中
def _epm_prior():
    """(a, b, {pid: 本季進攻 EPM}, info)：raw ≈ a + b·O（2025-26 擬合）；O 取 epm_live.run(write=False)。"""
    if 'epm' not in _CACHE:
        F = frozen()
        o25 = {int(r['playerId']): float(r['O']) for r in csv.DictReader(open(EPM25, encoding='utf-8')) if r['O']}
        ps = sorted(p for p, v in F['card'].items() if not v['imputed'] and p in o25)
        b, a = np.polyfit([o25[p] for p in ps], [F['card'][p]['raw'] for p in ps], 1)
        import importlib.util
        sp = importlib.util.spec_from_file_location('epm_live_g', ROOT / 'reports/impact-epm-2026-27/epm_live.py')
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        rows, summ = m.run(write=False)
        o26 = {int(r['playerId']): float(r['O']) for r in rows}
        _CACHE['epm'] = (float(a), float(b), o26, {'a': float(a), 'b': float(b), 'n25': len(ps), 'K': EPM_K, 'n26': len(o26),
                                                   'dataCutoff': summ.get('dataCutoff') if isinstance(summ, dict) else None})
    return _CACHE['epm']


def cur_leaders():
    """2026-27 gravity.json（scripts/fetch_gravity.mjs）；不存在或格式不對 → ({}, 說明)。"""
    if not CUR_FILE.exists():
        return {}, {'file': None, 'note': 'gravity.json 不存在，只用 2025-26'}
    d = json.loads(CUR_FILE.read_text(encoding='utf-8'))
    rows = d.get('leaders', [])
    assert rows and KEY in rows[0] and FR in rows[0], f'gravity.json 格式不對（缺 {KEY}／{FR}）'
    return _leaders(rows), {'file': CUR_FILE.relative_to(ROOT).as_posix(), 'fetchedAt': d.get('fetchedAt'), 'n': len(rows), 'sha256': sha(CUR_FILE)}


def _season_feats(data26):
    acc = {}
    for r in _rs(Path(data26) / 'player-games.json'):
        if not r['MIN']:
            continue
        a = acc.setdefault(int(r['PLAYER_ID']), [0.0, 0.0, 0.0])
        a[0] += float(r['MIN']); a[1] += float(r['FG3A'] or 0); a[2] += float(r['FG3M'] or 0)
    usg = {int(r['PLAYER_ID']): r.get('USG_PCT') for r in _rs(Path(data26) / 'bio.json')}
    return acc, usg


def live(c, data26, pos_of, rookies=(), cur=True, fit_exclude=()):
    """回傳 ({pid: {'gravity', 'raw', 'src', 'frames25', 'frames26'}}, info)。
    pos_of：{pid: 'PG'..'C'}（老將＝先驗卡 pos；新秀先換 SG/SF/C）；rookies：新秀 pid（本季沒上場時用 ROOKIE_G0）。
    cur=False：同一個 c 但不讀本季（＝卡片值／新秀 G0；基準用）。"""
    import rookie_defense as RD
    F = frozen()
    g26, finfo = cur_leaders() if cur else ({}, {'file': None})
    ww = RD.window_weights(c)
    w25, w26 = ww.get('2025-26', 0.0), ww.get('2026-27', 0.0)
    feats, usg = _season_feats(data26) if cur else ({}, {})
    out, blend = {}, {}
    for pid in set(pos_of):
        a, b = F['g25'].get(pid), g26.get(pid)
        num = den = 0.0
        if a and w25 > 0:
            num += w25 * a[1] * a[0]; den += w25 * a[1]
        if b and w26 > 0:
            num += w26 * b[1] * b[0]; den += w26 * b[1]
        if den > 0:
            blend[pid] = (num / den, a[1] if a else 0.0, b[1] if b else 0.0)
    # OLS 補值（本季資料）
    def x_of(pid):
        f, u = feats.get(pid), usg.get(pid)
        if not f or f[0] <= 0 or u is None or pos_of.get(pid) is None:
            return None
        return [1.0, 36 * f[1] / f[0], f[2] / f[1] if f[1] > 0 else 0.0, float(u)] + [float(pos_of[pid] == q) for q in POS]
    fit = [(x_of(p), blend[p][0]) for p in sorted(blend) if x_of(p) is not None and p not in fit_exclude]
    beta, ols = None, {'n': len(fit)}
    if len(fit) >= 30:
        X = np.array([f[0] for f in fit]); y = np.array([f[1] for f in fit])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        ols.update(beta=beta.tolist(), r2=float(1 - res.var() / y.var()))
    rk = set(rookies)
    for pid in pos_of:
        if pid in blend:
            r, f25, f26 = blend[pid]
            src = '2025-26+2026-27' if f25 and f26 else ('2025-26' if f25 else '2026-27')
        else:
            x = x_of(pid)
            f25 = f26 = 0.0
            if beta is not None and x is not None:
                r, src = float(np.array(x) @ beta), 'ols'
                if EPM_ON and cur:
                    ea, eb, o26, _ = _epm_prior()
                    if pid in o26:
                        w = feats[pid][0] / (feats[pid][0] + EPM_K)
                        r, src = w * r + (1 - w) * (ea + eb * o26[pid]), 'ols+epm'
            elif pid in F['card']:
                r, src = F['card'][pid]['raw'], 'card-ols' if F['card'][pid]['imputed'] else 'card'
            elif pid in rk:
                out[pid] = {'gravity': rookie_g0(), 'raw': None, 'src': 'rookie-g0', 'frames25': 0.0, 'frames26': 0.0}
                continue
            else:
                continue
        out[pid] = {'gravity': to_attr(r), 'raw': r, 'src': src, 'frames25': f25, 'frames26': f26}
    if EPM_ON and cur:
        ols['epmShrink'] = _epm_prior()[3]
    info = {'c': c, 'weights': {'2025-26': w25, '2026-27': w26}, 'cur': finfo, 'ols': ols,
            'src': {k: sum(v['src'] == k for v in out.values()) for k in sorted({v['src'] for v in out.values()})}}
    return out, info


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['freeze']:
        freeze()
