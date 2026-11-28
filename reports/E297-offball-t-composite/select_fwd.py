"""E-297 前向選擇（只看 fold 0）：每步剩餘候選各訓 seed 0–2，3 seed 平均預測的 fold 0 淨值 MSE；改善 ≥1.0 才加入，最多 6 欄。
完成寫 results/sel.json，並把 SEL 補訓 5 seed。單欄臂（+<欄>）要先訓好 seed 0–2（train.py）。
  python -I -X utf8 select_fwd.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o_lib as X  # noqa: E402
import numpy as np  # noqa: E402
import train as TR  # noqa: E402
import e227_eval as EV  # noqa: E402
from e227_model import tensors  # noqa: E402
SEEDS, MIN_GAIN, MAX_K = [0, 1, 2], 1.0, 6


def fold0_mse(arm, ye, va):
    P = np.stack([np.load(os.path.join(HERE, 'results', 'fold0', f'{arm}-{s}.npy')) for s in SEEDS])
    res, *_ = EV.metrics(va, ye, {'m': EV.ens(P)})
    return EV.val(res, 'm', 'net')


def name(cols):
    return 'base' if not cols else '+' + '+'.join(cols)


def main():
    D = TR.data(); va = D['va']
    ye = tensors(va, 'stats', D['means'], 'val')[3].numpy().reshape(-1, 6)
    TR.train_arm('base', SEEDS)
    cur, cur_mse, log = [], fold0_mse('base', ye, va), []
    print('base fold0 MSE', round(cur_mse, 3), flush=True)
    while len(cur) < MAX_K:
        cand = {}
        for c in X.OB:
            if c in cur:
                continue
            arm = name(cur + [c]); TR.train_arm(arm, SEEDS); cand[c] = fold0_mse(arm, ye, va)
        best = min(cand, key=cand.get); gain = cur_mse - cand[best]
        log.append({'step': len(cur) + 1, 'current': list(cur), 'currentMSE': round(cur_mse, 3),
                    'candidates': {k: round(v, 3) for k, v in sorted(cand.items(), key=lambda kv: kv[1])}, 'best': best, 'gain': round(gain, 3)})
        print(json.dumps(log[-1], ensure_ascii=False), flush=True)
        if gain < MIN_GAIN:
            break
        cur, cur_mse = cur + [best], cand[best]
    json.dump({'selected': cur, 'fold0MSE': round(cur_mse, 3), 'rule': f'gain>={MIN_GAIN}, max {MAX_K}, seeds {SEEDS}', 'log': log},
              open(os.path.join(HERE, 'results', 'sel.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if cur:
        TR.train_arm('SEL', [0, 1, 2, 3, 4])
    print('SEL', cur)


if __name__ == '__main__':
    main()
