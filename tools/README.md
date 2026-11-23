# 背景画廊（开发工具）

批量抽取真实论文图，同时产出 **SVG 与 PNG** 并嵌入一个 HTML 页面，用页面顶部的 **Light / Dark** 切换来预览它在浅色与深色网站上的实际效果。用来人工验收 `--background auto` 的判定是否合适。

这不是 skill 的一部分，不会随 `npx skills add` 或插件安装；它只是仓库里的开发/验收工具。

## 依赖

- Python 3.10+ 与 PyMuPDF、Pillow、numpy（见仓库 `requirements-dev.txt`）
- `poppler`（`pdftocairo`），抽取 SVG 时需要
- 画廊本身直接展示 SVG / PNG，不需要 `rsvg-convert`；只有 `check_border.py` 检查 SVG 时才需要 librsvg

## 快速开始

```bash
# 1. 写清单（每行一条）
cat > /tmp/manifest.txt <<'EOF'
/tmp/fa.pdf      2  1
/tmp/flash2.pdf  10 4  57.8,366,554.2,700
/tmp/ppo.pdf     5  1  60,455,535,600
EOF

# 2. 生成画廊
python tools/background_gallery.py /tmp/manifest.txt --out /tmp/auto-gallery

# 3. 查看
open /tmp/auto-gallery/gallery.html
# 或
python -m http.server -d /tmp/auto-gallery 8000
# 浏览 http://localhost:8000/gallery.html
```

仓库里的示例清单：`tools/background_gallery.example.txt`，其中注释写好了 PDF 的下载命令。

## 清单格式

```text
# 注释行以 # 开头
<pdf> <page> <fig> [x0,y0,x1,y1]
```

- `pdf`：本地 PDF 路径。相对路径按**清单文件所在目录**解析；
- `page`：从 1 开始的页码；
- `fig`：Figure 编号，支持 `3.1` 这种章节编号；
- 第四个字段：可选的 `--clip` 矩形，单位 PDF 点，适合双栏 / 表格 / 算法伪代码。

## 输出结构

```text
/tmp/auto-gallery/
├── gallery.html
├── fa-p2-f1/
│   ├── extracted.svg     # 按 --background 抽取的 SVG
│   ├── transparent.svg   # 强制透明底，用于对照
│   ├── extracted.png     # PNG 产物（默认 200 dpi）
│   ├── log-svg.txt
│   ├── log-transparent.txt
│   └── log-png.txt
└── ...
```

目录名规则：`<pdf 文件名>-p<页码>-f<图号>[-clip]`。

## 怎么读页面

页面顶部只有 **Light / Dark** 两个按钮，切换整页主题（背景与文字颜色）。SVG、透明 SVG、PNG 固定并排展示，不做产物切换。

页面顶部还会展示 **auto 判定规则**；每张卡片在属性卡片下方给出本条的实际判定依据，例如：

```text
background 判定：不透明 0.15 < 0.50，暗墨 0.41 ≥ 0.05 → white（透明画布默认）
```

这样不用去翻 log 就知道为什么选了白底、深底或保留原底。

图片都是抽取结果本身，不是重新排版的截图。透明 SVG 会跟随页面背景变化——这就是读者在浅色 / 深色网站上看到的效果。

```text
[Light] [Dark]

fa-p2-f1  [white]
page 2 · fig 1 · /tmp/fa/fa.pdf
┌──────────── PDF 原图属性（居中卡片）────────────┐
│ 图区尺寸 · 图内内容 · 内嵌位图 · 背景判定 …       │
└──────────────────────────────────────────────────┘
             ↓                  ↓                  ↓
┌──────────┬──────────┬──────────┐
│ SVG      │ 透明 SVG  │ PNG      │
└──────────┴──────────┴──────────┘
▸ extractor log
```

- **透明 SVG**：切到 Dark 时透明区域透出深色，黑色文字可能看不清——这正是需要 `--background auto` 的原因；切回 Light 又恢复正常，两者对比即可确认画布是否透明；
- **带底色的图像**（auto 判定为 white / dark / keep）：无论页面主题是什么，图都保持自身底色；
- **SVG vs PNG**：SVG 是矢量、可缩放；PNG 是位图，按 `--dpi` 渲染。并排模式最容易看出清晰度与体积差异。

想对照「不加底」的原始状态：

```bash
python tools/background_gallery.py /tmp/manifest.txt --background transparent --out /tmp/auto-gallery-transparent
```

判定徽章：

| 徽章 | 含义 | 怎么看 |
|---|---|---|
| `white` | auto 补了白底 | 切到 Light / Dark，图都保持白底 |
| `dark` | auto 补了深底 `#0f172a` | 图自身是深色块，浅色字正常 |
| `keep` | 论文自带底色，未覆盖 | 图保持原有底色 |
| `transparent` | 未加底 | 切到 Dark 时若文字看不清，说明需要加底 |
| `failed` | 抽取失败 | 展开 log 查看错误 |

## 属性面板

**每张产物图下方**以 caption 样式列出该输出自身的属性：

| 产物 | 行内属性 |
|---|---|
| SVG（当前背景） | 文件大小 · viewBox 尺寸 · 内嵌位图数 · 填充色数 · `background=` |
| SVG（透明底） | 同上，`background=transparent` |
| PNG | 文件大小 · 像素尺寸 · 色彩模式 · dpi · `background=` |

图片行上方居中展示 **「PDF 原图属性」** 卡片，卡片下方用箭头指向对应的产物，记录源文件信息：

| 分组 | 内容 |
|---|---|
| 图区尺寸 | 宽 × 高（pt / in） |
| 图内内容 | 文本行数、矢量绘图数、内嵌位图对象数量 |
| 内嵌位图像素 | 每个位图对象的像素尺寸（SVG 中的 `<image>` 可能重复引用同一对象） |
| 背景 | 自带白色 / 深色 / 彩色底或透明，不透明比例、背景亮度、墨色亮度、暗墨与亮墨占比 |

这些值直接来自 PDF 与输出文件，不依赖 `background` 判定；刷新/重跑后可以拿来对比同一张图在不同抽取参数下的变化。

验收标准：分别在 Light 与 Dark 下看一遍，**两种页面主题里文字都要可读**。透明画布重点看 Dark；发现不适配的，记录 PDF/页码/图号，再用 `--background white` 或 `dark` 强制验证。

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--out DIR` | `/tmp/auto-gallery` | 输出目录 |
| `--background` | `auto` | `auto` / `white` / `dark` / `transparent` |
| `--dpi` | `200` | PNG 预览的渲染 dpi（300 更清晰但更慢） |
| `--strict` | 关 | 有失败条目时以退出码 1 结束 |

## 和其他验证方式的分工

| 目的 | 手段 |
|---|---|
| 判定逻辑不回归 | `tests/test_background.py`（自动断言） |
| 少量代表性效果展示 | `docs/examples/`、`docs/comparison/` |
| 大批真实论文的人工验收 | 本工具生成的画廊 |

画廊输出放在 `/tmp` 即可，不要提交进仓库。
