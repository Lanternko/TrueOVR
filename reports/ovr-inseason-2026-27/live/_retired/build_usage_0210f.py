raise SystemExit('已淘汰：本檔只供對照。重現請 checkout 當時 commit（見 live/CURRENT.json、_retired/README.md）')  # R-124 retired guard（0.2.10g 換 build_usage_0210g.py；用人層 L、a 改四季窗口）
"""card 0.2.10f 用人層（E-191b P1m）：ranking.csv／OVR 與 0.2.10e 逐位元組相同，所以用人特徵、係數、r_repl、錨點（含 PR90／PR95）全同 0.2.10e
（reports/card-0.2.10d/usage-features.json＋reports/card-0.2.10f/summary.json 的 anchors）；只換 sourceSha256 的卡名（card-0.2.10f ranking.csv）。
逐人核對：card-0.2.10f/ranking.csv 的 ovr＝ovr_map(gRepl)（差 ≤0.06，gRepl 只存 4 位小數）、與 card-0.2.10e/ranking.csv 逐位元組相同、名單與 0.2.10d 相同。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_usage_0210f.py → live/usage-2025-26-card0210f.json"""
import csv, hashlib, importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D, E, P = ROOT / 'reports/card-0.2.10d', ROOT / 'reports/card-0.2.10f', ROOT / 'reports/card-0.2.10e'
FEAT = D / 'usage-features.json'
OUT = HERE / 'usage-2025-26-card0210f.json'
OM_PY = ROOT / 'reports/card-0.2.10a+E188-ovr-top-scale/ovr_map.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    s = importlib.util.spec_from_file_location('ovr_map', OM_PY)
    OM = importlib.util.module_from_spec(s); s.loader.exec_module(OM)
    f = json.loads(FEAT.read_text(encoding='utf-8'))
    summ = json.loads((E / 'summary.json').read_text(encoding='utf-8'))
    assert sha(E / 'ranking.csv') == summ['ranking_csv_sha256'], 'card-0.2.10f ranking.csv sha256 與 summary 不符'
    assert (E / 'ranking.csv').read_bytes() == (P / 'ranking.csv').read_bytes(), 'card 0.2.10f ranking.csv 與 0.2.10e 不同'
    assert json.loads((P / 'summary.json').read_text(encoding='utf-8'))['sources_sha256']['reports/card-0.2.10d/ranking.csv'] == sha(D / 'ranking.csv'), 'card 0.2.10e 不是用現行 0.2.10d 建的'
    card = {r['name']: r for r in csv.DictReader((E / 'ranking.csv').open(encoding='utf-8'))}
    players = f['players']
    assert len(players) == len(card) == 582 and {p['name'] for p in players.values()} == set(card), '名單與 card 不一致'
    assert f['predNewVsPipeline'] < 1e-12 and all(p['ok'] for p in players.values()), 'features 檔內核對未過'
    an = dict(f['anchors'])
    for k in ('PR1', 'PR50', 'PR99'):
        assert abs(an[k] - summ['anchors'][k]) < 1e-4, f'{k} 與 card 0.2.10f summary 不同'
    an['PR90'], an['PR95'] = summ['anchors']['PR90'], summ['anchors']['PR95']
    off = [n for n, r in card.items() if abs(float(OM.ovr_map([float(r['gRepl'])], an)[0]) - float(r['ovr'])) > 0.06]
    assert not off, f'card 0.2.10f ovr 用這組錨重現不了：{off[:5]}'
    payload = {'coef': f['coef'], 'rRepl': f['rRepl'], 'anchors': an, 'players': players}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    doc = {
        'doc': 'card-0.2.10f 用人層：同 card-0.2.10e（card-0.2.10d 的 KAU 重擬合係數、r_repl、PR1／PR50／PR99；anchors 多 PR90／PR95，E-188 S3），ranking.csv 逐位元組相同；'
               'players[].ovrCard 仍是 0.2.10d 舊映射的值（run_c4_live 不讀）',
        'features': 'predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L（b8_ydL＝0；has=True）；has=False → predNew = p',
        'check': {'n': len(players), 'ovrMapMismatch': 0, 'predNewVsPipeline': f['predNewVsPipeline'], 'hasFalse': sum(not p['has'] for p in players.values())},
        'payloadSha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'sourceSha256': {'card-0.2.10f ranking.csv': sha(E / 'ranking.csv'), 'card-0.2.10d usage-features.json': sha(FEAT),
                         'ovr_map.py': sha(OM_PY)},
        **payload,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'payloadSha256': doc['payloadSha256'], 'n': len(players), 'anchors': an}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
