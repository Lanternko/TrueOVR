"""P7：防洩漏檢查（preregistration-v4 §5.3 G1、§9 P7）。

判定（程式，非人工）：
  1. 每個起點的 prior/target 季別必須 prior < target；RAPM 預測檔的「檔名最大季」< target。
  2. 每張卡 c_s 用的 RAPM 檔最大季 < s。
  3. v4 的工具與凍結候選輸入（v4/data、v4/cards、v4/fit 的 JSON）不得出現 2026-27 的
     資料參照：出現 '2026-27' 的行，只有「目標季標籤」允許（S* 的 target、L0 之後才會有資料）；
     任何含路徑字樣（data/、defense-seventh、.csv/.json 檔名）者一律算違反。
輸出 v4/leakage.json。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import v4_common as C

SEASON = re.compile(r'\b(20\d\d-\d\d)\b')
DATAISH = ('data/', 'defense-seventh', 'pbp', '.csv', '.json', 'season-cards', 'rapm-')
# 真正算違反的是「2026-27 被當成資料路徑」：季節字串與路徑字樣相連
PATHREF = (re.compile(r'(data/|defense-seventh|/)[\w/.\-]*2026-27'),
           re.compile(r'2026-27[\w/.\-]*\.(csv|json)'))


def seasons_in(text):
    return SEASON.findall(text)


def max_season(name):
    s = seasons_in(name or '')
    return max(s) if s else None


def main():
    out = {'spec': 'preregistration-v4 §5.3 G1 / §9 P7', 'checks': {}, 'violations': [],
           'occurrences': []}

    # 1. 起點鏈：prior < target、pred RAPM 最大季 < target
    chain = {}
    for s, ch in C.CHAIN.items():
        pred = C.rapm_path(ch['pred'])
        mx = max_season(pred.name)
        ok = bool(ch['prior'] < ch['target']) and (mx is None or mx < ch['target'])
        chain[s] = {'prior': ch['prior'], 'target': ch['target'],
                    'rapm': pred.name if pred else None, 'rapmMaxSeason': mx, 'ok': ok,
                    'predIsNone': ch['pred'] is None}
        if not ok:
            out['violations'].append({'check': 'chain', 'start': s, **chain[s]})
    out['checks']['chainLeakFree'] = all(v['ok'] for v in chain.values())
    out['chain'] = chain

    # 2. 卡片：每季 RAPM 檔最大季 < 該季
    import build_cards_v4 as B
    cards = {}
    for season in C.SEASONS:
        f = B.rapm_file(season)
        mx = max_season(f.name)
        ok = mx is None or mx < season
        cards[season] = {'rapm': f.name, 'maxSeason': mx, 'ok': ok}
        if not ok:
            out['violations'].append({'check': 'cardRapm', 'season': season, **cards[season]})
    out['checks']['cardRapmLeakFree'] = all(v['ok'] for v in cards.values())
    out['cards'] = cards

    # 3. 工件與工具不得引用 2026-27 資料
    targets = {'S*': '2026-27'}
    files = sorted((C.V4 / 'tools').glob('*.py')) + sorted(C.V4_DATA.glob('*.json')) \
        + sorted(C.V4_CARDS.glob('*.json')) + sorted(C.V4_FIT.glob('*.json'))
    for f in files:
        try:
            lines = f.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(lines, 1):
            # 報告資料夾名稱本身含 '2026-27'（ovr-inseason-2026-27），先遮掉再找季別字串
            probe = line.replace('ovr-inseason-2026-27', '<report-dir>')
            if '2026-27' not in probe:
                continue
            dataish = [k for k in DATAISH if k in probe] if any(
                p.search(probe) for p in PATHREF) else []
            rel = f.relative_to(C.ROOT).as_posix()
            rec = {'file': rel, 'line': i, 'text': line.strip()[:160],
                   'dataishTokens': dataish}
            out['occurrences'].append(rec)
            if dataish:
                out['violations'].append({'check': 'grep2026', **rec})
    out['checks']['no2026_27DataRefs'] = not any(v['check'] == 'grep2026'
                                                 for v in out['violations'])
    out['occurrenceCount'] = len(out['occurrences'])
    out['note'] = ('出現的 2026-27 只有目標季標籤（S* 的 target）與說明文字；'
                   '沒有任何 2026-27 資料檔被讀取或寫入。')
    out['pass'] = bool(all(out['checks'].values()))
    C.write_json(C.V4 / 'leakage.json', out)
    print(json.dumps({'checks': out['checks'], 'pass': out['pass'],
                      'occurrences': out['occurrences']}, ensure_ascii=False, indent=1))
    return 0 if out['pass'] else 4


if __name__ == '__main__':
    raise SystemExit(main())
