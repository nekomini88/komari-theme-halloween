"""分析 nano-muse 内联样式：CSS 变量全量、暗色模式结构、色值使用频次。"""
import pathlib
import re

h = pathlib.Path('/root/komari-halloween/dist/index.html').read_text(encoding='utf-8')
styles = re.findall(r'<style[^>]*>(.*?)</style>', h, re.S)
scripts = re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)
css = '\n'.join(styles)
print(f'内联 style: {len(styles)} 块 / {len(css)//1024}KB   script: {len(scripts)} 块 / {sum(len(s) for s in scripts)//1024}KB')

# ---- 1) 有没有暗色模式结构 ----
print('\n=== 暗色模式相关选择器 ===')
for pat in [r'\.dark[^{,]{0,40}', r'\[data-theme[^\]]{0,30}\]', r'prefers-color-scheme[^{]{0,30}',
            r'html\[class[^\]]{0,30}\]', r'body\[class[^\]]{0,30}\]']:
    hits = sorted(set(re.findall(pat, css)))
    if hits:
        print(f'  {pat} → {hits[:6]}')

# ---- 2) 变量定义（含 :root 与其它作用域）----
print('\n=== CSS 变量定义（按出现顺序，共去重后）===')
defs = re.findall(r'(--[a-zA-Z0-9-]+)\s*:\s*([^;}]{1,40})', css)
seen = {}
for k, v in defs:
    seen.setdefault(k, []).append(v.strip())
print(f'  变量名 {len(seen)} 个：')
for k, vals in sorted(seen.items()):
    uniq = list(dict.fromkeys(vals))
    print(f'    {k:28} = {" | ".join(uniq[:3])}')

# ---- 3) 色值频次（含 alpha 十六进制）----
print('\n=== 十六进制色值频次（前 25）===')
hexes = [x.lower() for x in re.findall(r'#[0-9a-fA-F]{3,8}\b', css)]
from collections import Counter
for c, n in Counter(hexes).most_common(25):
    print(f'    {c:10} × {n}')

# ---- 4) rgb/rgba 与 oklch 等 ----
print('\n=== 其它颜色写法 ===')
funcs = Counter(re.findall(r'(rgba?|oklch|hsl|color-mix)\s*\(', css))
print('   ', dict(funcs))
rgbas = [x for x in re.findall(r'rgba?\([^)]{5,40}\)', css)]
print('    rgba 样例:', list(dict.fromkeys(rgbas))[:8])

# ---- 5) 品牌文案位置（供换口吻）----
print('\n=== 品牌/文案字符串（HTML + JS 全文）===')
for s in ['NanoMuse', 'NANOMUSE', 'Nano Muse', 'Muse', 'Miuler', 'KOMARI MONITOR', 'SciMuse']:
    n = h.count(s)
    if n:
        print(f'    "{s}" × {n}')
