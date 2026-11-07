"""E-198 步驟 C：同 card-0.2.10i/build_0210i.py 的 OVR 映射段（apply_to_card.py，E-188），只做 ranking.csv。
work/B-<臂>/KAU-2025-26/out/ranking.csv → work/<臂>-final/pre/ → work/<臂>-final/out/ranking.csv。
KAU 臂另核 c0：out/ranking.csv 須與 reports/card-0.2.10i/ranking.csv 逐位元相同。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.10j+E198-gravity/finalize.py KAU|KG"""
import hashlib, importlib.util, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D = ROOT / 'reports/card-0.2.10d'
I = ROOT / 'reports/card-0.2.10i'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main(arm):
    fin = HERE / f'work/{arm}/final'
    pre, out = fin / 'pre', fin / 'out'
    if fin.exists():
        shutil.rmtree(fin)
    pre.mkdir(parents=True); out.mkdir(parents=True)
    shutil.copyfile(HERE / f'work/{arm}/B-KG/KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(out), f'E202 {arm}')
    res = {'arm': arm, 'pre_sha256': sha(pre / 'ranking.csv'), 'ranking_sha256': sha(out / 'ranking.csv')}
    if arm == 'K0':
        J = ROOT / 'reports/card-0.2.10j/ranking.csv'
        res['c0_equal_0210j'] = (out / 'ranking.csv').read_bytes() == J.read_bytes()
        res['ref_sha256'] = sha(J)
    (fin / 'result.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(res))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1])
