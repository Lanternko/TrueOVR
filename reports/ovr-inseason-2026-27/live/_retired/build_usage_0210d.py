raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-124 retired guard（0.2.10e 換 build_usage_0210e.py；WIN10=0 用的 work-selfcheck 檔已產好）
"""card 0.2.10d 用人層（E-185；R-111/R-118）：和 0.2.12 版的差別是係數不凍結——card 0.2.10d 在新屬性上整套重擬合（E-187 KAU 同法：修正後 T6、第三層 WLS、r_repl、兩段映射錨都重算），
本程式只把 reports/card-0.2.10d/usage-features.json（e162_build.pipe 在重擬合當下存的每人特徵＋該次係數／r_repl／錨點）轉成 inseason 讀的 usage 檔，並逐人核對：
  ovr（.1f）、mpg（.2f）、gRepl（.4f）三欄與 card-0.2.10d/ranking.csv 逐格相同（features 檔內已核對，這裡再核對一次）。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_0210d.py [base10c]
  不帶參數：輸出 live/usage-2025-26-card0210d.json（現行）。
  base10c ：自我檢查拆項用（不上線）。來源改 card-0.2.10d/work-selfcheck（＝card 0.2.10c 的逐位元重建）、核對對象 card-0.2.10c/ranking.csv，
            輸出 work-selfcheck/usage-2025-26-card0210c-nowin.json 與 work-selfcheck/summary-card0210c.json（run_c4_live.py 在 WIN10=0 時讀）。"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = ROOT / 'reports/card-0.2.10d'
BASE = len(sys.argv) > 1 and sys.argv[1] == 'base10c'
if BASE:
    NAME, CARD = 'card-0.2.10c', ROOT / 'reports/card-0.2.10c'
    FEAT = D / 'work-selfcheck/KAU-2025-26/out/usage-features.json'
    OUT = D / 'work-selfcheck/usage-2025-26-card0210c-nowin.json'
    SUMM = D / 'work-selfcheck/summary-card0210c.json'
else:
    NAME, CARD = 'card-0.2.10d', D
    FEAT = D / 'usage-features.json'
    OUT = HERE / 'usage-2025-26-card0210d.json'
    SUMM = D / 'summary.json'
RANKING = CARD / 'ranking.csv'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    f = json.loads(FEAT.read_text(encoding='utf-8'))
    if BASE:
        SUMM.write_text(json.dumps({'version': 'card 0.2.10c', 'ranking_csv_sha256': sha(RANKING), 'note': '自我檢查用：card 0.2.10c 沒有自己的 summary.json，這裡只記 ranking.csv sha256'}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    summ = json.loads(SUMM.read_text(encoding='utf-8'))
    assert sha(RANKING) == summ['ranking_csv_sha256'], f'{NAME} ranking.csv sha256 與 summary 不符'
    card = {r['name']: r for r in csv.DictReader(RANKING.open(encoding='utf-8'))}
    players = f['players']
    assert len(players) == len(card) == 582 and {p['name'] for p in players.values()} == set(card), '名單與 card 不一致'
    assert f['predNewVsPipeline'] < 1e-12 and all(p['ok'] for p in players.values()), 'features 檔內核對未過'
    assert 'b8_ydL' in f['coef'] and f['coef']['b8_ydL'] == 0.0 and len(f['coef']) == 9
    for p in players.values():
        assert abs(p['ovrCard'] - float(card[p['name']]['ovr'])) < 1e-9
    payload = {'coef': f['coef'], 'rRepl': f['rRepl'], 'anchors': f['anchors'], 'players': players}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    doc = {
        'doc': f'{NAME} 用人層（重擬合值，不是凍結值）：部件卡 E-164 S 臂拿掉 stamina；用人層 E-158 Y0（b8_ydL＝0）；係數、r_repl、錨點取 e162_build.pipe 重擬合當下的結果；'
               'features＝scope_feats("full")（連續 d；窗口 MPG 只換 g 與錨用的 mpgAvail）。W = w_sat(mpg)',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L（b8_ydL＝0；has=True）；has=False → predNew = p',
        'check': {'n': len(players), 'mismatchOvr1dp_Mpg2dp_GRepl4dp': 0, 'predNewVsPipeline': f['predNewVsPipeline'], 'hasFalse': sum(not p['has'] for p in players.values())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {f'{NAME} ranking.csv': sha(RANKING), f'{NAME} usage-features.json': sha(FEAT)},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'payloadSha256': doc['payloadSha256'], 'n': len(players), 'rRepl': f['rRepl'], 'anchors': f['anchors']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
