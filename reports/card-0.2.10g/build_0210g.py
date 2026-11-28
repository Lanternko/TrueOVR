"""card 0.2.10g（E-192）= card 0.2.10f ＋ 用人層（L、a）四季窗口。把 run_g.py 的 KAU 輸出（work/…/out/ranking.csv）套 E-188 OVR 映射（apply_to_card.py，錨取本池 gRepl、MIN>=500），
three-value.csv 沿用 card-0.2.10f 的（3PT 欄 E-191b P1m；列集與順序須同），rapm-T6.csv 沿用 card-0.2.10d 的（屬性管線沒動）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10g/build_0210g.py selfcheck|real
  selfcheck：窗口關的 work-selfcheck 輸出 -> selfcheck-out/；ranking.csv／three-value.csv／rapm-T6.csv 必須和 card-0.2.10f 逐位元組相同，錨點相同
  real     ：work 輸出 -> card-0.2.10g/（ranking.csv、three-value.csv、rapm-T6.csv、summary.json）"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
F, D = ROOT / 'reports/card-0.2.10f', ROOT / 'reports/card-0.2.10d'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main(mode):
    work = HERE / ('work' if mode == 'real' else 'work-selfcheck')
    pre = HERE / ('pre' if mode == 'real' else 'pre-selfcheck')
    out = HERE if mode == 'real' else HERE / 'selfcheck-out'
    pre.mkdir(exist_ok=True)
    shutil.copyfile(work / 'KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(out), 'card 0.2.10g')
    shutil.copyfile(F / 'three-value.csv', out / 'three-value.csv')
    a = [r['playerId'] for r in csv.DictReader((pre / 'three-value.csv').open(encoding='utf-8'))]
    b = [r['playerId'] for r in csv.DictReader((out / 'three-value.csv').open(encoding='utf-8'))]
    assert a == b, '3PT 欄（0.2.10f）的列集或順序與本池不同'
    summ = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    summ.update({
        'version': 'card 0.2.10g', 'base': 'reports/card-0.2.10f',
        'change': 'E-192：用人層（L、a）改四季滑動窗口（2025-26 季末 c=82，window11.py）；係數（半季特徵訓練，沒動）、部件卡、3PT 欄同 0.2.10f，r_repl、錨點與 OVR 重算；E-188 OVR 映射照舊。',
        'usage_window': {'features': 'reports/card-0.2.10g/usage-window-c82.csv', 'sha256': sha(HERE / 'usage-window-c82.csv') if (HERE / 'usage-window-c82.csv').exists() else None,
                         'window': '四季線性遞減（E-175 U 臂權重，328 格）', 'unchanged': ['y', 'v（2025-26 季末年齡）', 'd（不在 Y0 設計矩陣）', 'p', 'mpg（E-185 窗口 MPG）']},
        'pre_ranking_sha256': sha(pre / 'ranking.csv'),
        'three_value_csv_sha256': sha(out / 'three-value.csv'), 'three_value_source': 'reports/card-0.2.10f/three-value.csv',
        'build_command': f'python -I -B -X utf8 reports/card-0.2.10g/build_0210g.py {mode}',
    })
    summ['sources_sha256']['reports/card-0.2.10f/three-value.csv'] = sha(F / 'three-value.csv')
    (out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if mode == 'selfcheck':
        res = {n: (out / n).read_bytes() == (F / n).read_bytes() for n in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv')}
        fs = json.loads((F / 'summary.json').read_text(encoding='utf-8'))
        res['anchors'] = all(abs(fs['anchors'][k] - summ['anchors'][k]) < 1e-12 for k in fs['anchors'])
        print('selfcheck vs card-0.2.10f:', json.dumps(res))
        assert all(res.values()), '窗口關時不能逐位元重現 0.2.10f'
    print(json.dumps({'ranking_csv_sha256': summ['ranking_csv_sha256'], 'anchors': summ['anchors']}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1])
