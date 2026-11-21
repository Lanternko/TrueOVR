"""card 0.2.10i 步驟 3：tail-U.csv ＝ card-0.2.12/tail-U.csv，只把 drive、creation 兩欄換成 0.2.10i 定義（R-130）的 2025-26 季末四季窗口值：
  drive    ＝ window8.Win8().U（e175_card.card_chain U 臂；SPLIT_DC=1：D 類候選、過去季池值 D 類）
  creation ＝ window10.Win10().end['creation']（SPLIT_DC=1：creationJ 窗口，池＝本季窗口值＋過去季單季 creationJ）
其他欄、mpg-c82.csv、three-value.csv 不動（兩項定義與 long／threeValue／MPG 無關）。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10i/make_tail_0210i.py c0|real
  c0  ：須在 SPLIT_DC=0 下執行；creation 逐字（repr）等於 card-0.2.12 tail-U、drive 與 tail-U |差|<1e-6（card_chain 重算，同 E-190 drive_chain c0）
  real：SPLIT_DC=1；寫 tail-U.csv、work/make_tail.json（含對 E-190 KJ／drive_D_U 的差）"""
import csv, hashlib, json, os, sys
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
sys.path.insert(0, str(ROOT / 'reports/ovr-inseason-2026-27/live'))
import window10 as W10  # noqa: E402
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SRC = ROOT / 'reports/card-0.2.12/tail-U.csv'
E190W = ROOT / 'reports/card-0.2.10c+E190-creation-jumper/work'


def main(mode):
    assert W10.SD.ON == (mode == 'real'), 'c0 要 SPLIT_DC=0、real 要 SPLIT_DC=1'
    W = W10.Win10()
    pid_i = {int(p): i for i, p in enumerate(W.pids)}
    rows = list(csv.DictReader(open(SRC, encoding='utf-8')))
    assert len(rows) == 582 and all(int(r['playerId']) in pid_i for r in rows)
    drv, cre = W.U['mapped']['drive'], W.end['creation']
    if mode == 'c0':
        dd = max(abs(float(drv[pid_i[int(r['playerId'])]]) - float(r['drive'])) for r in rows)
        ce = all(repr(float(cre[pid_i[int(r['playerId'])]])) == r['creation'] for r in rows)
        res = {'drive_max_abs_vs_0212': dd, 'creation_repr_equal': ce, 'pass': dd < 1e-6 and ce}
        (H / 'work/make_tail_c0.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
        print(json.dumps(res))
        assert res['pass']
        return
    keys = list(rows[0].keys())
    with open(H / 'tail-U.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(keys)
        for r in rows:
            i = pid_i[int(r['playerId'])]
            o = dict(r, drive=repr(float(drv[i])), creation=repr(float(cre[i])))
            w.writerow([o[k] for k in keys])
    kj = {int(r['playerId']): float(r['creationJ']) for r in csv.DictReader(open(E190W / 'creation-KP-KJ.csv', encoding='utf-8'))}
    dU = {int(r['playerId']): float(r['drive_D_U']) for r in csv.DictReader(open(E190W / 'drive-D.csv', encoding='utf-8'))}
    old = {int(r['playerId']): r for r in rows}
    cmp = lambda new, ref: (lambda d: {'n': len(d), 'mean_abs': float(np.mean(np.abs(d))), 'max_abs': float(np.max(np.abs(d))),
                                        'corr': float(np.corrcoef([x for x, _ in new], [y for _, y in new])[0, 1])})(np.array([x - y for x, y in new]))
    cpairs = [(float(cre[pid_i[p]]), kj[p]) for p in old if p in kj]
    dpairs = [(float(drv[pid_i[p]]), dU[p]) for p in old if p in dU]
    info = {'tail-U': sha(H / 'tail-U.csv'), 'src': str(SRC.relative_to(ROOT)), 'src_sha256': sha(SRC),
            'creation_vs_E190_KJ': cmp(cpairs, None), 'drive_vs_E190_drive_D_U': cmp(dpairs, None),
            'creation_vs_old': cmp([(float(cre[pid_i[p]]), float(old[p]['creation'])) for p in old], None),
            'drive_vs_old': cmp([(float(drv[pid_i[p]]), float(old[p]['drive'])) for p in old], None),
            'driveZ': W.U['info']['driveZ'], 'pool_drive_D_sha256': sha(W10.SD.POOL_D)}
    (H / 'work/make_tail.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1])
