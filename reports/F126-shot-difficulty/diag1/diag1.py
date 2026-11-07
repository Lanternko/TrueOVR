"""F-126 diag1：用只看半季資料的卡（E-081 的 E-075 半季卡）重做 diag0 的出手能力 SM 斜率，消掉整季卡的洩漏。
設計與判讀凍結在 preregistration.md（preregistration.sha256），本檔不照結果改。
用法（repo 根目錄）：python reports/F126-shot-difficulty/diag1/diag1.py   → result.json、report.md、inputs.sha256"""
import csv, hashlib, json, os, subprocess, sys, tempfile
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.abspath(os.path.join(here, '../../..'))
P = lambda p: os.path.join(root, p)
L = lambda p: list(csv.DictReader(open(p, encoding='utf-8')))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
SEED, NBOOT = 20261101, 2000
D0 = os.path.join(root, 'reports/F126-shot-difficulty/diag0')
E81 = P('reports/card-0.2.3+E081-age-residual')
CARDS, RAPM1 = os.path.join(E81, 'cards.json'), {h: os.path.join(E81, f'rapm1-{h}.csv') for h in 'AB'}
V58 = {h: P(f'reports/ovr-v58-holdout-2025-26/rapm-{h}.csv') for h in 'AB'}
CARD_FULL = P('reports/card-0.2.10/ranking.csv')
PG, POOL, R0 = (os.path.join(D0, f) for f in ('player_game.csv', 'pool.csv', 'result.json'))
DIRS = (('AB', 'A', 'B'), ('BA', 'B', 'A'))      # (方向, SM／卡的半季 s, 目標半季 t)

# ---- 自檢 ----
cj = json.load(open(CARDS, encoding='utf-8'))
checks = {'k0': {'pass': bool(cj['k0']['pass'])}}
v58 = {h: {int(x['playerId']): float(x['pooledNet']) for x in L(V58[h])} for h in 'AB'}
k1 = {}
for dn, s, t in DIRS:
    d = cj['dirs'][dn]
    diff = max(abs(a - v58[t][p] * m) for a, p, m in zip(d['ans'], d['pid'], d['mpg_ev']))
    k1[dn] = float(diff)
checks['k1'] = {'maxAbsDiff': k1, 'pass': max(k1.values()) < 1e-6}
# k2：在暫存資料夾重跑 diag0 的程式碼（不覆寫 diag0 任何檔案），slope_mean 要和已存的 result.json 逐位元一致
src = open(os.path.join(D0, 'diag0.py'), encoding='utf-8').read()
src = src.replace("here = os.path.dirname(os.path.abspath(__file__)); root = os.path.abspath(os.path.join(here, '../../..'))",
                  f"here = {D0!r}; root = {root!r}; _out = sys.argv[1]")
src = src.replace("os.path.join(here, 'result.json')", "os.path.join(_out, 'result.json')").replace("os.path.join(here, 'inputs.sha256')", "os.path.join(_out, 'inputs.sha256')")
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, 'diag0_rerun.py'); open(sp, 'w', encoding='utf-8').write(src)
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    subprocess.run([sys.executable, sp, td], check=True, capture_output=True, creationflags=flags)
    rerun = json.load(open(os.path.join(td, 'result.json'), encoding='utf-8'))
stored = json.load(open(R0, encoding='utf-8'))
checks['k2'] = {'stored': stored['slope_mean'], 'rerun': rerun['slope_mean'], 'pass': stored['slope_mean'] == rerun['slope_mean']}
if not all(c['pass'] for c in checks.values()):
    print(json.dumps(checks, ensure_ascii=False, indent=1)); sys.exit('自檢失敗，不出結論')

# ---- 讀入 ----
K = stored['k']
agg = {}                                     # (pid, half) → [FGA, FGM, sumXFG]
for x in L(PG):
    a = agg.setdefault((int(x['playerId']), x['half']), [0, 0, 0.0])
    a[0] += int(x['FGA']); a[1] += int(x['FGM']); a[2] += float(x['sumXFG'])
rap = {h: {int(x['playerId']): float(x['net']) for x in L(RAPM1[h])} for h in 'AB'}
SM = lambda p, h: (agg[(p, h)][1] - agg[(p, h)][2]) / (agg[(p, h)][0] + K)
name_pid = {x['name']: int(x['playerId']) for x in L(POOL)}
ovr_full = {name_pid[x['name']]: float(x['ovr']) for x in L(CARD_FULL) if x['name'] in name_pid}

