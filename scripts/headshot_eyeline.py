"""名單頁頭像對齊眉線（使用者 2026-10-30：Cason Wallace 和 Chet 眉頭高度不同）。

NBA CDN 260x190 頭像每人拍攝構圖不同，底部對齊後眉毛高低不一。這裡用 OpenCV 臉部偵測
（YuNet）找每張照片的雙眼高度 y，寫到 assets/players/headshot-eyeline.json：
{id: 眼睛 y（0–190 像素）或 null＝偵測不到}。enrich_roster_viewer 依此把頭像往下移到同一條眼線
（只往下移、底部同量裁掉，所以球衣下緣還是貼齊橫幅）。

照片快取在 data/headshots/、模型在 data/models/（都不進 git，缺了自動下載）；已算過的 id 不重抓，新球員第一次發布時才下載。
用法：python -I scripts/headshot_eyeline.py 1631096 1641717 ...
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'players' / 'headshot-eyeline.json'
CACHE = ROOT / 'data' / 'headshots'
URL = 'https://cdn.nba.com/headshots/nba/latest/260x190/{}.png'
TARGET = 76  # 對齊到的眼線 y：582 人中只有 5 人眼睛更低（多是高聳髮型被拍得較低），中位數 59
MODEL = ROOT / 'data' / 'models' / 'face_detection_yunet_2023mar.onnx'
MODEL_URL = 'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'


def _fetch(url, f):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    f.write_bytes(urllib.request.urlopen(req, timeout=30).read())


def _eye_y(path):
    import cv2
    import numpy as np
    from PIL import Image
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        _fetch(MODEL_URL, MODEL)
    im = Image.open(path).convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bgr = cv2.cvtColor(np.array(Image.alpha_composite(bg, im).convert('RGB')), cv2.COLOR_RGB2BGR)
    det = cv2.FaceDetectorYN.create(str(MODEL), '', im.size, 0.6)
    _, faces = det.detect(bgr)
    if faces is None:
        return None
    f = max(faces, key=lambda r: r[2] * r[3])  # 欄位：x y w h 右眼xy 左眼xy …
    return round(float(f[5] + f[7]) / 2, 1)


def ensure(ids):
    """補算缺的 id，回傳完整對照表；抓不到照片的 id 不寫入，下次再試。"""
    table = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    todo = [str(i) for i in ids if str(i) not in table]
    if not todo:
        return table
    try:
        import cv2  # noqa: F401  python -I 看不到使用者 site-packages；沒裝就先不對齊這些人
    except ImportError:
        print(f'headshot_eyeline：沒有 cv2，{len(todo)} 人照舊底部對齊；用 python scripts/headshot_eyeline.py <id...> 補算', file=sys.stderr)
        return table
    CACHE.mkdir(parents=True, exist_ok=True)
    for pid in todo:
        f = CACHE / f'{pid}.png'
        if not f.exists():
            try:
                _fetch(URL.format(pid), f)
            except Exception as e:  # 沒網路或沒照片：頁面照舊底部對齊
                print(f'headshot {pid}: {e}', file=sys.stderr)
                continue
        table[pid] = _eye_y(f)
    OUT.write_text(json.dumps(dict(sorted(table.items(), key=lambda kv: int(kv[0]))), indent=0) + '\n', encoding='utf-8')
    return table


if __name__ == '__main__':
    t = ensure(sys.argv[1:])
    for i in sys.argv[1:]:
        print(i, t.get(i))
