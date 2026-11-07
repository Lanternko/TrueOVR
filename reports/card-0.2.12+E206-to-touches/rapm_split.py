"""E-198：2025-26 本季 RAPM 單雙場分半（repo 沒有現成的單雙場分半）。
求解器、LAMBDAS、CV 折、觀測定義全部匯入 reports/card-0.2.7+E126-tank-next-season/rapm_season.py（不改原檔）；
單場＝int(gameId) 奇數、雙場＝偶數；兩半各自 fit_rapm（λ 各自 CV 選）。輸出 work/rapm-2025-26-{odd,even}.json（格式同 rapm-2025-26.json）。
另跑一次全季重算，核對與 rapm-2025-26.json 逐人 net 相同（c0）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j+E198-gravity/rapm_split.py"""
import hashlib, importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E126 = ROOT / 'reports/card-0.2.7+E126-tank-next-season'
s = importlib.util.spec_from_file_location('rapm_season', E126 / 'rapm_season.py')
R = importlib.util.module_from_spec(s); s.loader.exec_module(R)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fit(obs):
    players = sorted({p for o in obs for p in o[2] + o[3]})
    out, f = R.fit_rapm(obs, players)
    return {'season': '2025-26', 'fit': f, 'players': {str(p): v for p, v in out.items()}}


def main():
    obs = list(R.observations(['2025-26']))
    full = fit(obs)
    ref = json.load(open(E126 / 'rapm-2025-26.json', encoding='utf-8'))
    c0 = max(abs(full['players'][k]['net'] - v['net']) for k, v in ref['players'].items())
    info = {'c0_full_max_abs_net': c0, 'c0_pass': c0 < 1e-9, 'stints_sha256': sha(R.stint_path('2025-26')), 'n_obs': len(obs)}
    print('c0', info, flush=True)
    for nm, par in (('odd', 1), ('even', 0)):
        sub = [o for o in obs if int(o[1]) % 2 == par]
        d = fit(sub)
        d['split'] = nm
        (HERE / f'work/rapm-2025-26-{nm}.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        info[nm] = {'n_obs': len(sub), 'n_games': len({o[1] for o in sub}), 'lambda': d['fit']['lambda'], 'sha256': sha(HERE / f'work/rapm-2025-26-{nm}.json')}
        print(nm, info[nm], flush=True)
    (HERE / 'work/rapm-split.json').write_text(json.dumps(info, indent=1), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
