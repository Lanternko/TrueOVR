"""E-191b P1m（card／inseason 0.2.10f）：凍結 3PT 欄對照池的過去季人群（reports/card-0.2.7+E123-tail-3pt-rim-pres/work/season-values.json 的 vals.T 各季球員 id）。
window10.Win10.tv_past_pool 只用這份名單加 D.pidx、窗口加權 MIN>=500 篩人，不再讀研究資料夾。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_tvpool_0210f.py → live/tvpool-members-card0210f.json"""
import hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SV_FILE = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/work/season-values.json'
OUT = HERE / 'tvpool-members-card0210f.json'


def main():
    sv = json.loads(SV_FILE.read_text(encoding='utf-8'))['vals']['T']
    doc = {'doc': 'E-191b P1m 對照池：各季 SV（season-values.json vals.T）人群的 playerId；window10.Win10.tv_past_pool 讀取',
           'sourceSha256': {'season-values.json': hashlib.sha256(SV_FILE.read_bytes()).hexdigest()},
           'seasons': {t: sorted(int(p) for p in sv[t]) for t in sorted(sv)}}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'n': {t: len(v) for t, v in doc['seasons'].items()}}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
