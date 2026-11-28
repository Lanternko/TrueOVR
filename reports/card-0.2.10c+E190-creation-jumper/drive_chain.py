"""E-190 errata-1 新 c0 與 drive_D：用 tail-U drive 欄的同一條管線（reports/card-0.2.10/make_tail_U.py → E-175 e175_card.card_chain，
U 臂＝四季滑動窗口；V 臂＝tail-e123a.csv（歷史三原點用的 tail）的單季算法）重算 drive，只換 pbp-drive 輸入檔：
  OLD＝本目錄 extract_classes.py 重抽的舊候選（應與 V61 history 檔逐位元相同）；D＝errata-1 的切入 D 候選。
c0：OLD 的 U 臂 drive 對 tail-U.csv、V 臂 drive 對 tail-e123a.csv，|差| < 1e-6。
past_pool（2022-23～2024-25 凍結池值 pool-P50/raw-<季>.json）不重算（只換候選篩選，揭露）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10c+E190-creation-jumper/drive_chain.py
輸出：work/drive-c0.json、work/drive-D.csv。"""
import csv, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/E175-sliding-window-card'))
import e175_lib as L  # noqa: E402
import e175_card as C  # noqa: E402

TAG = {'v': None}
_orig = L.read_gz


def read_gz(path):
    p = Path(path)
    if p.name.startswith('pbp-drive-') and TAG['v'] is not None:
        p = HERE / 'work/history' / p.name.replace('pbp-drive-', f'pbp-drive-{TAG["v"]}-')
    return _orig(p)


L.read_gz = read_gz
TAIL_U = ROOT / 'reports/card-0.2.10/tail-U.csv'
TAIL_A = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv'


def run(tag):
    TAG['v'] = tag
    D = L.Data()
    inp = C.load_inputs()
    return {arm: C.card_chain(D, inp, arm) for arm in ('U', 'V')}


def main():
    res = {t: run(t) for t in ('ORIG', 'OLD', 'D')} if '--orig' in sys.argv else {t: run(t) for t in ('OLD', 'D')}
    tails = {'U': {int(r['playerId']): float(r['drive']) for r in csv.DictReader(open(TAIL_U, encoding='utf-8'))},
             'V': {int(r['playerId']): float(r['drive']) for r in csv.DictReader(open(TAIL_A, encoding='utf-8'))}}
    out = {'inputs_sha256': {str(p.relative_to(ROOT)): L.sha256(p) for p in (TAIL_U, TAIL_A, Path(__file__))}}
    for arm in ('U', 'V'):
        R = res['OLD'][arm]
        d = np.array([R['mapped']['drive'][i] - tails[arm][p] for i, p in enumerate(R['pids']) if p in tails[arm]])
        out[f'c0_{arm}'] = {'n': len(d), 'max_abs': float(np.abs(d).max()), 'n_gt_1e-6': int((np.abs(d) > 1e-6).sum()),
                            'pass': bool(np.abs(d).max() < 1e-6)}
    out['c0_pass'] = out['c0_U']['pass'] and out['c0_V']['pass']
    pids = res['D']['U']['pids']
    with open(HERE / 'work/drive-D.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['playerId', 'name', 'drive_U_old', 'drive_D_U', 'drive_V_old', 'drive_D_V'])
        for i, p in enumerate(pids):
            w.writerow([p, res['D']['U']['names'][i], repr(float(res['OLD']['U']['mapped']['drive'][i])), repr(float(res['D']['U']['mapped']['drive'][i])),
                        repr(float(res['OLD']['V']['mapped']['drive'][i])), repr(float(res['D']['V']['mapped']['drive'][i]))])
    out['driveZ_D_U'] = res['D']['U']['info']['driveZ']
    out['driveZ_OLD_U'] = res['OLD']['U']['info']['driveZ']
    out['drive_D_sha256'] = L.sha256(HERE / 'work/drive-D.csv')
    (HERE / 'work/drive-c0.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
