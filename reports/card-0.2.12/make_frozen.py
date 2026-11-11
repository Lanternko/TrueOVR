"""frozen.json：card 0.2.10 凍結在 0.2.9a 的值（R-110 精神：映射、係數、錨凍結在 2025-26，只換 8 項屬性）。
來源：0.2.9a 部件卡 summary.json／pergame-summary.json（公式、PR1/PR50/PR99 錨、r_repl、主／替補錨）、
use_layer.py capture 在 0.2.9a 部件卡上的輸出（用人層 WLS 係數、r_repl、兩段映射錨）。"""
import hashlib, json
from pathlib import Path
H = Path(__file__).resolve().parent
R = H.parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cap = json.loads((H / 'work/capture/captured.json').read_text(encoding='utf-8'))
src = {}
out = {'note': 'card 0.2.10 全凍結值（取自 card 0.2.9a）；只有 8 項屬性（drive, foulDraw, ft, mid, pass, rebound, short, tovSkill）換成滑動窗口值。',
       'parts': {}, 'use_layer': {'wls_card': cap['wls_card'], 'r_repl': cap['r_repl_this_run'], 'anchors': cap['anchors_this_run'],
                                  'design': '[1,p,L,a,y,v,y*L,v*L]（Y0，連續 d）', 'captured_from': 'reports/card-0.2.10/work/capture/captured.json（use_layer.py capture，ranking.csv 與 card-0.2.9a 逐位元相同）'}}
for p in ('primary', 'fitA', 'fitB'):
    d = R / 'reports/card-0.2.9a/cards/K6' / p
    s = json.loads((d / 'summary.json').read_text(encoding='utf-8'))
    g = json.loads((d / 'pergame-summary.json').read_text(encoding='utf-8'))
    out['parts'][p] = {'formula': s['formula'], 'scaleAnchorsPer36': s['scaleAnchorsPer36'], 'pergame': g}
    for f in ('summary.json', 'pergame-summary.json', 'pred.csv'):
        src[f'reports/card-0.2.9a/cards/K6/{p}/{f}'] = sha(d / f)
src['reports/card-0.2.9a/ranking.csv'] = sha(R / 'reports/card-0.2.9a/ranking.csv')
src['reports/card-0.2.10/work/capture/ranking.csv'] = sha(H / 'work/capture/ranking.csv')
out['source_sha256'] = src
out['cap_reference'] = 'H1 封頂參照（RAPM／2K 名次）是 2025-26 資料，不隨屬性改；封頂門檻 T(a) 依本卡 pred 分布重算（calibrate 內部）。'
(H / 'frozen.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('ok', len(json.dumps(out)))
