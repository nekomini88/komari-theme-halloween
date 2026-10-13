"""Komari-Halloween 立绘 v2（深青方案）：按用户新参考图出图，走 ListenHub gpt-image-2。

参考图要点（用户 2026-10-13 提供）：提帽子的黑衣绅士 + 金发少女 · 深青夜空 · 巨大满月 ·
哥特尖塔与绿窗 · 蝙蝠 · 蛛网 · 地面冷绿辉光。本主题只需**单主体**立绘位，故取
「金发少女 + 那顶点着南瓜灯的黑色高礼帽」这一意象，其余按参考图的夜色与配色还原。

管线复用 /root/v2_art/gen_halloween_art.py（提交/轮询/取件、一号一出口、取件用 imageId）。
用法：nohup python3 scripts/gen_art.py > /tmp/gen_art.log 2>&1 &
"""
import json
import time
from pathlib import Path

import requests

BASE = 'https://listenhub.ai'
OUT = Path('/root/komari-halloween/art-raw/v2-teal')
OUT.mkdir(parents=True, exist_ok=True)
GENLOG = OUT / 'GEN-LOG.json'
MODEL = 'gpt-image-2'

ACCOUNTS = [
    {'name': '1009', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1009.txt',
     'proxy': None, 'exit': '192.3.193.180'},
    {'name': '1007', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1007.txt',
     'proxy': {'http': 'http://127.0.0.1:8891', 'https': 'http://127.0.0.1:8891'}, 'exit': '216.23.120.14'},
    {'name': '1008', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1008.txt',
     'proxy': {'http': 'socks5h://127.0.0.1:8892', 'https': 'socks5h://127.0.0.1:8892'}, 'exit': '62.84.174.226'},
    {'name': 'lhjp', 'token': '/root/.hermes/secrets/listenhub_token_lhjp.txt',
     'proxy': {'http': 'http://127.0.0.1:8891', 'https': 'http://127.0.0.1:8891'}, 'exit': '216.23.120.14'},
    {'name': 'lhde', 'token': '/root/.hermes/secrets/listenhub_token_lhde.txt',
     'proxy': {'http': 'socks5h://127.0.0.1:8892', 'https': 'socks5h://127.0.0.1:8892'}, 'exit': '62.84.174.226'},
]

# 配色口径（与 src-skin/halloween.css 一致）：深青底 / 青绿强调 / 月光米白 / 鬼火绿
PALETTE = ("deep teal night palette: background #0d1c24, glow and rim light #2f9ea6 and #4fc6cb, "
           "pale moon cream #eadbbf, ghost green #7fd4a2 — no purple, no magenta, no orange")

P1 = f"""Anime illustration, cozy Halloween night mood. A sweet young girl with long pale blonde hair,
wearing a black lace-trimmed dress, lifting a tall black top hat with both hands — the hat's crown
glows from within with a carved jack-o-lantern face, warm candlelight spilling out. A small black cat
sits beside her. Behind her: a huge pale full moon, gothic cathedral spires with faint ghost-green
glowing windows, thin spider webs strung between ruined arches, bats scattered across the sky, cold
green ground glow rising like mist. {PALETTE}. Hand-painted anime style, soft cel shading, clean lines,
half-body composition placed on the right side with generous empty space on the left, no text, no
letters, no watermark, no logo, no signature, no border. 16:9 landscape"""

P2 = f"""Anime illustration, cozy Halloween night mood, same sweet young blonde girl in the black
lace-trimmed dress, now with bright open eyes and a lively happy expression, both arms raised holding
the tall black top hat high overhead, its carved jack-o-lantern face blazing with warm light that lights
up her face. The small black cat stretches up on its hind legs toward the hat. Behind her: the huge pale
full moon, gothic spires with ghost-green windows, bats in flight, spider webs, cold green mist. {PALETTE}.
Hand-painted anime style, soft cel shading, clean lines, half-body composition on the right side with
generous empty space on the left, no text, no letters, no watermark, no logo, no signature. 16:9 landscape"""

P3 = f"""Anime illustration, wide cinematic Halloween night banner. A small girl in a black dress with
pale blonde hair stands holding a glowing carved jack-o-lantern top hat, beside a black cat and a stone
gothic arch, under an enormous pale full moon; gothic cathedral spires and ghost-green glowing windows
recede into mist, bats and thin spider webs overhead, cold green ground glow. {PALETTE}. Hand-painted
anime style, calm and atmospheric, the left half left mostly empty for a title, no text, no letters,
no watermark, no logo, no signature. 16:9 landscape"""

