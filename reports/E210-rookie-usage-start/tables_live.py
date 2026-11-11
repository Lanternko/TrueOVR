"""E-210 3、4：live 完整主流程 B0 對 U1（同一份資料）。輸出 live-tables.json、live-tables.md。
3：2026 屆每人 OVR／Δ（Δ＝現在 OVR − 起點；兩版的起點都＝R-096 曲線值）。4：老將所有欄位逐字相同（除 rank）。"""
import csv, json, statistics as S, sys, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
H = Path(__file__).resolve().parent


def load(v):
    det = {int(x['playerId']): x for x in json.load(open(H / f'live-{v}/rookies-detail.json', encoding='utf-8'))}
    rk = list(csv.DictReader(open(H / f'live-{v}/ranking.csv', encoding='utf-8-sig')))
    return det, rk


dB, rB = load('B0')
dU, rU = load('U1')
start = {r['name']: r for r in csv.DictReader(open(H / 'start-u1.csv', encoding='utf-8'))}
md, out = [], {}
# ---- 4 老將
vetB = {r['playerId']: r for r in rB if int(r['playerId']) not in dB}
vetU = {r['playerId']: r for r in rU if int(r['playerId']) not in dU}
assert set(vetB) == set(vetU), 'vet sets differ'
cols = [c for c in rB[0] if c != 'rank']
diff_cells = sum(1 for pid in vetB for c in cols if vetB[pid][c] != vetU[pid][c])
rank_changed = sum(1 for pid in vetB if vetB[pid]['rank'] != vetU[pid]['rank'])
out['vets'] = {'n': len(vetB), 'columns': len(cols), 'cellsDiffer': diff_cells, 'rankChanged': rank_changed,
               'ovrBitIdentical': all(vetB[p]['ovr'] == vetU[p]['ovr'] for p in vetB)}
md.append('## 老將不受影響\n')
md.append(f"- 完整 live 主流程（老將＋新秀）B0 與 U1 各跑一次，同一份資料。老將 {len(vetB)} 人 × {len(cols)} 欄（除 rank）逐字比對：不同格數 **{diff_cells}**；OVR 欄位逐字相同：{out['vets']['ovrBitIdentical']}。")
md.append(f"- 名次（rank）欄位有 {rank_changed} 位老將不同：新秀 OVR 變動後插進排名的位置不同，不是老將自己的值變。")
# ---- 3 新秀
rows = []
for pid, d in dB.items():
    u = dU[pid]
    nm = d['name']
    T = float(start[nm]['target'])
    rr = next((r for r in rB if int(r['playerId']) == pid), None)
    rows.append({'name': nm, 'pick': d['pick'], 'N': d['N'], 'MIN26': float(rr['MIN26']) if rr else 0.0, 'T': T,
                 'ovrB0': d['ovr'], 'dB0': d['ovr'] - d['lastOVR'], 'ovrU1': u['ovr'], 'dU1': u['ovr'] - T,
                 'rankB0': d['rank'], 'rankU1': u['rank'], 'startCheckB0': d['lastOVR'] - T})
for r in rows:
    r['dB0_vsT'] = r['ovrB0'] - r['T']
out['rookies'] = rows
top15 = sorted(rows, key=lambda r: -r['ovrB0'])[:15]
g90 = [r for r in rows if r['MIN26'] >= 90]
sel = sorted({r['name']: r for r in top15 + g90}.values(), key=lambda r: -r['ovrB0'])
md.append('\n## 2026 屆新秀現況（資料同一份；Δ＝現在 − 起點，起點＝曲線值）\n')
md.append('| 球員 | 順位 | 場數 | 分鐘 | 起點 | B0 OVR | B0 Δ | U1 OVR | U1 Δ | 名次 B0 → U1 | 備註 |\n|---|---|---|---|---|---|---|---|---|---|---|')
for r in sel:
    tag = []
    if r in top15:
        tag.append('B0 前15')
    if r['MIN26'] >= 90:
        tag.append('≥90分鐘')
    md.append(f"| {r['name']} | {r['pick']} | {r['N']} | {r['MIN26']:.0f} | {r['T']:.1f} | {r['ovrB0']:.1f} | {r['dB0']:+.1f} | {r['ovrU1']:.1f} | {r['dU1']:+.1f} | {r['rankB0']} → {r['rankU1']} | {'、'.join(tag)} |")
for lab, sub in (('≥90分鐘', g90), ('其餘有上場', [r for r in rows if 0 < r['MIN26'] < 90]), ('全部42人', rows)):
    if sub:
        md.append(f"\n- {lab}（{len(sub)} 人）平均 Δ：B0 {S.fmean(r['dB0'] for r in sub):+.1f} → U1 {S.fmean(r['dU1'] for r in sub):+.1f}")
out['summary'] = {lab: {'n': len(sub), 'B0': S.fmean(r['dB0'] for r in sub), 'U1': S.fmean(r['dU1'] for r in sub)} for lab, sub in (('g90', g90), ('all', rows)) if sub}
n0 = [r for r in rows if r['N'] == 0]
md.append(f"- 沒上場的 {len(n0)} 人：B0 與 U1 的 OVR 都＝起點（最大偏差 B0 {max(abs(r['ovrB0']-r['T']) for r in n0):.2f}、U1 {max(abs(r['ovrU1']-r['T']) for r in n0):.2f}）" if n0 else '')
sha = {p: hashlib.sha256(open(H / p, 'rb').read()).hexdigest() for p in ('live-B0/ranking.csv', 'live-U1/ranking.csv', 'live-B0/rookies-detail.json', 'live-U1/rookies-detail.json')}
out['sha'] = sha
json.dump(out, open(H / 'live-tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
(H / 'live-tables.md').write_text('\n'.join(md), encoding='utf-8')
print('\n'.join(md))
