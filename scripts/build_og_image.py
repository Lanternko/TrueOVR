"""連結預覽縮圖（og:image）：1200×630，五格評分環＋TrueOVR 字樣。輸出 assets/og-image.png，發布時放 gh-pages 根目錄。

環的配色、角度與 season_nav.RING 相同（五格、亮四格薄荷綠）。字型用 Windows 內建微軟正黑體。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'og-image.png'
W, H, SS = 1200, 630, 2  # SS＝超取樣倍率
BG, PANEL, MINT, OFF, FG, MUTED = '#0b0e12', '#121820', '#3ddc97', '#1f2a26', '#f2f5f4', '#8b98a5'
FONT_BOLD, FONT_REG = r'C:\Windows\Fonts\msjhbd.ttc', r'C:\Windows\Fonts\msjh.ttc'


def ring(d, cx, cy, r, stroke):
    box = [cx - r, cy - r, cx + r, cy + r]
    seg, gap = 19.87 / 119.38 * 360, 4 / 119.38 * 360  # 同 SVG dasharray 的角度
    start = -86
    for i in range(5):
        a0 = start + i * (seg + gap)
        d.arc(box, a0, a0 + seg, fill=MINT if i < 4 else OFF, width=stroke)


def main():
    img = Image.new('RGB', (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    s = lambda v: int(v * SS)
    f = lambda path, size: ImageFont.truetype(path, s(size), index=0)

    # 右側淡淡的大環當背景裝飾
    deco = Image.new('RGB', img.size, BG)
    ring(ImageDraw.Draw(deco), s(1010), s(330), s(330), s(70))
    img = Image.blend(img, deco, 0.10)
    d = ImageDraw.Draw(img)

    # 主 logo 環
    cx, cy, r = 250, 315, 128
    ring(d, s(cx), s(cy), s(r), s(r * 9 / 19))

    # 文字
    x = 450
    d.text((s(x), s(215)), 'TrueOVR', font=f(FONT_BOLD, 118), fill=FG, anchor='ls')
    d.text((s(x + 4), s(290)), '球員能力值', font=f(FONT_BOLD, 54), fill=MINT, anchor='ls')
    d.text((s(x + 4), s(360)), 'NBA 球員評分・球隊戰力排行・賽程勝率', font=f(FONT_REG, 32), fill=MUTED, anchor='ls')
    d.rounded_rectangle([s(x + 4), s(410), s(x + 4 + 290), s(410 + 56)], radius=s(12), fill=PANEL, outline='#1e252e', width=s(2))
    d.text((s(x + 4 + 145), s(410 + 28)), 'trueovr.com', font=f(FONT_REG, 30), fill=FG, anchor='mm')

    OUT.parent.mkdir(exist_ok=True)
    img.resize((W, H), Image.LANCZOS).save(OUT, optimize=True)
    print(OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
