"""线上真站验收（只读）：渲染 127.0.0.1:25774 + 控制台报错 + 点位亮度 + 浅底清点。

与 mock 验收分开：mock 只能证明构建正确，不能证明**真实 Komari 里**渲染正确。
"""
import pathlib
import re

from PIL import Image
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:25774/'
SHOT = pathlib.Path('/tmp/ha-live.png')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='networkidle', timeout=60000)
    pg.wait_for_timeout(7000)

    stats = pg.evaluate("""() => {
      const pm = getComputedStyle(document.body).backgroundColor.match(/\\(([\\d.]+), ?([\\d.]+), ?([\\d.]+)/) || [0,'13','28','36'];
      const light = [];
      for (const e of document.querySelectorAll('*')) {
        const r = e.getBoundingClientRect();
        if (r.width < 120 || r.height < 80) continue;
        const m = getComputedStyle(e).backgroundColor.match(/rgba?\\(([\\d.]+), ?([\\d.]+), ?([\\d.]+)(?:, ?([\\d.]+))?\\)/);
        if (!m) continue;
        const a = m[4] === undefined ? 1 : +m[4];
        const c = [1,2,3].map(i => +pm[i] + (+m[i] - +pm[i]) * a);
        const lum = 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
        if (lum > 150) light.push(String(e.className).slice(0,36) + ' ' + Math.round(lum));
      }
      return {light, cards: document.querySelectorAll('[class*="card"]').length,
              decor: [...document.querySelectorAll('[class*="ha-"]')].length,
              brand: (document.body.innerText.match(/Komari-Halloween/g) || []).length,
              skin: !!document.getElementById('ha-skin')};
    }""")
    pg.screenshot(path=str(SHOT))
    im = Image.open(SHOT).convert('RGB')
    print(f'线上截图 {SHOT} {im.size[0]}x{im.size[1]}')
    print(f'  皮肤层注入: {"✓" if stats["skin"] else "✗"}   装饰节点: {stats["decor"]}')
    print(f'  品牌文本命中 Komari-Halloween: {stats["brand"]} 处')
    print(f'  浅底大面积元素: {len(stats["light"])} 个' + (f' → {stats["light"][:3]}' if stats['light'] else ' ✓'))
    print(f'  控制台报错: {len(errs)} 处' + (f' → {errs[:2]}' if errs else ' ✓'))
    for nm, (x, y) in {'页面底': (24, 24), '左栏': (48, 450), '右栏': (1552, 450), '主区': (800, 700)}.items():
        r, g, b_ = im.getpixel((min(x, im.size[0] - 1), min(y, im.size[1] - 1)))
        print(f'   {nm:6} RGB({r:3},{g:3},{b_:3}) 亮度{0.299*r+0.587*g+0.114*b_:5.1f} {"青" if b_ >= r else "暖"}')
    b.close()
