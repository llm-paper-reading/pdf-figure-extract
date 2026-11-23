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
├── docs/comparison/                   # README 效果对比素材（CC BY-NC-SA，非 MIT）
├── docs/examples/                     # 算法伪代码等额外示例
├── tools/                             # 开发工具：背景画廊（不随 skill 安装）
├── tests/                             # 单元 + 回归 + CLI + README 冒烟 + 打包校验
├── install.sh                         # 源码安装脚本（软链/复制到各 agent 目录）
└── .github/workflows/ci.yml
```

## 开发命令

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q                      # 离线测试
python -m pytest tests/test_readme_commands.py --net -q   # 联网冒烟
bash install.sh --dry-run                       # 检查安装目标路径
```

## 约定

- 技能本体只放在 `skills/pdf-figure-extract/`，不要在根目录再放一份 `SKILL.md`；
- `SKILL.md` 的 `name` 必须与所在目录同名（`pdf-figure-extract`），`description` 不超过 1024 字符；
- 版本号三处同步：`SKILL.md` 的 `metadata.version`、`plugin.json`、`.claude-plugin/plugin.json`；
- 脚本必须保持 harness 无关：只用 Python 标准库 + PyMuPDF / Pillow / numpy，不调用任何 Claude 专有 API；
- 脚本内的相对路径以技能目录为根，不写死本机绝对路径；
- 修改脚本或 CLI 行为后必须跑完整离线测试；
- 提交前确认 `git status` 里没有 `__pycache__`、`.pytest_cache` 等生成物。
