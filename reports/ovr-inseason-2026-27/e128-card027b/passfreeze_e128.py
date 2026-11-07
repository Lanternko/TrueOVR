"""E-128 errata-1：passFreeze（2025-26 卡片端收縮後 AST/36 與 AST% 的 zs 常數）。
照 card-0.2.7+E125-pass-volume/work/a0_p.py 原樣執行（不改計算，只把輸出與暫存改到臨時目錄、不覆寫 E-125 檔），
在 zs 之後取 avol／rate 在 zs 池（pidx）上的 mean、std(ddof=0)，並核對 r_out、pool_out 與 a0-pass-P50.json 逐位元相同。
輸出 passfreeze.json。用法：python -I -B -X utf8 passfreeze_e128.py
"""
import hashlib, json, os, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
A0 = ROOT / 'reports/card-0.2.7+E125-pass-volume/work/a0_p.py'
src = A0.read_text(encoding='utf-8')
tmp = Path(tempfile.mkdtemp(prefix='e128-a0p-'))
assert src.count("TMP = HERE / 'tmp' / 'a0p'") == 1
src = src.replace("TMP = HERE / 'tmp' / 'a0p'", f"TMP = Path({str(tmp)!r})")
tail = "(OUT / f'a0-pass-{TAG}.json').write_text("
assert src.count(tail) == 1
src = src.replace(tail, "FREEZE = dict(volMean=float(avol[pidx].mean()), volStd=float(avol[pidx].std()), rateMean=float(rate[pidx].mean()), rateStd=float(rate[pidx].std()), poolSize=len(pool_pids), r_out=r_out, pool_out=pool_out, fit=fit)\n(tmp_out := TMP / 'unused.json').write_text(")
sys.argv = ['a0_p.py', '0.5']
g = {'__file__': str(A0), '__name__': 'a0_p_e128'}
os.chdir(ROOT)
exec(compile(src, str(A0), 'exec'), g)
F = g['FREEZE']
ref = json.loads((A0.parent.parent / 'a0-pass-P50.json').read_text(encoding='utf-8'))
same = F['r_out'] == ref['r'] and F['pool_out'] == ref['pool']
out = {'wVol': 0.5, 'wRate': 0.5, 'vol': {'mean': F['volMean'], 'std': F['volStd']}, 'rate': {'mean': F['rateMean'], 'std': F['rateStd']},
       'pool': 'GP>=30, MPG>=20, 在 LEAGUE 名單（a0_p.py pool_pids）', 'poolSize': F['poolSize'],
       'reproducesA0PassP50BitIdentical': bool(same),
       'source': {'file': 'reports/card-0.2.7+E125-pass-volume/work/a0_p.py', 'sha256': hashlib.sha256(src.encode() if False else A0.read_bytes()).hexdigest(),
                  'a0-pass-P50.json': hashlib.sha256((A0.parent.parent / 'a0-pass-P50.json').read_bytes()).hexdigest()}}
(HERE / 'passfreeze.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1))
sys.exit(0 if same else 1)
