"""card 0.2.12c 用人層（R-144，E-207；328 窗口底 card-0.2.12c-w246）：同 build_usage_0210j.py（已退到 _retired/），只換卡：tovSkill 改觸球分母重擬合後，
係數、r_repl、錨點（含 PR90／PR95）全部取 reports/card-0.2.10j 的建卡輸出（usage-features.json、summary.json）；用人特徵 L、a 仍是 card-0.2.10g/usage-window-c82.csv（與屬性無關）。
逐人核對：card-0.2.12c-w246/ranking.csv 的 ovr＝ovr_map(gRepl)（差 ≤0.06）、名單與 0.2.10j 相同、L／a 與 usage-window-c82-246.csv 逐位相同。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_0212c.py → live/usage-2025-26-card0212c.json"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G, F = ROOT / 'reports/card-0.2.12c-w246', ROOT / 'reports/card-0.2.10j'
FEAT = G / 'usage-features.json'
WIN_CSV = ROOT / 'reports/card-0.2.12c-fit246/usage-window-c82-246.csv'   # W246 窗口的 L、a（2026-11-02 重擬合；328 版＝card-0.2.10g/usage-window-c82.csv）
OUT = HERE / 'usage-2025-26-card0212c.json'
OM_PY = ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    s = importlib.util.spec_from_file_location('ovr_map', OM_PY)
    OM = importlib.util.module_from_spec(s); s.loader.exec_module(OM)
    f = json.loads(FEAT.read_text(encoding='utf-8'))
    summ = json.loads((G / 'summary.json').read_text(encoding='utf-8'))
    assert sha(G / 'ranking.csv') == summ['ranking_csv_sha256'], 'card-0.2.12c-w246 ranking.csv sha256 與 summary 不符'
    card = {r['name']: r for r in csv.DictReader((G / 'ranking.csv').open(encoding='utf-8'))}
    old = {r['name'] for r in csv.DictReader((F / 'ranking.csv').open(encoding='utf-8'))}
    players = f['players']
    assert len(players) == len(card) == 582 and {p['name'] for p in players.values()} == set(card) == old, '名單與 card 不一致'
    assert f['predNewVsPipeline'] < 1e-12 and all(p['ok'] for p in players.values()), 'features 檔內核對未過'
    win = {int(r['playerId']): r for r in csv.DictReader(WIN_CSV.open(encoding='utf-8'))}
    bad = [k for k, p in players.items() if int(k) not in win or float(win[int(k)]['L']) != p['L'] or float(win[int(k)]['a']) != p['a'] or not p['has']]
    assert not bad, f'L／a 與 usage-window-c82.csv 不同：{bad[:5]}'
    an = dict(f['anchors'])
    for k in ('PR1', 'PR50', 'PR99'):
        assert abs(an[k] - summ['anchors'][k]) < 1e-4, f'{k} 與 card 0.2.10j summary 不同'
    an['PR90'], an['PR95'] = summ['anchors']['PR90'], summ['anchors']['PR95']
    off = [n for n, r in card.items() if abs(float(OM.ovr_map([float(r['gRepl'])], an)[0]) - float(r['ovr'])) > 0.06]
    assert not off, f'card 0.2.10j ovr 用這組錨重現不了：{off[:5]}'
    payload = {'coef': f['coef'], 'rRepl': f['rRepl'], 'anchors': an, 'players': players}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    doc = {
        'doc': 'card-0.2.12 用人層（tovSkill 改持球時間重擬合後的係數）：L、a＝2025-26 季末（c=82）四季窗口值（window11.py）；係數同 card-0.2.10d 的 KAU 重擬合；r_repl、PR1／PR50／PR99 用新池重取，PR90／PR95 同 E-188 S3 的取法；'
               'players[].ovrCard 是 0.2.12 的 OVR（run_c4_live 不讀）。賽中端 L、a、y、v、has 每天用當下窗口覆蓋（run_c4_live.usage_features），d 沿用此檔（b8＝0，不進模型）',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L（b8_ydL＝0；has=True）；has=False → predNew = p',
        'check': {'n': len(players), 'ovrMapMismatch': 0, 'predNewVsPipeline': f['predNewVsPipeline'], 'hasFalse': sum(not p['has'] for p in players.values())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {'card-0.2.12c-w246 ranking.csv': sha(G / 'ranking.csv'), 'card-0.2.12c-w246 usage-features.json': sha(FEAT),
                         'card-0.2.12c-fit246 usage-window-c82-246.csv': sha(WIN_CSV), 'ovr_map.py': sha(OM_PY)},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'payloadSha256': doc['payloadSha256'], 'n': len(players), 'anchors': an}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
