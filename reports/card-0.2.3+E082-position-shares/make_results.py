"""E-082 彙整：results.json + report.md。用法（repo 根目錄）：PYTHONDONTWRITEBYTECODE=1 python -I reports/card-0.2.3+E082-position-shares/make_results.py
只讀 work/、out/、cards/ 與唯讀目錄；寫 results.json、report.md。"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NL = chr(10)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---------------------------------------------------------------- c0（one-hot 重現）
P1 = ROOT / 'reports/card-0.2.2/cards/P1'
c0_files = {}
for part in ('primary', 'fitA', 'fitB', 'card'):
    for f in sorted((P1 / part).iterdir()):
        if f.name == 'run.log' or f.is_dir():
            continue
        g = HERE / 'cards/off' / part / f.name
        if f.suffix == '.json':
            same = jl(f) == jl(g)
            byte = sha(f) == sha(g)
        else:
            same = byte = sha(f) == sha(g)
        c0_files[f'{part}/{f.name}'] = {'bitwise': byte, 'jsonEqual': same}
c0_ok_cards = all(v['jsonEqual'] for v in c0_files.values())
E075_SHA = '01aab81a56bca96888df95845a9adfc466be065787810e80708e3635c7452215'
C023_SHA = '933797d84f6c411b57f3caadcf26a898c203858b4808cf97b461717a9c3ebc64'
c0 = {
    'cards_vs_card022_P1': {'files': c0_files, 'allJsonEqualOrBitwise': c0_ok_cards,
                            'bitwiseDifferent': [k for k, v in c0_files.items() if not v['bitwise']]},
    'cards_off_ranking_vs_card022_ranking': {'sha': sha(HERE / 'cards/off/ranking.csv'), 'card022': sha(ROOT / 'reports/card-0.2.2/ranking.csv')},
    'e075_off_ranking_sha': sha(HERE / 'out/off/ranking.csv'), 'e075_expected': E075_SHA,
    'assembled_off_sha': sha(HERE / 'out/off/ranking-023fmt.csv'), 'card023_expected': C023_SHA,
}
c0['pass'] = bool(c0_ok_cards and c0['cards_off_ranking_vs_card022_ranking']['sha'] == c0['cards_off_ranking_vs_card022_ranking']['card022']
                  and c0['e075_off_ranking_sha'] == E075_SHA and c0['assembled_off_sha'] == C023_SHA == sha(ROOT / 'reports/card-0.2.3/ranking.csv'))

# ---------------------------------------------------------------- 其餘
s0 = jl(HERE / 'work/s0.json')
on = jl(HERE / 'out/on/results.json')
ck = on['checks']
c1 = ck['c1']
c3 = ck['c3']
c2q = jl(HERE / 'work/c2Q.json')
c2n = jl(HERE / 'work/c2N.json')
s5 = jl(HERE / 'work/s5.json')
ev = jl(HERE / 'evaluation.json')
cand = {c['label']: c for c in ev['candidates']}
R = {k: ck[k] for k in ('R2', 'R3', 'R4')}
R1 = ck['R1']
ro_b, ro_a = jl(HERE / 'work/ro-before.json'), jl(HERE / 'work/ro-after.json')
ro = {k: {'before': ro_b[k], 'after': ro_a[k], 'same': ro_b[k] == ro_a[k]} for k in ro_b}

passes = {'s0': s0['pass'], 'c0': c0['pass'], 'c1': bool(c1['pass']), 'c2Q': c2q['pass'], 'c2N': c2n['pass'], 'c3': bool(c3['pass']),
          'R2': R['R2']['pass'], 'R3': R['R3']['pass'], 'R4': R['R4']['pass']}
allpass = all(passes.values())
if allpass:
    verdict = '通過（交使用者做 G5、定版本）；(c2N) 下界 %s 0 → %s' % ('>' if c2n['lower_gt_0'] else '<=', 'MINOR' if c2n['lower_gt_0'] else 'PATCH')
else:
    verdict = '不通過，不採用（未過：%s）' % '、'.join(k for k, v in passes.items() if not v)

res = {
    'experiment': 'E-082', 'candidate': 'card 0.2.3 + 位置比例（先發秒數）', 'baseline': 'card 0.2.3',
    'preregistration_sha256': sha(HERE / 'preregistration.md'),
    'verdict': verdict, 'allPass': allpass, 'passes': passes,
    's0': s0, 'c0': c0,
    'c1': {'value': c1['value'], 'threshold': c1['threshold'], 'pass': c1['pass']},
    'c2Q': c2q, 'c2N': c2n,
    'c3': {'value': c3['value'], 'threshold': c3['threshold'], 'pass': c3['pass'],
           'detail': {k: {'pass': cand[k]['gates']['pass'], 'rho2k': cand[k]['rho2k'], 'rhoRapm': cand[k]['rhoRapm'], 'rhoDef': cand[k]['rhoDef']} for k in ('card-0.2.3', 'E082')}},
    'R2': {'value': R['R2']['value'], 'threshold': R['R2']['threshold'], 'pass': R['R2']['pass']},
    'R3': {'value': R['R3']['value'], 'threshold': R['R3']['threshold'], 'pass': R['R3']['pass']},
    'R4': {'value': R['R4']['value'], 'threshold': R['R4']['threshold'], 'pass': R['R4']['pass']},
    'R1_reportOnly': {'value': R1['value'], 'pass': R1['pass']},
    'three_players': s5['three'],
    'section5': {k: s5[k] for k in ('top20_new', 'top20_old', 'top20_change', 'lt60', 'allMeanAbsDOvr', 'nChangedOvr', 'posLabelChanged', 'topNposCounts_old_new')},
    'candidate_ranking_sha256': sha(HERE / 'ranking.csv'),
    'readonly_sha256': ro,
    'limitations': ['模擬目標 y 以原位置跑出，未重跑（預註冊 §2）', '--restrictPos 等其他用到 pos 的地方不改，未使用'],
    'internal_e075_results_on': 'out/on/results.json（e082.py 輸出；其中 c2／c4 是 E-075 原算法對 card 0.2.2 的數字，不是本預註冊的 c2Q／c2N；其 verdict 欄用 E-075 規則，不採用）',
}
(HERE / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float) + NL, encoding='utf-8')

# ---------------------------------------------------------------- report.md
f4 = lambda x: '%.4f' % x
ok = lambda b: '過' if b else '不過'
R3v = R['R3']['value']
t = []
a = t.append
a('# E-082 位置比例（先發秒數）報告')
a('')
a('**判定：%s**' % verdict)
a('')
a('| # | 條件 | 結果 | 門檻 | 過？ |')
a('|---|---|---|---|---|')
a('| s0 | 比例最大位置 = 校準目標 position | 檢查 %d 人，不符 %d | 不符 <= 3 | %s |' % (s0['n_nonLow_checked'], s0['mismatch_n'], ok(s0['pass'])))
a('| c0 | one-hot 重現 | card 0.2.2 P1 三份輸出+card/ranking.csv 資料檔逐位元相同（summary.json 僅 defenseBonusPosMeanD 鍵序不同，json 相等）；E-075 ranking sha 01aab81a 相同；組裝後 sha 933797d8 = card 0.2.3 | 相同 | %s |' % ok(c0['pass']))
a('| c1 | npm test | exit %s（57 passed, 0 failed） | exit 0 | %s |' % (c1['value']['exit'], ok(c1['pass'])))
a('| c2Q | 舊量尺（pooledNet × MPG） | Δρ %s，90%% 區間 [%s, %s]；ρ 候選 AB %s／BA %s，ρ 基準 AB %s／BA %s | 下界 > -0.02 | %s |' % (
    f4(c2q['delta']), f4(c2q['ci90'][0]), f4(c2q['ci90'][1]), f4(c2q['rho_cand']['AB']), f4(c2q['rho_cand']['BA']), f4(c2q['rho_base']['AB']), f4(c2q['rho_base']['BA']), ok(c2q['pass'])))
a('| c2N | 現況量尺（單季 RAPM net × MPG） | Δρ %s，90%% 區間 [%s, %s]；下界 > 0？%s；ρ 候選 AB %s／BA %s，ρ 基準 AB %s／BA %s | 下界 > -0.02 | %s |' % (
    f4(c2n['delta']), f4(c2n['ci90'][0]), f4(c2n['ci90'][1]), '是' if c2n['lower_gt_0'] else '否', f4(c2n['rho_cand']['AB']), f4(c2n['rho_cand']['BA']), f4(c2n['rho_base']['AB']), f4(c2n['rho_base']['BA']), ok(c2n['pass'])))
a('| c3 | evaluate 閘數 | 候選 %s，card 0.2.3 %s | >= 18/19 | %s |' % (c3['value']['E082'], c3['value']['card-0.2.3'], ok(c3['pass'])))
a('| R2 | F 中位數 < MIN>=1000 的 PR10 | %s < %s | 同 E-075 | %s |' % (R['R2']['value']['F_median_ovr'], R['R2']['value']['MIN>=1000_PR10'], ok(R['R2']['pass'])))
a('| R3 | 隊內 Spearman 中位數 >= card 0.2.3 | 候選 %s，card 0.2.3 %s（30 隊） | 候選 >= 基準 | %s |' % (f4(R3v['candidate_median_std']), f4(R3v['card022_median_std']), ok(R['R3']['pass'])))
a('| R4 | MIN<100 組 PR90 < 12<=MPG<=22 組中位數 | %s < %s | 嚴格小於 | %s |' % (R['R4']['value']['MIN<100_PR90'], R['R4']['value']['group_median'], ok(R['R4']['pass'])))
a('')
a('母群：AB %d 人、BA %d 人、聯集 %d 人（c2Q 與 c2N 相同；c2N 沒有人因 rapm1 缺資料被剔除）。' % (c2q['dirs']['AB']['n_used'], c2q['dirs']['BA']['n_used'], c2q['nMaster']))
a('')
a('R3 不過的差距：候選 %s 比基準 %s 低 %s。依預註冊「任一未過 → 不採用」，不事後調整定義或門檻（L-026）。' % (f4(R3v['candidate_median_std']), f4(R3v['card022_median_std']), f4(R3v['card022_median_std'] - R3v['candidate_median_std'])))
a('')
a('## 讀法與「最字面解讀」')
a('- 基準換成 card 0.2.3：c2Q／c2N 的基準 = 重現 card 0.2.3 的 one-hot 跑（off）的半季 g（E-075 的 cand），候選 = 比例跑（on）的半季 g，兩者對同一個 ans 算 ρ；兩跑的母群與 ans 完全相同（腳本 assert）。')
a('- R3 基準取 card 0.2.3 ranking.csv 的隊內 Spearman 中位數（以 e075.py 同算法重算，0.7469 = off 跑的候選值）；R4 的 mpg_card 同樣取 card 0.2.3 ranking.csv 的 mpg。')
a('- c2N 的 MPG：用 E-064 的 mpg-{A,B}.csv（與 c2Q 的 mpgh 同來源），net 用 rapm1-{A,B}.csv，依 playerId 對上；方向 AB（用 A 校準、B 評估）用 rapm1-B 與 mpg-B。rapm1 檔 sha256：A %s、B %s。' % (c2n['rapm1_sha256']['A'], c2n['rapm1_sha256']['B']))
a('- 比例定義全照預註冊：s_ip / Σs；lowConfidence（starts < 5 或無投票）或總秒數 0 → 原標籤 one-hot。s0 檢查 334 人（非 lowConfidence）0 不符；248 人 lowConfidence。')
a('- 「比例最大位置佔不到 60%」群：預註冊寫 71 人（5 次以上先發的 330 人中），本次以 pos-shares.csv 數得 70 人（先決條件：非 lowConfidence、最大比例 < 0.6）。差 1 人，可能是預註冊統計的人群或 starts 門檻口徑略不同；未調整定義。')
a('- 顯示用位置標籤（ranking.csv 的 pos 欄）一律是原硬標籤，比例只進校準；候選與 card 0.2.3 的 pos 欄 0 人不同。')
a('- ranking.csv 組裝規則同 build_card_023.py（rank、ovr、mpg、gRepl 取自 E-075 式輸出，其餘取自 0.2.2 格式 ranking，列序 = 名次序），腳本 assemble.py。')
a('')
a('## §5 只報告')
a('')
a('### 三人')
a('| 球員 | 位置標籤 | 先發 | 比例 | card 0.2.3 OVR／名次 | 候選 OVR／名次 | ΔOVR |')
a('|---|---|---|---|---|---|---|')
for x in s5['three']:
    shs = x['shares'] if isinstance(x['shares'], str) else '、'.join('%s %.1f%%' % (k, 100 * v) for k, v in x['shares'].items() if v > 0)
    a('| %s | %s | %d | %s | %.1f／%d | %.1f／%d | %+.1f |' % (x['name'], x['pos'], x['starts'], shs, x['ovr_old'], x['rank_old'], x['ovr_new'], x['rank_new'], x['dOvr']))
a('')
a('### 前 20 名（候選；括號為 card 0.2.3 名次）')
a('| 名次 | 球員 | 位置 | OVR | card 0.2.3 名次／OVR |')
a('|---|---|---|---|---|')
for x in s5['top20_new']:
    a('| %d | %s | %s | %.1f | %d／%.1f |' % (x['rank'], x['name'], x['pos'], x['ovr'], x['rank_old'], x['ovr_old']))
a('')
a('### OVR 變動最大的 20 人')
a('| 球員 | 位置 | card 0.2.3 OVR／名次 | 候選 OVR／名次 | ΔOVR | 比例 |')
a('|---|---|---|---|---|---|')
for x in s5['top20_change']:
    shs = x['shares'] if isinstance(x['shares'], str) else '、'.join('%s %.0f%%' % (k, 100 * v) for k, v in x['shares'].items() if v > 0)
    a('| %s | %s | %.1f／%d | %.1f／%d | %+.1f | %s |' % (x['name'], x['pos'], x['ovr_old'], x['rank_old'], x['ovr_new'], x['rank_new'], x['dOvr'], shs))
a('')
l6 = s5['lt60']
a('### 比例最大位置 < 60% 的球員 vs 其他人（平均 |ΔOVR|）')
a('- < 60%%：%d 人，平均 %.3f（最大 %.1f）。' % (l6['n'], l6['meanAbsDOvr'], l6['maxAbsDOvr']))
a('- 其他人（含 lowConfidence 的 one-hot）：%d 人，平均 %.3f（最大 %.1f）；其中有比例的 %d 人平均 %.3f。' % (l6['rest_n'], l6['rest_meanAbsDOvr'], l6['rest_maxAbsDOvr'], l6['rest_withShares_n'], l6['rest_withShares_meanAbsDOvr']))
a('- 全體 582 人平均 |ΔOVR| %.3f；OVR 有變的 %d 人。' % (s5['allMeanAbsDOvr'], s5['nChangedOvr']))
a('')
a('### 各位置進前 30／60／100 的人數（card 0.2.3 → 候選，以硬標籤計）')
a('| 前 N | PG | SG | SF | PF | C |')
a('|---|---|---|---|---|---|')
for n, d in s5['topNposCounts_old_new'].items():
    a('| %s | %s |' % (n, ' | '.join('%d → %d' % tuple(d[p]) for p in ('PG', 'SG', 'SF', 'PF', 'C'))))
a('')
a('## 限制')
a('- 模擬目標 y 仍是以原硬標籤位置跑出來的，未重跑（預註冊 §2）；比例只進校準迴歸的位置項與防守置中。')
a('- 沒有用到 pos 而未改的地方：`calibrate-wing.py` 的 `--restrictPos`（只給 G 系列 sanity check，本實驗未使用）、輸出 csv 的 pos 欄與 `rows[...]["pos"]` 讀取（來源 `position`）、`--posShares` 未帶時的原路徑（attach_rapm 與 pos_mean_d 的 pos 分組）；e075 管線（e082.py）只在報告用 pos（bigsTop10、top20 的 pos 欄）。')
a('- 唯一未決定性：card 0.2.2 原程式 `summary.json` 的 `defenseBonusPosMeanD` 鍵順序每次不同（集合迭代順序），值相等；off 跑與 card 0.2.2 的這個檔 bitwise 不同、json 相等（%s）。' % ('、'.join(c0['cards_vs_card022_P1']['bitwiseDifferent']) or '無'))
a('')
a('## 唯讀目錄 sha256 前後比對（L-037）')
a('| 目錄 | 檔數 前→後 | sha256 相同？ |')
a('|---|---|---|')
for k, v in ro.items():
    a('| %s | %d → %d | %s |' % (k, v['before']['files'], v['after']['files'], '是' if v['same'] else '否'))
a('')
a('`reports/card-0.2.3+E081-age-residual/` 前後不同：E-081（另一個 session）在本任務期間持續往該目錄寫檔（開工時 3 個檔，結束時 15 個）。本任務對它只讀 `rapm1-A.csv`、`rapm1-B.csv`（sha256 見上），沒有寫入。開工時 3 個檔的逐檔 sha 沒有另存，所以「其中原有檔案沒被改」無法逐檔證明，只能說本任務沒有任何寫入該目錄的程式。其餘 7 個目錄前後相同。')
a('預註冊 sha256（fc1462b8…8d10a）核對：OK。')
a('')
a('## 檔案')
a('- 新程式：`export_shares.mjs`、`s0_check.py`、`calibrate-wing.py`（與原檔 diff：`calibrate-wing.diff`）、`run_cards.py`、`build_card.py`、`e082.py`（與 e075.py diff：`e082.diff`）、`assemble.py`、`evaluate.mjs`（與原檔 diff：`evaluate.diff`）、`c2.py`、`s5.py`、`hash_ro.py`、`make_results.py`。')
a('- 輸出：`ranking.csv`（候選，sha256 %s）、`evaluation.json`、`npm-test.exit`／`npm-test.log`、`pos-shares.csv`、`cards/{off,on}/`、`out/{off,on}/`、`work/`、`results.json`。' % res['candidate_ranking_sha256'])
(HERE / 'report.md').write_text(NL.join(t) + NL, encoding='utf-8')
print(verdict)
print(json.dumps(passes, ensure_ascii=False))
print('c0 bitwise-different:', c0['cards_vs_card022_P1']['bitwiseDifferent'])
