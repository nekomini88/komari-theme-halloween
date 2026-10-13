"""枚举底座里所有「高亮度 rgba 面」—— 这些是绕过 CSS 变量的硬编码浅底，置换的主要目标。"""
import pathlib
import re
from collections import Counter

BASE = pathlib.Path('/root/komari-halloween/src-base/index.html')
html = BASE.read_text(encoding='utf-8')

# 只分析 style 块（避免把角色图 data-uri / JS 里的数值算进来）
styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)
css = '\n'.join(styles)

def lum(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

pat = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)')
rows = []
for m in pat.finditer(css):
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a = float(m.group(4)) if m.group(4) else 1.0
    L = lum(r, g, b)
    if L > 170:                      # 高亮度 = 浅底/浅面
        rows.append((m.group(0).replace(' ', ''), L, a))

cnt = Counter(x[0] for x in rows)
print(f'高亮度(>170) rgba 写法共 {len(rows)} 处，去重 {len(cnt)} 种：\n')
for val, n in cnt.most_common(40):
    L = lum(*[int(x) for x in pat.match(val).groups()[:3]])
    print(f'  {val:32} × {n:3}  亮度 {L:5.1f}')

print('\n=== 高亮度十六进制（style 块内）===')
hexes = Counter(x.lower() for x in re.findall(r'#[0-9a-fA-F]{6}\b', css))
for h, n in hexes.most_common(30):
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    L = lum(r, g, b)
    if L > 170:
        print(f'  {h:10} × {n:3}  亮度 {L:5.1f}')
