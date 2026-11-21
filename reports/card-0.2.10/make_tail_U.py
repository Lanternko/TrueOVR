"""card 0.2.10 步驟 1：用 E-175 的 U 臂（滑動窗口，c=82）重算 2025-26 季末 8 項屬性，寫成 tail-U.csv（= tail-e123a.csv，只換 8 欄）。
同時寫 tail-V8.csv（8 欄換成 E-175 重算的 V 值，供建構器自我檢查）。8 欄 = drive, foulDraw, ft, mid, pass, rebound, short, tovSkill。
用法：python -I -X utf8 reports/card-0.2.10/make_tail_U.py"""
import csv, hashlib, json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
E175 = ROOT / 'reports/E175-sliding-window-card'
sys.path.insert(0, str(E175))
import e175_lib as L, e175_card as C
TAIL = ROOT / 'reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv'
D = L.Data(); inp = C.load_inputs()
V = C.card_chain(D, inp, 'V'); U = C.card_chain(D, inp, 'U')
pid_i = {int(p): i for i, p in enumerate(V['pids'])}
rows = list(csv.DictReader(open(TAIL, encoding='utf-8')))
assert len(rows) == 582 and all(int(r['playerId']) in pid_i for r in rows)
for tag, R in (('U', U), ('V8', V)):
    with open(H / f'tail-{tag}.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(list(rows[0].keys()))
        for r in rows:
            i = pid_i[int(r['playerId'])]
            o = dict(r)
            for a in C.ATTRS8:
                o[a] = repr(float(R['mapped'][a][i]))
            w.writerow([o[k] for k in rows[0].keys()])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
print(json.dumps({'tail_src_sha256': sha(TAIL), 'tail-U': sha(H / 'tail-U.csv'), 'tail-V8': sha(H / 'tail-V8.csv'), 'info_U': U['info']}, ensure_ascii=False, default=float)[:1500])
