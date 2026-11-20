"""打包与跨 harness 兼容性测试：清单、frontmatter、版本一致性、安装脚本。"""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "pdf-figure-extract"
SKILL_MD = SKILL_DIR / "SKILL.md"


def frontmatter(path=SKILL_MD):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md 缺少 frontmatter"
    end = text.index("\n---\n", 4)
    return text[4:end]


def field(name, fm=None):
    fm = frontmatter() if fm is None else fm
    m = re.search(rf"^{re.escape(name)}:\s*(.+)$", fm, re.M)
    assert m, f"frontmatter 缺少 {name}"
    return m.group(1).strip()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestSkillFrontmatter:
    def test_name_matches_directory(self):
        assert field("name") == SKILL_DIR.name

    def test_name_follows_spec(self):
        name = field("name")
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), name
        assert len(name) <= 64

    def test_description_within_limit(self):
        desc = field("description")
        assert 0 < len(desc) <= 1024

    def test_license_and_compatibility(self):
        assert field("license")
        compat = field("compatibility")
        assert 0 < len(compat) <= 500

    def test_version_is_semver(self):
        m = re.search(r'^\s+version:\s*"([^"]+)"', frontmatter(), re.M)
        assert m and re.fullmatch(r"\d+\.\d+\.\d+", m.group(1))

    def test_no_claude_only_variable(self):
        body = SKILL_MD.read_text(encoding="utf-8")
        assert "${CLAUDE_SKILL_DIR}" not in body, "技能正文不应依赖 Claude 专有变量"


class TestManifests:
    def test_portable_plugin_manifest(self):
        data = load(ROOT / "plugin.json")
        assert data["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        assert data["name"] == SKILL_DIR.name
        assert data["description"]
        assert data["license"] == "MIT"

    def test_claude_plugin_manifest(self):
        data = load(ROOT / ".claude-plugin" / "plugin.json")
        assert data["name"] == SKILL_DIR.name
        assert data["version"] == load(ROOT / "plugin.json")["version"]

    def test_marketplace_entry(self):
        data = load(ROOT / ".claude-plugin" / "marketplace.json")
        assert data["name"]
        assert data["owner"]["name"]
        entries = [p for p in data["plugins"] if p["name"] == SKILL_DIR.name]
        assert len(entries) == 1
        assert entries[0]["source"] == "./"

    def test_versions_consistent(self):
        fm = frontmatter()
        skill_version = re.search(r'^\s+version:\s*"([^"]+)"', fm, re.M).group(1)
        assert skill_version == load(ROOT / "plugin.json")["version"]
        assert skill_version == load(ROOT / ".claude-plugin" / "plugin.json")["version"]

    def test_codex_metadata(self):
        text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        assert "display_name" in text
        assert "short_description" in text


class TestInstallScript:
    def run(self, *args, cwd=ROOT):
        return subprocess.run(["bash", str(ROOT / "install.sh"), *args],
                              capture_output=True, text=True, cwd=str(cwd))

    def test_help(self):
        r = self.run("--help")
        assert r.returncode == 0
        assert "-a codex" in r.stdout

    def test_dry_run_lists_targets(self):
        r = self.run("--dry-run", "-a", "claude-code,codex")
        assert r.returncode == 0
        assert ".claude/skills/pdf-figure-extract" in r.stdout
        assert ".agents/skills/pdf-figure-extract" in r.stdout

    def test_project_copy_install(self, tmp_path):
        r = self.run("-p", "-a", "claude-code", "--copy", cwd=tmp_path)
        assert r.returncode == 0, r.stderr
        target = tmp_path / ".claude" / "skills" / "pdf-figure-extract"
        assert (target / "SKILL.md").is_file()
        assert (target / "scripts" / "extract_fig.py").is_file()

    def test_project_symlink_install(self, tmp_path):
        r = self.run("-p", "-a", "codex", cwd=tmp_path)
        assert r.returncode == 0, r.stderr
        target = tmp_path / ".agents" / "skills" / "pdf-figure-extract"
        assert target.is_symlink()
        assert (target / "SKILL.md").is_file()

    def test_refuses_overwrite_without_force(self, tmp_path):
        assert self.run("-p", "--copy", cwd=tmp_path).returncode == 0
        r = self.run("-p", "--copy", cwd=tmp_path)
        assert r.returncode == 1
        assert "--force" in r.stderr

    def test_unknown_agent_rejected(self):
        r = self.run("--dry-run", "-a", "no-such-agent")
        assert r.returncode == 2
