"""量测成片：浅底元素清点 + 关键点位像素亮度。用法：python3 measure.py <截图路径>"""
import sys
from PIL import Image
from playwright.sync_api import sync_playwright

shot = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ha-v3.png'

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000})
    pg.goto('http://127.0.0.1:2599/', wait_until='networkidle', timeout=60000)
    pg.wait_for_timeout(6000)
    res = pg.evaluate("""() => {
      const out = [];
      for (const e of document.querySelectorAll('*')) {
        const r = e.getBoundingClientRect();
        if (r.width < 120 || r.height < 80) continue;
        const bg = getComputedStyle(e).backgroundColor;
        const m = bg.match(/rgba?\\(([\\d.]+), ?([\\d.]+), ?([\\d.]+)(?:, ?([\\d.]+))?\\)/);
        if (!m) continue;
        // 按 alpha 合成到 body 底色上再判亮度：低透明度不该被当成浅底（实测 0.02 误报）
        const pm = getComputedStyle(document.body).backgroundColor.match(/\\(([\\d.]+), ?([\\d.]+), ?([\\d.]+)/) || [0, '13', '28', '36'];
        const a = m[4] === undefined ? 1 : +m[4];
        const comp = [1, 2, 3].map(i => +pm[i] + (+m[i] - +pm[i]) * a);
        const lum = 0.2126 * comp[0] + 0.7152 * comp[1] + 0.0722 * comp[2];
        if (lum > 150) out.push({cls: String(e.className).slice(0, 40), bg, w: Math.round(r.width), h: Math.round(r.height), lum: Math.round(lum)});
      }
      return out;
    }""")
    print(f'[DOM] 浅底大面积元素: {len(res)} 个')
    for r in res[:8]:
        print(f"    {r['cls'][:36]:36} {r['bg']:26} {r['w']}x{r['h']} lum={r['lum']}")
    b.close()

print(f'\n[像素] {shot}')
try:
    im = Image.open(shot).convert('RGB')
    W, H = im.size
    for name, x, y in [('顶栏', 800, 30), ('左侧栏中部', 110, 500), ('右侧栏中部', 1480, 480),
                       ('中央主区', 800, 520), ('底部统计', 800, 950), ('页面最左', 12, 500)]:
        if x < W and y < H:
            r, g, blue = im.getpixel((x, y))
            L = round(0.2126 * r + 0.7152 * g + 0.0722 * blue)
            tag = '浅 ✗' if L > 150 else ('中' if L > 90 else '深 ✓')
            print(f'  {name:12} rgb({r:3},{g:3},{blue:3}) 亮度 {L:3} {tag}')
except FileNotFoundError:
    print('  截图不存在')
