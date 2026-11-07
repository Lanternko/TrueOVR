"""v5 §R.3：答案卡 RAPM 季集 = 目標季（含）往前最多四季，最早 2021-22。

  2023-24 答案卡  2021-22..2023-24（三季；使用者 2026-10-27 決定照 §R.3，最早 2021-22）
  2024-25 答案卡  2021-22..2024-25（四季）
  對照（不是答案）2023-24 四季版 2020-21..2023-24 → v5/data/rapm-2020-21_2023-24.csv
                  2020-21 stint 解壓到 reports/defense-seventh/2020-21/stints/stints.jsonl

做法：用 v4 的 rapm_v4.build（= tools/rapm_2022_25.py 的 ridge + CV，λ 網格不變）
從本機 stint 重算兩組 RAPM 到暫存目錄，逐位比對 §R.3 指定的現有檔：
  v3/data/rapm-2021-22_2023-24.csv
  v4/data/rapm-2021-22_2024-25.csv
相同才算過；答案卡讀的是 §R.3 指定的現有檔（SHA 寫進 v5/data/rapm-answer-v5.json）。
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V4_TOOLS = HERE.parents[1] / 'v4' / 'tools'
sys.path.insert(0, str(V4_TOOLS))
import v4_common as C  # noqa: E402
import rapm_v4 as RV  # noqa: E402
import rapm_2022_25 as R  # noqa: E402

V5 = C.REPORT / 'v5'
V5_DATA = V5 / 'data'
WANTED = {
    '2023-24': ['2021-22', '2022-23', '2023-24'],
    '2024-25': ['2021-22', '2022-23', '2023-24', '2024-25'],
}
# 對照用季集（不進答案卡）。第一次跑時寫入 v5/data/rapm-<tag>.csv，之後逐位比對該檔。
ALT = {'2023-24': ['2020-21', '2021-22', '2022-23', '2023-24']}
# 已存在、§R.3 指定的檔（以季集 tag 為鍵）
PINNED = {
    '2021-22_2023-24': C.V3_DATA / 'rapm-2021-22_2023-24.csv',
    '2021-22_2024-25': C.V4_DATA / 'rapm-2021-22_2024-25.csv',
}


# 不是 cdn liveData 管線產出的 stint：來源與管線差異（同時寫進 README）
STINT_SOURCES = {
    '2020-21': {
        'archive': 'v5/history/stints/stints-2020-21.jsonl.gz（解壓到 reports/defense-seventh/2020-21/stints/stints.jsonl）',
        'preparation': 'v5/history/stints/preparation-2020-21.json',
        'validation': 'v5/history/validation-onoff.json',
        'pipelineDiffs': [
            '從 stats.nba.com playbyplayv2 存檔重建（shufinskiy/nba_data 鏡像），不是 cdn liveData',
            '回合數為回合結束的整數計數，不按時鐘分攤',
            '排除規則的分鐘容許誤差 2.1 秒（cdn 管線 1.1 秒）',
            '1080 場中 1066 場可用；整季得分效率比值 1.002',
            '同法重建 2022-23/2023-24 對照 repo onoff.csv（≥2000 回合）：在場淨效率 r=0.966/0.978，on-off 差 r=0.945/0.943',
        ],
    },
}


def answer_rapm_file(target):
    """答案卡讀的 RAPM 檔（§R.3 指定的現有檔）。"""
    seasons = WANTED[target]
    tag = f'{seasons[0]}_{seasons[-1]}'
    return tag, seasons, PINNED[tag]


def alt_rapm_file(target):
    """對照用 RAPM 檔；沒有對照季集或缺 stint 時回 None。"""
    seasons = ALT.get(target)
    if not seasons or not all(stint_file(s).exists() for s in seasons):
        return None
    tag = f'{seasons[0]}_{seasons[-1]}'
    return tag, seasons, V5_DATA / f'rapm-{tag}.csv'


def run_set(tag, seasons, final, tmp):
    path, meta = RV.build(tag, seasons, outdir=tmp)
    first = not final.exists()
    if first:
        shutil.copyfile(path, final)
    chk = RV.compare(path, final)
    return {'seasons': seasons, 'file': final.relative_to(C.ROOT).as_posix(),
            'sha256': C.sha256_file(final), 'rerunSha256': meta['sha256'],
            'rerun': {k: meta[k] for k in ('observations', 'players', 'pooled', 'lastSeason')},
            'rerunVsFile': chk,
            'rerunVsFileNote': ('第一次寫入：identical 只表示寫入無誤' if first
                                else '從 stint 重跑，與檔案逐位比對'),
            'stintSha256': {s: C.sha256_file(stint_file(s)) for s in seasons},
            'stintSources': {s: STINT_SOURCES[s] for s in seasons if s in STINT_SOURCES}}


def stint_file(season):
    if season == '2021-22':
        return C.V3_DATA / 'derived-2021-22/stints/stints.jsonl'
    return R.stint_path(season)


def main():
    V5_DATA.mkdir(parents=True, exist_ok=True)
    tmp = V5_DATA / '_rapm_rerun'
    tmp.mkdir(exist_ok=True)
    out = {'spec': 'preregistration-v5 §R.3（答案端：含目標季、最多四季、最早 2021-22）',
           'decision': '2026-10-27 使用者決定 2023-24 主卡用三季版（照 §R.3）；四季版只做對照',
           'method': 'v4/tools/rapm_v4.build → tools/rapm_2022_25.py fit_rapm（ridge，CV 選 λ，網格 100..30000）',
           'targets': {}}
    ok = True
    for target in WANTED:
        tag, seasons, final = answer_rapm_file(target)
        main_set = run_set(tag, seasons, final, tmp)
        entry = {'usedSeasons': seasons, **main_set}
        alt = alt_rapm_file(target)
        if alt:
            entry['comparison'] = {'note': '對照用，不進答案卡', **run_set(*alt, tmp)}
            ok = ok and entry['comparison']['rerunVsFile']['identical']
        out['targets'][target] = entry
        ok = ok and main_set['rerunVsFile']['identical']
    shutil.rmtree(tmp)
    out['pass'] = bool(ok)
    C.write_json(V5_DATA / 'rapm-answer-v5.json', out)
    brief = lambda v: {'seasons': v['seasons'], 'sha256': v['sha256'],
                       'identical': v['rerunVsFile']['identical'],
                       'maxAbsDiff': v['rerunVsFile']['maxAbsDiff'],
                       'lambda': v['rerun']['pooled']['lambda']}
    print(json.dumps({t: {'main': brief(v)} | ({'comparison': brief(v['comparison'])}
                                                if 'comparison' in v else {})
                      for t, v in out['targets'].items()}, ensure_ascii=False, indent=1))
    return 0 if ok else 3


if __name__ == '__main__':
    raise SystemExit(main())
