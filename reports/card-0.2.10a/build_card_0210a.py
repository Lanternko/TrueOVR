"""card 0.2.10a = card 0.2.10 只換 2025-26 T6 目標檔（L-102／F-128：BBRef 聯盟第一的格子包在 <strong> 裡，BPM 讀成空值，Jokić、Wembanyama 從 T6 消失、align＝0）。
修 reports/E142-card-target/c0d_collect.py 的解析後重產 bpm_*.csv 與 phase1 候選檔（舊檔在 pre-L102/），make_t6_fixed.py 用同一個 swap_rapm 換進三份 --rapm。
屬性（tail-U.csv）、係數、OVR 錨、用人層全部和 0.2.10 相同（frozen.json 同檔）。
自我檢查：t6tag=repro（舊候選檔）須與 0.2.10 ranking.csv 逐位元相同。
用法：python -I -X utf8 reports/card-0.2.10a/build_card_0210a.py [--rebuild]"""
import csv, hashlib, json, shutil, subprocess, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
C0210 = ROOT / 'reports/card-0.2.10'
C029 = ROOT / 'reports/card-0.2.9'
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
        run(OUT / 'make_t6_fixed.py')
        for t in ('repro', 'fixed'):
            run(OUT / 'run_parts.py', t, OUT / 'tail-U.csv', t)
            run(OUT / 'use_layer.py', 'frozen', OUT / f'work/{t}/cards', OUT / f'work/{t}/out', OUT / 'frozen.json')
    assert sha(OUT / 'work/repro/out/ranking.csv') == sha(C0210 / 'ranking.csv'), 'repro 與 0.2.10 不同'
    W = OUT / 'work/fixed'
    shutil.copyfile(W / 'out/ranking.csv', OUT / 'ranking.csv')
    shutil.copyfile(C029 / 'three-value.csv', OUT / 'three-value.csv')
    shutil.copyfile(OUT / 'work/t6/fixed/rapm-R.csv', OUT / 'rapm-T6.csv')
    for part in ('primary', 'fitA', 'fitB'):
        d = OUT / 'cards/K6' / part
        d.mkdir(parents=True, exist_ok=True)
        for f in ('pred.csv', 'summary.json', 'pergame-summary.json', 'pergame-repl.csv', 'ranking.csv'):
            shutil.copyfile(W / 'cards' / part / f, d / f)
    fz = json.loads((OUT / 'frozen.json').read_text(encoding='utf-8'))
    a, b = rd(C0210 / 'ranking.csv'), rd(OUT / 'ranking.csv')
    assert len(a) == len(b) == 582

    def rk(rows):
        rr = sorted(((r['name'], float(r['ovr'])) for r in rows if float(r['MIN']) >= 500), key=lambda x: -x[1])
        return {n: i + 1 for i, (n, _) in enumerate(rr)}
    ra, rb = rk(a), rk(b)
    oa = {r['name']: float(r['ovr']) for r in a}; ob = {r['name']: float(r['ovr']) for r in b}
    moved = sum(1 for n in ra if ra[n] <= 300 and abs(rb.get(n, 999) - ra[n]) >= 10)
    moved100 = sum(1 for n in ra if ra[n] <= 100 and abs(rb.get(n, 999) - ra[n]) >= 10)
    keys = ('Victor Wembanyama', 'Shai Gilgeous-Alexander', 'Kawhi Leonard', 'Giannis Antetokounmpo', 'Luka Dončić', 'Jayson Tatum', 'Jalen Williams', 'Cooper Flagg', 'Anthony Edwards', 'Paolo Banchero', 'Nikola Jokić', 'Anthony Davis', 'Joel Embiid', 'Alperen Sengun')
    t6 = json.loads((OUT / 'work/t6/t6-fixed.json').read_text(encoding='utf-8'))
    srcs = [OUT / 'tail-U.csv', OUT / 'frozen.json', OUT / 'calibrate_frozen.py', OUT / 'use_layer.py', OUT / 'run_parts.py', OUT / 'make_t6_fixed.py',
            C0210 / 'ranking.csv', C029 / 'three-value.csv', ROOT / 'reports/E142-card-target/c0d_collect.py',
            ROOT / 'reports/E142-card-target/phase1-work/cands/T6-2025-26.pkl', ROOT / 'reports/E142-card-target/phase1-work/cands/pre-L102/T6-2025-26.pkl',
            ROOT / 'data/external-impact/bpm/bpm_2025-26.csv', ROOT / 'data/external-impact/bpm/adv2026.html']
    out = {
        'version': 'card 0.2.10a', 'baseVersion': 'card 0.2.10', 'players': 582,
        'change': 'L-102／F-128：修 BPM 解析（<strong> 包的聯盟第一讀成空值），2025-26 T6 補回 Jokić、Wembanyama（504→506 人，其他人 T6 重標準化最多動 0.10）；'
                  '屬性、係數、OVR 錨、用人層全同 0.2.10（frozen.json）。',
        'prereg_verdict': '資料錯修正，不是新假設（不走預註冊）；repro 臂逐位元重現 0.2.10。',
        'version_rule': 'PATCH（R-114）：前 300 名移動 ≥10 名 %d 人。' % moved,
        'moved10_top300': moved, 'moved10_top100': moved100,
        'frozen': {'r_repl': fz['use_layer']['r_repl'], 'anchors': fz['use_layer']['anchors'], 'wls_card': fz['use_layer']['wls_card'], 'file': 'reports/card-0.2.10a/frozen.json'},
        'self_check': 'work/repro（舊 T6 候選檔）ranking.csv 與 0.2.10 逐位元相同',
        't6': t6,
        'key_players_2025_26': {n: {'0.2.10': [oa[n], ra[n]], '0.2.10a': [ob[n], rb[n]]} for n in keys if n in rb and n in ra},
        'top20': {'out': sorted(n for n in ra if ra[n] <= 20 and rb[n] > 20), 'in': sorted(n for n in rb if rb[n] <= 20 and ra[n] > 20)},
        'part_card_sha256': {p: sha(OUT / 'cards/K6' / p / 'summary.json') for p in ('primary', 'fitA', 'fitB')},
        'part_card_pred_csv_sha256': {p: sha(OUT / 'cards/K6' / p / 'pred.csv') for p in ('primary', 'fitA', 'fitB')},
        'rapm_inputs_sha256': {k.split('/')[1]: v['sha256'] for k, v in t6['files'].items() if k.startswith('fixed/')},
        'sources_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in srcs},
        'frozen_sources_sha256': fz['source_sha256'],
        'build_command': 'python -I -X utf8 reports/card-0.2.10a/build_card_0210a.py --rebuild',
        'generator': 'reports/card-0.2.10a/build_card_0210a.py', 'ranking_csv_sha256': sha(OUT / 'ranking.csv'),
    }
    (OUT / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + '\n', encoding='utf-8')
    print(out['ranking_csv_sha256'], moved, moved100, out['top20'], json.dumps(out['key_players_2025_26'], ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
