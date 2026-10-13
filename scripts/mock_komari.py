"""本地模拟 Komari 接口 + 静态托管主题 dist —— 用于不触碰线上实例的前提下的验收。

用法：
  python3 scripts/mock_komari.py [port]          # 默认 2599
数据来源：
  scripts/api-fixtures/*.json（从真实实例只读抓取一次，形状一致）
"""
import json
import pathlib
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
FIX = ROOT / 'scripts' / 'api-fixtures'

MIME = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
        '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml',
        '.json': 'application/json', '.ico': 'image/x-icon', '.woff2': 'font/woff2'}


def fixture(name, default):
    p = FIX / f'{name}.json'
    if p.exists():
        return p.read_text(encoding='utf-8')
    return json.dumps(default)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静默
        pass

    def _send(self, code, body: bytes, ctype='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]

        # ---- API 模拟：优先用真实抓取的 fixture ----
        if path.startswith('/api/'):
            key = path.strip('/').replace('/', '_')
            p = FIX / f'{key}.json'
            if p.exists():
                return self._send(200, p.read_bytes())
            if path == '/api/nodes':
                return self._send(200, fixture('nodes', {'data': []}).encode())
            if path == '/api/public':
                return self._send(200, fixture('public', {}).encode())
            if path == '/api/me':
                return self._send(200, b'{"logged_in":false,"data":{}}')
            if path == '/api/clients':
                return self._send(200, b'{"data":{}}')
            # 记录类接口：空数组即可，图表会画不出但页面结构可验
            return self._send(200, b'{"data":[],"count":0}')

        # ---- 静态资源 ----
        rel = path.lstrip('/') or 'index.html'
        f = (DIST / rel).resolve()
        if not str(f).startswith(str(DIST.resolve())):
            return self._send(403, b'forbidden', 'text/plain')
        if f.is_dir():
            f = f / 'index.html'
        if not f.exists() and not f.suffix:
            f = DIST / 'index.html'      # SPA 回退
        if not f.exists():
            return self._send(404, b'not found', 'text/plain')
        ctype = MIME.get(f.suffix, 'application/octet-stream')
        self._send(200, f.read_bytes(), ctype)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 2599
    FIX.mkdir(parents=True, exist_ok=True)
    print(f'mock komari on http://127.0.0.1:{port}  (dist={DIST}, fixtures={FIX})')
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
