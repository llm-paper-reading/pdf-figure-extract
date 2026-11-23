"""背景画廊工具：生成 HTML，并直接嵌入 SVG 供 light/dark 页面预览。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "background_gallery.py"


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True, check=False)


class TestGallery:
    def test_builds_cards_and_previews(self, simple_pdf, tmp_path):
        manifest = tmp_path / "manifest.txt"
        manifest.write_text(f"# sample\n{simple_pdf} 1 1\n")
        out = tmp_path / "gallery"
        r = run_tool(manifest, "--out", out)
        assert r.returncode == 0, r.stdout + r.stderr
        page = (out / "gallery.html").read_text(encoding="utf-8")
        assert "background=white" in page
        assert 'class="controls"' in page
        assert 'data-theme="light"' in page
        assert 'data-fmt' not in page
        assert "图区尺寸" in page and "内嵌位图" in page
        assert "/extracted.svg" in page and "/extracted.png" in page and "/transparent.svg" in page
        assert "PDF 原图属性" in page
        assert "填充色" in page and "background=" in page and "dpi" in page
        card = next(p for p in out.iterdir() if p.is_dir())
        assert (card / "extracted.svg").is_file()
        assert (card / "transparent.svg").is_file()
        assert (card / "extracted.png").is_file()
        assert (card / "log-svg.txt").is_file()
        assert (card / "log-transparent.txt").is_file()
        assert (card / "log-png.txt").is_file()

    def test_failed_entry_is_reported(self, simple_pdf, tmp_path):
        manifest = tmp_path / "manifest.txt"
        manifest.write_text(f"{simple_pdf} 1 2\n")  # 没有 Figure 2
        out = tmp_path / "gallery"
        r = run_tool(manifest, "--out", out)
        assert r.returncode == 0
        assert "class=\"badge failed\"" in (out / "gallery.html").read_text(encoding="utf-8")