TARGETS = [{'key': 'char', 'prompt': P1},
           {'key': 'char-awake', 'prompt': P2},
           {'key': 'og', 'prompt': P3}]


def sess(acc):
    s = requests.Session()
    s.trust_env = False
    if acc['proxy']:
        s.proxies = acc['proxy']
    return s


def submit(acc, body, timeout=90):
    s = sess(acc)
    token = Path(acc['token']).read_text().strip()
    r = s.post(BASE + '/api/listenhub/v1/images', json=body, timeout=timeout,
               headers={'Authorization': 'Bearer ' + token})
    if r.status_code == 429:
        return None, '429:' + r.headers.get('Retry-After', '?')
    try:
        d = r.json()
    except Exception:
        return None, f'badjson:{r.status_code}'
    if d.get('code') == 26004:
        return None, '26004:quota'
    iid = (d.get('data') or {}).get('imageId')
    return (iid, 'ok') if iid else (None, f'no-id:{str(d)[:80]}')


def _first_url(o):
    if isinstance(o, str):
        return o if o.startswith('http') else None
    if isinstance(o, dict):
        for v in o.values():
            u = _first_url(v)
            if u:
                return u
    if isinstance(o, list):
        for v in o:
            u = _first_url(v)
            if u:
                return u
    return None


def poll(acc, iid, tries=60, gap=4):
    s = sess(acc)
    token = Path(acc['token']).read_text().strip()
    for _ in range(tries):
        try:
            r = s.get(f'{BASE}/api/listenhub/v1/images/{iid}', timeout=60,
                      headers={'Authorization': 'Bearer ' + token})
            txt = r.text
        except Exception:
            time.sleep(gap)
            continue
        if '"success"' in txt or '"status": "success"' in txt:
            url = _first_url(json.loads(txt))
            if url:
                data = sess(acc).get(url, timeout=180).content
                return data if len(data) > 1024 else None
        time.sleep(gap)
    return None


def gen(target, attempt_budget=3):
    body = {'prompt': target['prompt'], 'model': MODEL,
            'aspectRatio': '16:9', 'imageSize': '2K', 'language': 'en'}
    attempts = []
    for attempt in range(1, attempt_budget + 1):
        for acc in ACCOUNTS:
            t0 = time.time()
            iid, why = submit(acc, body)
            if not iid:
                attempts.append({'account': acc['name'], 'exit': acc['exit'],
                                 'result': why, 'attempt': attempt})
                print(f"    [{target['key']}] {acc['name']} 提交失败: {why}", flush=True)
                if why.startswith('429'):
                    try:
                        time.sleep(min(int(why.split(':')[1]), 300))
                    except Exception:
                        time.sleep(30)
                continue
            data = poll(acc, iid)
            dt = round(time.time() - t0, 1)
            if data:
                p = OUT / f"{target['key']}.png"
                p.write_bytes(data)
                from PIL import Image
                w, h = Image.open(p).size
                print(f"  ✓ {target['key']}.png {w}x{h} {len(data)//1024}KB "
                      f"via {acc['name']}/{acc['exit']} {dt}s", flush=True)
                attempts.append({'account': acc['name'], 'exit': acc['exit'], 'result': 'ok',
                                 'attempt': attempt, 'iid': iid, 'seconds': dt,
                                 'kb': len(data) // 1024, 'file': p.name})
                return p.name, acc, dt, attempts
            attempts.append({'account': acc['name'], 'exit': acc['exit'],
                             'result': 'poll-fail', 'attempt': attempt, 'iid': iid, 'seconds': dt})
            print(f"    [{target['key']}] {acc['name']} 取件超时 {dt}s", flush=True)
        time.sleep(5)
    return None, None, None, attempts


def main():
    results = []
    for t in TARGETS:
        print(f"→ {t['key']}", flush=True)
        name, acc, dt, attempts = gen(t)
        results.append({'target': t['key'], 'file': name,
                        'account': acc['name'] if acc else None,
                        'exit': acc['exit'] if acc else None,
                        'prompt': t['prompt'], 'attempts': attempts})
        GENLOG.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    done = [r for r in results if r['file']]
    print(f"\n完成 {len(done)}/{len(results)} 张 → {OUT}", flush=True)


if __name__ == '__main__':
    main()
