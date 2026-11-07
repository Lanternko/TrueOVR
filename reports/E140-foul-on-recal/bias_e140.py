"""E-140 偏袒量測與對答案 ρ：重用 E-067 bias_check（數學不動），在 baseline 三模型後接 E-140「關閉版（現行引擎重跑）」與「開啟版（犯規開＋重校）」主版／位置版。
用法：python -I reports/E140-foul-on-recal/bias_e140.py
"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]; HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('bias_check', ROOT / 'reports/bias-check-E067/bias_check.py')
BC = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(BC)
BASE = json.loads((ROOT / 'reports/bias-check-E067/baseline.json').read_text(encoding='utf-8'))
def csvmodel(fn, col):
    rows = list(csv.DictReader((HERE / fn).open(encoding='utf-8-sig')))
    return lambda ev: {r['name']: (float(r[col]), r['pos'], None) for r in rows}
NEW = [('off 主版', csvmodel('winimp-off.csv', 'winsPer82')), ('off 位置版', csvmodel('winimp-off.csv', 'winsPer82_pos')),
       ('on 主版', csvmodel('winimp-on.csv', 'winsPer82')), ('on 位置版', csvmodel('winimp-on.csv', 'winsPer82_pos'))]
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rng = np.random.default_rng(BC.SEED)
    res = {'preregSha256': BASE.get('preregSha256'), 'models': {}}
    for name, model in BC.MODELS + NEW:
        d = {dr: BC.measure(model, ev, rng) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        k2 = {dr: BC.measure(model, ev, rng, answer={n: BC.K2[n] for n in BC.answers(ev) if n in BC.K2}) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        res['models'][name] = {'verdict': BC.verdict(d), 'directions': d, 'vs2K27': {k: {'S': v['S'], 'CI90': v['CI90'], 'n': v['n']} for k, v in k2.items()}}
        print(f'## {name}：{BC.verdict(d)}')
        for dr, x in d.items(): print(f"  {dr} n={x['n']} S={x['S']:+.1f} CI {[round(t, 1) for t in x['CI90']]} rho={x['rho']:.3f}")
    for name in list(BASE['models']):
        assert json.dumps(res['models'][name]['directions'], sort_keys=True) == json.dumps(BASE['models'][name]['directions'], sort_keys=True), 'baseline drift ' + name
    print('baseline 重現：OK')
    (HERE / 'bias.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
if __name__ == '__main__': main()
