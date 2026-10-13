"""Komari-Halloween 立绘 v3：**忠实还原用户参考图**（v2 把帽子做错了）。

v2 的错误（用户指出「帽子不要换 就是原图的满意」）：
  用户原图：南瓜头绅士戴一顶**普通黑色高礼帽**（南瓜灯脸是他的**头**）+ 金发少女戴**黑色尖顶女巫帽**。
  v2 出的图：把南瓜灯脸**画在了帽子上** ✗ = 把帽子换成了别的东西 ✗。
本版修正：帽子保持普通黑色高礼帽（只有暗色帽带，帽身无任何图案），南瓜灯脸回到"戴帽者的头部"。

管线同 scripts/gen_art.py（一号一出口、取件用 imageId、失败换号重试）。
用法：nohup python3 -u scripts/gen_art_v3.py > /tmp/gen_art_v3.log 2>&1 &
"""
import json
import time
from pathlib import Path

import requests

BASE = 'https://listenhub.ai'
OUT = Path('/root/komari-halloween/art-raw/v3-faithful')
OUT.mkdir(parents=True, exist_ok=True)
GENLOG = OUT / 'GEN-LOG.json'
MODEL = 'gpt-image-2'

ACCOUNTS = [
    {'name': '1009', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1009.txt',
     'proxy': None, 'exit': '192.3.193.180'},
    {'name': '1007', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1007.txt',
     'proxy': {'http': 'http://127.0.0.1:8891', 'https': 'http://127.0.0.1:8891'}, 'exit': '216.23.120.14'},
    {'name': 'lhjp', 'token': '/root/.hermes/secrets/listenhub_token_lhjp.txt',
     'proxy': {'http': 'http://127.0.0.1:8891', 'https': 'http://127.0.0.1:8891'}, 'exit': '216.23.120.14'},
    {'name': '1008', 'token': '/root/.hermes/secrets/listenhub_token_nekomini1008.txt',
     'proxy': {'http': 'socks5h://127.0.0.1:8892', 'https': 'socks5h://127.0.0.1:8892'}, 'exit': '62.84.174.226'},
]

PALETTE = ("deep teal Halloween night: background #0d1c24, teal rim light #2f9ea6 and #4fc6cb, "
           "pale moon cream #eadbbf, ghost green #7fd4a2 — no purple, no magenta")

# 关键差别（务必写死）：帽子是普通黑色高礼帽，南瓜脸在"头上"而不在帽子上
HAT = ("a plain black tall top hat with only a dark hatband, the hat surface completely plain "
       "with NO pumpkin face, NO face pattern, NO lantern on the hat")

P1 = f"""Anime illustration, cozy Halloween night. A tall elegant gentleman in a long black coat with
white ruffled collar and cuffs, bowing down kindly: his head is a glowing carved jack-o-lantern
(triangular eyes, triangular nose, jagged smiling mouth, warm candlelight inside the pumpkin — the
pumpkin IS his head, sitting under the brim of his hat). He wears {HAT}. Facing him, a small sweet
girl with long pale blonde hair, wearing a black pointed witch hat with a wide brim and a black
lace-trimmed dress, looks up at him with a gentle smile. A black cat sits nearby. Background: an
enormous pale full moon, gothic cathedral spires with ghost-green glowing windows, thin spider webs
strung between broken arches, bats crossing the sky, cold green mist on the ground. {PALETTE}.
Hand-painted anime style, soft cel shading, clean lineart, half-body composition, no text, no
letters, no watermark, no logo, no signature. 16:9 landscape"""

P2 = f"""Anime illustration, cozy Halloween night, same two characters full of joy: the tall gentleman
in the long black coat, his head a glowing carved jack-o-lantern grinning widely with bright warm light
inside the pumpkin, {HAT}, raising one hand in greeting; the small sweet girl with long pale blonde
hair and a black pointed witch hat laughing happily beside him, the black cat arching its back.
Background: the enormous pale full moon, gothic spires with ghost-green window light, spider webs,
bats, cold green ground mist. {PALETTE}. Hand-painted anime style, soft cel shading, clean lineart,
half-body composition, no text, no letters, no watermark, no logo, no signature. 16:9 landscape"""

P3 = f"""Anime illustration, wide cinematic Halloween night banner: on the right, a tall gentleman in a
long black coat with a white ruffled collar, his head a glowing carved jack-o-lantern, wearing {HAT},
stands beside a small blonde girl in a black pointed witch hat and black lace dress, a black cat at
their feet; behind them an enormous pale full moon, gothic cathedral spires with ghost-green glowing
windows receding into mist, thin spider webs, bats overhead, cold green ground glow. {PALETTE}.
Hand-painted anime style, calm and atmospheric, the left half mostly empty, no text, no letters, no
watermark, no logo, no signature. 16:9 landscape"""

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
