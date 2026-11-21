"""E-101 複本（自 reports/card-0.2.5+E097-topscale/chain/compare.py，候選改成 E101_CAND：e101 主要／e101z、e101g、e101w 只報告）。E-097 原說明：E-097 複本（自 reports/card-0.2.5+E096-tail150/chain/compare.py，候選改成 E097_CAND：e097 主要／e097s、e097p、e097v 只報告）。E-096 原說明：E-096 複本（自 reports/card-0.2.5+E090-onball-tail/chain/compare.py）：候選改成 E096_CAND（e096 主要／e096v 只報告），輸出 c2-<cand>.json；(c0) 讀 E-090＠0.2.5。原說明：E-090＠0.2.5 (c2N)(c2Q)（照 E-090 預註冊 §6.2，基準換成 card 0.2.5）：候選（e090 變體＋飽和分鐘）對 card 0.2.5（cur 變體＋飽和分鐘，(c0) 已證明與 card 0.2.5 相同）的季量尺 ρ 差。
答案（季量尺 N／Q）與 E-090 相同，不改成 E-089 的 W 加權答案。
評估程式 = chain/e084.py 的 season_eval（照 E-084 §3：bootstrap 2000、seed 1、master 聯集、兩方向平均、候選與基準共用抽樣）。
兩個變體各自 import 一份 e084.py（環境變數 E090_VARIANT 不同，D 各自獨立），各跑 pipeline(BASE_OPTS, pools, 'season')。
season_eval 的人群檢查要求兩邊 p（fit 半季 pred）相同；E-090 改的就是屬性，p 本來就會變，所以基準的 p 換成候選的 p 才呼叫。
基準的 p 在 season_eval 裡只用於這個檢查（c4 用候選自己的 p／pn），ρ_N、ρ_Q 只用 cand（卡片 g）與答案，不受影響。
門檻：兩者都是 90% 下界 > −0.02（E-090 預註冊 §6.2；與 E-084 的 c2Q −0.05 不同）。
用法：python -I -B reports/card-0.2.5+E090-onball-tail/chain/compare.py → c2.json
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
assert json.loads((HERE.parent / 'card-0.2.5+E090-onball-tail/c0.json').read_text(encoding='utf-8'))['pass'] is True, '(c0) 未通過'
CAND = os.environ.get('E101_CAND', 'e101')
assert CAND in ('e101', 'e101z', 'e101g', 'e101w'), CAND


def load(var):
    os.environ['E090_VARIANT'] = var
    spec = importlib.util.spec_from_file_location('e084_' + var, HERE / 'chain/e084.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.load_data()
    pools = m.build_pools()
    res = m.pipeline(m.BASE_OPTS, pools, 'season')
    return m, pools, res['_aux']['dirs']


sys.stdout.reconfigure(encoding='utf-8', errors='replace')
mc, pc, dc = load('cur')
me, pe, de = load(CAND)
assert pc == pe, 'pools 不同'
bdirs = {dn: {**dc[dn], 'p': de[dn]['p']} for dn in me.DNS}
for dn in me.DNS:
    assert dc[dn]['names'] == de[dn]['names'] and dc[dn]['pid'] == de[dn]['pid']
ev = me.season_eval(de, bdirs)
out = {
    'baseline': 'card 0.2.5（cur 變體＋飽和分鐘）', 'candidate': f'E-101（{CAND} 變體＋飽和分鐘）',
    'c2N': {'point': ev['dRho_N']['point'], 'ci90': ev['dRho_N']['ci90'], 'threshold': '下界 > -0.02', 'pass': bool(ev['dRho_N']['ci90'][0] > -0.02)},
    'c2Q': {'point': ev['dRho_Q']['point'], 'ci90': ev['dRho_Q']['ci90'], 'threshold': '下界 > -0.02', 'pass': bool(ev['dRho_Q']['ci90'][0] > -0.02)},
    'rho_N': {'card025': ev['rho_N_card023'], CAND: ev['rho_N_cand']},
    'rho_Q': {'card025': ev['rho_Q_card023'], CAND: ev['rho_Q_cand']},
    'reportOnly': {'dS_N': ev['dS_N'], 'dS_Q': ev['dS_Q']},
    'n': ev['n'], 'master_size': ev['master_size'], 'n_boot': ev['n_boot'], 'seed': ev['seed'],
    'note': "season_eval 回傳鍵名沿用 E-084（*_card023 = 這裡的基準 card 0.2.5，*_cand = E-101）",
}
(HERE / f'c2-{CAND}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
print(json.dumps({k: out[k] for k in ('c2N', 'c2Q')}, ensure_ascii=False, default=float))
