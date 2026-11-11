"""card 0.2.10j（R-134／R-135，E-200）＝card 0.2.10i＋能力值 gravity（NBA.com 無球外線引力 AVGOFFBALLPERIMETERGRAVITYSCORE，E-198 KG 臂），全部係數重擬合、不設下限。
直接採用 E-198 的建法與產物（reports/card-0.2.10j+E198-gravity/：gravity_raw.py → build_kg.py cards KG → run_i.py KG → finalize.py KG），
本檔只做 build_0210i.py 的步驟 4c（E-188 OVR 映射，apply_to_card.py）並把正式版檔案放到本目錄：
  ranking.csv、summary.json（apply_to_card 產）、rapm-T6.csv（card-0.2.10d，RAPM 目標沒動）、three-value.csv（沿用 card-0.2.10i；列集與順序須同）、
  usage-features.json（E-198 work/B-KG）、cards/K6/{primary,fitA,fitB}（E-198 work/A/base-KG-2025-26/c0/cards/K0，賽中端 CARD_DIR）、
  gravity-raw.csv／gravity-attr.csv（E-198 gravity_raw.py 產物；網站引力欄與賽中端凍結池用）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j/build_0210j.py
  GRAVITY=0：改用 E-198 KAU 臂（＝0.2.10i 部件卡）→ work/C-c0/；ranking.csv 必須和 card-0.2.10i/ranking.csv 逐位元組相同（c0）。
  預設：→ 本目錄；ranking.csv 必須和 E-198 work/KG-final/out/ranking.csv 逐位元組相同。"""
import csv, hashlib, importlib.util, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E = ROOT / 'reports/card-0.2.10j+E198-gravity'
I, D = ROOT / 'reports/card-0.2.10i', ROOT / 'reports/card-0.2.10d'
GRAVITY = os.environ.get('GRAVITY', '1') != '0'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main():
    arm = 'KG' if GRAVITY else 'KAU'
    pre = HERE / f'work/pre-{arm}'
    out = HERE if GRAVITY else HERE / 'work/C-c0'
    if pre.exists():
        shutil.rmtree(pre)
    pre.mkdir(parents=True); out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(E / f'work/B-{arm}/KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(out), 'card 0.2.10j' if GRAVITY else 'card 0.2.10i')
    shutil.copyfile(I / 'three-value.csv', out / 'three-value.csv')
    a = [r['playerId'] for r in csv.DictReader((pre / 'three-value.csv').open(encoding='utf-8'))]
    b = [r['playerId'] for r in csv.DictReader((out / 'three-value.csv').open(encoding='utf-8'))]
    assert a == b, '3PT 欄（0.2.10i）的列集或順序與本池不同'
    summ = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    if not GRAVITY:
        res = {n: (out / n).read_bytes() == (I / n).read_bytes() for n in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv')}
        gs = json.loads((I / 'summary.json').read_text(encoding='utf-8'))
        res['anchors'] = all(abs(gs['anchors'][k] - summ['anchors'][k]) < 1e-12 for k in gs['anchors'])
        res['ranking_sha256'] = sha(out / 'ranking.csv')
        (HERE / 'work/c0-card.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
        print('c0 vs card-0.2.10i:', json.dumps(res))
        assert all(v for k, v in res.items() if k != 'ranking_sha256'), 'GRAVITY=0 不能逐位元重現 card 0.2.10i'
        return 0
    kg = E / 'work/KG-final/out/ranking.csv'
    same = (out / 'ranking.csv').read_bytes() == kg.read_bytes()
    assert same, 'ranking.csv 與 E-198 KG-final 不同'
    A = E / 'work/A/base-KG-2025-26/c0/cards/K0'
    for p in ('primary', 'fitA', 'fitB'):
        dst = HERE / 'cards/K6' / p
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(A / p, dst)
    shutil.copyfile(E / 'work/B-KG/KAU-2025-26/out/usage-features.json', HERE / 'usage-features.json')
    for n in ('gravity-raw.csv', 'gravity-attr.csv'):
        shutil.copyfile(E / n, HERE / n)
    gi = json.loads((E / 'work/gravity-impute.json').read_text(encoding='utf-8'))
    summ.update({
        'version': 'card 0.2.10j', 'base': 'reports/card-0.2.10i',
        'change': 'R-134／R-135：加能力值 gravity（NBA.com 無球外線引力 AVGOFFBALLPERIMETERGRAVITYSCORE；2025-26 沒有值的人用 OLS 補：3PA/36、3P%、USG%、位置），'
                  '0–99 映射照 creation（池 GP≥30 且 MPG≥20，兩端尾巴開）；其餘 15 項、用人層特徵、3PT 欄同 0.2.10i；部件卡全部係數重擬合（不設下限，E-198 KG），用人層、r_repl、錨點、OVR 重算；E-188 OVR 映射照舊。',
        'gravity': {'raw_csv': 'reports/card-0.2.10j/gravity-raw.csv', 'raw_sha256': sha(HERE / 'gravity-raw.csv'),
                    'attr_csv': 'reports/card-0.2.10j/gravity-attr.csv', 'attr_sha256': sha(HERE / 'gravity-attr.csv'),
                    'n_has': gi['n_has'], 'n_imputed': gi['n_imputed'], 'ols_r2': gi['ols']['r2'], 'pool_n': gi['pool_n']},
        'pre_ranking_sha256': sha(pre / 'ranking.csv'),
        'three_value_csv_sha256': sha(out / 'three-value.csv'), 'three_value_source': 'reports/card-0.2.10i/three-value.csv',
        'equals_E198_KG_final': same,
        'build_command': 'E-198：gravity_raw.py → build_kg.py cards KG 2025-26（E185_TAIL_U=card-0.2.10i/tail-U.csv, E185_WORK=work/A）→ run_i.py KG → build_0210j.py',
        'c0': json.loads((HERE / 'work/c0-card.json').read_text(encoding='utf-8')),
    })
    summ['sources_sha256']['reports/card-0.2.10i/three-value.csv'] = sha(I / 'three-value.csv')
    (out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'ranking_csv_sha256': summ['ranking_csv_sha256'], 'anchors': summ['anchors'], 'equals_E198_KG_final': same}))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
