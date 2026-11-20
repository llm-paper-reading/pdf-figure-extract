#!/usr/bin/env bash
# pdf-figure-extract 安装脚本：把 skill 以软链接（或副本）方式装进各 agent 的 skills 目录。
#
#   ./install.sh                                   # Claude Code，用户级（~/.claude/skills）
#   ./install.sh -a codex                          # Codex，用户级（~/.agents/skills）
#   ./install.sh -a claude-code,codex              # 同时装给多个 agent
#   ./install.sh -p -a claude-code                 # 装到当前项目的 .claude/skills
#   ./install.sh -a codex --copy                   # 复制而不是软链接
#   ./install.sh --force                           # 覆盖已存在的目标
#   ./install.sh --list                            # 只列出 agent 与目标路径
set -euo pipefail

NAME="pdf-figure-extract"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$REPO_DIR/skills/$NAME"

AGENTS="claude-code"
SCOPE="global"
COPY=0
FORCE=0
DRY=0

usage() {
  cat <<'USAGE'
pdf-figure-extract 安装脚本：把 skill 以软链接（或副本）方式装进各 agent 的 skills 目录。

  ./install.sh                              Claude Code，用户级（~/.claude/skills）
  ./install.sh -a codex                     Codex，用户级（~/.agents/skills）
  ./install.sh -a claude-code,codex        同时装给多个 agent
  ./install.sh -p -a claude-code           装到当前项目的 .claude/skills
  ./install.sh -a codex --copy             复制而不是软链接
  ./install.sh --force                     覆盖已存在的目标
  ./install.sh --list                      列出 agent 与目标路径
USAGE
}

agent_dir() {
  case "$1" in
    claude|claude-code) echo ".claude/skills" ;;
    codex|cursor|cline|gemini|gemini-cli|windsurf|copilot|github-copilot|opencode|amp|antigravity|zed|warp|kimi-code-cli|devin) echo ".agents/skills" ;;
    *) return 1 ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    -a|--agent) AGENTS="${2:?--agent 需要一个值}"; shift 2 ;;
    -p|--project) SCOPE="project"; shift ;;
    -g|--global) SCOPE="global"; shift ;;
    --copy) COPY=1; shift ;;
    --force|-f) FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --list|-l)
      printf '%-16s %s\n' "claude-code" "~/.claude/skills (项目级 .claude/skills)"
      printf '%-16s %s\n' "codex" "~/.agents/skills (项目级 .agents/skills)"
      printf '%-16s %s\n' "cursor" "~/.agents/skills (项目级 .agents/skills)"
      printf '%-16s %s\n' "generic" "~/.agents/skills (项目级 .agents/skills)"
      exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：${1}（--help 查看用法）" >&2; exit 2 ;;
  esac
done

[ -f "$SKILL_DIR/SKILL.md" ] || { echo "找不到 $SKILL_DIR/SKILL.md，请在仓库内运行本脚本" >&2; exit 1; }

old_ifs="$IFS"; IFS=','; set -- $AGENTS; IFS="$old_ifs"

for agent in "$@"; do
  [ -n "$agent" ] || continue
  dir="$(agent_dir "$agent")" || { echo "不支持的 agent：${agent}（--list 查看）" >&2; exit 2; }
  if [ "$SCOPE" = "project" ]; then base="$PWD/$dir"; else base="$HOME/$dir"; fi
  target="$base/$NAME"
  if [ "$DRY" = 1 ]; then
    echo "[dry-run] $agent -> $target"
    continue
  fi
  mkdir -p "$base"
  if [ -e "$target" ] || [ -L "$target" ]; then
    if [ "$FORCE" != 1 ]; then
      echo "目标已存在：${target}（用 --force 覆盖）" >&2; exit 1
    fi
    rm -rf "$target"
  fi
  if [ "$COPY" = 1 ]; then cp -R "$SKILL_DIR" "$target"; else ln -s "$SKILL_DIR" "$target"; fi
  echo "已安装 $agent -> $target"
done

echo "完成。重启或新开 agent 会话后即可使用；对 agent 说「从论文抽取 Figure 2」触发。"
