"""E-070：用 E-064 複本的 calibrate-wing.py 建卡。python -X utf8 run_cards.py <tag> <primary|fitA|fitB|c0-switch-off> [possScale]
tag = w0（w_vol=0）或 w075。子程序一律 CREATE_NO_WINDOW。從 repo 根目錄執行。"""
import subprocess, sys
D = 'reports/card-0.2.0+E070-foul-volume'
E64 = 'reports/card-0.1.2+E064-pergame'
V58 = 'reports/ovr-v58-holdout-2025-26'
tag, which = sys.argv[1], sys.argv[2]
scale = sys.argv[3] if len(sys.argv) > 3 else '0.5'
args = [sys.executable, '-I', E64 + '/calibrate-wing.py', '--direction', 'H1', '--capMargin', '0',
        '--attrSource', f'{D}/attributes-{tag}/attributes-new.csv',
        '--defSource', 'reports/card-0.1.1+E060-onball-targeting/defense-attributes-e060.csv', '--perGame']
out = f'{D}/cards-{tag}/{which}' + (f'-scale{scale}' if which.startswith('fit') and scale != '0.5' else '')
if which.startswith('fit'):
    h = which[-1]
    args += ['--rapm', f'{V58}/rapm-{h}.csv', '--possScale', scale, '--mpgSource', f'{E64}/mpg-{h}.csv']
args += ['--out', out]
p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
print(out, p.returncode, (p.stdout + p.stderr)[-300:])
