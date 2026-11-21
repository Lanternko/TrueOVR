"""card 0.2.12 = E-185：long、creation、threeValue、MPG 也改 E-175 四季滑動窗口（0.2.10 已窗口化 8 項）。PATCH，係數、OVR 錨、r_repl、用人層係數全凍結 0.2.9a（frozen.json）。
（建在 card 0.2.10a 上：2025-26 T6 用 L-102 修正後的目標檔（make_t6_fixed.py，R-121）；版號跳過 0.2.11——該號被另一個 session 先用過後改名 0.2.10a。）
流程：make_tail_U.py -> tail-U.csv（long、creation 換窗口值）、mpg-c82.csv、three-value.csv；run_parts.py U tail-U.csv -> work/U/cards；
use_layer.py frozen work/U/cards work/U/out frozen.json mpg-c82.csv -> work/U/out/ranking.csv；本檔整理成 0.2.10 同構的目錄並記錄所有輸入 sha256（G2）。
自我檢查：(1) 關掉新窗口（0.2.10 的 tail-U.csv、不給 mpg 檔）＋修正後 T6 重建須與 0.2.10a ranking.csv 逐位元相同（work/Sf）；(2) 同上但舊 T6 須與 0.2.10 ranking.csv 相同（work/S，建 0.2.12 時第一版）。
用法：python -I -X utf8 reports/card-0.2.12/build_card_0212.py [--rebuild]"""
import csv, hashlib, json, shutil, subprocess, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C0210 = ROOT / 'reports/card-0.2.10'
C0210A = ROOT / 'reports/card-0.2.10a'   # 底（正式卡，R-121）
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
        run(OUT / 'make_t6_fixed.py')
        run(OUT / 'run_parts.py', 'Sf', C0210 / 'tail-U.csv', 'fixed')
        run(OUT / 'use_layer.py', 'frozen', OUT / 'work/Sf/cards', OUT / 'work/Sf/out', OUT / 'frozen.json')
        run(OUT / 'run_parts.py', 'U', OUT / 'tail-U.csv', 'fixed')
        run(OUT / 'use_layer.py', 'frozen', OUT / 'work/U/cards', OUT / 'work/U/out', OUT / 'frozen.json', OUT / 'mpg-c82.csv')
    assert sha(OUT / 'work/Sf/out/ranking.csv') == sha(C0210A / 'ranking.csv'), '關掉新窗口＋修正 T6 重建與 0.2.10a 不同'
    W = OUT / 'work/U'
    shutil.copyfile(W / 'out/ranking.csv', OUT / 'ranking.csv')
    shutil.copyfile(OUT / 'work/t6/fixed/rapm-R.csv', OUT / 'rapm-T6.csv')
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(W / 'cards' / part / f, d / f)
    fz = json.loads((OUT / 'frozen.json').read_text(encoding='utf-8'))
    a, b = rd(C0210A / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert len(a) == len(b) == 582

    def rk(rows):
        rr = sorted(((r['name'], float(r['ovr'])) for r in rows if float(r['MIN']) >= 500), key=lambda x: -x[1])
        return {n: i + 1 for i, (n, _) in enumerate(rr)}
    ra, rb = rk(a), rk(b)
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    moved300 = sum(1 for n in ra if ra[n] <= 300 and abs(rb.get(n, 999) - ra[n]) >= 10)
    moved100 = sum(1 for n in ra if ra[n] <= 100 and abs(rb.get(n, 999) - ra[n]) >= 10)
    keys = ('Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Stephen Curry', 'Michael Porter Jr.', 'Anthony Davis', 'Joel Embiid', 'Alperen Sengun')
    srcs = [OUT / 'tail-U.csv', OUT / 'mpg-c82.csv', OUT / 'three-value.csv', OUT / 'mpg-L-selection.json', OUT / 'abilityC-by-season.json', OUT / 'frozen.json',
            OUT / 'calibrate_frozen.py', OUT / 'use_layer.py', OUT / 'run_parts.py', OUT / 'make_t6_fixed.py', OUT / 'make_tail_U.py', OUT / 'mpg_select.py', OUT / 'dump_abilityc.py',
            ROOT / 'reports/ovr-inseason-2026-27/live/window10.py', ROOT / 'reports/ovr-inseason-2026-27/live/window8.py',
            C0210 / 'ranking.csv', C0210A / 'ranking.csv', C0210 / 'tail-U.csv', C0210 / 'three-value.csv', C0210A / 'three-value.csv', C0210 / 'frozen.json',
            ROOT / 'reports/E142-card-target/c0d_collect.py', ROOT / 'reports/E142-card-target/phase1-work/cands/T6-2025-26.pkl',
            E175 / 'e175_card.py', E175 / 'e175_lib.py', ROOT / 'reports/ovr-v62-3pt-difficulty-2025-26/new-long.json',
            ROOT / 'reports/player-impact-v41/2025-26-player-validation.csv', ROOT / 'data/season-source/player-games.json']
    t6 = json.loads((OUT / 'work/t6/t6-fixed.json').read_text(encoding='utf-8'))
    sel = json.loads((OUT / 'mpg-L-selection.json').read_text(encoding='utf-8'))
    out = {
        'version': 'card 0.2.12', 'baseVersion': 'card 0.2.10a', 'players': 582,
        'change': 'E-185：long、creation（進 OVR）、threeValue（3PT 欄，只顯示）、MPG（g 的 MPG_hat）改 E-175 四季滑動窗口（c=82；long／creation 照 stage1-methods §2 的 U 版；'
                  'threeValue 窗口加權 3PA／MIN、acc＝逐季 abilityC×加權 3PA 再 THREE_K 收縮；MPG＝Σu·MIN／Σu·GP，窗口長度 L=%d 季，只用 2024-25 選）；係數、OVR 錨、r_repl、用人層全凍結用 0.2.9a。' % sel['selected_L'],
        'prereg_verdict': 'R-118：使用者決定直接上線，不做預註冊回測。',
        'mpg_L': sel['selected_L'],
        'version_rule': 'PATCH（R-114）：前 300 名移動 ≥10 名 %d 人。' % moved300,
        'moved10_top300': moved300, 'moved10_top100': moved100,
        'frozen': {'r_repl': fz['use_layer']['r_repl'], 'anchors': fz['use_layer']['anchors'], 'wls_card': fz['use_layer']['wls_card'], 'file': 'reports/card-0.2.12/frozen.json'},
        'self_check': '關掉新窗口（0.2.10 tail-U.csv、不給 mpg 檔）＋修正 T6 用同一條鏈重建＝0.2.10a ranking.csv 逐位元相同（work/Sf）；舊 T6 版＝0.2.10 ranking.csv（work/S）',
        'key_players_2025_26': {n: {'0.2.10a': [oa[n], ra[n]], '0.2.12': [ob[n], rb[n]]} for n in keys if n in rb and n in ra},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'part_card_sha256': {p: sha(OUT / 'cards/K6' / p / 'summary.json') for p in ('primary', 'fitA', 'fitB')},
        'part_card_pred_csv_sha256': {p: sha(OUT / 'cards/K6' / p / 'pred.csv') for p in ('primary', 'fitA', 'fitB')},
        't6': t6, 'rapm_inputs_sha256': {k.split('/')[1]: v['sha256'] for k, v in t6['files'].items() if k.startswith('fixed/')},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'frozen_sources_sha256': fz['source_sha256'],
        'build_command': 'python -I -X utf8 reports/card-0.2.12/build_card_0212.py --rebuild',
        'generator': 'reports/card-0.2.12/build_card_0212.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + chr(10), encoding='utf-8')
    print(out['ranking_csv_sha256'], moved300, moved100, out['top20'], json.dumps(out['key_players_2025_26'], ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
