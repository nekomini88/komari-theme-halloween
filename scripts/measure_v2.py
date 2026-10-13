"""量测 v2 成片：哪些元素仍是浅底 + 截图关键点位像素亮度。"""
from PIL import Image
from playwright.sync_api import sync_playwright

# ---- 1) DOM 侧：列出亮度 > 150 的大面积元素 ----
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
        const cs = getComputedStyle(e);
        const bg = cs.backgroundColor;
        const m = bg.match(/rgba?\\(([\\d.]+), ?([\\d.]+), ?([\\d.]+)/);
        if (!m) continue;
        const lum = 0.2126 * +m[1] + 0.7152 * +m[2] + 0.0722 * +m[3];
        if (lum > 150) out.push({cls: String(e.className).slice(0, 44), bg,
                                 w: Math.round(r.width), h: Math.round(r.height), lum: Math.round(lum)});
      }
      return out.slice(0, 14);
    }""")
    print(f'浅底元素（亮度>150 的大面积元素）: {len(res)} 个')
    for r in res:
        print(f"    {r['cls'][:40]:40} {r['bg']:24} {r['w']}x{r['h']} lum={r['lum']}")
    b.close()

# ---- 2) 像素侧：关键点位 ----
print('\n关键点位像素实测：')
im = Image.open('/tmp/ha-v2.png').convert('RGB')
W, H = im.size
pts = [('顶栏', 800, 30), ('左上 logo 区', 60, 40), ('左侧栏中部', 110, 500),
       ('左侧栏下部', 110, 780), ('中央主区', 800, 500), ('右侧栏中部', 1480, 480),
       ('底部统计栏', 800, 950), ('月亮处', 110, 160), ('页面最左', 12, 500)]
for name, x, y in pts:
    if x < W and y < H:
        r, g, blue = im.getpixel((x, y))
        lum = round(0.2126 * r + 0.7152 * g + 0.0722 * blue)
        tag = '浅 ✗' if lum > 150 else ('中' if lum > 90 else '深 ✓')
        print(f'  {name:12} rgb({r:3},{g:3},{blue:3}) 亮度 {lum:3}  {tag}')
