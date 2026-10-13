"""从用户给的参考图里真实取色：量化主色 + 分区域取样 + 亮度分层。

不做主观命名，只输出可核对的数值，供配色方案使用。
"""
import pathlib
from collections import Counter

from PIL import Image

SRC = pathlib.Path('/root/.hermes/cache/images/img_f15d64663b80.png')
OUT = pathlib.Path('/root/komari-halloween/docs/ref-palette.png')


def name_of(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx / 255
    s = 0 if mx == 0 else (mx - mn) / mx
    if s < 0.12:
        return '中性灰' if v < 0.5 else '中性亮'
    h = 0
    if mx == r:
        h = (60 * ((g - b) / (mx - mn))) % 360
    elif mx == g:
        h = 60 * ((b - r) / (mx - mn)) + 120
    else:
        h = 60 * ((r - g) / (mx - mn)) + 240
    names = [(15, '红'), (45, '橙'), (70, '黄'), (105, '黄绿'), (150, '绿'),
             (185, '青'), (210, '青蓝'), (255, '蓝'), (290, '蓝紫'), (330, '紫'), (361, '粉红')]
    for lim, nm in names:
        if h < lim:
            return nm
    return '?'


def main():
    im = Image.open(SRC).convert('RGB')
    w, h = im.size
    print(f'参考图: {SRC.name}  {w}x{h}')

    # ① 全图量化主色（16 色）
    print('\n① 全图主色（轮廓法量化 16 色，按占比排序）')
    q = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = Counter(q.getdata())
    total = w * h
    for idx, cnt in counts.most_common(16):
        r, g, b = pal[idx * 3:idx * 3 + 3]
        print(f'   #{r:02x}{g:02x}{b:02x}  {cnt / total * 100:5.1f}%  RGB({r:3},{g:3},{b:3})  {name_of(r, g, b)}  '
              f'亮度{(0.299 * r + 0.587 * g + 0.114 * b):.0f}')

    # ② 分区域取样（了解各区域色相：天空/月亮/地面光/人物）
    regions = {
        '顶部夜空+满月': (0, 0, w, int(h * 0.22)),
        '中部城堡剪影': (0, int(h * 0.22), w, int(h * 0.55)),
        '左下枯枝雾': (0, int(h * 0.55), int(w * 0.45), h),
        '右下人物+地面辉光': (int(w * 0.45), int(h * 0.55), w, h),
    }
    print('\n② 分区域平均色 / 主色')
    for nm, box in regions.items():
        crop = im.crop(box)
        px = list(crop.getdata())
        ar = sum(p[0] for p in px) // len(px)
        ag = sum(p[1] for p in px) // len(px)
        ab = sum(p[2] for p in px) // len(px)
        q2 = crop.quantize(colors=4)
        p2 = q2.getpalette()
        top = Counter(q2.getdata()).most_common(2)
        tops = ' '.join(f'#{p2[i * 3]:02x}{p2[i * 3 + 1]:02x}{p2[i * 3 + 2]:02x}' for i, _ in top)
        print(f'   {nm:16} 平均 #{ar:02x}{ag:02x}{ab:02x} {name_of(ar, ag, ab):4}  主色 {tops}')

    # ③ 亮度分层（做界面底色/面板/文字的取色依据）
    print('\n③ 亮度分层（按亮度排序，供"底/面/强调/文字"四层取色）')
    greys = sorted(px, key=lambda p: 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2])
    for q_, lab in ((0.02, '最暗 2%'), (0.18, '暗部 18%'), (0.5, '中位'),
                    (0.82, '亮部 82%'), (0.98, '最亮 2%')):
        r, g, b = greys[int(len(greys) * q_)]
        print(f'   {lab:9} #{r:02x}{g:02x}{b:02x}  亮度{(0.299 * r + 0.587 * g + 0.114 * b):.0f}  {name_of(r, g, b)}')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.resize((320, int(h * 320 / w))).save(OUT)
    print(f'\n缩略图: {OUT}')


if __name__ == '__main__':
    main()
