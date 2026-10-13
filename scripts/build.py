"""Komari-Halloween 构建：原貌基线 + 万圣节皮肤 → dist/

设计：
  src-base/index.html            ← nano-muse 原版单文件（留档，永不修改）
  src-base/komari-theme.base.json ← 原版清单（留档）
  src-skin/halloween.css         ← 皮肤层（变量覆盖 + 装饰）
  → dist/index.html              ← 成品（幂等：每次从基线重做）
  → komari-theme.json            ← 改名后的清单

配色重映射为什么用「规则计算」而不是手工色表：
  底座是亮色主题，压缩样式里有 110 种高亮度色写法（196 处）绕过 CSS 变量。
  手工列表既写不全也会漏；改为按「亮度 + 色相倾向」分类计算：
  把「面（surface）」压到深青底、把「冷亮强调（accent）」调到青与月光米白，
  alpha 原样保留。目标配色来自参考图实测取色（scripts/extract_ref_palette.py）。

用法：python3 scripts/build.py
"""
import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / 'src-base'
SKIN = ROOT / 'src-skin'
DIST = ROOT / 'dist'

# ── 夜色目标（与 src-skin/halloween.css 的调色板保持一致，取自参考图）──
NIGHT_SURFACE = (14, 32, 40)      # 面：深青卡底（参考图 #152735）
NIGHT_TINT = (22, 52, 64)         # 冷浅「面」：青中间调（参考图 #173546）
NIGHT_WARM = (44, 38, 26)         # 暖浅「面」：月光暗部（低饱和暖，不抢青）
ACCENT_TEAL = (63, 184, 189)      # 冷亮强调 → 青（参考图中位 #298286 / #4d868a）
ACCENT_MOON = (234, 219, 191)     # 极亮 → 月光米白（参考图满月，占 7.8%）
INK_COOL_WHITE = (234, 246, 247)  # 纯白 → 冷白（文字仍是"白"，只是不刺眼）
MUTE_RATIO = 0.42                 # 中亮度暖/绿语义色的降饱和比例


def lum(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_cool(r, g, b):
    return b >= r + 8


def map_color(r, g, b):
    """按亮度与色相倾向决定去向。返回 (r,g,b) 或 None（保持原样）。"""
    L = lum(r, g, b)
    cool = is_cool(r, g, b)
    if L >= 250 and not cool:                 # 纯白 / 近纯白
        return INK_COOL_WHITE
    if L > 225:                               # 近白「面」
        return NIGHT_TINT if cool else NIGHT_WARM
    if 195 < L <= 225:                        # 亮「面」/ 冷浅灰
        return NIGHT_TINT if cool else NIGHT_WARM
    if 170 < L <= 195 and cool:               # 冷亮强调（青系）→ 青 / 月光
        return ACCENT_TEAL if L < 182 else ACCENT_MOON
    if 170 < L <= 195:                        # 暖亮（旧琥珀 / 绿）→ 月光米白
        return ACCENT_MOON
    if 90 < L <= 170 and not cool:             # 中亮度暖/绿语义色：保色相、降饱和
        grey = 0.299 * r + 0.587 * g + 0.114 * b
        return tuple(round(c + (grey - c) * MUTE_RATIO) for c in (r, g, b))
    return None                               # 其余不动（深色本就是夜色调）


RGBA_RE = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(,\s*[\d.]+\s*)?\)')
HEX_RE = re.compile(r'#([0-9a-fA-F]{6})\b')


