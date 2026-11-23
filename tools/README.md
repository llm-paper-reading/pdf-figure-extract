# 背景画廊（开发工具）

批量抽取真实论文图，把每张图同时渲染到**白底**和**深底**上，生成一个 HTML 页面，用来人工验收 `--background auto` 的判定是否合适。

这不是 skill 的一部分，不会随 `npx skills add` 或插件安装；它只是仓库里的开发/验收工具。

## 依赖

- Python 3.10+ 与 Pillow、PyMuPDF（见仓库 `requirements-dev.txt`）
- `rsvg-convert`：macOS `brew install librsvg`

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
│   ├── extracted.svg     # 实际抽取结果
│   ├── on-white.png      # 合成到白底
│   ├── on-dark.png       # 合成到深底
│   └── log.txt           # background=... ink_luma=... opaque=...
└── ...
```

目录名规则：`<pdf 文件名>-p<页码>-f<图号>[-clip]`。

## 怎么读页面

每个条目一张卡片，左右两栏分别是白底与深底的渲染结果：

```text
fa-p2-f1  [white]
page 2 · fig 1 · /tmp/fa/fa.pdf
┌──────────────┬──────────────┐
│ 渲染在白底     │ 渲染在深底     │
└──────────────┴──────────────┘
▸ extractor log
```

判定徽章：

| 徽章 | 含义 | 怎么看 |
|---|---|---|
| `white` | 自动补白底 | 深底预览里是一块白底图，黑字正常 |
| `dark` | 自动补深底 `#0f172a` | 白底预览里是深色块，浅色字正常 |
| `keep` | 论文自带底色，未覆盖 | 左右两版一致 |
| `transparent` | 使用 `--background transparent` | 两版底色不同，用于对比不加底的效果 |
| `failed` | 抽取或渲染失败 | 展开 log 查看错误 |

验收标准只有一条：**白底那侧不应有浅色字，深底那侧不应有深色字**。发现两边都难读的，记录 PDF/页码/图号，再用 `--background white` 或 `dark` 强制验证。

## 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--out DIR` | `/tmp/auto-gallery` | 输出目录 |
| `--background` | `auto` | `auto` / `white` / `dark` / `transparent` |
| `--width` | `1400` | 预览 PNG 宽度 |
| `--strict` | 关 | 有失败条目时以退出码 1 结束 |

## 和其他验证方式的分工

| 目的 | 手段 |
|---|---|
| 判定逻辑不回归 | `tests/test_background.py`（自动断言） |
| 少量代表性效果展示 | `docs/examples/`、`docs/comparison/` |
| 大批真实论文的人工验收 | 本工具生成的画廊 |

画廊输出放在 `/tmp` 即可，不要提交进仓库。
