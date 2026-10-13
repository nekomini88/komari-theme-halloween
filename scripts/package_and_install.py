"""收尾：拼文案修正 → 建 git 仓 → 打包 zip → 装成未激活主题 → 自检。

产物：
  release/komari-theme-Komari-Halloween-v<ver>-<sha>.zip   可直接上传给 Komari
  /home/project/komari/data/theme/Komari-Halloween/        已装但**未激活**
"""
import json
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path('/root/komari-halloween')
DIST = ROOT / 'dist'
THEME_DIR = pathlib.Path('/home/project/komari/data/theme/Komari-Halloween')
VERSION = '1.0.0'


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f'  ✗ {cmd}\n    {r.stderr[:300]}')
    return r


def main():
    # ── 1) 文案修正：底座里的拼写错误（若存在）──────────────────────────
    idx = DIST / 'index.html'
    html = idx.read_text(encoding='utf-8')
    fixes = {'OUTGRESS': 'EGRESS', 'OUTGRES': 'EGRESS', 'Dowload': 'Download', 'Bandwitdh': 'Bandwidth'}
    applied = {}
    for bad, good in fixes.items():
        n = html.count(bad)
        if n:
            html = html.replace(bad, good)
            applied[bad] = (good, n)
    if applied:
        idx.write_text(html, encoding='utf-8')
        print('文案修正:', ', '.join(f'{k}→{v[0]}×{v[1]}' for k, v in applied.items()))
    else:
        print('文案修正: 无需修正')

    # ── 2) 版本号写入清单 ────────────────────────────────────────────────
    mp = ROOT / 'komari-theme.json'
    man = json.loads(mp.read_text(encoding='utf-8'))
    man['version'] = VERSION
    mp.write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # ── 3) git 初始化与提交 ──────────────────────────────────────────────
    (ROOT / '.gitignore').write_text(
        'node_modules/\n__pycache__/\n*.pyc\nscripts/api-fixtures/*.json\ntmp/\n', encoding='utf-8')
    if not (ROOT / '.git').exists():
        sh('git init -q -b main && git config user.name nekomini && '
           'git config user.email nekomini@users.noreply.github.com', cwd=ROOT)
    sh('git add -A && git commit -q -m "feat: Komari-Halloween v1.0.0 —— 基于 NanoMuse 的万圣节主题"', cwd=ROOT)
    sha = sh('git rev-parse --short HEAD', cwd=ROOT).stdout.strip() or 'nogit'
    print(f'  git: {sha}')

    # ── 4) 打包 zip（dist + 清单 + 预览图）──────────────────────────────
    rel = ROOT / 'release'
    rel.mkdir(exist_ok=True)
    for old in rel.glob('*.zip'):
        old.unlink()
    zipname = f'komari-theme-Komari-Halloween-v{VERSION}-{sha}'
    shutil.make_archive(str(rel / zipname), 'zip', root_dir=str(ROOT),
                        base_dir='.', verbose=False)
    zp = rel / f'{zipname}.zip'
    print(f'  zip: {zp.name} {zp.stat().st_size//1024//1024}MB')

    # ── 5) 装成未激活主题 ────────────────────────────────────────────────
    THEME_DIR.mkdir(parents=True, exist_ok=True)
    if (THEME_DIR / 'dist').exists():
        shutil.rmtree(THEME_DIR / 'dist')
    shutil.copytree(DIST, THEME_DIR / 'dist')
    shutil.copy2(mp, THEME_DIR / 'komari-theme.json')
    for extra in ('preview.png', 'preview-dashboard.jpg', 'preview-detail.jpg'):
        src = ROOT / extra
        if src.exists():
            shutil.copy2(src, THEME_DIR / extra)
    print(f'  已装到 {THEME_DIR}（未激活）')

    # ── 6) 自检 ─────────────────────────────────────────────────────────
    print('\n自检：')
    print('  主题目录:', ', '.join(sorted(p.name for p in THEME_DIR.iterdir())))
    print('  清单:', man['name'], '|', man['short'], '|', man['version'])
    print('  当前激活主题（应仍是 Komari-Farmer，未被改动）:',
          sh('sqlite3 /home/project/komari/data/komari.db "select value from configs where key=\'theme\';"'
             ).stdout.strip())
    print('  列表里可见的新主题:',
          sh("ls -d /home/project/komari/data/theme/*/ | xargs -n1 basename | tr '\\n' ' '").stdout.strip())


if __name__ == '__main__':
    main()
