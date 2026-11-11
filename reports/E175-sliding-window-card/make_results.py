"""E-175 收工：把 repro、§2（主／敏感度）、§3 合成 results.json，附輸入檔 sha256 與程式 git 狀態。
用法（cwd＝repo 根目錄）：python -I -X utf8 reports/E175-sliding-window-card/make_results.py
"""
import json
import subprocess
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import e175_lib as L

ROOT = L.ROOT
j = lambda n: json.loads((H / n).read_text(encoding='utf-8'))
main, sens, s3, s3a, repro, chk = j('backtest-result.json'), j('backtest-result-sens.json'), j('section3-result.json'), j('section3-attrs.json'), j('repro-result.json'), j('check_rate_level.json')

inputs = [L.V61 / 'backtest.json', L.HIST / 'positions.csv', L.LEAGUE, L.DISCOUNT_LOG, L.BENCH / 'base.json', L.BENCH / 'shots.json', L.E090 / 'h1-results.json', L.E101 / 'h1-results.json',
          L.E070 / 'vol-fit.json', L.E125 / 'astvol-fit.json', ROOT / 'src/constants.js', R_ := L.R / 'card-0.2.9a/ranking.csv', L.R / 'card-0.2.9a/cards/K6/primary/summary.json',
          L.R / 'card-0.2.5/ranking.csv', H / 'preregistration.md']
inputs += [L.HIST / f'pergame-{s}.csv.gz' for s in L.SEASONS]
inputs += [L.E101 / 'history' / f'pbp-zones-{s}.csv.gz' for s in L.ZONE_SEASONS]
inputs += [L.HIST / f'pbp-drive-{s}.csv.gz' for s in L.DRIVE_SEASONS]
inputs += [L.E125 / 'pool-P50' / f'raw-{s}.json' for s in ('2022-23', '2023-24', '2024-25')]
inputs += [ROOT / 'data/season-source/player-games.json'] + [ROOT / 'data/defense-seventh' / s / 'player-games.json' for s in L.SEASONS[:-1]]


def git(*a):
    r = subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
    return r.stdout.strip()


code = sorted(H.glob('*.py'))
res = {
    'experiment': 'E-175', 'preregistration_sha256': L.sha256(H / 'preregistration.md'),
    'preregistration_sha256_frozen': (H / 'preregistration.sha256').read_text().split()[0],
    'git': {'head': git('rev-parse', 'HEAD'), 'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
            'status_E175_dir': git('status', '--porcelain', '--', 'reports/E175-sliding-window-card'),
            'note': 'E-175 腳本尚未 commit（任務限制：不 commit）；以 code_sha256 為準'},
    'code_sha256': {p.name: L.sha256(p) for p in code},
    'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): L.sha256(p) for p in inputs},
    'step1_repro': {'pooled': repro['pooled'], 'per_attr': {a: {k: v[k] for k in ('nVsRanking', 'within0.1', 'share', 'maxDiffRanking', 'maxDiffFull(tail-e123a)')} for a, v in repro['attrs'].items()}, 'pass': repro['pooled']['share'] >= 0.99},
    'step2_main_2025-26': {k: main['2025-26'][k] for k in ('cells', 'cut', 'pooledAttr', 'pooled', 'verdict', 'fits')},
    'step2_secondary_2024-25': {k: main['2024-25'][k] for k in ('cells', 'cut', 'pooledAttr', 'pooled', 'verdict')},
    'step2_sensitivity_midshort_league_prior': {S: {k: sens[S][k] for k in ('cut', 'pooledAttr', 'pooled', 'verdict')} for S in ('2025-26', '2024-25')},
    'step2_meta': main['meta'], 'sanity_rate_level_vs_backtest_json': chk,
    'step3_sd_ratio': s3a['sd'], 'step3_sd_all_in_band': s3a['allInBand'], 'step3_ovr': {k: v for k, v in s3.items()},
    'verdict': main['2025-26']['verdict'],
}
(H / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
v = res['verdict']
print('verdict', v['label'], '| pooled Rbar', round(main['2025-26']['pooled']['Rbar'], 4), [round(x, 4) for x in main['2025-26']['pooled']['Rbar_ci90']])
for S in ('2025-26', '2024-25'):
    m = main[S]
    print(S, 'cut Rbar+ci', {c: (round(x['Rbar'], 4), [round(y, 3) for y in x['Rbar_ci90']]) for c, x in m['cut'].items()})
    print(S, 'pooled attr R', {a: (round(x['R'], 3), [round(y, 3) for y in x['R_ci90']]) for a, x in m['pooledAttr'].items()})
    print(S, 'n per attr (46.7%)', {a: m['cells'][f'46.7%|{a}']['n'] for a in L.MIN_D2 if a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short')}, 'drive', m['cells']['46.7%|drive']['n'])
print('inputs', len(res['input_sha256']))