dat = {}                                     # 方向 → dict(pid, card, ovr, sm, net, ans, mpg, ...) 以 pid 為鍵的陣列
for dn, s, t in DIRS:
    d = cj['dirs'][dn]; keep = [i for i, p in enumerate(d['pid'])
                                if all((p, h) in agg and p in rap[h] for h in 'AB')]
    pid = np.array([d['pid'][i] for i in keep])
    dat[dn] = {'pid': pid, 'n_cards': len(d['pid']), 'cand': np.array([d['cand'][i] for i in keep]),
               'mpg': np.array([d['mpg_ev'][i] for i in keep]), 'ans': np.array([d['ans'][i] for i in keep]),
               'sm': np.array([SM(p, s) for p in pid]), 'net': np.array([rap[t][p] for p in pid]),
               'ovr': np.array([ovr_full.get(int(p), np.nan) for p in pid])}
master = sorted(set(dat['AB']['pid']) | set(dat['BA']['pid'])); M = len(master)
mi = {p: i for i, p in enumerate(master)}
pos = {dn: np.array([mi[p] for p in dat[dn]['pid']]) for dn in dat}          # 方向內第 j 人在 master 的位置

# ---- 統計量 ----
z = lambda v: (v - v.mean()) / v.std()
def coef_z(y, sm, card=None):
    """OLS y ~ 1 [+ card] + z(sm)，回傳 z(sm) 係數"""
    cols = [np.ones_like(sm)] + ([card] if card is not None else []) + [z(sm)]
    return float(np.linalg.lstsq(np.c_[tuple(cols)], y, rcond=None)[0][-1])
def coef_r1(y, sm, card):
    X = np.c_[np.ones_like(card), card]; res = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
    return float(np.linalg.lstsq(np.c_[np.ones_like(sm), z(sm)], res, rcond=None)[0][1])
# 各統計量：(目標欄, 卡欄, 函式)
SPECS = {'main': ('net', 'cand', coef_z), 'r1': ('net', 'cand', coef_r1), 'r2': ('net', 'ovr', coef_z), 'r3': ('net', None, coef_z),
         'r4': ('ans', 'cand', coef_z), 'r5': ('netmpg', 'cand', coef_z), 'r6': ('net', 'candrate', coef_z)}
for dn in dat:
    dat[dn]['netmpg'] = dat[dn]['net'] * dat[dn]['mpg']; dat[dn]['candrate'] = dat[dn]['cand'] / dat[dn]['mpg']
def stat(spec, sel=None):
    """sel＝dict 方向 → 該方向要用的人（index 陣列，可重複）；None＝全體。回傳 (AB, BA, 平均)"""
    ycol, ccol, fn = SPECS[spec]; out = []
    for dn, s, t in DIRS:
        d = dat[dn]; ix = np.arange(len(d['pid'])) if sel is None else sel[dn]
        if ccol == 'ovr': ix = ix[~np.isnan(d['ovr'][ix])]       # r2：沒有 0.2.10 OVR 的人剔除
        out.append(fn(d[ycol][ix], d['sm'][ix], None if ccol is None else d[ccol][ix]))
    return out[0], out[1], (out[0] + out[1]) / 2
pt = {k: stat(k) for k in SPECS}
rng = np.random.default_rng(SEED); boots = {k: [] for k in SPECS}
for _ in range(NBOOT):
    draw = rng.integers(0, M, M); cnt = np.bincount(draw, minlength=M)      # 兩方向同一組抽樣
    sel = {dn: np.repeat(np.arange(len(pos[dn])), cnt[pos[dn]]) for dn in dat}
    for k in SPECS: boots[k].append(stat(k, sel))
boots = {k: np.array(v) for k, v in boots.items()}

def verdict(lo, hi, mde):          # 預先定好（preregistration.md）
    if lo > 0: return '卡片低估難球命中者'
    if hi < 0: return '卡片高估難球命中者'
    return f'未偵測到（MDE＝{mde:.3f} RAPM/100 回合／SD）'
res = {'N_AB': len(dat['AB']['pid']), 'N_BA': len(dat['BA']['pid']), 'N_master': M,
       'N_cards_AB': dat['AB']['n_cards'], 'N_cards_BA': dat['BA']['n_cards'], 'k': K, 'seed': SEED, 'boot_n': NBOOT,
       'n_r2_AB': int((~np.isnan(dat['AB']['ovr'])).sum()), 'n_r2_BA': int((~np.isnan(dat['BA']['ovr'])).sum()), 'checks': checks}
for k in SPECS:
    b = boots[k][:, 2]; lo, hi = (float(v) for v in np.percentile(b, [5, 95])); se = float(b.std(ddof=1))
    res[k] = {'AB': pt[k][0], 'BA': pt[k][1], 'mean': pt[k][2], 'lo90': lo, 'hi90': hi, 'boot_se': se, 'MDE': 2.49 * se,
              'verdict_rule': verdict(lo, hi, 2.49 * se)}
