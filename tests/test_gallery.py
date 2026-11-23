"""背景画廊工具：生成 HTML，并渲染白底/深底两版供人工检查。"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "background_gallery.py"


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which("rsvg-convert"), reason="needs rsvg-convert")
class TestGallery:
    def test_builds_cards_and_previews(self, simple_pdf, tmp_path):
        manifest = tmp_path / "manifest.txt"
        manifest.write_text(f"# sample\n{simple_pdf} 1 1\n")
        out = tmp_path / "gallery"
        r = run_tool(manifest, "--out", out, "--width", "600")
        assert r.returncode == 0, r.stdout + r.stderr
        page = (out / "gallery.html").read_text(encoding="utf-8")
        assert "background=white" in page
        card = next(p for p in out.iterdir() if p.is_dir())
        assert (card / "extracted.svg").is_file()
        assert (card / "on-white.png").is_file()
        assert (card / "on-dark.png").is_file()
        assert (card / "log.txt").is_file()

    def test_failed_entry_is_reported(self, simple_pdf, tmp_path):
        manifest = tmp_path / "manifest.txt"
        manifest.write_text(f"{simple_pdf} 1 2\n")  # 没有 Figure 2
        out = tmp_path / "gallery"
        r = run_tool(manifest, "--out", out, "--width", "600")
        assert r.returncode == 0
        assert "class=\"badge failed\"" in (out / "gallery.html").read_text(encoding="utf-8")
