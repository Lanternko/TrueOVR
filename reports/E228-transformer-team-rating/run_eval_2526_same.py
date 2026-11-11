"""errata-1：eval_t.py 的 `from e223_lib import *` 把 HERE 蓋成 E-223 目錄，凍結守門去 E-223 找 FREEZE.txt，相對路徑也落到 E-223。
本檔不改凍結的 eval_t.py：讀原始碼，只把守門的 FREEZE.txt 路徑指回 E-228，其餘照原碼執行；--pred／--out 用絕對路径。"""
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
assert os.path.exists(os.path.join(D, 'FREEZE.txt'))
src = open(os.path.join(D, 'eval_t.py'), encoding='utf-8').read()
old = "os.path.exists(os.path.join(HERE, 'FREEZE.txt'))"
assert src.count(old) == 1
src = src.replace(old, repr(True))
sys.argv = ['eval_t.py', '--key', '2526', '--pred', os.path.join(D, 'work', 'pred-T-2526-same.json'), '--out', os.path.join(D, 'results', 'test-2526-same.json')]
g = {'__name__': '__main__', '__file__': os.path.join(D, 'eval_t.py')}
exec(compile(src, os.path.join(D, 'eval_t.py'), 'exec'), g)
