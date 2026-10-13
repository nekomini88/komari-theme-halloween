# Komari-Halloween

万圣节主题 · **紫夜底 + 南瓜橙 + 烛光暖黄** · 甜系女巫立绘 + 动漫 HUD 监控面板，用于 [Komari](https://github.com/komari-monitor/komari) 探针面板。

> **血统说明**：本主题基于 [saladinxp/komari-nano-muse](https://github.com/saladinxp/komari-nano-muse)（作者 **Miuler**）改造。
> 上游只发布编译产物、未附许可证，本仓库为私人改造与自用；界面内保留原作者署名，若上游作者有异议请联系删除。

## 改了什么

| 维度 | NanoMuse（上游） | Komari-Halloween（本主题） |
| --- | --- | --- |
| 底色 | 明亮冷白 + 青蓝 HUD | 紫夜底（`#150c26`）+ 南瓜橙（`#f97316`）+ 烛光暖黄（`#fcd34d`） |
| 立绘 | 白发耳机少女（亮底） | 甜系黑发女巫 + 星空帽 + 黑猫 + 南瓜灯 + 紫夜城堡（gpt-image-2 出图） |
| 氛围 | 轻科幻 | 满月 / 蛛网 / 蝙蝠群 / 南瓜灯 / 雾气 / 烛光呼吸动效 |
| 文案 | NANO MUSE 呼号 | 万圣节口吻；页脚保留原作者署名 |
| 色调档 | 亮 / 暗 | 深夜（默认）/ 迟暮（切到 LIGHT 时），**两档都是夜**，不会出现白面板 |

## 安装

1. 从 [Releases](../../releases) 下载 `komari-theme-Komari-Halloween-v*.zip`；
2. Komari 后台 → 主题管理 → 上传主题包；
3. 「设置 → 主题」中选择 `Komari-Halloween` 并保存（设置组名为「Komari-Halloween 设置」）。

## 构建（本仓库为产物仓，改动源码的方式见下）

```
src-base/index.html            底座：NanoMuse 原版单文件（留档，永不修改）
src-base/komari-theme.base.json 底座清单（留档）
src-skin/halloween.css         皮肤层：变量覆盖 + 装饰 + 动效
art-raw/                       gpt-image-2 出的原图
scripts/build.py               构建：配色重映射 + 文案 + 注入皮肤 → dist/
scripts/prepare_art.py         把出图对齐成主题需要的尺寸
scripts/mock_komari.py         本地模拟 Komari 接口，用于不触碰线上实例的验收
scripts/contrast_audit.py      WCAG 对比度审计（交付前必跑，须 0 个不达标）
scripts/measure.py             量测：浅底元素清点 + 关键点位像素亮度
```

```bash
python3 scripts/build.py                 # 产出 dist/
python3 scripts/mock_komari.py 2599 &    # 本地预览 http://127.0.0.1:2599/
python3 scripts/contrast_audit.py        # 可读性审计
python3 scripts/prepare_art.py           # 出图对齐（有新的 art-raw/*.png 时）
```

### 配色为什么用「规则计算」而不是手工色表

底座是亮色主题，压缩样式里有 **110 种高亮度色写法（196 处）绕过 CSS 变量**。手工列表既写不全也会漏，
因此 `scripts/build.py` 按「亮度 + 色相倾向」分类计算：**面（surface）压到紫夜、冷亮强调（accent）换成暖橙**，
alpha 原样保留；再由 `src-skin/halloween.css` 用同名变量覆盖覆盖主要层级。

## 交付验收（每次改动都要过）

- `scripts/contrast_audit.py` → 低于 WCAG AA 的文本元素 **0 个**
- `scripts/measure.py` → 亮度 > 150 的大面积元素 **0 个**（不能出现白面板）
- 浏览器控制台 **0 报错**
- 与上一版做像素级对比，确认只有预期区域变化
