"""card 0.2.14 正式卡：從 card-0.2.14-cand2 產出（R-183 MIX 加分＋R-184 500 分鐘以下按比例打折），格式照 card-0.2.13a。
ranking.csv＝cand2 原樣（核對 sha）；其他附檔（three-value、gravity、pnr、def-L、rapm-T6）與 0.2.13a 相同，複製過來讓本卡自足。
summary.json 沿用 0.2.13a 的錨點／映射欄（係數不重擬合，MIX 是疊在 OVR 上的加分），run_c4_live 的 sha 核對讀 ranking_csv_sha256。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.14/build_card_0214.py"""
import hashlib, json, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE, CAND2 = ROOT / 'reports/card-0.2.13a', ROOT / 'reports/card-0.2.14-cand2'
c2 = json.loads((CAND2 / 'summary.json').read_text(encoding='utf-8'))
assert sha(CAND2 / 'ranking.csv') == c2['ranking_csv_sha256'], 'cand2 ranking.csv 與 summary 不符'
shutil.copyfile(CAND2 / 'ranking.csv', HERE / 'ranking.csv')
shutil.copyfile(CAND2 / 'g5.md', HERE / 'g5.md')
for f in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'pnr-attr.csv', 'rapm-T6.csv', 'three-value.csv'):
    shutil.copyfile(BASE / f, HERE / f)
s = json.loads((BASE / 'summary.json').read_text(encoding='utf-8'))
mix = json.loads((ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214.json').read_text(encoding='utf-8'))
s.update({
    'version': 'card 0.2.14',
    'base': 'card 0.2.13a（reports/card-0.2.13a/）＋MIX 加分（reports/card-0.2.14-cand2/）',
    'change': 'E-290 MIX 籃板／兩分干擾加分（R-183）：ovr＝ovr_0213a＋λ·sd·P_MIX；P_MIX＝0.5·REBc 縮放＋0.5·CON 縮放再縮放，REBc＝clip(mean(z rebound, z orebPct, z drebPct), 0, 1.5)、CON＝clip(z con2_36, 0, 1.5)，z 尺／縮放／sd＝13.41／λ＝0.5 取自 ≥500 分鐘評估人群；E-292 上場 <500 分鐘按比例打折 × MIN/500（R-184）。能力值、係數、錨點與 0.2.13a 相同。',
    'ovr_changed': 'ovr = round(ovr_0213a + mixBonus, 1)；rank 依新 ovr 重排、同分依原名次；欄 mixBonus',
    'mix': {'config': mix['config'], 'frozen': 'reports/ovr-inseason-2026-27/live/mix-pool-card0214.json',
            'bonus_population': c2['bonus_population'], 'bonus_max': c2['bonus_max'], 'n_at_cap': c2['n_at_cap']},
    'source_cand2': {'summary': 'reports/card-0.2.14-cand2/summary.json', 'ranking_csv_sha256': c2['ranking_csv_sha256'],
                     'sources_sha256': c2['sources_sha256']},
    'card_0213a_ranking_csv_sha256': s['ranking_csv_sha256'],
    'ranking_csv_sha256': sha(HERE / 'ranking.csv'),
    'build_command': 'python -I -B -X utf8 reports/card-0.2.14-cand2/build_cand2.py → python -I -B -X utf8 reports/card-0.2.14/build_card_0214.py',
})
(HERE / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: s[k] for k in ('version', 'ranking_csv_sha256')}, ensure_ascii=False))
