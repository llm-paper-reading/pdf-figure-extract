---
name: pdf-figure-extract
description: 从论文 PDF 中安全抽取 Figure 为 PNG/SVG，保证不贴边裁剪、不含论文自带 caption、可校验。用于把 arXiv/会议 PDF 中的架构图、曲线图、流程图抽取到静态站点或文档的图片目录。触发场景：用户说"从论文抽取 Figure N"、"裁一张论文图"、"把 PDF 里的架构图拿出来"、"论文图片 404 / 撕裂 / 被切边"。
license: MIT
compatibility: Requires Python 3.10+ with PyMuPDF, Pillow and numpy; poppler (pdftocairo) for SVG; librsvg (rsvg-convert) for SVG border checks.
metadata:
  author: xu-song
  version: "1.1.0"
  repository: https://github.com/llm-paper-reading/pdf-figure-extract
---

# PDF Figure Extract

## 解决什么问题

从论文 PDF 抽图时最常见的三类失败，本 skill 都有对应防线：

| 问题 | 成因 | 本 skill 的防线 |
|---|---|---|
| 图被切边（顶/底文字切一半、坐标轴没截全） | 手估 bbox + 无校验 | 贴边自动检测 + 强制安全边距 |
| 图 404 / 撕裂 | 只写了引用、没产出文件 | 提取后立即落盘并自检 |
| 把论文自带 caption / 正文 / 页眉裁进图 | 整页截图式提取 | caption 锚定 + clip 内容核查 |

## 流程（四步，不要跳步）

1. **下载 PDF 放进临时目录**，不要在站点图片目录里直接操作。
2. **定位 Figure**：用 `pdftotext -layout` 或 fitz 找到 `Figure N:` 所在页与 caption 位置。
3. **抽取**（脚本在本 skill 目录的 `scripts/` 下）：
   - 矢量图（架构/示意图优先）→ `extract_svg.py` 转 SVG，任意缩放不失真；
   - 位图 / 通用 → `extract_fig.py` PNG 模式，自动注入白边。
4. **校验**：
   - 文件存在；
   - 四边墨迹比例检查（> 0.3% 即 WARN，退出码 3，**不许忽略**）；
   - `check_border.py` 对目录批量复检；
   - `get_text(clip=...)` 确认 clip 内无 caption / 页眉 / 正文文本；
   - 浏览器打开目标页面肉眼确认（**提交前必须**，脚本 OK 不等于内容裁对了）。

**禁止**：
- 无校验直接覆盖线上图片；
- 批量替换后不看页面；
- 把 PDF 的 caption 留在图里；
- 跳过人工核对就提交。

## 三段脚本

前置依赖见 frontmatter 的 `compatibility`：Python 3.10+（pymupdf、Pillow、numpy）、poppler（`pdftocairo`）、librsvg（`rsvg-convert`，仅检查 SVG 时需要）。

```bash
# PNG：caption 锚定 + 自动白边 + 边界自检；fig 支持 "1" 或章节编号 "3.1"
extract_fig.py <pdf> <page> <fig> <out.png> [--dpi 300] [--margin-pt 20] [--clip x0,y0,x1,y1]

# SVG：矢量提取（经 pdftocairo）
extract_svg.py <pdf> <page> <fig> <out.svg> [--margin-pt 20] [--clip x0,y0,x1,y1]

# 边界检查：PNG/JPG/SVG/目录批量，背景感知（深色图不误报）
check_border.py <path...>
```

`--clip` 单位为 PDF 点（pt），指定时跳过 caption 锚定，用于双栏排版与特殊图注格式。

## 已知坑与对策（实战沉淀）

| 症状 | 原因 | 对策 |
|---|---|---|
| caption 锚定报 not found | 图注是 `Figure 1 \|`、`Fig. 1:`、`Figure 1 Illustration`（无冒号）、`Figure 1.1` | `--clip` 显式矩形；章节编号可直接作 `fig` 参数 |
| 混入正文 / 另一栏的图 | 双栏排版，caption 上方启发式跨栏误并 | `--clip` 按栏指定：先打印块布局（`get_text('dict')` blocks + `get_drawings()`）确认栏的 x 区间 |
| 混入页眉（TECHNICAL REPORT、页码） | 图区 union 伸到 y < 40 | clip 上界压到页眉底线之下，落盘前 `get_text(clip=...)` 核查 |
| 混入 caption 末行 | 图与 caption 间隙 < 6pt | 列出 caption 顶上方 20pt 内的文本行 y 坐标，clip 下界取图内容底 +1~2pt |
| 底部 0.1–0.5% 残余墨迹 | 轴标签/tick 贴近下界（SVG 无法注入白边） | clip 下放 1~2pt；仍不行改 PNG 模式 |
| 图内图例/标签被切（check_border 报底部墨迹但 get_text 无 caption） | 图例文字是 TXT 块，不属于 drawings，union 漏掉（如 FlashAttention Fig 1 的 "Inner Loop" 标签） | v1.0.0 起 figure_clip 自动并入「图区与 caption 之间的文本行」；旧版用 `--clip` 手动扩展 |
| 表格被当图裁入 | 图与 Table 同页 | 打印块布局区分 `type==1`（IMG）与 TXT，clip 只圈目标 |
| 网页截图贴边 | 来源非 PDF | 本 skill 不适用，重新截图 |

## 核对清单

- [ ] 目标文件存在且替换后旧文件已删（避免 PNG/SVG 双份）
- [ ] `check_border.py` 全绿
- [ ] clip 内无 caption / 页眉 / 正文
- [ ] 页面上图片正常渲染、无裂图
- [ ] 图注由站点自身样式控制（不携带 PDF caption）
