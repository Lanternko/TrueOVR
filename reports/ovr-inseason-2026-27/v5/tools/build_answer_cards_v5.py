"""v5 §R.3：重建 D1（2023-24）、D2（2024-25）答案卡，只換 RAPM 檔。

管線、summary、prior（season-cards 能力值）全部照 v4 的 build_cards_v4.build，
只把 rapm_file 換成 §R.3 指定的檔：
  2023-24  v3/data/rapm-2021-22_2023-24.csv（三季；使用者 2026-10-27 決定照 §R.3）
           另建四季對照卡 2023-24-v5-4season（v5/data/rapm-2020-21_2023-24.csv），不是答案
  2024-25  v4/data/rapm-2021-22_2024-25.csv（四季）
被交易球員分鐘數仍照 v4（不跨隊加總），因為 §R.7 第 1 條使用者尚未定案。

輸出（v4 舊卡不動）：
  v5/cards/<season>-v5.csv / .json      新答案卡
  v5/cards/diff-v4-v5-<season>.csv      每位球員 v4 vs v5 OVR、名次、變化
  v5/cards/diff-summary-v5.json         相關、最大變動前 10、對 2K27 / 同期 2K 的 rank ρ 與中位數
先自我檢查：用同一支程式以 v4 RAPM 重建，必須和 v4/cards/<season>.csv 位元相同。
"""
import csv
import json
import re
import shutil
import statistics
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
sys.path.insert(0, str(HERE))
import v4_common as C  # noqa: E402
import build_cards_v4 as B  # noqa: E402
import rapm_answer_v5 as RA  # noqa: E402
from scipy.stats import pearsonr, spearmanr  # noqa: E402

V5_CARDS = C.REPORT / 'v5' / 'cards'
TWOK = C.ROOT / 'reports/ovr-v55-2k27-compare'
SEASONS = {
    '2023-24': {'start': 'D1', 'v4': C.V3_DATA / 'rapm-2021-22_2022-23.csv',
                'v4Seasons': ['2021-22', '2022-23'], 'twokSame': '2K24'},
    '2024-25': {'start': 'D2', 'v4': C.V3_DATA / 'rapm-2021-22_2023-24.csv',
                'v4Seasons': ['2021-22', '2022-23', '2023-24'], 'twokSame': '2K25'},
}
# v5 RAPM 檔與季集由 rapm_answer_v5 決定（先跑那支）
for _s, _cfg in SEASONS.items():
    _tag, _have, _cfg['v5'] = RA.answer_rapm_file(_s)
    _cfg['v5Seasons'] = _have
    _cfg['note'] = f'{len(_have)} 季，含目標季'
    _cfg['alt'] = RA.alt_rapm_file(_s)  # (tag, seasons, path) 或 None
MIN_CUT = 500


def build_with(season, rapm_path, outdir):
    """呼叫 v4 的 build()，只換 RAPM 檔與輸出目錄。"""
    orig_rf, orig_cards = B.rapm_file, C.V4_CARDS
    try:
        B.rapm_file = lambda s: rapm_path
        C.V4_CARDS = outdir
        outdir.mkdir(parents=True, exist_ok=True)
        return B.build(season)
    finally:
        B.rapm_file, C.V4_CARDS = orig_rf, orig_cards


