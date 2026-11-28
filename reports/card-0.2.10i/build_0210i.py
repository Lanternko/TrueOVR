"""card 0.2.10i（R-130／R-132）= card 0.2.10g，drive → drive_D、creation → creationJ（四季窗口），全部係數重擬合。
步驟 4c：把 run_i.py 的 KAU 輸出（work/B-<mode>/…/out/ranking.csv）套 E-188 OVR 映射（apply_to_card.py，同 build_0210g.py），
three-value.csv 沿用 card-0.2.10g（3PT 欄與兩項定義無關；列集與順序須同），rapm-T6.csv 沿用 card-0.2.10d（RAPM 目標沒動）。
real 另把部件卡（work/A-real/base-KAU-2025-26/c0/cards/K0/*）複製成 cards/K6/*（賽中端 CARD_DIR）、usage-features.json 複製到本目錄。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/build_0210i.py c0|real
  c0  ：舊 tail（card-0.2.12）重建 -> work/C-c0/；ranking.csv／three-value.csv／rapm-T6.csv 必須和 card-0.2.10g 逐位元組相同、錨點相同
  real：-> card-0.2.10i/（ranking.csv、three-value.csv、rapm-T6.csv、summary.json、usage-features.json、cards/K6）"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
G, D = ROOT / 'reports/card-0.2.10g', ROOT / 'reports/card-0.2.10d'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main(mode):
    work = HERE / f'work/B-{mode}'
    pre = HERE / f'work/pre-{mode}'
    out = HERE if mode == 'real' else HERE / 'work/C-c0'
    pre.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(work / 'KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(out), 'card 0.2.10i' if mode == 'real' else 'card 0.2.10g')
    shutil.copyfile(G / 'three-value.csv', out / 'three-value.csv')
    a = [r['playerId'] for r in csv.DictReader((pre / 'three-value.csv').open(encoding='utf-8'))]
    b = [r['playerId'] for r in csv.DictReader((out / 'three-value.csv').open(encoding='utf-8'))]
    assert a == b, '3PT 欄（0.2.10g）的列集或順序與本池不同'
    summ = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    if mode == 'c0':
        res = {n: (out / n).read_bytes() == (G / n).read_bytes() for n in ('ranking.csv', 'three-value.csv', 'rapm-T6.csv')}
        gs = json.loads((G / 'summary.json').read_text(encoding='utf-8'))
        res['anchors'] = all(abs(gs['anchors'][k] - summ['anchors'][k]) < 1e-12 for k in gs['anchors'])
        res['ranking_sha256'] = sha(out / 'ranking.csv')
        (HERE / 'work/c0-card.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
        print('c0 vs card-0.2.10g:', json.dumps(res))
        assert all(v for k, v in res.items() if k != 'ranking_sha256'), '舊 tail 不能逐位元重現 0.2.10g'
        return
    A = HERE / 'work/A-real/base-KAU-2025-26/c0/cards/K0'
    for p in ('primary', 'fitA', 'fitB'):
        dst = HERE / 'cards/K6' / p
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(A / p, dst)
    shutil.copyfile(work / 'KAU-2025-26/out/usage-features.json', HERE / 'usage-features.json')
    summ.update({
        'version': 'card 0.2.10i', 'base': 'reports/card-0.2.10g',
        'change': 'R-130／R-132：drive 改 drive_D（只算帶球切入的自主兩分，E-190 errata-1 D 類；量與效率各半）、creation 改 creationJ（自己創造的跳投與低位出手，不含切入上籃、補籃、空切；per36），'
                  '都是四季滑動窗口（E-175 U 臂權重）；其餘 13 項、用人層特徵、3PT 欄同 0.2.10g；部件卡全部係數重擬合（card-0.2.10d/build.py KAU 同旗標），用人層、r_repl、錨點、OVR 重算；E-188 OVR 映射照舊。',
        'tail_U': {'path': 'reports/card-0.2.10i/tail-U.csv', 'sha256': sha(HERE / 'tail-U.csv'), 'builder': 'reports/card-0.2.10i/make_tail_0210i.py real'},
        'pool_drive_D_sha256': sha(HERE / 'work/pool-drive-D.json'),
        'pre_ranking_sha256': sha(pre / 'ranking.csv'),
        'three_value_csv_sha256': sha(out / 'three-value.csv'), 'three_value_source': 'reports/card-0.2.10g/three-value.csv',
        'build_command': 'make_tail_0210i.py real → card-0.2.10d/build.py cards|run KAU 2025-26（E185_TAIL_U, E185_WORK=work/A-real）→ run_i.py real → build_0210i.py real',
        'c0': json.loads((HERE / 'work/c0-card.json').read_text(encoding='utf-8')),
    })
    summ['sources_sha256']['reports/card-0.2.10g/three-value.csv'] = sha(G / 'three-value.csv')
    (out / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'ranking_csv_sha256': summ['ranking_csv_sha256'], 'anchors': summ['anchors']}))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1])
