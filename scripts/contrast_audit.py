"""客观可读性审计：遍历页面文本元素，计算其与**有效背景**的 WCAG 对比度。

有效背景 = 沿祖先链找第一个非透明背景色，与之合成（含半透明叠加）。
输出低于 4.5:1（AA 正文）/ 3:1（大字）的元素清单。
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:2599/'

JS = r"""() => {
  const parse = c => {
    const m = String(c).match(/rgba?\(([\d.]+), ?([\d.]+), ?([\d.]+)(?:, ?([\d.]+))?\)/);
    return m ? {r:+m[1], g:+m[2], b:+m[3], a: m[4] === undefined ? 1 : +m[4]} : null;
  };
  const over = (fg, bg) => ({          // fg 叠在 bg 上
    r: fg.r*fg.a + bg.r*(1-fg.a),
    g: fg.g*fg.a + bg.g*(1-fg.a),
    b: fg.b*fg.a + bg.b*(1-fg.a), a: 1
  });
  const lum = c => {
    const f = v => { v/=255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(c.r) + 0.7152*f(c.g) + 0.0722*f(c.b);
  };
  const ratio = (a,b) => { const l1=lum(a), l2=lum(b); const hi=Math.max(l1,l2), lo=Math.min(l1,l2); return (hi+0.05)/(lo+0.05); };

  const effBg = el => {              // 累加整条祖先链的背景
    let stack = [], node = el;
    while (node && node !== document.documentElement.parentNode) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) stack.push(c);
      node = node.parentElement;
    }
    let base = {r:21, g:12, b:38, a:1};
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };

  const out = [];
  for (const el of document.querySelectorAll('*')) {
    const txt = (el.innerText || '').trim();
    if (!txt || el.children.length > 0) continue;     // 只看叶子文本节点
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 6 || r.top > innerHeight || r.left > innerWidth) continue;
    const cs = getComputedStyle(el);
    const fg = parse(cs.color);
    if (!fg || fg.a === 0) continue;
    const bg = effBg(el);
    const f = over(fg, bg);
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3.0 : 4.5;
    const cr = ratio(f, bg);
    if (cr < need) out.push({txt: txt.slice(0,24), size: Math.round(size), weight,
                             color: cs.color, cr: +cr.toFixed(2), need});
  }
  out.sort((a,b) => a.cr - b.cr);
  return {count: out.length, items: out.slice(0, 14)};
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1600, 'height': 1000})
    pg.goto(URL, wait_until='networkidle', timeout=60000)
    pg.wait_for_timeout(6000)
    res = pg.evaluate(JS)
    print(f'低于 AA 的文本元素: {res["count"]} 个')
    for it in res['items']:
        print(f"  对比度 {it['cr']:5.2f} (需 {it['need']}) {it['size']}px/{it['weight']} "
              f"{it['color']:24} «{it['txt']}»")
    b.close()