def norm(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', s)
    return re.sub(r'\s+', '', s)


def load_2k():
    k27 = {}
    for r in C.load_csv(TWOK / '2k27_ratings.csv'):
        k27[norm(r['name'])] = float(r['overall2k'])
    yearly = {}
    for r in C.load_csv(TWOK / '2k_yearly_ovr.csv'):
        yearly[norm(r['name'])] = {k: float(v) for k, v in r.items() if k.startswith('2K') and v}
    return k27, yearly


def ranks(rows):
    order = sorted(rows, key=lambda r: (-float(r['ovr']), int(r['playerId'])))
    return {int(r['playerId']): i + 1 for i, r in enumerate(order)}


def vs_2k(rows, ref, label):
    pairs = [(float(r['ovr']), ref[norm(r['name'])]) for r in rows if norm(r['name']) in ref]
    if len(pairs) < 3:
        return {'ref': label, 'n': len(pairs)}
    xs, ys = zip(*pairs)
    return {'ref': label, 'n': len(pairs),
            'rankRho': round(float(spearmanr(xs, ys).statistic), 4),
            'medianCardOvr': round(statistics.median(xs), 3),
            'median2k': round(statistics.median(ys), 3),
            'medianCardMinus2k': round(statistics.median(x - y for x, y in pairs), 3)}


def summarize(season, cfg, old, new, k27, yearly, diff_name=None, labels=('v4', 'v5')):
    """old/new 兩張卡的差異；labels 決定欄位與 2K 區塊的名稱（v4/v5 或 3season/4season）。"""
    la, lb = labels
    old_by = {int(r['playerId']): r for r in old}
    new_by = {int(r['playerId']): r for r in new}
    assert set(old_by) == set(new_by), f'{la}/{lb} 球員集合不同'
    ro, rn = ranks(old), ranks(new)
    diff = []
    for pid in sorted(old_by, key=lambda p: rn[p]):
        o, n = old_by[pid], new_by[pid]
        diff.append({'playerId': pid, 'name': n['name'], 'pos': n['pos'],
                     'MIN_season': n['MIN_season'],
                     f'ovr_{la}': float(o['ovr']), f'ovr_{lb}': float(n['ovr']),
                     'dOvr': round(float(n['ovr']) - float(o['ovr']), 4),
                     f'rank_{la}': ro[pid], f'rank_{lb}': rn[pid], 'dRank': ro[pid] - rn[pid]})
    C.write_csv(V5_CARDS / (diff_name or f'diff-v4-v5-{season}.csv'), diff)

    def stats(sub):
        a = [d[f'ovr_{la}'] for d in sub]
        b = [d[f'ovr_{lb}'] for d in sub]
        dv = [d['dOvr'] for d in sub]
        return {'n': len(sub), 'pearson': round(float(pearsonr(a, b).statistic), 4),
                'spearman': round(float(spearmanr(a, b).statistic), 4),
                'meanDOvr': round(statistics.fmean(dv), 3),
                'medianDOvr': round(statistics.median(dv), 3),
                'meanAbsDOvr': round(statistics.fmean(abs(x) for x in dv), 3),
                'maxAbsDOvr': round(max(abs(x) for x in dv), 3),
                'nAbsDOvrGt3': sum(abs(x) > 3 for x in dv),
                f'medianOvr_{la}': round(statistics.median(a), 3),
                f'medianOvr_{lb}': round(statistics.median(b), 3),
                'meanAbsDRank': round(statistics.fmean(abs(d['dRank']) for d in sub), 2)}

    big = [d for d in diff if float(d['MIN_season']) >= MIN_CUT]
    top = lambda sub: [{k: d[k] for k in ('name', 'pos', 'MIN_season', f'ovr_{la}', f'ovr_{lb}', 'dOvr',
                                          f'rank_{la}', f'rank_{lb}')}
                       for d in sorted(sub, key=lambda d: -abs(d['dOvr']))[:10]]
    same = {k: v[cfg['twokSame']] for k, v in yearly.items() if cfg['twokSame'] in v}
    twok = {}
    for tag, rows in ((la, old), (lb, new)):
        rows_big = [r for r in rows if float(r['MIN_season']) >= MIN_CUT]
        twok[tag] = {'all': {'2K27': vs_2k(rows, k27, '2K27'),
                             cfg['twokSame']: vs_2k(rows, same, cfg['twokSame'])},
                     f'MIN>={MIN_CUT}': {'2K27': vs_2k(rows_big, k27, '2K27'),
                                         cfg['twokSame']: vs_2k(rows_big, same, cfg['twokSame'])}}
    return {'start': cfg['start'], 'all': stats(diff), f'MIN>={MIN_CUT}': stats(big),
            'top10AbsDOvr_all': top(diff), f'top10AbsDOvr_MIN>={MIN_CUT}': top(big),
            'vs2k': twok}


def main():
    V5_CARDS.mkdir(parents=True, exist_ok=True)
    tmp = V5_CARDS / '_build'
    k27, yearly = load_2k()
    report = {'spec': 'preregistration-v5 §R.3', 'minCut': MIN_CUT, 'seasons': {}}
    ok = True
    for season, cfg in SEASONS.items():
        # 自我檢查：同一支程式以 v4 RAPM 重建 → 必須與 v4 舊卡位元相同
        build_with(season, cfg['v4'], tmp)
        repro = C.sha256_file(tmp / f'{season}.csv') == C.sha256_file(C.V4_CARDS / f'{season}.csv')
        # v5：只換 RAPM 檔
        meta = build_with(season, cfg['v5'], tmp)
        meta['rapm']['seasons'] = cfg['v5Seasons']
        meta['rapm']['note'] = f"preregistration-v5 §R.3：含目標季、最多四季（{cfg['note']}）"
        meta['file'] = (V5_CARDS / f'{season}-v5.csv').relative_to(C.ROOT).as_posix()
        meta['replaces'] = {'file': (C.V4_CARDS / f'{season}.csv').relative_to(C.ROOT).as_posix(),
                            'sha256': C.sha256_file(C.V4_CARDS / f'{season}.csv'),
                            'rapmFile': cfg['v4'].relative_to(C.ROOT).as_posix(),
                            'rapmSeasons': cfg['v4Seasons']}
        meta['reproducesV4WithV4Rapm'] = repro
        meta['crossTeamMinutes'] = '照 v4，不跨隊加總（§R.7 第 1 條未定案）'
        shutil.move(tmp / f'{season}.csv', V5_CARDS / f'{season}-v5.csv')
        meta['sha256'] = C.sha256_file(V5_CARDS / f'{season}-v5.csv')
        C.write_json(V5_CARDS / f'{season}-v5.json', meta)
        old = C.load_csv(C.V4_CARDS / f'{season}.csv')
        new = C.load_csv(V5_CARDS / f'{season}-v5.csv')
        s = summarize(season, cfg, old, new, k27, yearly)
        s.update({'v5Card': meta['file'], 'v5Sha256': meta['sha256'],
                  'v4Card': meta['replaces']['file'], 'rapmV4': meta['replaces']['rapmFile'],
                  'rapmV5': meta['rapm']['file'], 'rapmV5Sha256': meta['rapm']['sha256'],
                  'rapmSeasonsV4': cfg['v4Seasons'], 'rapmSeasonsV5': cfg['v5Seasons'],
                  'buildChecksPass': meta['pass'], 'reproducesV4WithV4Rapm': repro})
        if cfg['alt']:  # 2023-24：四季版（2020-21..2023-24）只做對照
            _, alt_seasons, alt_path = cfg['alt']
            n, m = len(alt_seasons), len(cfg['v5Seasons'])
            am = build_with(season, alt_path, tmp)
            am['rapm']['seasons'] = alt_seasons
            am['rapm']['note'] = f'對照用，不是答案卡：{n} 季（含 2020-21，playbyplayv2 存檔重建）'
            alt_card = V5_CARDS / f'{season}-v5-{n}season.csv'
            shutil.move(tmp / f'{season}.csv', alt_card)
            am['file'] = alt_card.relative_to(C.ROOT).as_posix()
            am['sha256'] = C.sha256_file(alt_card)
            am['role'] = 'comparison only'
            C.write_json(alt_card.with_suffix('.json'), am)
            sa = summarize(season, cfg, new, C.load_csv(alt_card), k27, yearly,
                           diff_name=f'diff-{m}season-{n}season-{season}.csv',
                           labels=(f'{m}season', f'{n}season'))
            sa.update({'altCard': am['file'], 'altSha256': am['sha256'],
                       'altRapm': am['rapm']['file'], 'altRapmSeasons': alt_seasons,
                       'altBuildChecksPass': am['pass']})
            s[f'vs{n}season'] = sa
        report['seasons'][season] = s
        ok = ok and repro and meta['pass']
    shutil.rmtree(tmp, ignore_errors=True)
    report['pass'] = bool(ok)
    C.write_json(V5_CARDS / 'diff-summary-v5.json', report)
    print(json.dumps({s: {'repro': v['reproducesV4WithV4Rapm'], 'pass': v['buildChecksPass'],
                          'all': v['all'], 'vs2k27': {t: v['vs2k'][t]['all']['2K27'] for t in ('v4', 'v5')}}
                      for s, v in report['seasons'].items()}, ensure_ascii=False, indent=1))
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
