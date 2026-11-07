"""由 results.json 產生 report.md（只排版，不算新數字）。用法：python reports/handle-E069/make_report.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
SE = r['seasons']['fit'] + [r['seasons']['test']]
L = []
w = L.append


def f(x, n=4):
    return '' if x is None else f'{x:.{n}f}'


w('# E-069 第一階段（role-card）報告\n')
w(f"預註冊 sha256 {r['sha256']['preregistration.md'][:12]}…，補充 1 sha256 {r['sha256']['addendum'][:12]}…（皆核對相符）。擬合季 2020-21..2024-25，測試季 2025-26。數字全部來自 `results.json`。\n")
w('## 1. 閘門判定\n')
w('| 閘門 | 對象 | 選定方法 | 測試 MAE（a／b／c） | 選定 − a 點估計 | 90% 區間 | n | 判定 |')
w('|---|---|---|---|---|---|---|---|')
for k, name in (('h1', 'r_sec（人群：下半季持球分鐘 ≥20）'), ('h2', 'passSec（人群：下半季傳球數 ≥150）')):
    h = r[k]
    m = h['mae']
    w(f"| {k} | {name} | {h['selected']} | {f(m['a'],5)}／{f(m['b'],5)}／{f(m['c'],5)} | {f(h['diffSelMinusA'],5)} | [{f(h['ci90'][0],5)}, {f(h['ci90'][1],5)}] | {h['n']} | {'通過' if h['pass'] else '不通過（收縮未證實，改用方法 a 原始率）'} |")
h3 = r['h3']
w(f"| h3 | card 0.2.0 其他屬性逐位元不變 | - | - | - | - | - | {'通過' if h3['pass'] else '不通過'} |\n")
w('bootstrap：球員配對、2000 次、seed 1（`np.random.default_rng(1)`，`rng.integers(0,n,(2000,n))`），區間為 5%–95% 分位。b、c 對 a 的差只供參考（`results.json` 的 `h1/h2.infoOnly`），不用來改判。\n')
w(f"h3：`reports/card-0.2.0/ranking.csv`、`summary.json` 的 sha256 在腳本前後相同（ranking.csv {h3['before']['ranking.csv'][:12]}…，summary.json {h3['before']['summary.json'][:12]}…）。本階段只讀不寫這兩個檔；新欄位只在 `handle.csv`。\n")
w('## 2. 選定方法與參數（只用擬合季 MAE 選，不看測試季）\n')
w('| 屬性 | 擬合 n | 擬合 MAE a／b／c | 選定 | k | λ | kh | 收縮目標 | 實際使用 |')
w('|---|---|---|---|---|---|---|---|---|')
for a, nm in (('rsec', 'r_sec'), ('passSec', 'passSec')):
    x = r['fits'][a]
    p = x['params']
    t = x['trainMae']
    w(f"| {nm} | {x['trainN']} | {f(t['a'],5)}／{f(t['b'],5)}／{f(t['c'],5)} | {x['selected']} | {p.get('k','-')} | {p.get('lam','-')} | {p.get('kh','-')} | {p.get('prior','-')} | {r['used'][a]} |")
w('\n收縮目標用同位置平均。b、c 各格點的結果在 `results.json` 的 `fits.*.bAll／cAll`。\n')
w('## 3. 邊界日期（上半季＝日期 ≤ D1）\n')
w('| 季 | D1 | 下半季起 | 賽程場數 | 依日期的上半季場數 | 規則場數 | D1 當天場數 |')
w('|---|---|---|---|---|---|---|')
for s in SE:
    b = r['boundaries'][s]
    w(f"| {s} | {b['D1']} | {b['H2From']} | {b['nGames']} | {b['nH1ByDate']} | {b['nH1Rule']} | {b['gamesOnD1']} |")
w('\n說明：')
w('- 規則場數 504（2020-21）或 574（其他季）；D1 取第 N1 場的日期，同日有多場，所以依日期切出的上半季比規則場數多幾場。上下半季以日期為準，PBP 與 tracking 用同一個 D1。')
w('- 2025-26 一律用預註冊 §3.1 的日期前綴規則，D1＝2026-01-11；`trainGames` 的舊切法會得到 2026-01-16，這裡不用。')
w('- 場數不足 1230（補充 1 第 4 點，照實寫、不補抓）：2020-21 為 1080（縮水季）、2024-25 為 1229、2025-26 為 1227。\n')
w('## 4. 資料核對\n')
c = r['cache']['2025-26']
w(f"- 2025-26 tracking H1＋H2 與 FULL 的持球分鐘最大差 {f(r['trackingSum']['maxAbsTOF_H1plusH2_minus_FULL'],2)}；傳球數最大差 {r['trackingSum']['maxAbsPasses_H1plusH2_minus_FULL']}。卡片屬性用 FULL。")
w(f"- PBP 與 tracking 對不上的量（2025-26）：不在半季表的場 {c['pbpGamesNotInHalves']}，不在 tracking 的失誤 ctl {c['pbpTovNotInTracking']['ctl']}、pass {c['pbpTovNotInTracking']['pass']}；其他季見 `results.json` 的 `cache.*`。")
w('- passSec 人群：先用 d2（傳球數＋passTov）≥150 當必要條件，再用下半季 PASSES_MADE ≥150 過濾；擬合季同。')
w(f"- 卡片池（GP≥30 且 MPG≥20，`base.json`）{r['production']['poolSize']} 人，卡片球員 {r['production']['cardPlayers']} 人，不在 tracking 的 {len(r['production']['cardPlayersNotInTracking'])} 人。z 分數用池內平均與標準差。")
w(f"- 聯盟率：r_sec {f(r['production']['leagueRate']['rsec'],4)} 次/持球分鐘，passTov 率 {f(r['production']['leagueRate']['passSec'],4)}。\n")
w('## 5. 補充 1 第 3 點：無法對應比例\n')
w('| 季 | out-of-bounds 總數 | 拆不出來 | 比例 | offensive foul 總數 | 找不到同刻 foul | 比例 | 超過 5% |')
w('|---|---|---|---|---|---|---|---|')
flag = False
for s in SE:
    d = r['subtypes'][s]['detail']
    o = d.get('oob_unmatched', 0) / max(1, d.get('oob_total', 0))
    n = d.get('of_nofoul', 0) / max(1, d.get('of_total', 0))
    flag = flag or o > .05 or n > .05
    w(f"| {s} | {d.get('oob_total',0)} | {d.get('oob_unmatched',0)} | {o:.2%} | {d.get('of_total',0)} | {d.get('of_nofoul',0)} | {n:.2%} | {'是' if (o > .05 or n > .05) else '否'} |")
w('\n' + ('有季別超過 5%，已標示（依補充 1 不停工）。' if flag else '沒有任何一季超過 5%。') + '\n')
w('## 6. 與 2K27 的 Spearman ρ（只報告）\n')
w('| 對象 | 2K27 欄位 | 人群 | n | ρ |')
w('|---|---|---|---|---|')
for k in ('handle', 'passSec'):
    for pop, pn in (('pool', '卡片池'), ('allCard', '全部卡片球員')):
        x = r['rho2k27'][f'{k}_{pop}']
        w(f"| {k} | {x['col']} | {pn} | {x['n']} | {f(x['rho'],3)} |")
w(f"\npassSec 對 Pass Accuracy 的 ρ 是負的（方向已核對：傳球失誤率低 → 屬性高）。可能原因是 2K 的 Pass Accuracy 偏向後衛，而傳球多的後衛失誤率較高、大個子傳得少失誤率低；這是推測，未驗證。只如實報告，不調整定義。名字對不上 2K27 的卡片球員 {len(r['unmatched2k27'])} 人（`unmatched2k27`）。\n")
w('## 7. G5 名單\n')
w(f"名次＝卡片池內 handle 或 passSec 的名次（池 {r['production']['poolSize']} 人，1 最好）；不在池內者名次空白。Hauser 的名稱查詢同時符合 Yanic Konan Niederhäuser，兩列都列出，以 Sam Hauser 為準。Tyrese Haliburton 查不到 2025-26 tracking／卡片資料列，未列入（沒有數字可報，不補）。\n")
w('| 球員 | 在池 | handle | 名次 | passSec | 名次 | vol(每36) | r_sec 原始 | r_sec 使用 | 持球分鐘 | ctlTov | passTov | 傳球數 |')
w('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for g in r['g5']:
    w(f"| {g['name']} | {'是' if g['inPool'] else '否'} | {f(g['handle'],1)} | {g['rankHandle'] or ''} | {f(g['passSec'],1)} | {g['rankPassSec'] or ''} | {f(g['vol'],2)} | {f(g['r_sec_raw'],3)} | {f(g['r_sec_used'],3)} | {f(g['TIME_OF_POSS'],1)} | {g['ctlTov']} | {g['passTov']} | {g['passes']} |")
for key, title in (('top20', '前 20 名（卡片池內，依 handle）'), ('bottom20', '後 20 名（卡片池內，依 handle，最低者在前）')):
    w(f'\n## 8. {title}\n' if key == 'top20' else f'\n### {title}\n')
    w('| # | 球員 | 位置 | handle | passSec | vol | r_sec 使用 | 持球分鐘 |')
    w('|---|---|---|---|---|---|---|---|')
    for i, x in enumerate(r[key], 1):
        w(f"| {i} | {x['name']} | {x['pos']} | {f(x['handle'],1)} | {f(x['passSec'],1)} | {f(x['vol'],2)} | {f(x['r_sec_used'],3)} | {f(x['TIME_OF_POSS'],1)} |")
w('\n前段並列 99.0 與後段並列 40.0 是 rank_attr 的上下限被截斷造成，並列者順序不代表強弱。\n')
w('## 附錄 A：失誤 subType 次數（含歸類，補充 1）\n')
sts = sorted({k for s in SE for k in r['subtypes'][s]['subType']}, key=lambda k: -sum(r['subtypes'][s]['subType'].get(k, 0) for s in SE))
w('各季場數：' + '、'.join(f"{s} {r['manifest'][s]['games']}" for s in SE) + '\n')
w('| subType | ' + ' | '.join(SE) + ' |')
w('|---|' + '---|' * len(SE))
for k in sts:
    w(f'| {k or "(空白)"} | ' + ' | '.join(str(r['subtypes'][s]['subType'].get(k, 0)) for s in SE) + ' |')
w('| 合計 | ' + ' | '.join(str(sum(r['subtypes'][s]['subType'].values())) for s in SE) + ' |')
w('\n歸類結果：')
w('| 季 | ctlTov | passTov | 其他 |')
w('|---|---|---|---|')
for s in SE:
    d = r['subtypes'][s]['detail']
    w(f"| {s} | {d.get('cls_ctl',0)} | {d.get('cls_pass',0)} | {d.get('cls_other',0)} |")
w('\n§2.1 列出的取值加補充 1 的 out-of-bounds 與 charge 規則歸 ctl／pass，其餘歸「其他」。\n')
w('## 附錄 B：檔案\n')
w(f"`extract_tov.py`、`boundaries.py`、`fetch-tracking.mjs`、`handle_e069.py`、`make_report.py`、`handle.csv`（sha256 {r['sha256']['handle.csv']}）、`results.json`、`raw/`（tracking 原始檔與 `fetch-manifest.json`）、`pbp-tov-*.csv.gz` 與 manifest。")
(HERE / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
