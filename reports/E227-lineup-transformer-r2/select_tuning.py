"""E-227 調參選擇：每臂在 9 組 (lr, wd) 中，以 3 seed 的 fold-0 驗證總損失平均最低者入選（同分取較小 lr）。寫 tuning.json。
用法（本目錄）：python -I -X utf8 select_tuning.py"""
import glob, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
g = defaultdict(list)
for f in glob.glob(os.path.join(HERE, 'results', 'tune-*.json')):
    r = json.load(open(f)); g[(r['arm'], r['lr'], r['wd'])].append(r)
grid = {}; sel = {}
for (arm, lr, wd), rs in sorted(g.items()):
    v = [r['valLoss'] for r in rs]
    grid.setdefault(arm, []).append({'lr': lr, 'wd': wd, 'n': len(rs), 'meanValLoss': round(sum(v) / len(v), 5), 'valLosses': v,
                                     'bestEpochs': [r['bestEpoch'] for r in rs]})
for arm, L in grid.items():
    assert all(x['n'] == 3 for x in L), arm
    b = min(L, key=lambda x: (x['meanValLoss'], x['lr'])); sel[arm] = {'lr': b['lr'], 'wd': b['wd'], 'meanValLoss': b['meanValLoss']}
json.dump({'rule': '每臂 9 組 lr×wd、各 3 seed（0,1,2），選 fold-0 驗證總損失平均最低；只用 split=train，folds 1-4 訓練、fold 0 驗證',
           'selected': sel, 'grid': grid}, open(os.path.join(HERE, 'tuning.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(sel, ensure_ascii=False, indent=1))
