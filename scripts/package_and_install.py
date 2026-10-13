"""修正版打包与安装：用 zip CLI + 白名单路径，杜绝「把自己递归打进去」。

上一版 bug：shutil.make_archive(base_dir='.') 把 release/ 自身也归档了，
zip 一路膨胀到 6.4GB 还没停（自包含归档）。现在只打包主题必需的四个对象。
"""
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path('/root/komari-halloween')
DIST = ROOT / 'dist'
THEME_DIR = pathlib.Path('/home/project/komari/data/theme/Komari-Halloween')
VERSION = '1.2.0'


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f'  ✗ {cmd}\n    {(r.stderr or r.stdout)[:300]}')
    return r


def main():
    # ── 0) 清掉上一版失控的巨型 zip ─────────────────────────────────────
    for junk in (ROOT / 'release').glob('*.zip'):
        sz = junk.stat().st_size
        junk.unlink()
        print(f'  清掉旧 zip: {junk.name} ({sz // 1024 // 1024}MB)')

    # ── 1) 版本号写入清单 ────────────────────────────────────────────────
    mp = ROOT / 'komari-theme.json'
    man = json.loads(mp.read_text(encoding='utf-8'))
    man['version'] = VERSION
    mp.write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    # ── 2) git 提交（含工作流与 README）─────────────────────────────────
    sh = lambda c, **kw: run(c, cwd=ROOT, **kw)
    sh('git add -A')
    r = sh('git diff --cached --quiet || git commit -q -m '
           '"feat: Komari-Halloween v1.0.0 —— 万圣节主题（构建脚本/皮肤层/发版工作流/README）"', check=False)
    sha = sh('git rev-parse --short HEAD').stdout.strip() or 'nogit'
    print(f'  git HEAD: {sha}')

    # ── 3) 打包：只打 dist/ + 清单 + 预览图（白名单，绝不自包含）────────
    rel = ROOT / 'release'
    rel.mkdir(exist_ok=True)
    zipname = f'komari-theme-Komari-Halloween-v{VERSION}-{sha}.zip'
    stage = ROOT / 'tmp' / 'pack'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    shutil.copytree(DIST, stage / 'dist')
    shutil.copy2(mp, stage / 'komari-theme.json')
    shutil.copy2(ROOT / 'preview.png' if (ROOT / 'preview.png').exists() else DIST / 'preview.png',
                 stage / 'preview.png')
    run(f'zip -qr9 "{rel / zipname}" komari-theme.json preview.png dist', cwd=stage)
    zp = rel / zipname
    size_mb = zp.stat().st_size / 1024 / 1024
    print(f'  zip: {zp.name} {size_mb:.1f}MB')
    assert size_mb < 40, f'包体异常（{size_mb:.1f}MB），疑似自包含'

    # ── 4) 打包内容自检 ──────────────────────────────────────────────────
    listing = run(f'unzip -l "{zp}"').stdout
    n_dist = listing.count('dist/')
    print(f'  包内条目: {len(listing.splitlines()) - 3} 行，dist 下 {n_dist} 项')
    assert 'komari-theme.json' in listing and 'preview.png' in listing, '包内缺少清单或预览图'

    # ── 5) 装成未激活主题 ────────────────────────────────────────────────
    THEME_DIR.mkdir(parents=True, exist_ok=True)
    if (THEME_DIR / 'dist').exists():
        shutil.rmtree(THEME_DIR / 'dist')
    shutil.copytree(DIST, THEME_DIR / 'dist')
    shutil.copy2(mp, THEME_DIR / 'komari-theme.json')
    shutil.copy2(stage / 'preview.png', THEME_DIR / 'preview.png')
    print(f'  已装: {THEME_DIR}')

    # ── 6) 自检 ─────────────────────────────────────────────────────────
    print('\n自检：')
    print('  主题目录内容:', ', '.join(sorted(p.name for p in THEME_DIR.iterdir())))
    print('  清单:', man['name'], '|', man['short'], '|', man['version'])
    print('  当前激活主题:', run('sqlite3 /home/project/komari/data/komari.db '
                             '"select value from configs where key=\'theme\';"').stdout.strip(),
          '（应仍是 "Komari-Farmer" —— 本主题只装不激活）')


if __name__ == '__main__':
    main()
