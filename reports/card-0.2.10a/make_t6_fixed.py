"""card 0.2.10a 步驟 0：L-102 修正 BPM 解析後重產 2025-26 T6 目標檔（primary／split A／B），換進部件卡的 --rapm。
做法與 E-153 c6_2526 相同（swap_rapm(來源, 輸出, T6 候選)）；先用 pre-L102 舊候選檔重現 0.2.10 實際用的三份檔（sha 必須相同），再用新候選檔產出。
用法：python -I -X utf8 reports/card-0.2.10a/make_t6_fixed.py"""
import hashlib, json, pickle, sys
from pathlib import Path
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E142-card-target'))
import build_card_t as BC   # noqa: E402
CANDS = ROOT / 'reports/E142-card-target/phase1-work/cands'
E164W = ROOT / 'reports/card-0.2.9+E164-no-stamina/work/base-S-2025-26/c0'
SRC = {'primary': ROOT / 'reports/impact-rapm/rapm.csv',
       'fitA': BC.SW / 'c0p/split/rapm-A.csv', 'fitB': BC.SW / 'c0p/split/rapm-B.csv'}
DST = {'primary': 'rapm-R.csv', 'fitA': 'split/rapm-A.csv', 'fitB': 'split/rapm-B.csv'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    old = pickle.load(open(CANDS / 'pre-L102/T6-2025-26.pkl', 'rb'))
    new = pickle.load(open(CANDS / 'T6-2025-26.pkl', 'rb'))
    out = {'cand_old_rows': len(old), 'cand_new_rows': len(new), 'added': sorted(set(new) - set(old)), 'files': {}}
    for tag, sub in (('repro', old), ('fixed', new)):
        W = H / 'work/t6' / tag; (W / 'split').mkdir(parents=True, exist_ok=True)
        for p in SRC:
            rows = BC.swap_rapm(SRC[p], W / DST[p], sub)
            out['files'][f'{tag}/{p}'] = {'rows': rows, 'sha256': sha(W / DST[p])}
            if tag == 'repro':
                assert sha(W / DST[p]) == sha(E164W / DST[p]), f'{p}：舊候選檔重現不了 0.2.10 的目標檔'
    (H / 'work/t6/t6-fixed.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
