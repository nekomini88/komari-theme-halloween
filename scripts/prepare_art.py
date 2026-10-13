"""把 gpt-image-2 出的万圣节插画对齐成主题需要的尺寸（drop-in 替换底座素材）。

原版尺寸：char.png 1024×687（右透水印式立绘）/ char-awake.png 1248×832 /
         og-image.png 1200×630 / preview.png 1280×640（preview 用截图生成，不走这里）

源目录优先用 art-raw/v2-teal（深青方案，按用户新参考图出图），没有才回落 art-raw。
"""
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path('/root/komari-halloween')
_V3 = ROOT / 'art-raw' / 'v3-faithful'
_V2 = ROOT / 'art-raw' / 'v2-teal'
# 优先级：v3-faithful（忠实还原参考图，帽子已修正）> v2-teal > art-raw
ART = _V3 if (_V3 / 'char.png').exists() else (_V2 if (_V2 / 'char.png').exists() else ROOT / 'art-raw')


def fit(src_path, size, out_path):
    im = Image.open(src_path).convert('RGB')
    W, H = im.size
    tw, th = size
    r = tw / th
    if W / H > r:                      # 原图更宽 → 裁两侧
        nw = int(H * r)
        box = ((W - nw) // 2, 0, (W + nw) // 2, H)
    else:                              # 原图更高 → 裁上下
        nh = int(W / r)
        box = (0, (H - nh) // 2, W, (H + nh) // 2)
    out = im.crop(box).resize(size, Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, optimize=True)
    print(f'  {src_path.name} {im.size} → {out_path.name} {size} {out_path.stat().st_size//1024}KB')
    return out


def main():
    src = ART / 'char.png'
    if not src.exists():
        print('还没有 art-raw/char.png')
        return
    fit(src, (1024, 687), ROOT / 'dist' / 'char.png')
    fit(src, (1200, 630), ROOT / 'dist' / 'og-image.png')
    aw = ART / 'char-awake.png'
    if aw.exists():
        fit(aw, (1248, 832), ROOT / 'dist' / 'char-awake.png')
    else:
        print('  （char-awake 尚未生成，暂用同一张派生）')
        fit(src, (1248, 832), ROOT / 'dist' / 'char-awake.png')


if __name__ == '__main__':
    main()
