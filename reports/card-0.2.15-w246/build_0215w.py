"""card 0.2.15（持球進攻＝creation＋pnr 合成，E-303 MRG5，2026-11-10）係數底：自 reports/card-0.2.13-w246/build_0213w.py 複本，擬合鏈換 reports/card-0.2.15-fit/（creation 欄＝crtpnr_live 合成值、KG 臂 --offBallCols gravity，pnr 不再當獨立特徵）。
以下 0.2.13 原說明：card 0.2.13（擋拆持球 pnr，E-255／E-258）係數底：自 reports/card-0.2.12c-w246/build_0212c.py 複本，擬合鏈換 reports/card-0.2.13-fit/（KG 臂 --offBallCols gravity,pnr），多複製 gravity-pnr-attr.csv；PNR=0 鏈＝224db781（card-0.2.12c-w246）。
以下原說明：card 0.2.12c 的 W246 窗口底（R-144，E-207 W246 重擬合 2026-11-02）＝E-206 KC 臂的做法（tovSkill r 分母改觸球次數）在 W246 窗口上重擬合：
池 mu/sd／收縮先驗／0-99 映射／全部 OVR 係數、usage 層、def-L 皆 W246（reports/card-0.2.12c-fit246/，各步驟以 FIT_WIN=328 逐位元重現 KC）。
同 card-0.2.12-tov/build_0212.py：KC 的 KAU ranking 走 E-188 OVR 映射（apply_to_card.py），放到本目錄；結果須與 KC final 逐位元組相同。
本夾是賽中管線的係數／RAPM／tov-raw 來源（對應 0.2.12b 的 card-0.2.12-tov）；W246 的正式卡在 reports/card-0.2.12c/。
用法（repo root）：python -I -B -X utf8 reports/card-0.2.15-w246/build_0215w.py"""
import csv, hashlib, importlib.util, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E = ROOT / 'reports/card-0.2.15-fit'
E13 = ROOT / 'reports/card-0.2.13-fit'
LIVE = ROOT / 'reports/ovr-inseason-2026-27/live'
F246 = ROOT / 'reports/card-0.2.12c-fit246'
ARM = 'W246'
J, D = ROOT / 'reports/card-0.2.10j', ROOT / 'reports/card-0.2.10d'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s = importlib.util.spec_from_file_location('apply_to_card', ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/apply_to_card.py')
AC = importlib.util.module_from_spec(s); s.loader.exec_module(AC)


def main():
    pre = HERE / 'work/pre-W246'
    if pre.exists():
        shutil.rmtree(pre)
    pre.mkdir(parents=True)
    shutil.copyfile(E / 'work/W246/B-KG/KAU-2025-26/out/ranking.csv', pre / 'ranking.csv')
    for n in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(D / n, pre / n)
    rel = lambda p: p.relative_to(ROOT).as_posix()
    AC.main(rel(pre), rel(HERE), 'card 0.2.15 W246')
    shutil.copyfile(J / 'three-value.csv', HERE / 'three-value.csv')
    a = [r['playerId'] for r in csv.DictReader((pre / 'three-value.csv').open(encoding='utf-8'))]
    b = [r['playerId'] for r in csv.DictReader((HERE / 'three-value.csv').open(encoding='utf-8'))]
    assert a == b
    kc = E / 'work/W246/final/out/ranking.csv'
    same = (HERE / 'ranking.csv').read_bytes() == kc.read_bytes()
    assert same, 'ranking.csv 與 card-0.2.15-fit W246 final 不同'
    for p in ('primary', 'fitA', 'fitB'):
        dst = HERE / 'cards/K6' / p
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(E / 'work/W246/A/base-KG-2025-26/c0/cards/K0' / p, dst)
    shutil.copyfile(E / 'work/W246/B-KG/KAU-2025-26/out/usage-features.json', HERE / 'usage-features.json')
    for n in ('gravity-raw.csv', 'gravity-attr.csv'):
        shutil.copyfile(J / n, HERE / n)
    shutil.copyfile(E13 / 'gravity-pnr-attr.csv', HERE / 'gravity-pnr-attr.csv')
    shutil.copyfile(F246 / 'tov-raw-W246.csv', HERE / 'tov-raw.csv')
    shutil.copyfile(F246 / 'tov-raw-info-W246.json', HERE / 'tov-raw-info.json')
    summ = json.loads((HERE / 'summary.json').read_text(encoding='utf-8'))
    summ.update({'version': 'card 0.2.15（W246 窗口底，creation＝持球進攻合成）', 'equals_fit0215_W246_final': same,
                 'crtpnr': {'tail_csv': 'reports/card-0.2.15-fit/tail-W246full-crtpnr.csv', 'tail_sha256': sha(E / 'tail-W246full-crtpnr.csv'),
                            'frozen': 'reports/ovr-inseason-2026-27/live/crtpnr-pool-card0215.json', 'frozen_sha256': sha(LIVE / 'crtpnr-pool-card0215.json')},
                 'ranking_sha256': sha(HERE / 'ranking.csv'),
                 'tov': {'raw_csv': 'reports/card-0.2.15-w246/tov-raw.csv', 'raw_sha256': sha(HERE / 'tov-raw.csv')}})
    (HERE / 'summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(sha(HERE / 'ranking.csv'), same)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
