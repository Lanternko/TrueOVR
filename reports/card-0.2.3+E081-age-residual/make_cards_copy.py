"""一次性：把 e075.py 複製成 e081_cards.py，只做預註冊允許的改動（只加輸出，演算法一字不改）。"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE.parents[0] / 'card-0.2.2+E073-usage-evidence/e075.py').read_text(encoding='utf-8')

def rep(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)

# 1) 檔頭說明
src = rep(src, '"""E-075：', '"""E-081 用：複製自 reports/card-0.2.2+E073-usage-evidence/e075.py。演算法不改，只在主規格「半季評估」之後輸出 names／cand／ans／pid，然後停止（不跑敏感度、不寫卡片）。\n原 docstring：E-075：')
# 2) pipeline 加 half_only 參數與提前輸出
src = rep(src, 'def pipeline(o, pools, full_report=False):', 'def pipeline(o, pools, full_report=False, half_only=False):')
src = rep(src, "    out['population'] = {'AB': len(pools['AB']), 'BA': len(pools['BA']), 'union': NN}\n",
          "    out['population'] = {'AB': len(pools['AB']), 'BA': len(pools['BA']), 'union': NN}\n"
          "    if half_only:   # E-081：只加輸出\n"
          "        out['_dirs'] = {dn: {'names': d['names'], 'pid': [int(nm2pid[n]) for n in d['names']], 'cand': [float(x) for x in d['cand']],\n"
          "                             'ans': [float(x) for x in d['ans']], 'mpg_ev': [float(D['mpgh'][dn[1]][nm2pid[n]][1]) for n in d['names']],\n"
          "                             'age': [D['age'].get(nm2pid[n]) for n in d['names']]} for dn, d in dirs.items()}\n"
          "        out['_master'] = master\n"
          "        return out\n")
# 3) main 換成只跑主規格
i = src.index('def main():')
j = src.index("if __name__ == '__main__':")
new_main = '''def main():
    load_data()
    pools = build_pools()
    r = pipeline(BASE_OPTS, pools, half_only=True)
    ref = jload(ROOT / 'reports/card-0.2.2+E073-usage-evidence/results.json')['checks']['c2']['value']
    k0 = {'delta': [r['c2']['value']['delta'], ref['delta']], 'ci90': [r['c2']['value']['ci90'], ref['ci90']],
          'rho_cand': [r['c2']['value']['rho_cand'], ref['rho_cand']], 'rho_base': [r['c2']['value']['rho_base'], ref['rho_base']]}
    diffs = [abs(r['c2']['value']['delta'] - ref['delta']), abs(r['c2']['value']['ci90'][0] - ref['ci90'][0]), abs(r['c2']['value']['ci90'][1] - ref['ci90'][1])]
    for dn in ('AB', 'BA'):
        diffs += [abs(r['c2']['value']['rho_cand'][dn] - ref['rho_cand'][dn]), abs(r['c2']['value']['rho_base'][dn] - ref['rho_base'][dn])]
    k0_out = {'maxAbsDiff': max(diffs), 'pass': bool(max(diffs) < 1e-9), 'values_this_run_vs_E075': k0, 'threshold': '< 1e-9'}
    out = {'k0': k0_out, 'population': r['population'], 'dirs': r['_dirs'], 'master': r['_master'],
           'sha256': {'e075.py': sha(ROOT / 'reports/card-0.2.2+E073-usage-evidence/e075.py'),
                      'results.json(E-075)': sha(ROOT / 'reports/card-0.2.2+E073-usage-evidence/results.json')}}
    (HERE / 'cards.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\\n', encoding='utf-8')
    print(json.dumps({'k0': k0_out, 'population': r['population']}, ensure_ascii=False, indent=1))
    assert k0_out['pass'], '(k0) 自檢失敗，停下回報'


'''
src = src[:i] + new_main + src[j:]
(HERE / 'e081_cards.py').write_text(src, encoding='utf-8')
print('ok')
