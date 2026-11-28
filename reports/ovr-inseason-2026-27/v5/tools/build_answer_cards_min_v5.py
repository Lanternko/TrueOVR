"""v5 §R.7：重建 D1/D2 答案卡，MIN/GP 改用跨隊加總（-min 版）。

管線、summary、season-cards 能力值、RAPM 季集全部照 v5（build_answer_cards_v5.py），
只把既有的 prior 換成 v5/data/prior-<season>-v5.json（MIN/GP 跨隊加總）。輸出另存 -min，
v4 卡與 v5 舊卡都不動：
  v5/cards/2023-24-v5-min.csv / .json
  v5/cards/2024-25-v5-min.csv / .json
  v5/cards/2023-24-v5-4season-min.csv / .json（四季對照，不是答案）
自我檢查：
  1. 用 v4 prior + v4 RAPM 重建 → 與 v4/cards/<season>.csv 位元相同（builder 沒走鐘）。
  2. 2024-25 的 v5 prior 與 v3 prior 的 MIN 完全相同，所以 -min 卡應與 2024-25-v5.csv 位元相同。
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'v4' / 'tools'))
sys.path.insert(0, str(HERE))
import v4_common as C  # noqa: E402
import build_cards_v4 as B  # noqa: E402
import build_answer_cards_v5 as BA  # noqa: E402
import rapm_answer_v5 as RA  # noqa: E402
import minutes_v5 as M  # noqa: E402
import build_prior_v5 as P  # noqa: E402

V5 = C.REPORT / 'v5'
V5_CARDS = V5 / 'cards'
V5_DATA = V5 / 'data'
V5_PRIOR = {s: V5_DATA / f'prior-{s}-v5.json' for s in M.SEASONS}
SEASONS = {
    '2023-24': {'start': 'D1', 'twokSame': '2K24',
                'v4rapm': C.V3_DATA / 'rapm-2021-22_2022-23.csv'},
    '2024-25': {'start': 'D2', 'twokSame': '2K25',
                'v4rapm': C.V3_DATA / 'rapm-2021-22_2023-24.csv'},
}
for _s, _cfg in SEASONS.items():
    _tag, _have, _cfg['v5rapm'] = RA.answer_rapm_file(_s)
    _cfg['v5Seasons'] = _have
    _cfg['alt'] = RA.alt_rapm_file(_s)


def build_with(season, prior_path, rapm_path, outdir):
    """呼叫 v4 的 build()，只換 prior、RAPM 檔與輸出目錄。"""
    orig_prior = C.PRIOR_PATH[season]
    orig_rf, orig_cards = B.rapm_file, C.V4_CARDS
    try:
        C.PRIOR_PATH[season] = prior_path
        B.rapm_file = lambda s: rapm_path
        C.V4_CARDS = outdir
        outdir.mkdir(parents=True, exist_ok=True)
        return B.build(season)
    finally:
        C.PRIOR_PATH[season] = orig_prior
        B.rapm_file, C.V4_CARDS = orig_rf, orig_cards


def main():
    V5_CARDS.mkdir(parents=True, exist_ok=True)
    tmp = V5_CARDS / '_build_min'
    k27, yearly = BA.load_2k()
    report = {'spec': 'preregistration-v5 §R.7 第 1 條（跨隊加總）',
              'minCut': BA.MIN_CUT, 'seasons': {}}
    ok = True
    for season, cfg in SEASONS.items():
        # 1) builder 回歸：v4 prior + v4 RAPM
        build_with(season, P.PRIOR_SRC[season], cfg['v4rapm'], tmp)
        repro_v4 = (C.sha256_file(tmp / f'{season}.csv')
                    == C.sha256_file(C.V4_CARDS / f'{season}.csv'))
        # 2) v5-min：v5 prior（MIN 跨隊）+ v5 RAPM
        meta = build_with(season, V5_PRIOR[season], cfg['v5rapm'], tmp)
        out = V5_CARDS / f'{season}-v5-min.csv'
        shutil.move(tmp / f'{season}.csv', out)
        meta['file'] = out.relative_to(C.ROOT).as_posix()
        meta['sha256'] = C.sha256_file(out)
        meta['rapm']['seasons'] = cfg['v5Seasons']
        meta['rapm']['note'] = 'preregistration-v5 §R.3：含目標季、最多四季'
        v5old = V5_CARDS / f'{season}-v5.csv'
        meta['replacesV5'] = {'file': v5old.relative_to(C.ROOT).as_posix(),
                              'sha256': C.sha256_file(v5old)}
        meta['replacesV4'] = {'file': (C.V4_CARDS / f'{season}.csv').relative_to(C.ROOT).as_posix(),
                              'sha256': C.sha256_file(C.V4_CARDS / f'{season}.csv')}
        meta['minutes'] = {
            'rule': '§R.7 第 1 條：被交易球員 MIN/GP 跨隊加總',
            'source': M.describe(season),
            'priorFile': V5_PRIOR[season].relative_to(C.ROOT).as_posix(),
            'priorSha256': C.sha256_file(V5_PRIOR[season]),
        }
        meta['reproducesV4WithV4PriorAndRapm'] = repro_v4
        meta['identicalToV5Card'] = meta['sha256'] == meta['replacesV5']['sha256']
        C.write_json(out.with_suffix('.json'), meta)

        old = C.load_csv(v5old)
        new = C.load_csv(out)
        s = BA.summarize(season, cfg, old, new, k27, yearly,
                         diff_name=f'diff-v5-v5min-{season}.csv',
                         labels=('v5', 'v5min'))
        s.update({'v5minCard': meta['file'], 'v5minSha256': meta['sha256'],
                  'v5Card': meta['replacesV5']['file'], 'v5Sha256': meta['replacesV5']['sha256'],
                  'v4Card': meta['replacesV4']['file'], 'v4Sha256': meta['replacesV4']['sha256'],
                  'rapmV5': meta['rapm']['file'], 'rapmV5Sha256': meta['rapm']['sha256'],
                  'minutesSource': meta['minutes']['source'],
                  'identicalToV5Card': meta['identicalToV5Card'],
                  'reproducesV4WithV4PriorAndRapm': repro_v4,
                  'buildChecksPass': meta['pass']})
        if cfg['alt']:  # 2023-24 四季對照
            _, alt_seasons, alt_path = cfg['alt']
            n = len(alt_seasons)
            am = build_with(season, V5_PRIOR[season], alt_path, tmp)
            alt_old = V5_CARDS / f'{season}-v5-{n}season.csv'
            alt_new = V5_CARDS / f'{season}-v5-{n}season-min.csv'
            shutil.move(tmp / f'{season}.csv', alt_new)
            am['file'] = alt_new.relative_to(C.ROOT).as_posix()
            am['sha256'] = C.sha256_file(alt_new)
            am['rapm']['seasons'] = alt_seasons
            am['rapm']['note'] = f'對照用，不是答案卡：{n} 季（含 2020-21，playbyplayv2 存檔重建）'
            am['role'] = 'comparison only'
            am['minutes'] = meta['minutes']
            am['replacesV5'] = {'file': alt_old.relative_to(C.ROOT).as_posix(),
                                'sha256': C.sha256_file(alt_old)}
            C.write_json(alt_new.with_suffix('.json'), am)
            sa = BA.summarize(season, cfg, C.load_csv(alt_old), C.load_csv(alt_new), k27, yearly,
                              diff_name=f'diff-{n}season-{n}season-min-{season}.csv',
                              labels=(f'{n}season', f'{n}season-min'))
            sa.update({'altCard': alt_new.relative_to(C.ROOT).as_posix(),
                       'altSha256': am['sha256'],
                       'altRapm': am['rapm']['file'], 'altRapmSeasons': alt_seasons,
                       'altBuildChecksPass': am['pass']})
            s[f'vs{n}season'] = sa
        report['seasons'][season] = s
        ok = ok and repro_v4 and meta['pass']
    shutil.rmtree(tmp, ignore_errors=True)
    report['pass'] = bool(ok)
    C.write_json(V5_CARDS / 'diff-summary-v5-min.json', report)
    print(json.dumps({s: {'reproV4': v['reproducesV4WithV4PriorAndRapm'],
                          'pass': v['buildChecksPass'],
                          'identicalToV5': v['identicalToV5Card'],
                          'all': v['all'],
                          'vs2k27': {t: v['vs2k'][t]['all']['2K27'] for t in ('v5', 'v5min')}}
                      for s, v in report['seasons'].items()}, ensure_ascii=False, indent=1))
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