def remap(text):
    stats = {}

    def _rgba(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        tail = m.group(4) or ''
        new = map_color(r, g, b)
        if new is None:
            return m.group(0)
        key = f'rgba({r},{g},{b}) → rgba({new[0]},{new[1]},{new[2]})'
        stats[key] = stats.get(key, 0) + 1
        return f'rgba({new[0]},{new[1]},{new[2]}{tail})'

    def _hex(m):
        h = m.group(1)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        new = map_color(r, g, b)
        if new is None:
            return m.group(0)
        key = f'#{h} → #{new[0]:02x}{new[1]:02x}{new[2]:02x}'
        stats[key] = stats.get(key, 0) + 1
        return '#%02x%02x%02x' % new

    text = RGBA_RE.sub(_rgba, text)
    text = HEX_RE.sub(_hex, text)
    return text, stats


# ── 文案换口吻：只替换「页面可见的品牌文本」，绝不碰标识符 ──────────────
COPY_MAP = [
    ('>NanoMuse · Miuler<', '>Komari-Halloween · Miuler<'),   # 页脚署名（保留原作者）
    ('>NanoMuse<', '>Komari-Halloween<'),
    ('NanoMuse</', 'Komari-Halloween</'),
]

# ── 装饰层 DOM（与 src-skin/halloween.css 对应；按参考图：满月/蛛网/蝙蝠/
# 哥特尖塔+绿窗/地面青辉）
DECOR = (
    '<div class="ha-fog" aria-hidden="true"></div>'
    '<div class="ha-web" aria-hidden="true"></div>'
    '<div class="ha-bats" aria-hidden="true"><i></i><i></i><i></i><i></i></div>'
    '<div class="ha-spire" aria-hidden="true"></div>'
    '<div class="ha-ghow" aria-hidden="true"></div>'
)


def main():
    assert (BASE / 'index.html').exists(), '缺少 src-base/index.html 基线'
    html = (BASE / 'index.html').read_text(encoding='utf-8')
    skin = (SKIN / 'halloween.css').read_text(encoding='utf-8')

    DIST.mkdir(exist_ok=True)

    # 1) 配色重映射（计算式）
    html, stats = remap(html)

    # 2) 文案换口吻
    copy_hits = {}
    for old, new in COPY_MAP:
        n = html.count(old)
        if n:
            html = html.replace(old, new)
            copy_hits[old] = n

    # 3) 注入皮肤层：样式 + 装饰 DOM
    style_tag = f'<style id="ha-skin">{skin}\n#app{{position:relative;z-index:1;}}</style>'
    html = html.replace('</head>', '</head>' + style_tag, 1)
    m = re.search(r'<body[^>]*>', html)
    assert m, '找不到 <body>'
    html = html[:m.end()] + DECOR + html[m.end():]

    (DIST / 'index.html').write_text(html, encoding='utf-8')

    # 4) 清单改名
    base_json = json.loads((BASE / 'komari-theme.base.json').read_text(encoding='utf-8'))
    manifest = dict(base_json)
    manifest.update({
        'name': 'Komari-Halloween',
        'short': 'Komari-Halloween',
        'description': '万圣节主题 · 深青底 + 青绿强调 + 月光米白 · 甜系女巫立绘 + 动漫 HUD 监控面板'
                       '（基于 NanoMuse 改造）',
        'url': 'https://github.com/nekomini88/komari-theme-halloween',
        'preview': 'preview.png',
        'author': 'Neko（基于 Miuler 的 NanoMuse 改造）',
    })
    (ROOT / 'komari-theme.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # 5) 报告
    total = sum(stats.values())
    print(f'配色重映射 {total} 处 / {len(stats)} 种（深青方案）：')
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:10]:
        print(f'    {k:44} × {v}')
    print(f'文案换口吻 {sum(copy_hits.values())} 处: {copy_hits or "（无匹配）"}')
    print(f'署名保留: {"✓ 仍是 Miuler" if "Miuler" in html else "✗ 丢失"}')
    decor_re = re.compile(r'class="(ha-[a-z]+)"')
    print(f'装饰层: {decor_re.findall(html)}')
    print(f'产出 dist/index.html {len(html) // 1024}KB')

    # 6) 资源同步（角色图等）
    for f in BASE.glob('*.png'):
        if f.name == 'char-source.png':
            continue
        tgt = DIST / f.name
        if not tgt.exists():
            shutil.copy2(f, tgt)


if __name__ == '__main__':
    main()
