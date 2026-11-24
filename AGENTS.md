# AGENTS.md

本仓库既是一个可被 **任何 Agent Skills 客户端**（Claude Code、Codex、Cursor、Cline、Gemini CLI 等）加载的技能，也是一个可安装的 **plugin 包**。本文件给在本仓库里干活的编码 agent 看。

## 目录结构

```
pdf-figure-extract/
├── plugin.json                        # 通用 Agent Plugins 清单（OpenAI/Codex 等）
├── .claude-plugin/
│   ├── plugin.json                    # Claude Code 插件清单
│   └── marketplace.json               # 自托管 marketplace 清单
├── skills/pdf-figure-extract/         # 技能本体（唯一真源）
│   ├── SKILL.md
│   ├── agents/openai.yaml             # Codex/ChatGPT 展示元数据（可选）
│   └── scripts/                       # 抽图与边界检查脚本
├── docs/comparison/                   # README 效果对比素材（非 MIT）
├── docs/examples/                     # 算法伪代码等额外示例
├── tools/                             # 开发工具：背景画廊（不随 skill 安装）
├── tests/                             # 单元 + 回归 + CLI + README 冒烟 + 打包校验
├── install.sh                         # 源码安装脚本（软链/复制到各 agent 目录）
└── .github/workflows/ci.yml
```

## 开发命令

```bash
pip install -r requirements-dev.txt
bash install.sh --dry-run                       # 检查安装目标路径
```

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q                      # 离线：单元 + 回归 + CLI + 打包校验
python -m pytest tests/test_readme_commands.py --net -q   # 联网冒烟（下载 arXiv PDF）
```

测试分层：

- `tests/test_unit.py`：caption 锚定（含章节编号、无交叉误配）、边界墨迹检测（含深色背景不误报）、错误路径；
- `tests/test_regression.py`：历史 bug 回归（图内图例 TXT 块被切、两脚本 figure_clip 行为一致性）；
- `tests/test_cli.py`：CLI 退出码、`--clip` 跳过 caption 查找、PNG 白边注入、check_border 目录扫描；
- `tests/test_background.py`：`--background auto/white/transparent`、深底保留、透明 SVG 的边界检测；
- `tests/test_gallery.py`：背景画廊生成与失败条目展示（`tools/background_gallery.py`）；
- `tests/test_readme_commands.py`：与 README 示例对应的命令（默认跳过，`--net` 开启）；
- `tests/test_packaging.py`：frontmatter 规范、三处版本号一致、marketplace 条目、`install.sh` 行为。

## 约定

- 技能本体只放在 `skills/pdf-figure-extract/`，不要在根目录再放一份 `SKILL.md`；
- `SKILL.md` 的 `name` 必须与所在目录同名（`pdf-figure-extract`），`description` 不超过 1024 字符；
- 版本号三处同步：`SKILL.md` 的 `metadata.version`、`plugin.json`、`.claude-plugin/plugin.json`；
- 脚本必须保持 harness 无关：只用 Python 标准库 + PyMuPDF / Pillow / numpy，不调用任何 Claude 专有 API；
- 脚本内的相对路径以技能目录为根，不写死本机绝对路径；
- 修改脚本或 CLI 行为后必须跑完整离线测试；
- 提交前确认 `git status` 里没有 `__pycache__`、`.pytest_cache` 等生成物。
