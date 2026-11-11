"""card 0.2.14a 正式卡：從 card-0.2.15-cand（E-294 臂 H-same）產出；使用者裁定採用 H、版號用字母版 0.2.14a（修同版本的錯估）。
ranking.csv＝候選卡原樣（核對 sha；名次與 mixBonus 與 card-0.2.15-cand 相同）；g5.md 同候選卡；其他附檔（three-value、gravity、pnr、def-L、rapm-T6）
與 0.2.13a／0.2.14 相同，複製過來讓本卡自足。summary.json 格式照 card-0.2.14（錨點／映射沿用 0.2.13a，MIX 是疊在 OVR 上的加分）。
位置來源：card 0.2.13a 的 pos 欄（F-033：2025-26 先發最多的位置）。
用法（repo root）：python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_h → python -I -B -X utf8 reports/card-0.2.14a/build_card_0214a.py"""
import hashlib, json, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE, CAND, C14 = ROOT / 'reports/card-0.2.13a', ROOT / 'reports/card-0.2.15-cand', ROOT / 'reports/card-0.2.14'
FROZEN_H = ROOT / 'reports/ovr-inseason-2026-27/live/mix-pool-card0214a.json'
cs = json.loads((CAND / 'summary.json').read_text(encoding='utf-8'))
assert sha(CAND / 'ranking.csv') == cs['ranking_csv_sha256'], 'card-0.2.15-cand ranking.csv 與 summary 不符'
shutil.copyfile(CAND / 'ranking.csv', HERE / 'ranking.csv')
shutil.copyfile(CAND / 'g5.md', HERE / 'g5.md')
for f in ('def-L-primary.csv', 'gravity-attr.csv', 'gravity-raw.csv', 'pnr-attr.csv', 'rapm-T6.csv', 'three-value.csv'):
    assert sha(BASE / f) == sha(C14 / f), f
    shutil.copyfile(BASE / f, HERE / f)
s = json.loads((BASE / 'summary.json').read_text(encoding='utf-8'))
s14 = json.loads((C14 / 'summary.json').read_text(encoding='utf-8'))
mix = json.loads(FROZEN_H.read_text(encoding='utf-8'))
s.update({
    'version': 'card 0.2.14a',
    'base': 'card 0.2.13a（reports/card-0.2.13a/）＋MIX 加分 H-same（reports/card-0.2.15-cand/，E-294）；取代 card 0.2.14',
    'change': 'E-294 臂 H-same（使用者裁定採用，字母版 0.2.14a＝修 0.2.14 的錯估；role-audit 4/5 reports/audit-0.2.14a/）：MIX 加分的 z 改「全聯盟尺、位置平均只留一半」'
              'z_H＝z_L−0.5·m_pos（m_pos＝該位置在算尺人群的全聯盟 z 平均，缺值記 0.5·m_pos），飽和改 1.5·tanh(z⁺/1.5)，再乘位置權重 C=1、PF=0.243（0.68/2.80）、其他 0；'
              'λ＝0.5、sd＝13.41 同 0.2.14，三個均方根縮放在同一算尺人群重算（s_reb 1.05237、s_con 1.02558、s_mix 1.12377）；500 分鐘以下 × MIN/500（R-184）。'
              '位置＝card 0.2.13a pos（F-033，2025-26 先發最多的位置）。能力值、係數、錨點與 0.2.13a 相同。',
    'ovr_changed': 'ovr = round(ovr_0213a + mixBonus, 1)；rank 依新 ovr 重排、同分依原名次；欄 mixBonus',
    'mix': {'config': mix['config'], 'frozen': 'reports/ovr-inseason-2026-27/live/mix-pool-card0214a.json',
            'bonus_population': cs['bonus_population'], 'bonus_max': cs['bonus_max'], 'n_near_cap_0.2': cs['n_near_cap_0.2'],
            'theoretical_cap_C': cs['theoretical_cap_C'], 'reproduceCandMaxAbs': mix['reproduceCandMaxAbs']},
    'source_cand': {'summary': 'reports/card-0.2.15-cand/summary.json', 'ranking_csv_sha256': cs['ranking_csv_sha256'],
                    'sources_sha256': cs['sources_sha256']},
    'audit': 'reports/audit-0.2.14a/report.md（4/5 建議採用）',
    'card_0213a_ranking_csv_sha256': s['ranking_csv_sha256'],
    'card_0214_ranking_csv_sha256': s14['ranking_csv_sha256'],
    'ranking_csv_sha256': sha(HERE / 'ranking.csv'),
    'build_command': 'python -I -B -X utf8 reports/card-0.2.15-cand/build_cand.py → python -I -X utf8 reports/ovr-inseason-2026-27/live/mix_live.py freeze_h → python -I -B -X utf8 reports/card-0.2.14a/build_card_0214a.py',
})
for k in ('source_cand2',):
    s.pop(k, None)
(HERE / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: s[k] for k in ('version', 'ranking_csv_sha256')}, ensure_ascii=False))
