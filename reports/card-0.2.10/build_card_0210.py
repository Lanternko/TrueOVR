"""card 0.2.10 = E-175 滑動窗口卡上線（R-111、R-114 PATCH）。8 項屬性（drive、foulDraw、ft、mid、pass、rebound、short、tovSkill）改用 U 窗口（c=82，四季滑動），
其餘沿用 0.2.9a；lead 裁定 B＋全凍結：係數、OVR 錨、H1 cap 參照、用人層 r_repl／WLS 係數、兩段映射錨全取 0.2.9a（frozen.json）。
流程：make_tail_U.py -> tail-U.csv；run_parts.py U tail-U.csv -> work/U/cards；use_layer.py frozen work/U/cards work/U/out frozen.json -> work/U/out/ranking.csv；
本檔把結果整理成 0.2.9a 同構的目錄（cards/K6、ranking.csv、summary.json），並記錄所有輸入 sha256（G2）。
自我檢查：餵 0.2.9a 的 V 屬性（tail-V8.csv）重建，須與 0.2.9a 逐位元相同（work/V8、work/self 已驗：sha b7972182…）。
用法：python -I -X utf8 reports/card-0.2.10/build_card_0210.py [--rebuild]   （--rebuild 先重跑上述三步，約 10 分鐘）"""
import csv, hashlib, json, shutil, subprocess, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C029 = ROOT / 'reports/card-0.2.9'
C029A = ROOT / 'reports/card-0.2.9a'
E175 = ROOT / 'reports/E175-sliding-window-card'
PY = [sys.executable, '-I', '-X', 'utf8']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rd(p):
    return list(csv.DictReader(Path(p).open(encoding='utf-8')))


def run(*a):
    r = subprocess.run(PY + [str(x) for x in a], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=3000)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def main():
    if '--rebuild' in sys.argv:
        run(OUT / 'make_tail_U.py')
        run(OUT / 'run_parts.py', 'U', OUT / 'tail-U.csv')
        run(OUT / 'use_layer.py', 'frozen', OUT / 'work/U/cards', OUT / 'work/U/out', OUT / 'frozen.json')
    W = OUT / 'work/U'
    shutil.copyfile(W / 'out/ranking.csv', OUT / 'ranking.csv')
    for f in ('three-value.csv', 'rapm-T6.csv'):
        shutil.copyfile(C029 / f, OUT / f)
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(W / 'cards' / part / f, d / f)
    fz = json.loads((OUT / 'frozen.json').read_text(encoding='utf-8'))
    a, b = rd(C029A / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert len(a) == len(b) == 582

    def rk(rows):
        rr = sorted(((r['name'], float(r['ovr'])) for r in rows if float(r['MIN']) >= 500), key=lambda x: -x[1])
        return {n: i + 1 for i, (n, _) in enumerate(rr)}
    ra, rb = rk(a), rk(b)
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    moved = sum(1 for n in ra if ra[n] <= 300 and abs(rb.get(n, 999) - ra[n]) >= 10)
    moved100 = sum(1 for n in ra if ra[n] <= 100 and abs(rb.get(n, 999) - ra[n]) >= 10)
    keys = ('Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Anthony Davis', 'Joel Embiid', 'Alperen Sengun')
    bc0 = json.loads((ROOT / 'reports/card-0.2.9+E164-no-stamina/work/base-S-2025-26/build-c0.json').read_text(encoding='utf-8'))
    srcs = [OUT / 'tail-U.csv', OUT / 'tail-V8.csv', OUT / 'frozen.json', OUT / 'calibrate_frozen.py', OUT / 'use_layer.py', OUT / 'run_parts.py',
            OUT / 'make_tail_U.py', OUT / 'make_frozen.py', C029A / 'ranking.csv', C029 / 'rapm-T6.csv', C029 / 'three-value.csv',
            E175 / 'e175_card.py', E175 / 'e175_lib.py', ROOT / 'reports/ovr-v61-shrink-history-2025-26/backtest.json']
    out = {
        'version': 'card 0.2.10', 'baseVersion': 'card 0.2.9a', 'players': 582,
        'change': 'E-175 滑動窗口：8 項屬性（drive、foulDraw、ft、mid、pass、rebound、short、tovSkill）改用四季滑動窗口 U（c=82；過去季依 window_weights 加權、方法 b 收縮）；'
                  '係數、OVR 錨、H1 cap 參照、用人層 r_repl／WLS 係數、兩段映射錨全凍結用 0.2.9a（lead 2026-11-01 裁定 B＋全凍結）。',
        'prereg_verdict': 'E-175 預註冊 §3：8 項 SD 比皆在 [0.9,1.1]，不重擬合；使用者 R-111 採用。',
        'version_rule': 'PATCH（R-114）：前 300 名移動 ≥10 名 %d 人。' % moved,
        'moved10_top300': moved, 'moved10_top100': moved100,
        'frozen': {'r_repl': fz['use_layer']['r_repl'], 'anchors': fz['use_layer']['anchors'], 'wls_card': fz['use_layer']['wls_card'], 'file': 'reports/card-0.2.10/frozen.json'},
        'self_check': 'builder 餵 0.2.9a V 屬性（tail-V8.csv）重建 = 0.2.9a ranking.csv 逐位元相同（sha b7972182…）；work/self、work/V8 已驗',
        'key_players_2025_26': {n: {'0.2.9a': [oa[n], ra[n]], '0.2.10': [ob[n], rb[n]]} for n in keys if n in rb and n in ra},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'part_card_sha256': bc0['part_card_sha256'] if False else {p: sha(OUT / 'cards/K6' / p / 'summary.json') for p in ('primary', 'fitA', 'fitB')},
        'part_card_pred_csv_sha256': {p: sha(OUT / 'cards/K6' / p / 'pred.csv') for p in ('primary', 'fitA', 'fitB')},
        'rapm_inputs_sha256': bc0['rapm_inputs_sha256'],
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'frozen_sources_sha256': fz['source_sha256'],
        'build_command': 'python -I -X utf8 reports/card-0.2.10/build_card_0210.py --rebuild',
        'generator': 'reports/card-0.2.10/build_card_0210.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], moved, moved100, out['top20'], json.dumps(out['key_players_2025_26'], ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
