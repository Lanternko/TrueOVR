"""E-122 偏袒量測（W4）與對答案 ρ（W5）：重用 E-067 bias_check 的 measure/answers/MODELS（數學不動），把「關體力」主版／位置版兩欄接在 baseline 三個模型後面（rng 消耗順序同 E-067/E-076）。
「開體力」沿用 baseline.json 的 WinImp 主版／位置版（即 E-065 winimp.csv）。前三個模型必須和 baseline.json 逐位相同。
用法：python -I reports/E120-foul-defense/bias_e122.py
"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('bias_check', ROOT / 'reports/bias-check-E067/bias_check.py')
BC = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(BC)
BASE = json.loads((ROOT / 'reports/bias-check-E067/baseline.json').read_text(encoding='utf-8'))

def offcsv(col):
    rows = list(csv.DictReader((HERE / 'winimp-on.csv').open(encoding='utf-8-sig')))
    return lambda ev: {r['name']: (float(r[col]), r['pos'], None) for r in rows}

NEW = [('clock-d1 主版', offcsv('winsPer82')), ('clock-d1 位置版', offcsv('winsPer82_pos'))]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rng = np.random.default_rng(BC.SEED)
    res = {'preregSha256': BASE.get('preregSha256'), 'models': {}}
    for name, model in BC.MODELS + NEW:
        d = {dr: BC.measure(model, ev, rng) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        k2 = {dr: BC.measure(model, ev, rng, answer={n: BC.K2[n] for n in BC.answers(ev) if n in BC.K2}) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
        res['models'][name] = {'verdict': BC.verdict(d), 'directions': d, 'vs2K27': {k: {'S': v['S'], 'CI90': v['CI90'], 'n': v['n']} for k, v in k2.items()}}
        print(f'## {name}：{BC.verdict(d)}')
        for dr, x in d.items():
            print(f"  {dr} n={x['n']} S={x['S']:+.1f} CI {[round(t, 1) for t in x['CI90']]} rho={x['rho']:.3f}")
    for name in list(BASE['models']):
        assert json.dumps(res['models'][name]['directions'], sort_keys=True) == json.dumps(BASE['models'][name]['directions'], sort_keys=True), 'baseline drift ' + name
    print('baseline 重現：OK')
    v = {}
    for lab, bn, dn in (('main', 'WinImp 主版', 'clock-d1 主版'), ('pos', 'WinImp 位置版', 'clock-d1 位置版')):
        b, d = BASE['models'][bn]['directions'], res['models'][dn]['directions']
        v[lab] = {'S_current': {k: b[k]['S'] for k in b}, 'S_d1': {k: d[k]['S'] for k in d}, 'S_CI90_current': {k: b[k]['CI90'] for k in b}, 'S_CI90_d1': {k: d[k]['CI90'] for k in d},
                  'rho_current': {k: b[k]['rho'] for k in b}, 'rho_d1': {k: d[k]['rho'] for k in d},
                  'rho_current_mean': float(np.mean([b[k]['rho'] for k in b])), 'rho_d1_mean': float(np.mean([d[k]['rho'] for k in d])),
                  'verdict_current': BASE['models'][bn]['verdict'], 'verdict_d1': res['models'][dn]['verdict']}
        v[lab]['rho_diff_d1_minus_current'] = v[lab]['rho_d1_mean'] - v[lab]['rho_current_mean']
    res['e120'] = v
    print(json.dumps(v, ensure_ascii=False, indent=1))
    (HERE / 'bias.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')

if __name__ == '__main__':
    main()
