"""渲染成片：截图 + 控制台报错收集 + 关键点位像素亮度。用法：
    python3 scripts/render.py [输出png] [宽 高]
"""
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ha-shot.png'
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1600
H = int(sys.argv[3]) if len(sys.argv) > 3 else 900
URL = 'http://127.0.0.1:2599/'

points = {
    '页面底(远角)': (24, 24),
    '左侧栏中部': (int(W * 0.03), int(H * 0.5)),
    '右侧栏中部': (int(W * 0.97), int(H * 0.5)),
    '主面板中央': (int(W * 0.5), int(H * 0.45)),
    '顶部栏': (int(W * 0.5), 26),
}

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='networkidle', timeout=60000)
    pg.wait_for_timeout(6000)
    pg.screenshot(path=out)
    im = Image.open(out).convert('RGB')
    print(f'截图: {out} {im.size[0]}x{im.size[1]}')
    print('关键点位像素亮度（越低越夜）:')
    for nm, (x, y) in points.items():
        r, g, b_ = im.getpixel((min(x, W - 1), min(y, H - 1)))
        L = 0.299 * r + 0.587 * g + 0.114 * b_
        tone = '青' if b_ >= r else '暖'
        print(f'   {nm:14} RGB({r:3},{g:3},{b_:3}) 亮度{L:5.1f} {tone}')
    print(f'控制台报错: {len(errs)} 处' + (f' → {errs[:3]}' if errs else ' ✓'))
    b.close()
