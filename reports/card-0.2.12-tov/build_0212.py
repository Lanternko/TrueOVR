"""card 0.2.12（R-139，E-203）＝card 0.2.11（檔案在 card-0.2.10j/）＋tovSkill 改看持球時間（E-202 KT 臂），全部係數重擬合、不設下限。
直接採用 E-202 的建法與產物（reports/card-0.2.10j+E202-to-possession/：tov_raw.py → build_kg.py cards KT → run_i.py KT → finalize.py KT），
本檔只做 build_0210j.py 同款的 OVR 映射段（apply_to_card.py，E-188）並把正式版檔案放到本目錄。
（reports/card-0.2.12/ 是被放棄的舊 0.2.12 實驗夾，許多腳本還引用，不動；正式 0.2.12 放本夾。）
用法（repo root）：python -I -B -X utf8 reports/card-0.2.12-tov/build_0212.py
  TOV_POSS=0：改用 E-202 K0 臂 → work/C-c0/；ranking.csv 必須和 card-0.2.10j/ranking.csv（＝card 0.2.11）逐位元組相同（c0）。
  預設：→ 本目錄；ranking.csv 必須和 E-202 work/KT/final/out/ranking.csv 逐位元組相同。"""
import csv, hashlib, importlib.util, json, os, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E = ROOT / 'reports/card-0.2.10j+E202-to-possession'
J, D = ROOT / 'reports/card-0.2.10j', ROOT / 'reports/card-0.2.10d'
TOV_POSS = os.environ.get('TOV_POSS', '1') != '0'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main():
    arm = 'KT' if TOV_POSS else 'K0'
    pre = HERE / f'work/pre-{arm}'
    out = HERE if TOV_POSS else HERE / 'work/C-c0'
    if pre.exists():
        shutil.rmtree(pre)
    pre.mkdir(parents=True); out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(E / f'work/{arm}/B-KG/KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(out), 'card 0.2.12' if TOV_POSS else 'card 0.2.11')
    shutil.copyfile(J / 'three-value.csv', out / 'three-value.csv')
    a = [r['playerId'] for r in csv.DictReader((pre / 'three-value.csv').open(encoding='utf-8'))]
    b = [r['playerId'] for r in csv.DictReader((out / 'three-value.csv').open(encoding='utf-8'))]
    assert a == b, '3PT 欄的列集或順序與本池不同'
    summ = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    if not TOV_POSS:
        res = {n: (out / n).read_bytes() == (J / n).read_bytes() for n in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv')}
        gs = json.loads((J / 'summary.json').read_text(encoding='utf-8'))
        res['anchors'] = all(abs(gs['anchors'][k] - summ['anchors'][k]) < 1e-12 for k in gs['anchors'])
        res['ranking_sha256'] = sha(out / 'ranking.csv')
        (HERE / 'work/c0-card.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
        print('c0 vs card-0.2.10j(=0.2.11):', json.dumps(res))
        assert all(v for k, v in res.items() if k != 'ranking_sha256'), 'TOV_POSS=0 不能逐位元重現 card 0.2.11'
        return 0
    kt = E / 'work/KT/final/out/ranking.csv'
    same = (out / 'ranking.csv').read_bytes() == kt.read_bytes()
    assert same, 'ranking.csv 與 E-202 KT final 不同'
    A = E / 'work/KT/A/base-KG-2025-26/c0/cards/K0'
    for p in ('primary', 'fitA', 'fitB'):
        dst = HERE / 'cards/K6' / p
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(A / p, dst)
    shutil.copyfile(E / 'work/KT/B-KG/KAU-2025-26/out/usage-features.json', HERE / 'usage-features.json')
    for n in ('tov-raw.csv', 'tov-raw-info.json'):
        shutil.copyfile(E / n, HERE / n)
    for n in ('gravity-raw.csv', 'gravity-attr.csv'):
        shutil.copyfile(J / n, HERE / n)
    summ.update({
        'version': 'card 0.2.12', 'base': 'reports/card-0.2.10j（card 0.2.11）',
        'change': 'R-139：tovSkill 改看持球時間（NBA.com tracking Possessions TIME_OF_POSS）：raw＝0.5·z(−每持球分鐘失誤，E-069 方法 c 收縮)＋0.5·z(持球分鐘/36)，'
                  '0–99 映射照舊 tovSkill；其餘 16 項、gravity、用人層特徵、3PT 欄同 0.2.11；部件卡全部係數重擬合（不設下限，E-202 KT），用人層、r_repl、錨點、OVR 重算；E-188 OVR 映射照舊。',
        'tov': {'raw_csv': 'reports/card-0.2.12-tov/tov-raw.csv', 'raw_sha256': sha(HERE / 'tov-raw.csv')},
        'pre_ranking_sha256': sha(pre / 'ranking.csv'),
        'three_value_csv_sha256': sha(out / 'three-value.csv'), 'three_value_source': 'reports/card-0.2.10j/three-value.csv',
        'equals_E202_KT_final': same,
        'build_command': 'E-202：tov_raw.py → build_kg.py cards KT → run_i.py KT → finalize.py KT；本檔 build_0212.py',
        'c0': json.loads((HERE / 'work/c0-card.json').read_text(encoding='utf-8')),
    })
    (out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'ranking_csv_sha256': summ['ranking_csv_sha256'], 'anchors': summ['anchors'], 'equals_E202_KT_final': same}))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
