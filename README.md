# pdf-figure-extract

[![Claude Skill](https://img.shields.io/badge/Claude-Code%20Skill-blueviolet)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

从论文 PDF 中安全抽取 Figure 为 **PNG / SVG** 的 [Claude Code skill](https://docs.claude.com/en/docs/claude-code/skills)。

杜绝抽图最常见的四类问题：

- ✂️ **贴边裁剪** —— 顶部/底部文字被切一半、坐标轴没截全
- 📰 **混入杂质** —— 论文自带 caption、正文段落、页眉被裁进图里
- 🔗 **双栏误判** —— 把另一栏的图或正文并进同一张图
- ❌ **图 404** —— 只写了引用没产出文件

## 安装

```bash
# 项目级安装（推荐，随仓库版本管理）
mkdir -p .claude/skills
git clone git@github.com:llm-paper-reading/pdf-figure-extract.git .claude/skills/pdf-figure-extract

# 或用户级安装（所有项目可用）
git clone git@github.com:llm-paper-reading/pdf-figure-extract.git ~/.claude/skills/pdf-figure-extract
```

## 依赖

| 依赖 | 用途 | 安装 |
|---|---|---|
| Python 3.10+ | 运行脚本 | — |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF 解析、渲染 | `pip install pymupdf pillow numpy` |
| [poppler](https://poppler.freedesktop.org/) | `pdftocairo` SVG 转换 | macOS: `brew install poppler` |
| [librsvg](https://gitlab.gnome.org/GNOME/librsvg) | `rsvg-convert`（仅 SVG 边界检查） | macOS: `brew install librsvg` |

## 使用

安装后对 Claude 说「从论文抽取 Figure 2」即可自动触发；也可直接调脚本：

```bash
cd /tmp && mkdir work && cd work
curl -sL -o paper.pdf "https://arxiv.org/pdf/2205.14135"

# 矢量图 → SVG（推荐，任意缩放不失真）
python <skill-dir>/scripts/extract_svg.py paper.pdf 2 1 fig1.svg

# 位图 → PNG（自动注入 1.2% 白边；FlashAttention 的 Figure 2 在第 6 页）
python <skill-dir>/scripts/extract_fig.py paper.pdf 6 2 fig2.png

# 双栏页 / 特殊图注（Figure 1 |、Fig. 1: 等）→ 显式矩形（pt）
# 例：vLLM 论文第 5 页右栏的 Figure 5
python <skill-dir>/scripts/extract_svg.py paper.pdf 5 5 fig5.svg --clip "318,40,560,168"

# 批量边界检查（PNG / JPG / SVG / 目录）
python <skill-dir>/scripts/check_border.py path/to/images/
```

每个脚本都内置自检：提取后立即检查四边墨迹比例，超阈值（0.3%）即以退出码 3 报 WARN，不会静默输出坏图。

## 工作原理

1. **caption 锚定**：以 `Figure N:` 图注文本行 bbox 为锚点，向「上」合并 image/vector 块并集作为图区，硬停在 caption 之前；
2. **安全边距**：PNG 模式注入 1.2% 白边后自检四边；SVG 模式校验 clip 矩形边界；
3. **背景感知**：边界检查以四角颜色估计背景，深色主题图不误报。

详细设计、已知坑与对策见 [SKILL.md](SKILL.md)。

## 已验证场景

- arXiv 单栏技术报告（DeepSeek-V3、Llama 3、Kimi K2/K3、GLM-5 等）
- 双栏论文（vLLM、Attention Is All You Need、KD 综述）
- 章节式图编号（GPT-3 的 `Figure 3.1`）
- 非冒号图注（`Figure 2 |`）
- 双子图拆分（同一 Figure 的左右子图独立提取）

## 不适用

- 网页 / 博客截图来源（非 PDF）：贴边只能重新截图；
- 跨页图：需手工处理。

## 测试

```bash
pip install -r requirements-dev.txt

# 离线单元 + 回归 + CLI 测试（合成 PDF 夹具，无需网络）
python -m pytest tests/ -q

# README 命令逐条冒烟（联网下载 arXiv PDF）
python -m pytest tests/test_readme_commands.py --net -q
```

测试分层：

- `tests/test_unit.py`：caption 锚定（含章节编号、无交叉误配）、边界墨迹检测（含深色背景不误报）、错误路径；
- `tests/test_regression.py`：历史 bug 回归（图内图例 TXT 块被切、两脚本 figure_clip 行为一致性）；
- `tests/test_cli.py`：CLI 退出码、`--clip` 跳过 caption 查找、PNG 白边注入、check_border 目录扫描；
- `tests/test_readme_commands.py`：README 示例命令原样执行（默认跳过，`--net` 开启）——README 页码写错这类问题由此拦截。

## License

[MIT](LICENSE)
