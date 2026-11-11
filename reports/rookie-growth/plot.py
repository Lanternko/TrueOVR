"""畫新秀 OVR 成長曲線（growth.csv）＋2K 起點換算（twok-start.csv、twok-by-pick.json）。
2K → 本站 OVR 的換算：2K26 與 card 0.2.7 同季 572 人的分位數對應（只做顯示，不是上線算法）。
用法：python -I -X utf8 plot.py → growth-2025.png、growth-2026.png
"""
import bisect
import csv
import json
import math
import unicodedata
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
plt.rcParams['font.family'] = ['Microsoft JhengHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
BLUE, ORANGE, AQUA, INK, MUTED, GRID, SURF = '#2a78d6', '#eb6834', '#1baf7a', '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower() if c.isalnum())


def qmap_factory():
    card = {norm(r['name']): float(r['ovr']) for r in csv.DictReader(open(ROOT / 'reports/card-0.2.7/ranking.csv', encoding='utf-8-sig'))}
    pairs = [(int(r['2K26']), card[norm(r['name'])])
             for r in csv.DictReader(open(ROOT / 'reports/ovr-v55-2k27-compare/2k_yearly_ovr.csv', encoding='utf-8'))
             if r['2K26'] and norm(r['name']) in card]
    xs, ys = sorted(p[0] for p in pairs), sorted(p[1] for p in pairs)

    def qmap(v):
        lo, hi = bisect.bisect_left(xs, v), bisect.bisect_right(xs, v)
        q = (lo + hi) / 2 / len(xs)
        return ys[min(int(q * len(ys)), len(ys) - 1)]
    return qmap


def series(rows, name):
    rr = sorted((r for r in rows if r['name'] == name), key=lambda r: int(r['N']))
    e = [(int(r['N']), float(r['ovr_e116'])) for r in rr]
    o = [(int(r['N']), float(r['ovr_own'])) for r in rr if r['ovr_own']]
    end = next((float(r['seasonEnd']) for r in rr if r['seasonEnd']), None)
    return rr[0], e, o, end


def panel(ax, title, e, o, end, twok, xmax, ylim):
    ax.set_facecolor(SURF)
    ax.grid(True, color=GRID, lw=0.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    if end is not None:
        ax.axhline(end, color=MUTED, lw=1.2, ls=(0, (4, 3)))
    if o:
        ax.plot(*zip(*o), color=ORANGE, lw=1.4, alpha=0.9)
    ax.plot(*zip(*e), color=BLUE, lw=2.2, marker='o', ms=3.5, markeredgecolor=SURF, markeredgewidth=1)
    if twok is not None:
        ax.plot([0], [twok], marker='D', ms=8, color=AQUA, markeredgecolor=SURF, markeredgewidth=1.5, zorder=5)
    ax.set_title(title, fontsize=10, color=INK, loc='left')
    ax.set_xlim(-xmax * 0.03, xmax * 1.03)
    ax.set_ylim(*ylim)


def legend(fig, has_end):
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=BLUE, lw=2.2, marker='o', ms=4, label='網站上線的新秀版 OVR（起點＋自己數據加權）'),
         Line2D([], [], color=ORANGE, lw=1.4, label='只看他自己的數據'),
         Line2D([], [], color=AQUA, marker='D', ms=7, lw=0, label='2K 新秀評分換算的起點')]
    if has_end:
        h.append(Line2D([], [], color=MUTED, lw=1.2, ls=(0, (4, 3)), label='季末正式卡 OVR'))
    fig.legend(handles=h, loc='upper center', ncol=len(h), frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.955))


def main():
    rows = list(csv.DictReader(open(HERE / 'growth.csv', encoding='utf-8')))
    qmap = qmap_factory()
    tk = {r['name']: int(r['rookie2K']) for r in csv.DictReader(open(HERE / 'twok-start.csv', encoding='utf-8'))
          if r['draftYear'] == '2025'}
    fitp = json.load(open(HERE / 'twok-by-pick.json', encoding='utf-8'))['fitRecent3']

    # 2025 屆：前 5 順位＋季末特別高的 4 個非樂透
    names25 = ['Cooper Flagg', 'Dylan Harper', 'VJ Edgecombe', 'Kon Knueppel', 'Ace Bailey', 'Tre Johnson',
               'Collin Murray-Boyles', 'Cedric Coward', 'Nique Clifford', 'Sion James', 'Hugo González', 'Will Richard']
    r25 = [r for r in rows if r['class'] == '2025']
    fig, axs = plt.subplots(3, 4, figsize=(14, 9.5), sharex=True, sharey=True, facecolor=SURF)
    for ax, nm in zip(axs.flat, names25):
        head, e, o, end = series(r25, nm)
        t = qmap(tk[nm]) if nm in tk else None
        panel(ax, f'{nm}（第 {head["pick"]} 順位）', e, o, end, t, 82, (30, 100))
    for ax in axs[-1]:
        ax.set_xlabel('球隊第幾場（0＝開季前）', fontsize=9, color=MUTED)
    fig.suptitle('2025 屆新秀：2025-26 整季的 OVR 怎麼隨比賽變化', fontsize=14, color=INK, x=0.02, ha='left', y=0.995)
    legend(fig, True)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(HERE / 'growth-2025.png', dpi=130, facecolor=SURF)

    # 2026 屆：前 12 順位
    r26 = [r for r in rows if r['class'] == '2026']
    picks = sorted({(int(r['pick']), r['name']) for r in r26})[:12]
    fig, axs = plt.subplots(3, 4, figsize=(14, 9.5), sharex=True, sharey=True, facecolor=SURF)
    xmax = max(int(r['N']) for r in r26)
    for ax, (pk, nm) in zip(axs.flat, picks):
        head, e, o, end = series(r26, nm)
        t = qmap(round(fitp['a'] + fitp['b_lnPick'] * math.log(pk)))
        panel(ax, f'{nm}（第 {pk} 順位）', e, o, None, t, xmax, (30, 95))
        ax.set_xticks(range(0, xmax + 1))
    for ax in axs[-1]:
        ax.set_xlabel('球隊第幾場（0＝開季前）', fontsize=9, color=MUTED)
    fig.suptitle('2026 屆新秀：2026-27 開季到現在（2K 起點用近三屆同順位平均換算）', fontsize=14, color=INK, x=0.02, ha='left', y=0.995)
    legend(fig, False)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(HERE / 'growth-2026.png', dpi=130, facecolor=SURF)
    print('ok')


if __name__ == '__main__':
    main()
