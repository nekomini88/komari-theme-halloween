"""从真实渲染截图生成发布预览图（主题包里的 preview.png）。

底座原 preview.png 是 1280x640（2:1）→ 从渲染图中央按 2:1 裁切再缩放，保持同一规格。
用法：python3 scripts/make_preview.py <渲染图> [输出]
"""
import pathlib
import sys

from PIL import Image

src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/ha-cyan2.png')
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else
                   '/root/komari-halloween/dist/preview.png')
ROOT = pathlib.Path('/root/komari-halloween')
TARGET = (1280, 640)          # 与底座原预览图一致

im = Image.open(src).convert('RGB')
w, h = im.size
want = TARGET[0] / TARGET[1]
if w / h > want:              # 太宽 → 裁左右
    nw = int(h * want)
    box = ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
else:                         # 太高 → 裁上下（略偏上，保住顶栏与主面板）
    nh = int(w / want)
    top = int((h - nh) * 0.35)
    box = (0, top, w, top + nh)
im = im.crop(box).resize(TARGET, Image.LANCZOS)

out.parent.mkdir(parents=True, exist_ok=True)
im.save(out, optimize=True)
(ROOT / 'preview.png').write_bytes(out.read_bytes())      # 仓库根也要一份（工作流从根打包）
print(f'预览图 {out} {im.size[0]}x{im.size[1]} {out.stat().st_size // 1024}KB')
print(f'仓库根 preview.png 同步 {((ROOT / "preview.png").stat().st_size) // 1024}KB')
