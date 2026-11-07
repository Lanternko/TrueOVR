"""復出老將補卡（2026-11-04 使用者要求「滑動窗口跳過受傷賽季，拿更早的季當最近」）：
2025-26 沒有先驗卡（整季受傷／在國外／兩人合約）、但本季有名單的老將，原本被「先驗卡門檻」擋掉，只進 no-prior.csv。
做法：以 prior-2025-26-card0212c.json 為底，補上這些人最近一季的 v5 卡（2024-25 優先，沒有就 2023-24）。
  - 能力值只當窗口的「起點」：8 項窗口屬性、long、creation、MPG、用人層本來就由 window8／10／11 用四季逐場資料重算，
    先驗卡的值只影響窗口沒蓋到的欄位（onBall／help／stamina／physique／pressure）。
  - observed.MIN 設 0：不進百分位池（pr_mask＝MIN≥500）、不進同位置 MIN 加權平均；真實分鐘留在 sample.min。
  - RAPM（rapm-T6.csv）沒有這些人的列 → poss＝0 → 不套防守加成／align／封頂（跟新秀一樣）。
  - 0.2.12c 才有的欄位（foulDraw／presDisplay／foulDisc／gravity）用中性值；窗口與引力模組會蓋掉。
用法：python -I -B -X utf8 reports/ovr-inseason-2026-27/live/build_returning_vet_prior.py"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
V5 = HERE.parent / 'v5/data'
PNR = __import__('os').environ.get('PNR', '1') != '0'   # 0.2.13：底換 prior-2025-26-card0213.json，pnr＝pnr_live 的窗口值（c=0，跳過沒打的季）；PNR=0 重現 0.2.12c 的 rv 檔
BASE = HERE / ('prior-2025-26-card0213.json' if PNR else '_retired/prior-2025-26-card0212c.json')
OUT = HERE / ('prior-2025-26-card0213-rv.json' if PNR else '_retired/prior-2025-26-card0212c-rv.json')
NOPRIOR = HERE / '2026-11-02/no-prior.csv'     # 凍結候選名單（2026-11-02 的 no-prior.csv）
SEASONS = ('2024-25', '2023-24')
MIN_V5_MIN = 800        # 樣本太小（Beekman 473 分鐘）窗口只剩雜訊，不補；只是樣本量門檻，不看結果
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    d = json.loads(BASE.read_text(encoding='utf-8'))
    have = {p['playerId'] for p in d['players']}
    rookies = {p['playerId'] for p in json.loads((HERE / 'rookie-prior-2026.json').read_text(encoding='utf-8'))['players']}
    cands = [int(r['playerId']) for r in csv.DictReader(NOPRIOR.open(encoding='utf-8'))]
    if PNR:   # 2026-11-02/no-prior.csv 之後被每日流程覆寫，名單改取 0.2.12c rv 檔凍結的 returningVets（同一批人）
        cands = [r['playerId'] for r in json.loads((HERE / '_retired/prior-2025-26-card0212c-rv.json').read_text(encoding='utf-8'))['returningVets']]
    v5 = {s: {p['playerId']: p for p in json.loads((V5 / f'prior-{s}-v5.json').read_text(encoding='utf-8'))['players']} for s in SEASONS}
    added, skipped = [], []
    if PNR:
        sys.path.insert(0, str(HERE))
        import win_len
        win_len.install()
        import pnr_live as PL
        pv, _ = PL.live(0.0, None, cands, cur=False)
    for pid in cands:
        if pid in have or pid in rookies:
            continue
        pick = next(((s, v5[s][pid]) for s in SEASONS if pid in v5[s] and v5[s][pid]['sample']['min'] >= MIN_V5_MIN), None)
        if pick is None:
            skipped.append(pid)
            continue
        s, src = pick
        p = json.loads(json.dumps(src))
        p['age'] = None
        p['e2'] = None
        p['observed']['MIN'] = 0.0
        p.update({'foulDraw': 70.0, 'presDisplay': 70.0, 'foulDisc': 70.0, 'gravity': 70.0, 'gravityImputed': 1, 'topMissing': 0,
                  'rvSource': s, 'rvMin': src['sample']['min'],
                  'rvMpg': round(src['sample']['min'] / src['sample']['gp'], 3)})   # lastOVR 基準用的舊季 MPG（observed.MIN 設 0 後 MIN／GP 變 0）
        if PNR:
            p['pnr'] = pv[pid]['pnr'] if pid in pv else 70.0
        d['players'].append(p)
        added.append((pid, p['name'], s, src['sample']['min']))
    d['returningVets'] = [{'playerId': a[0], 'name': a[1], 'season': a[2], 'min': a[3]} for a in added]
    d['note'] = '復出老將補卡版：' + d['note']
    d['sources']['base0213' if PNR else 'base0212c'] = {'file': 'reports/ovr-inseason-2026-27/live/' + BASE.name, 'sha256': sha(BASE)}
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'out': str(OUT), 'added': added, 'noHistory': skipped}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
