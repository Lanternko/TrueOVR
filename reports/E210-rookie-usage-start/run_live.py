"""E-210 3：2026 屆最新 live 資料。variant=B0（現行）或 U1；跑完整 live 主流程（老將＋新秀）寫到 out（本資料夾下，不寫 live/）。
用法：python run_live.py <B0|U1> <out_dir>"""
import sys, json
sys.path.insert(0, 'D:/Projects/CODING/basketball-autochess/reports/E210-rookie-usage-start')
sys.stdout.reconfigure(encoding='utf-8')
import u1_lib as U
variant, out = sys.argv[1], sys.argv[2]
RW = U.RW
if variant == 'U1':
    RW.ROOKIE_JSON = U.HERE / 'rookie-prior-2026-u1.json'
    doc = json.load(open(RW.ROOKIE_JSON, encoding='utf-8'))
    U.patch_live({p['playerId']: p['mpg0'] for p in doc['players']})
ns = RW.load_ns()
sys.argv = ['run_c4_live.py', out]
raise SystemExit(ns['main']())