res['verdict'] = res['main']['verdict_rule']
res['diag0_slope_mean'] = stored['slope_mean']
# 描述：卡與 SM、卡與 0.2.10 OVR 的相關（報告用）
dd = dat['AB']; ok = ~np.isnan(dd['ovr'])
res['desc'] = {'corr_SM_cand_AB': float(np.corrcoef(dd['sm'], dd['cand'])[0, 1]), 'corr_SM_cand_BA': float(np.corrcoef(dat['BA']['sm'], dat['BA']['cand'])[0, 1]),
               'corr_cand_ovr_AB': float(np.corrcoef(dd['cand'][ok], dd['ovr'][ok])[0, 1])}
json.dump(res, open(os.path.join(here, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- inputs.sha256 ----
with open(os.path.join(here, 'inputs.sha256'), 'w', encoding='utf-8') as fh:
    for p in (CARDS, RAPM1['A'], RAPM1['B'], V58['A'], V58['B'], CARD_FULL, PG, POOL, R0, os.path.join(D0, 'diag0.py'), os.path.join(here, 'preregistration.md')):
        fh.write(f'{sha(p)}  {os.path.relpath(p, root).replace(os.sep, "/")}\n')

# ---- report.md（只放數字；六段回覆格式寫在對話裡）----
f3 = lambda v: f'{v:+.3f}'
rows = ''.join(f"| {k} | {f3(res[k]['AB'])} | {f3(res[k]['BA'])} | {f3(res[k]['mean'])} | [{f3(res[k]['lo90'])}, {f3(res[k]['hi90'])}] | {res[k]['MDE']:.3f} |\n" for k in SPECS)
open(os.path.join(here, 'report.md'), 'w', encoding='utf-8').write(f"""# F-126 diag1 報告（半季卡乾淨複查）

預註冊：`preregistration.md`（sha256 見 `preregistration.sha256`，先於本檔 commit）。k 沿用 diag0＝{K:.4f}，不重估。

## 主統計量
z(SM_s) 係數（RAPM／100 回合 每 +1 SD），bootstrap {NBOOT} 次（seed {SEED}，兩方向同一組抽樣）。
- AB {f3(res['main']['AB'])}，BA {f3(res['main']['BA'])}，平均 **{f3(res['main']['mean'])}**，90% [{f3(res['main']['lo90'])}, {f3(res['main']['hi90'])}]，MDE {res['main']['MDE']:.3f}
- 判讀：**{res['verdict']}**
- 人群：AB {res['N_AB']}（cards.json {res['N_cards_AB']}）、BA {res['N_BA']}（{res['N_cards_BA']}）、master {M}
- 對照 diag0（card 0.2.10 整季卡、全部 303 人）：{stored['slope_mean']:+.3f}

## 只報告（同一組 bootstrap；單位：r1–r3、r6 為 RAPM／100 回合／SD；r4、r5 目標乘了出場分鐘，單位不同，只看正負與區間）
| 項目 | AB | BA | 平均 | 90% 區間 | MDE |
|---|---|---|---|---|---|
{rows}
- r1 先殘差化再回歸（diag0 式，卡＝cand）；r2 卡換成 card 0.2.10 OVR（AB n={res['n_r2_AB']}、BA n={res['n_r2_BA']}）＝洩漏大小；r3 不放卡；
  r4 目標＝Q（V58 多季合併 pooledNet×mpg_ev，cards.json 的 ans，與主統計量不同口徑）；r5 目標＝N（rapm1 net×mpg_ev）；r6 卡換成 cand／mpg_ev（率尺度）。
- 描述：corr(SM, cand) AB {res['desc']['corr_SM_cand_AB']:.3f}、BA {res['desc']['corr_SM_cand_BA']:.3f}；corr(cand, 0.2.10 OVR) AB {res['desc']['corr_cand_ovr_AB']:.3f}

## 自檢
- k0 `cards.json` k0.pass＝{checks['k0']['pass']}
- k1（修正後：ans＝V58 pooledNet×mpg_ev）最大差 AB {k1['AB']:.2e}、BA {k1['BA']:.2e}（門檻 <1e-6）→ 通過
- k2 diag0 重跑（暫存資料夾）slope_mean {rerun['slope_mean']!r} 與已存 {stored['slope_mean']!r} 逐位元一致 → 通過

## 限制
半季卡是 card 0.2.3 架構不是 0.2.10；係數 coef[AB] 用 B 半特徵→RAPM_A 訓練（群體係數，對個別球員洩漏極小）；人群受 diag0 逐球資料 303 人限制；單季分半（樣本內，R-007）。
`cand` 是乘了出場分鐘的量（r6 為率尺度核對）。

## 輸入雜湊
見 `inputs.sha256`。
""")
print(json.dumps({k: res[k] for k in ('N_AB', 'N_BA', 'N_master', 'verdict')} | {k: res[k] for k in SPECS}, ensure_ascii=False, indent=1))
